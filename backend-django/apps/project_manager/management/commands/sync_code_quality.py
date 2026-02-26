from django.core.management.base import BaseCommand

from apps.project_manager.code_quality.code_quality_service import (
    refresh_all_projects_quality,
)


class Command(BaseCommand):
    help = "同步所有开启代码质量统计项目的代码质量数据"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting code quality synchronization..."))
        try:
            summary = refresh_all_projects_quality()
            total = int(summary.get("total", 0))
            success = int(summary.get("success", 0))
            failed = int(summary.get("failed", 0))

            self.stdout.write(
                self.style.SUCCESS(
                    f"Code quality sync finished: total={total}, success={success}, failed={failed}",
                )
            )

            failed_projects = summary.get("failed_projects") or []
            for item in failed_projects:
                self.stdout.write(
                    self.style.WARNING(
                        f"- [{item.get('project_name')}] {item.get('error')}",
                    )
                )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error syncing code quality: {exc}"))
