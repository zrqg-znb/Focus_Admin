import hashlib
import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, close_old_connections

from apps.code_scan.models import ScanResult, ScanResultOccurrence
from apps.code_scan.services import ScanService


class Command(BaseCommand):
    help = "只读统计 code_scan 结果表重复度与规范化存储的预估瘦身收益"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", dest="project_id", help="仅统计指定扫描项目")
        parser.add_argument("--top", type=int, default=20, help="输出重复分组 Top N")
        parser.add_argument("--chunk-size", type=int, default=300, help="每次读取的 scan_result 行数")
        parser.add_argument("--limit", type=int, default=0, help="最多扫描多少行旧结果，0 表示不限")
        parser.add_argument("--max-retries", type=int, default=3, help="单批查询断线后的重试次数")
        parser.add_argument("--progress-every", type=int, default=10000, help="每扫描多少行输出一次进度")

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        top = options["top"]
        chunk_size = max(int(options["chunk_size"] or 300), 1)
        limit = max(int(options["limit"] or 0), 0)
        max_retries = max(int(options["max_retries"] or 0), 0)
        progress_every = max(int(options["progress_every"] or 0), 0)

        total_rows = 0
        scanned_rows = 0
        total_detail_chars = 0
        unique_detail_chars: dict[bytes, int] = {}
        finding_keys: set[bytes] = set()
        group_stats: dict[tuple[str, str, str], dict] = {}

        last_id = ""
        next_progress = progress_every
        while True:
            current_batch_size = chunk_size
            if limit:
                remaining = limit - scanned_rows
                if remaining <= 0:
                    break
                current_batch_size = min(current_batch_size, remaining)

            rows = self._fetch_legacy_batch(
                last_id=last_id,
                chunk_size=current_batch_size,
                project_id=project_id,
                max_retries=max_retries,
            )
            if not rows:
                break

            last_id = str(rows[-1]["id"])
            scanned_rows += len(rows)

            for row in rows:
                if self._is_inactive_row(row):
                    continue
                total_rows += 1

                project_key = str(row.get("task__project_id") or "")
                fingerprint = str(row.get("fingerprint") or "")
                finding_digest = self._digest(project_key, fingerprint)
                finding_keys.add(finding_digest)

                payload = ScanService._normalize_detail_payload(row)
                detail_digest = bytes.fromhex(ScanService.build_detail_hash(payload))
                detail_chars = sum(len(str(value or "")) for value in payload.values())
                total_detail_chars += detail_chars
                unique_detail_chars.setdefault(detail_digest, detail_chars)

                group_key = (
                    str(row.get("task__project__name") or project_key or "-"),
                    str(row.get("task__tool_name") or "-"),
                    str(row.get("task__sub_module") or "-"),
                )
                stats = group_stats.setdefault(
                    group_key,
                    {"total": 0, "fingerprints": set()},
                )
                stats["total"] += 1
                stats["fingerprints"].add(finding_digest)

            if progress_every and scanned_rows >= next_progress:
                self.stdout.write(
                    f"scanned={scanned_rows}, active_legacy_rows={total_rows}, "
                    f"distinct_findings={len(finding_keys)}, distinct_details={len(unique_detail_chars)}"
                )
                next_progress += progress_every

        occurrence_rows = self._scan_occurrence_count(
            project_id=project_id,
            chunk_size=chunk_size,
            max_retries=max_retries,
        )

        finding_count = len(finding_keys)
        unique_detail_count = len(unique_detail_chars)
        unique_detail_total_chars = sum(unique_detail_chars.values())
        duplicate_detail_chars = max(total_detail_chars - unique_detail_total_chars, 0)
        duplicate_detail_rate = (
            duplicate_detail_chars / total_detail_chars if total_detail_chars else 0
        )
        estimated_row_saving_rate = (
            1 - (unique_detail_count + finding_count + total_rows) / (total_rows * 3)
            if total_rows
            else 0
        )

        self.stdout.write("code_scan storage audit")
        self.stdout.write(f"- scanned scan_result rows: {scanned_rows}")
        self.stdout.write(f"- active legacy scan_result rows: {total_rows}")
        self.stdout.write(f"- normalized occurrence rows: {occurrence_rows}")
        self.stdout.write(f"- distinct project+fingerprint findings: {finding_count}")
        self.stdout.write(f"- distinct detail payloads: {unique_detail_count}")
        self.stdout.write(f"- duplicate detail chars: {duplicate_detail_chars}")
        self.stdout.write(f"- duplicate detail char rate: {duplicate_detail_rate:.2%}")
        self.stdout.write(f"- rough normalized row saving signal: {estimated_row_saving_rate:.2%}")

        self.stdout.write("")
        self.stdout.write(f"Top {top} duplicate groups by project/tool/sub_module:")
        grouped = sorted(
            group_stats.items(),
            key=lambda item: item[1]["total"],
            reverse=True,
        )[:top]
        for (project, tool, module), stats in grouped:
            total = int(stats["total"] or 0)
            fingerprints = len(stats["fingerprints"])
            duplicate_rows = max(total - fingerprints, 0)
            self.stdout.write(
                f"- {project} / {tool} / {module}: total={total}, "
                f"fingerprints={fingerprints}, duplicate_rows={duplicate_rows}"
            )

    def _fetch_legacy_batch(
        self,
        *,
        last_id: str,
        chunk_size: int,
        project_id: str | None,
        max_retries: int,
    ) -> list[dict]:
        qs = ScanResult.objects.all()
        if last_id:
            qs = qs.filter(id__gt=last_id)
        if project_id:
            qs = qs.filter(task__project_id=project_id)

        fields = [
            "id",
            "is_deleted",
            "task_id",
            "task__is_deleted",
            "task__project_id",
            "task__project__name",
            "task__project__is_deleted",
            "task__tool_name",
            "task__sub_module",
            "fingerprint",
            "file_path",
            "defect_type",
            "severity",
            "description",
            "help_info",
            "code_snippet",
        ]
        return self._retrying_values_query(
            qs.order_by("id").values(*fields)[:chunk_size],
            max_retries=max_retries,
            label="scan_result batch",
        )

    def _scan_occurrence_count(
        self,
        *,
        project_id: str | None,
        chunk_size: int,
        max_retries: int,
    ) -> int:
        total = 0
        last_id = 0
        while True:
            qs = ScanResultOccurrence.objects.all()
            if last_id:
                qs = qs.filter(id__gt=last_id)
            if project_id:
                qs = qs.filter(task__project_id=project_id)
            rows = self._retrying_values_query(
                qs.order_by("id").values(
                    "id",
                    "is_deleted",
                    "task__is_deleted",
                    "task__project__is_deleted",
                )[:chunk_size],
                max_retries=max_retries,
                label="scan_result_occurrence batch",
            )
            if not rows:
                break
            last_id = int(rows[-1]["id"])
            for row in rows:
                if self._is_inactive_row(row):
                    continue
                total += 1
        return total

    def _retrying_values_query(self, qs, *, max_retries: int, label: str) -> list[dict]:
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
                    f"{label} failed with OperationalError, retry "
                    f"{attempt + 1}/{max_retries} after {sleep_seconds}s: {exc}"
                )
                time.sleep(sleep_seconds)
        return []

    @staticmethod
    def _is_inactive_row(row: dict) -> bool:
        return bool(
            row.get("is_deleted")
            or row.get("task__is_deleted")
            or row.get("task__project__is_deleted")
        )

    @staticmethod
    def _digest(*parts: str) -> bytes:
        digest = hashlib.blake2b(digest_size=16)
        for part in parts:
            digest.update(str(part or "").encode("utf-8"))
            digest.update(b"\x00")
        return digest.digest()
