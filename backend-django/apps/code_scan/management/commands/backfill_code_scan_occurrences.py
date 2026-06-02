from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
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

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        batch_size = options["batch_size"]
        limit = options["limit"]
        dry_run = options["dry_run"]

        base_qs = ScanResult.objects.filter(
            is_deleted=False,
            normalized_occurrence__isnull=True,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        if project_id:
            base_qs = base_qs.filter(task__project_id=project_id)

        pending_count = base_qs.count()
        self.stdout.write(f"pending legacy scan_result rows: {pending_count}")
        if dry_run:
            return

        processed = 0
        while True:
            remaining = limit - processed if limit else batch_size
            if limit and remaining <= 0:
                break
            current_batch_size = min(batch_size, remaining) if limit else batch_size
            batch = list(
                base_qs.select_related("task", "task__project")
                .order_by("task__sys_create_datetime", "sys_create_datetime", "id")[
                    :current_batch_size
                ]
            )
            if not batch:
                break

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

        self.stdout.write(self.style.SUCCESS(f"backfill finished, processed={processed}"))
