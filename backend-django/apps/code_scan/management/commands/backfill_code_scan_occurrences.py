from collections import defaultdict
import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, close_old_connections, connections, transaction
from django.utils import timezone

from apps.code_scan.models import ScanResult, ScanResultOccurrence, ScanTask, ShieldApplication
from apps.code_scan.services import ScanService


class Command(BaseCommand):
    help = "将旧 scan_result 数据批量回填到 scan_finding/detail/occurrence，旧数据保留不删除"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", dest="project_id", help="仅回填指定扫描项目")
        parser.add_argument("--batch-size", type=int, default=1000, help="每批处理的旧结果行数")
        parser.add_argument(
            "--detail-batch-size",
            type=int,
            default=0,
            help="每次读取带大文本字段并写入 occurrence 的行数，默认 min(batch-size, 50)",
        )
        parser.add_argument("--limit", type=int, default=0, help="最多处理多少行，0 表示不限")
        parser.add_argument("--dry-run", action="store_true", help="只统计待回填数量，不写入")
        parser.add_argument("--max-retries", type=int, default=3, help="单批查询断线后的重试次数")
        parser.add_argument(
            "--scan-window-size",
            type=int,
            default=0,
            help="每轮从 scan_result 主表预扫描的候选行数，默认 batch-size 的 10 倍",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        batch_size = max(int(options["batch_size"] or 1000), 1)
        detail_batch_size = int(options["detail_batch_size"] or 0)
        if detail_batch_size <= 0:
            detail_batch_size = min(batch_size, 50)
        detail_batch_size = max(min(detail_batch_size, batch_size), 1)
        limit = options["limit"]
        dry_run = options["dry_run"]
        max_retries = max(int(options["max_retries"] or 0), 0)
        scan_window_size = int(options["scan_window_size"] or 0)
        if scan_window_size <= 0:
            scan_window_size = max(batch_size * 10, batch_size)

        active_project_task_ids = self._load_project_task_ids(
            project_id,
            max_retries=max_retries,
        ) if project_id else None
        processed = 0
        scanned = 0
        last_id = ""
        while True:
            remaining = limit - processed if limit else batch_size
            if limit and remaining <= 0:
                break
            candidate_rows = self._fetch_candidate_rows(
                last_id=last_id,
                window_size=scan_window_size,
                max_retries=max_retries,
            )
            if not candidate_rows:
                break
            scanned += len(candidate_rows)
            last_id = str(candidate_rows[-1]["id"])

            active_task_map = self._load_active_task_map(
                [str(row["task_id"]) for row in candidate_rows if row.get("task_id")],
                active_project_task_ids=active_project_task_ids,
                max_retries=max_retries,
            )
            active_candidate_ids = [
                str(row["id"])
                for row in candidate_rows
                if not row.get("is_deleted") and str(row.get("task_id") or "") in active_task_map
            ]
            if not active_candidate_ids:
                self.stdout.write(f"scanned candidate rows: {scanned}, no active rows in window")
                continue

            existing_legacy_ids = self._fetch_existing_occurrence_legacy_ids(
                active_candidate_ids,
                max_retries=max_retries,
            )
            missing_ids = [
                result_id
                for result_id in active_candidate_ids
                if result_id not in existing_legacy_ids
            ]
            if limit:
                missing_ids = missing_ids[: max(limit - processed, 0)]
            missing_ids = missing_ids[:batch_size]
            if not missing_ids:
                self.stdout.write(
                    f"scanned candidate rows: {scanned}, no pending rows in window"
                )
                continue

            for start in range(0, len(missing_ids), detail_batch_size):
                chunk_ids = missing_ids[start:start + detail_batch_size]
                batch = self._fetch_result_batch(
                    chunk_ids,
                    max_retries=max_retries,
                )
                if not batch:
                    continue

                if dry_run:
                    processed += len(batch)
                    self.stdout.write(
                        f"would process legacy rows: {processed}, scanned candidate rows: {scanned}"
                    )
                    connections.close_all()
                    continue

                self._persist_result_batch(batch, max_retries=max_retries)
                processed += len(batch)
                self.stdout.write(
                    f"processed legacy rows: {processed}, scanned candidate rows: {scanned}"
                )
                connections.close_all()

        action = "dry-run finished" if dry_run else "backfill finished"
        self.stdout.write(self.style.SUCCESS(f"{action}, processed={processed}"))

    def _fetch_candidate_rows(
        self,
        *,
        last_id: str,
        window_size: int,
        max_retries: int,
    ) -> list[dict]:
        qs = ScanResult.objects.all()
        if last_id:
            qs = qs.filter(id__gt=last_id)
        qs = qs.order_by("id").values("id", "is_deleted", "task_id")[:window_size]
        return self._retrying_query(qs, max_retries=max_retries, label="scan_result candidate window")

    def _load_project_task_ids(
        self,
        project_id: str,
        *,
        max_retries: int,
    ) -> set[str]:
        qs = ScanTask.objects.filter(
            project_id=project_id,
            is_deleted=False,
            project__is_deleted=False,
        ).values_list("id", flat=True)
        return {
            str(task_id)
            for task_id in self._retrying_query(
                qs,
                max_retries=max_retries,
                label="project task id load",
            )
        }

    def _load_active_task_map(
        self,
        task_ids: list[str],
        *,
        active_project_task_ids: set[str] | None,
        max_retries: int,
    ) -> dict[str, ScanTask]:
        normalized_task_ids = list(dict.fromkeys(task_ids))
        if active_project_task_ids is not None:
            normalized_task_ids = [
                task_id for task_id in normalized_task_ids if task_id in active_project_task_ids
            ]
        if not normalized_task_ids:
            return {}
        qs = ScanTask.objects.select_related("project").filter(
            id__in=normalized_task_ids,
            is_deleted=False,
            project__is_deleted=False,
        )
        tasks = self._retrying_query(qs, max_retries=max_retries, label="active task map load")
        return {str(task.id): task for task in tasks}

    def _fetch_existing_occurrence_legacy_ids(
        self,
        result_ids: list[str],
        *,
        max_retries: int,
    ) -> set[str]:
        if not result_ids:
            return set()
        qs = ScanResultOccurrence.objects.filter(
            legacy_result_id__in=result_ids,
        ).values_list("legacy_result_id", flat=True)
        return {
            str(result_id)
            for result_id in self._retrying_query(
                qs,
                max_retries=max_retries,
                label="existing occurrence lookup",
            )
        }

    def _fetch_result_batch(
        self,
        result_ids: list[str],
        *,
        max_retries: int,
    ) -> list[ScanResult]:
        if not result_ids:
            return []
        qs = ScanResult.objects.select_related("task", "task__project").filter(
            id__in=result_ids,
        )
        result_by_id = {
            str(result.id): result
            for result in self._retrying_query(
                qs,
                max_retries=max_retries,
                label="scan_result detail batch",
            )
        }
        return [result_by_id[result_id] for result_id in result_ids if result_id in result_by_id]

    def _persist_result_batch(
        self,
        batch: list[ScanResult],
        *,
        max_retries: int,
    ) -> None:
        for attempt in range(max_retries + 1):
            try:
                close_old_connections()
                with transaction.atomic():
                    self._persist_result_batch_once(batch)
                return
            except OperationalError as exc:
                connections.close_all()
                if attempt >= max_retries:
                    raise
                sleep_seconds = min(2 ** attempt, 8)
                self.stderr.write(
                    f"scan_result write batch failed, retry "
                    f"{attempt + 1}/{max_retries} after {sleep_seconds}s: {exc}"
                )
                time.sleep(sleep_seconds)
        return None

    def _persist_result_batch_once(self, batch: list[ScanResult]) -> None:
        grouped_results: dict[str, list[ScanResult]] = defaultdict(list)
        task_by_id = {}
        for result in batch:
            task_id = str(result.task_id)
            grouped_results[task_id].append(result)
            task_by_id[task_id] = result.task

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

    def _retrying_query(self, qs, *, max_retries: int, label: str):
        for attempt in range(max_retries + 1):
            try:
                close_old_connections()
                return list(qs)
            except OperationalError as exc:
                connections.close_all()
                if attempt >= max_retries:
                    raise
                sleep_seconds = min(2 ** attempt, 8)
                self.stderr.write(
                    f"{label} failed, retry "
                    f"{attempt + 1}/{max_retries} after {sleep_seconds}s: {exc}"
                )
                time.sleep(sleep_seconds)
        return []
