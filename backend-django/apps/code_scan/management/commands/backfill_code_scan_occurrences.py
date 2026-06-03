from collections import defaultdict
import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, close_old_connections, transaction
from django.utils import timezone

from apps.code_scan.models import ScanResult, ScanResultOccurrence, ShieldApplication
from apps.code_scan.services import ScanService


class Command(BaseCommand):
    help = "将旧 scan_result 数据批量回填到 scan_finding/detail/occurrence，旧数据保留不删除"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", dest="project_id", help="仅回填指定扫描项目")
        parser.add_argument("--batch-size", type=int, default=1000, help="每批处理的旧结果行数")
        parser.add_argument("--limit", type=int, default=0, help="最多处理多少行，0 表示不限")
        parser.add_argument("--dry-run", action="store_true", help="只统计待回填数量，不写入")
        parser.add_argument("--max-retries", type=int, default=3, help="单批查询断线后的重试次数")

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        batch_size = options["batch_size"]
        limit = options["limit"]
        dry_run = options["dry_run"]
        max_retries = max(int(options["max_retries"] or 0), 0)

        base_qs = ScanResult.objects.filter(
            is_deleted=False,
            normalized_occurrence__isnull=True,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        if project_id:
            base_qs = base_qs.filter(task__project_id=project_id)

        processed = 0
        last_id = ""
        while True:
            remaining = limit - processed if limit else batch_size
            if limit and remaining <= 0:
                break
            current_batch_size = min(batch_size, remaining) if limit else batch_size
            current_qs = base_qs
            if last_id:
                current_qs = current_qs.filter(id__gt=last_id)
            batch = self._fetch_batch(
                current_qs.select_related("task", "task__project").order_by("id")[
                    :current_batch_size
                ],
                max_retries=max_retries,
            )
            if not batch:
                break
            last_id = str(batch[-1].id)

            if dry_run:
                processed += len(batch)
                self.stdout.write(f"would process legacy rows: {processed}")
                continue

            grouped_results: dict[str, list[ScanResult]] = defaultdict(list)
            task_by_id = {}
            for result in batch:
                task_id = str(result.task_id)
                grouped_results[task_id].append(result)
                task_by_id[task_id] = result.task

            with transaction.atomic():
                for task_id, results in grouped_results.items():
                    defects = [
                        {
                            "file_path": result.file_path,
                            "line_number": result.line_number,
                            "defect_type": result.defect_type,
                            "severity": result.severity,
                            "description": result.description,
                            "help_info": result.help_info,
                            "code_snippet": result.code_snippet,
                        }
                        for result in results
                    ]
                    ScanService.persist_normalized_results(
                        task_by_id[task_id],
                        defects,
                        legacy_results=results,
                    )

                occurrence_map = {
                    str(item.legacy_result_id): item.id
                    for item in ScanResultOccurrence.objects.filter(
                        legacy_result_id__in=[result.id for result in batch],
                    )
                }
                applications = list(
                    ShieldApplication.objects.filter(
                        result_id__in=occurrence_map.keys(),
                        occurrence__isnull=True,
                    )
                )
                update_time = timezone.now()
                for app in applications:
                    app.occurrence_id = occurrence_map.get(str(app.result_id))
                    app.sys_update_datetime = update_time
                if applications:
                    ShieldApplication.objects.bulk_update(
                        applications,
                        ["occurrence", "sys_update_datetime"],
                    )

            processed += len(batch)
            self.stdout.write(f"processed legacy rows: {processed}")

        action = "dry-run finished" if dry_run else "backfill finished"
        self.stdout.write(self.style.SUCCESS(f"{action}, processed={processed}"))

    def _fetch_batch(self, qs, *, max_retries: int) -> list[ScanResult]:
        for attempt in range(max_retries + 1):
            try:
                close_old_connections()
                return list(qs)
            except OperationalError as exc:
                close_old_connections()
                if attempt >= max_retries:
                    raise
                sleep_seconds = min(2 ** attempt, 8)
                self.stderr.write(
                    f"scan_result backfill batch failed, retry "
                    f"{attempt + 1}/{max_retries} after {sleep_seconds}s: {exc}"
                )
                time.sleep(sleep_seconds)
        return []
