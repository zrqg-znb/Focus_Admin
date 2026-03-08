import json
from typing import List

from django.core.management.base import BaseCommand

from apps.code_scan.models import ScanProject, ScanResult, ScanTask
from apps.code_scan.services import ScanService
from core.user.user_model import User


class MockFile:
    def __init__(self, name: str, content: str):
        self.name = name
        self._content = content.encode("utf-8")

    def read(self):
        return self._content


class Command(BaseCommand):
    help = "Upload mock scan reports for multiple sub-modules and print aggregation check"

    def add_arguments(self, parser):
        parser.add_argument("--project-key", type=str, default="")
        parser.add_argument("--tool", type=str, default="cppcheck")
        parser.add_argument("--modules", type=str, default="core,ui")
        parser.add_argument("--uploads-per-module", type=int, default=2)

    def _ensure_project(self, project_key: str) -> ScanProject | None:
        if project_key:
            return ScanProject.objects.filter(
                is_deleted=False,
                project_key=project_key.strip(),
            ).first()

        project = ScanProject.objects.filter(is_deleted=False).order_by("-sys_create_datetime").first()
        if project:
            return project

        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not user:
            return None

        return ScanProject.objects.create(
            name="Mock Submodule Scan Project",
            repo_url="https://github.com/example/mock-submodule-project",
            branch="main",
            description="Mock project for sub-module upload tests",
            sys_creator=user,
        )

    def _build_cppcheck_xml(self, module_name: str, upload_index: int) -> str:
        line_base = 10 + upload_index * 10
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<results version="2">
  <cppcheck version="2.10"/>
  <errors>
    <error id="memleak" severity="error" msg="Memory leak in {module_name} u{upload_index}" file="src/{module_name}/a.cpp" line="{line_base}">
      <location file="src/{module_name}/a.cpp" line="{line_base}" column="1"/>
    </error>
    <error id="nullPointer" severity="error" msg="Null pointer in {module_name} u{upload_index}" file="src/{module_name}/b.cpp" line="{line_base + 1}">
      <location file="src/{module_name}/b.cpp" line="{line_base + 1}" column="1"/>
    </error>
  </errors>
</results>
"""

    def _build_valgrind_json(self, module_name: str, upload_index: int) -> str:
        line_base = 100 + upload_index * 10
        payload = [
            {
                "file_path": f"src/{module_name}/vg_a.cpp",
                "line_number": line_base,
                "defect_type": "invalid_read",
                "severity": "High",
                "description": f"Invalid read in {module_name} u{upload_index}",
            },
            {
                "file_path": f"src/{module_name}/vg_b.cpp",
                "line_number": line_base + 1,
                "defect_type": "possibly_lost",
                "severity": "Medium",
                "description": f"Possible leak in {module_name} u{upload_index}",
            },
        ]
        return json.dumps(payload, ensure_ascii=False)

    def _build_tsan_json(self, module_name: str, upload_index: int) -> str:
        line_base = 300 + upload_index * 10
        payload = [
            {
                "file_path": f"src/{module_name}/tsan_a.cpp",
                "line_number": line_base,
                "defect_type": "data_race",
                "severity": "High",
                "description": f"TSan data race in {module_name} u{upload_index}",
            },
            {
                "file_path": f"src/{module_name}/tsan_b.cpp",
                "line_number": line_base + 1,
                "defect_type": "lock_order",
                "severity": "High",
                "description": f"TSan lock order in {module_name} u{upload_index}",
            },
        ]
        return json.dumps(payload, ensure_ascii=False)

    def _build_mock_file(self, tool: str, module_name: str, upload_index: int) -> MockFile:
        normalized_tool = (tool or "").strip().lower()
        if normalized_tool == "valgrind":
            content = self._build_valgrind_json(module_name, upload_index)
            return MockFile(f"mock_{normalized_tool}_{module_name}_{upload_index}.json", content)
        if normalized_tool == "tsan":
            content = self._build_tsan_json(module_name, upload_index)
            return MockFile(f"mock_{normalized_tool}_{module_name}_{upload_index}.json", content)
        content = self._build_cppcheck_xml(module_name, upload_index)
        return MockFile(f"mock_{normalized_tool}_{module_name}_{upload_index}.xml", content)

    def _normalize_modules(self, raw_modules: str) -> List[str]:
        values = [x.strip() for x in (raw_modules or "").split(",")]
        return [x for x in values if x]

    def handle(self, *args, **options):
        project = self._ensure_project(options.get("project_key") or "")
        if not project:
            self.stderr.write(self.style.ERROR("No project/user found for mock upload."))
            return

        tool = (options.get("tool") or "cppcheck").strip().lower()
        modules = self._normalize_modules(options.get("modules") or "")
        uploads_per_module = max(int(options.get("uploads_per_module") or 1), 1)
        if not modules:
            self.stderr.write(self.style.ERROR("No valid modules provided."))
            return

        self.stdout.write(f"project={project.name} project_key={project.project_key} tool={tool}")
        created_tasks: List[str] = []
        for module_name in modules:
            for upload_index in range(1, uploads_per_module + 1):
                mock_file = self._build_mock_file(tool, module_name, upload_index)
                task = ScanService.handle_upload(
                    project_key=str(project.project_key),
                    tool_name=tool,
                    file_obj=mock_file,
                    sub_module=module_name,
                )
                created_tasks.append(str(task.id))
                self.stdout.write(
                    f"uploaded module={module_name} upload_index={upload_index} task={task.id} status={task.status}",
                )

        tasks = (
            ScanTask.objects.filter(
                is_deleted=False,
                project=project,
                tool_name=tool,
                status="success",
            )
            .exclude(sub_module="")
            .order_by("-sys_create_datetime")
            .values("id", "sub_module")
        )
        latest_task_by_module = {}
        module_set = {m.lower() for m in modules}
        for item in tasks:
            sub_module = str(item.get("sub_module") or "").strip()
            if not sub_module:
                continue
            lowered = sub_module.lower()
            if lowered not in module_set or lowered in latest_task_by_module:
                continue
            latest_task_by_module[lowered] = str(item["id"])
            if len(latest_task_by_module) == len(module_set):
                break

        task_ids = list(latest_task_by_module.values())
        result_count = ScanResult.objects.filter(task_id__in=task_ids, is_deleted=False).count() if task_ids else 0
        self.stdout.write(f"latest_task_by_module={latest_task_by_module}")
        self.stdout.write(self.style.SUCCESS(f"aggregated_results={result_count} selected_tasks={task_ids}"))
