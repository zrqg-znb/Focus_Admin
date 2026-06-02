from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.code_scan.models import ScanResult, ScanResultOccurrence
from apps.code_scan.services import ScanService


class Command(BaseCommand):
    help = "只读统计 code_scan 结果表重复度与规范化存储的预估瘦身收益"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", dest="project_id", help="仅统计指定扫描项目")
        parser.add_argument("--top", type=int, default=20, help="输出重复分组 Top N")
        parser.add_argument("--chunk-size", type=int, default=2000, help="扫描旧结果的批大小")

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        top = options["top"]
        chunk_size = options["chunk_size"]

        legacy_qs = ScanResult.objects.filter(
            is_deleted=False,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        occurrence_qs = ScanResultOccurrence.objects.filter(
            is_deleted=False,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        if project_id:
            legacy_qs = legacy_qs.filter(task__project_id=project_id)
            occurrence_qs = occurrence_qs.filter(task__project_id=project_id)

        total_rows = legacy_qs.count()
        occurrence_rows = occurrence_qs.count()
        finding_count = legacy_qs.values("task__project_id", "fingerprint").distinct().count()

        total_detail_chars = 0
        unique_detail_chars: dict[str, int] = {}
        for row in legacy_qs.values(
            "file_path",
            "defect_type",
            "severity",
            "description",
            "help_info",
            "code_snippet",
        ).iterator(chunk_size=chunk_size):
            payload = ScanService._normalize_detail_payload(row)
            content_hash = ScanService.build_detail_hash(payload)
            detail_chars = sum(len(str(value or "")) for value in payload.values())
            total_detail_chars += detail_chars
            unique_detail_chars.setdefault(content_hash, detail_chars)

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
        self.stdout.write(f"- legacy scan_result rows: {total_rows}")
        self.stdout.write(f"- normalized occurrence rows: {occurrence_rows}")
        self.stdout.write(f"- distinct project+fingerprint findings: {finding_count}")
        self.stdout.write(f"- distinct detail payloads: {unique_detail_count}")
        self.stdout.write(f"- duplicate detail chars: {duplicate_detail_chars}")
        self.stdout.write(f"- duplicate detail char rate: {duplicate_detail_rate:.2%}")
        self.stdout.write(f"- rough normalized row saving signal: {estimated_row_saving_rate:.2%}")

        self.stdout.write("")
        self.stdout.write(f"Top {top} duplicate groups by project/tool/sub_module:")
        grouped = (
            legacy_qs.values(
                "task__project__name",
                "task__tool_name",
                "task__sub_module",
            )
            .annotate(total=Count("id"), fingerprints=Count("fingerprint", distinct=True))
            .order_by("-total")[:top]
        )
        for item in grouped:
            total = int(item["total"] or 0)
            fingerprints = int(item["fingerprints"] or 0)
            duplicate_rows = max(total - fingerprints, 0)
            self.stdout.write(
                "- {project} / {tool} / {module}: total={total}, "
                "fingerprints={fingerprints}, duplicate_rows={duplicate_rows}".format(
                    project=item["task__project__name"] or "-",
                    tool=item["task__tool_name"] or "-",
                    module=item["task__sub_module"] or "-",
                    total=total,
                    fingerprints=fingerprints,
                    duplicate_rows=duplicate_rows,
                )
            )
