import json
import os
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from apps.code_scan.models import ScanProject, ScanTask
from apps.code_scan.services import ScanService


class Command(BaseCommand):
    help = "Create a mock weggli scan task and parse results"

    def handle(self, *args, **options):
        project = ScanProject.objects.filter(is_deleted=False).order_by("-sys_create_datetime").first()
        if not project:
            self.stderr.write("No ScanProject found. Create one first.")
            return

        payload = {
            "results": [
                {
                    "file": "src/foo.c",
                    "line": 42,
                    "rule": "weggli-demo",
                    "message": "Potential unsafe function usage",
                    "severity": "high",
                    "snippet": "strcpy(buf, input);",
                },
                {
                    "file_path": "src/bar.c",
                    "line_number": 10,
                    "defect_type": "weggli-demo-2",
                    "description": "Hardcoded credentials pattern match",
                    "level": "medium",
                    "code_snippet": "const char* pwd = \"123456\";",
                },
            ]
        }

        file_name = f"scan_reports/{project.id}/mock_weggli.json"
        saved_path = default_storage.save(file_name, ContentFile(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")))
        full_path = os.path.join(settings.MEDIA_ROOT, saved_path)

        task = ScanTask.objects.create(
            project=project,
            tool_name="weggli",
            status="processing",
            source="manual",
            report_file=full_path,
        )
        ScanService.process_report(str(task.id))
        self.stdout.write(f"Mock weggli task created: {task.id}")

