from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from apps.code_scan.models import ScanResult, ScanResultOccurrence, ShieldApplication


class Command(BaseCommand):
    help = "校验旧 scan_result 与规范化 occurrence 的回填一致性"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", dest="project_id", help="仅校验指定扫描项目")
        parser.add_argument("--strict", action="store_true", help="发现不一致时返回失败")
        parser.add_argument("--top", type=int, default=20, help="输出任务级不一致 Top N")

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        strict = options["strict"]
        top = options["top"]

        legacy_qs = ScanResult.objects.filter(
            is_deleted=False,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        occurrence_qs = ScanResultOccurrence.objects.filter(
            is_deleted=False,
            legacy_result__isnull=False,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        if project_id:
            legacy_qs = legacy_qs.filter(task__project_id=project_id)
            occurrence_qs = occurrence_qs.filter(task__project_id=project_id)

        legacy_total = legacy_qs.count()
        occurrence_total = occurrence_qs.count()
        missing_legacy_count = legacy_qs.filter(normalized_occurrence__isnull=True).count()
        duplicate_occurrence_count = (
            occurrence_qs.values("legacy_result_id")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .count()
        )

        legacy_non_shielded = legacy_qs.exclude(shield_status="Shielded").count()
        occurrence_non_shielded = occurrence_qs.exclude(shield_status="Shielded").count()

        legacy_by_task = {
            str(row["task_id"]): int(row["cnt"])
            for row in legacy_qs.values("task_id").annotate(cnt=Count("id"))
        }
        occurrence_by_task = {
            str(row["task_id"]): int(row["cnt"])
            for row in occurrence_qs.values("task_id").annotate(cnt=Count("id"))
        }
        mismatched_tasks = []
        for task_id in sorted(set(legacy_by_task) | set(occurrence_by_task)):
            legacy_count = legacy_by_task.get(task_id, 0)
            occurrence_count = occurrence_by_task.get(task_id, 0)
            if legacy_count != occurrence_count:
                mismatched_tasks.append((task_id, legacy_count, occurrence_count))

        app_qs = ShieldApplication.objects.filter(
            is_deleted=False,
            result__isnull=False,
            result__task__is_deleted=False,
            result__task__project__is_deleted=False,
            result__normalized_occurrence__isnull=False,
            occurrence__isnull=True,
        )
        if project_id:
            app_qs = app_qs.filter(result__task__project_id=project_id)
        missing_app_links = app_qs.count()

        self.stdout.write("code_scan occurrence parity")
        self.stdout.write(f"- legacy rows: {legacy_total}")
        self.stdout.write(f"- occurrence rows mapped to legacy: {occurrence_total}")
        self.stdout.write(f"- legacy rows missing occurrence: {missing_legacy_count}")
        self.stdout.write(f"- duplicated occurrence legacy mappings: {duplicate_occurrence_count}")
        self.stdout.write(f"- legacy non-shielded rows: {legacy_non_shielded}")
        self.stdout.write(f"- occurrence non-shielded rows: {occurrence_non_shielded}")
        self.stdout.write(f"- shield applications missing occurrence link: {missing_app_links}")
        self.stdout.write(f"- mismatched task count: {len(mismatched_tasks)}")

        for task_id, legacy_count, occurrence_count in mismatched_tasks[:top]:
            self.stdout.write(
                f"  task={task_id}: legacy={legacy_count}, occurrence={occurrence_count}"
            )

        failed = any(
            [
                legacy_total != occurrence_total,
                missing_legacy_count,
                duplicate_occurrence_count,
                legacy_non_shielded != occurrence_non_shielded,
                missing_app_links,
                mismatched_tasks,
            ]
        )
        if failed and strict:
            raise CommandError("code_scan occurrence parity check failed")
        if failed:
            self.stdout.write(self.style.WARNING("parity check found differences"))
        else:
            self.stdout.write(self.style.SUCCESS("parity check passed"))
