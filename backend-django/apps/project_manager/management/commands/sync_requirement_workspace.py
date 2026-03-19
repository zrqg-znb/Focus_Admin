from django.core.management.base import BaseCommand

from apps.project_manager.requirement_workspace import requirement_workspace_services


class Command(BaseCommand):
    help = "生成工作台需求交付合规快照"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting requirement workspace snapshot refresh..."))
        try:
            snapshot = requirement_workspace_services.refresh_requirement_workspace_snapshot()
            self.stdout.write(
                self.style.SUCCESS(
                    "Requirement workspace snapshot finished: "
                    f"scope={snapshot.get('scope')}, "
                    f"projects={snapshot.get('project_count')}, "
                    f"requirements={snapshot.get('requirement_count')}, "
                    f"generated_at={snapshot.get('generated_at')}"
                )
            )
        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(f"Error refreshing requirement workspace snapshot: {exc}")
            )
