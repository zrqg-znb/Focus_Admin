from datetime import date, timedelta
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone
from ninja.errors import HttpError

from apps.integration_report import integration_service
from apps.code_scan.models import (
    ScanFinding,
    ScanProject,
    ScanResultDetail,
    ScanResultOccurrence,
    ScanTask,
)
from apps.code_scan.services import ScanService
from apps.integration_report.integration_api import create_config, history, update_config
from apps.integration_report.integration_email import CODE_COLUMNS
from apps.integration_report.integration_models import (
    IntegrationDtFuzzSnapshot,
    IntegrationMetricDefinition,
    IntegrationProjectConfig,
    IntegrationProjectMetricValue,
)
from apps.integration_report.integration_schema import ProjectConfigUpsertIn
from core.user.user_model import User


class IntegrationReportTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.user = User.objects.create(
            username="integration-report-tester",
            password="secret",
            name="Integration Report Tester",
            is_active=True,
        )

    def _create_scan_project(self, *, project_key: str = "scan-key") -> ScanProject:
        return ScanProject.objects.create(
            name="Code Scan Project",
            repo_url="https://example.com/code-scan.git",
            branch="main",
            project_key=project_key,
        )

    def _create_scan_task(
        self,
        scan_project: ScanProject,
        *,
        tool_name: str,
        sub_module: str = "",
        created_at=None,
    ) -> ScanTask:
        task = ScanTask.objects.create(
            project=scan_project,
            tool_name=tool_name,
            status="success",
            source="pipeline",
            sub_module=sub_module,
        )
        if created_at is not None:
            ScanTask.objects.filter(id=task.id).update(
                sys_create_datetime=created_at,
                sys_update_datetime=created_at,
            )
            task.refresh_from_db()
        return task

    def _create_scan_occurrence(
        self,
        task: ScanTask,
        *,
        index: int,
    ) -> ScanResultOccurrence:
        detail_payload = {
            "file_path": f"src/{task.tool_name}_{index}.cpp",
            "defect_type": "RaceCondition" if task.tool_name == "tsan" else "MemoryLeak",
            "severity": "High",
            "description": f"{task.tool_name} defect {index}",
            "help_info": "",
            "code_snippet": "",
        }
        fingerprint = ScanService.build_fingerprint(detail_payload)
        finding, _ = ScanFinding.objects.get_or_create(
            project=task.project,
            fingerprint=fingerprint,
            defaults={
                "first_seen_task": task,
                "last_seen_task": task,
                "first_seen_at": timezone.now(),
                "last_seen_at": timezone.now(),
            },
        )
        detail_hash = ScanService.build_detail_hash(detail_payload)
        detail, _ = ScanResultDetail.objects.get_or_create(
            content_hash=detail_hash,
            defaults=detail_payload,
        )
        return ScanResultOccurrence.objects.create(
            task=task,
            finding=finding,
            detail=detail,
            line_number=index,
            shield_status="Normal",
        )

    def test_config_supports_dt_bin_and_cooddy_check_task_ids(self):
        payload = ProjectConfigUpsertIn(
            project_id=None,
            name="Daily Integration",
            managers=[],
            enabled=True,
            code_check_task_id="codecheck-1",
            dt_bin_task_id="dt-bin-1",
            cooddy_check_task_id="cooddy-check-1",
            bin_scope_task_id="bin-scope-1",
            build_check_task_id="build-1",
            compile_check_task_id="compile-1",
            dt_project_id="dt-1",
            code_scan_project_key="",
            valgrind_sub_modules=[],
        )

        request = self.factory.post("/api/integration-report/configs")
        config_id = create_config(request, payload)

        config = IntegrationProjectConfig.objects.get(id=config_id)
        self.assertEqual(config.dt_bin_task_id, "dt-bin-1")
        self.assertEqual(config.cooddy_check_task_id, "cooddy-check-1")

        payload.dt_bin_task_id = "dt-bin-2"
        payload.cooddy_check_task_id = "cooddy-check-2"
        payload.name = "Daily Integration Updated"

        update_request = self.factory.put(f"/api/integration-report/configs/{config_id}")
        updated = update_config(update_request, config_id, payload)
        self.assertTrue(updated)

        config.refresh_from_db()
        self.assertEqual(config.name, "Daily Integration Updated")
        self.assertEqual(config.dt_bin_task_id, "dt-bin-2")
        self.assertEqual(config.cooddy_check_task_id, "cooddy-check-2")

        rows = integration_service.list_configs_with_latest(self.user)
        row = next(item for item in rows if item.id == str(config.id))
        self.assertEqual(row.dt_bin_task_id, "dt-bin-2")
        self.assertEqual(row.cooddy_check_task_id, "cooddy-check-2")

    def test_default_metric_definitions_include_new_metrics_and_labels(self):
        integration_service.ensure_default_metric_definitions()

        dt_bin = IntegrationMetricDefinition.objects.get(key="dt_bin_error_num")
        cooddy_check = IntegrationMetricDefinition.objects.get(key="cooddy_check_error_num")
        cooddy_scan = IntegrationMetricDefinition.objects.get(key="cooddy_error_num")

        self.assertEqual(dt_bin.name, "DT_Bin错误数")
        self.assertEqual(cooddy_check.name, "Cooddy Check错误数")
        self.assertEqual(cooddy_scan.name, "Cooddy问题数（代码扫描）")
        self.assertEqual(dt_bin.warn_operator, ">")
        self.assertEqual(dt_bin.warn_value, 0)
        self.assertEqual(cooddy_check.warn_operator, ">")
        self.assertEqual(cooddy_check.warn_value, 0)

        self.assertEqual(
            integration_service.CODE_KEYS[:6],
            [
                "codecheck_error_num",
                "dt_bin_error_num",
                "cooddy_check_error_num",
                "bin_scope_error_num",
                "build_check_error_num",
                "compile_error_num",
            ],
        )
        self.assertEqual(
            CODE_COLUMNS[:6],
            [
                ("codecheck_error_num", "CodeCheck 错误数"),
                ("dt_bin_error_num", "DT_Bin错误数"),
                ("cooddy_check_error_num", "Cooddy Check错误数"),
                ("bin_scope_error_num", "Bin Scope 错误数"),
                ("build_check_error_num", "Build 检测错误数"),
                ("compile_error_num", "Compile 错误数"),
            ],
        )
        self.assertIn(
            ("cooddy_error_num", "Cooddy问题数（代码扫描）"),
            CODE_COLUMNS,
        )

    def test_collect_daily_metrics_persists_new_metric_values(self):
        record_date = date(2026, 4, 23)
        config = IntegrationProjectConfig.objects.create(
            name="Collector Config",
            enabled=True,
            dt_bin_task_id="dt-bin-1",
            cooddy_check_task_id="cooddy-check-1",
        )

        fetch_payload = {
            "codecheck_error_num": (None, ""),
            "dt_bin_error_num": (3.0, "https://example.com/dt-bin"),
            "cooddy_check_error_num": (2.0, "https://example.com/cooddy-check"),
            "bin_scope_error_num": (None, ""),
            "build_check_error_num": (None, ""),
            "compile_error_num": (None, ""),
            "dt_pass_rate": (None, ""),
            "dt_pass_num": (None, ""),
            "dt_line_coverage": (None, ""),
            "dt_method_coverage": (None, ""),
        }

        with patch(
            "apps.integration_report.integration_service.IntegrationDataFetcher.fetch_metrics",
            return_value=fetch_payload,
        ):
            integration_service.collect_daily_metrics(
                record_date=record_date,
                config_ids=[str(config.id)],
            )

        dt_bin_value = IntegrationProjectMetricValue.objects.select_related("metric").get(
            config=config,
            record_date=record_date,
            metric__key="dt_bin_error_num",
        )
        cooddy_check_value = IntegrationProjectMetricValue.objects.select_related("metric").get(
            config=config,
            record_date=record_date,
            metric__key="cooddy_check_error_num",
        )

        self.assertEqual(dt_bin_value.value_number, 3.0)
        self.assertEqual(dt_bin_value.detail_url, "https://example.com/dt-bin")
        self.assertEqual(dt_bin_value.value_text, "")
        self.assertEqual(cooddy_check_value.value_number, 2.0)
        self.assertEqual(cooddy_check_value.detail_url, "https://example.com/cooddy-check")
        self.assertEqual(cooddy_check_value.value_text, "")

    def test_history_returns_placeholder_cells_for_unconfigured_new_metrics(self):
        record_date = date(2026, 4, 23)
        integration_service.ensure_default_metric_definitions()
        config = IntegrationProjectConfig.objects.create(
            name="History Config",
            enabled=True,
        )
        dt_metric = IntegrationMetricDefinition.objects.get(key="dt_pass_num")
        IntegrationProjectMetricValue.objects.create(
            config=config,
            record_date=record_date,
            metric=dt_metric,
            value_number=12,
            value_text="",
            detail_url="",
        )

        request = self.factory.get(
            "/api/integration-report/history",
            {"start": record_date.isoformat(), "end": record_date.isoformat()},
        )
        payload = history(request, start=record_date, end=record_date)

        self.assertEqual(len(payload.items), 1)
        row = payload.items[0]
        dt_bin_cell = next(cell for cell in row.code_metrics if cell.key == "dt_bin_error_num")
        cooddy_check_cell = next(
            cell for cell in row.code_metrics if cell.key == "cooddy_check_error_num"
        )

        self.assertIsNone(dt_bin_cell.value)
        self.assertIsNone(dt_bin_cell.text)
        self.assertIsNone(cooddy_check_cell.value)
        self.assertIsNone(cooddy_check_cell.text)

    def test_code_scan_metrics_fallback_to_unscoped_submodule_tasks(self):
        record_date = timezone.now().date()
        scan_project = self._create_scan_project(project_key="scan-key-fallback")
        config = IntegrationProjectConfig.objects.create(
            name="Code Scan Config",
            enabled=True,
            code_scan_project_key=scan_project.project_key,
            valgrind_sub_modules=["engine"],
        )
        valgrind_task = self._create_scan_task(scan_project, tool_name="valgrind")
        tsan_task = self._create_scan_task(scan_project, tool_name="tsan")
        self._create_scan_occurrence(valgrind_task, index=1)
        self._create_scan_occurrence(valgrind_task, index=2)
        self._create_scan_occurrence(tsan_task, index=3)

        payload = integration_service._fetch_code_scan_metrics(config, record_date)

        self.assertEqual(payload["valgrind_error_num"][0], 2.0)
        self.assertEqual(payload["tsan_error_num"][0], 1.0)
        self.assertIn("sub_modules=engine", payload["valgrind_error_num"][1])

    def test_config_supports_dt_fuzz_fields_and_normalizes_branches(self):
        payload = ProjectConfigUpsertIn(
            project_id=None,
            name="DT Fuzz Config",
            managers=[],
            enabled=True,
            enable_dt_fuzz=True,
            dt_fuzz_version_name="HarmonySpace 510 1.0.0",
            dt_fuzz_branches=["main", " main ", "release"],
            dt_fuzz_pbi_id="pbi-1",
            dt_fuzz_domain_id="domain-1",
            dt_fuzz_project_id="project-1",
        )

        request = self.factory.post("/api/integration-report/configs")
        config_id = create_config(request, payload)
        config = IntegrationProjectConfig.objects.get(id=config_id)

        self.assertTrue(config.enable_dt_fuzz)
        self.assertEqual(config.dt_fuzz_version_name, "HarmonySpace 510 1.0.0")
        self.assertEqual(config.dt_fuzz_branches, ["main", "release"])
        self.assertEqual(config.dt_fuzz_pbi_id, "pbi-1")
        self.assertEqual(config.dt_fuzz_domain_id, "domain-1")
        self.assertEqual(config.dt_fuzz_project_id, "project-1")

        rows = integration_service.list_configs_with_latest(self.user)
        row = next(item for item in rows if item.id == str(config.id))
        self.assertTrue(row.enable_dt_fuzz)
        self.assertEqual(row.dt_fuzz_branches, ["main", "release"])

    def test_enabled_dt_fuzz_requires_all_config_fields(self):
        payload = ProjectConfigUpsertIn(
            project_id=None,
            name="Invalid DT Fuzz Config",
            managers=[],
            enabled=True,
            enable_dt_fuzz=True,
            dt_fuzz_version_name="",
            dt_fuzz_branches=[],
            dt_fuzz_pbi_id="pbi-1",
            dt_fuzz_domain_id="domain-1",
            dt_fuzz_project_id="project-1",
        )

        request = self.factory.post("/api/integration-report/configs")
        with self.assertRaises(HttpError) as ctx:
            create_config(request, payload)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("versionName", str(ctx.exception))
        self.assertIn("branch", str(ctx.exception))

    def test_collect_daily_metrics_persists_dt_fuzz_snapshots_per_branch(self):
        record_date = date(2026, 6, 22)
        config = IntegrationProjectConfig.objects.create(
            name="DT Fuzz Collector",
            enabled=True,
            enable_dt_fuzz=True,
            dt_fuzz_version_name="HarmonySpace 510 1.0.0",
            dt_fuzz_branches=["main", "release"],
            dt_fuzz_pbi_id="pbi-1",
            dt_fuzz_domain_id="domain-1",
            dt_fuzz_project_id="project-1",
        )

        def fake_fetch(_fetcher, branch, due_date):
            return {
                "name": f"root-{branch}",
                "type": "version",
                "highRiskApiCover": "1",
                "highRiskApiTotal": "2",
                "highRiskApiCoverage": "50.00",
                "defectNumber": "3",
                "children": [],
                "reportUrl": f"https://example.com/{branch}/{due_date}",
            }

        with patch(
            "apps.integration_report.integration_service.IntegrationDataFetcher.fetch_dt_fuzz",
            fake_fetch,
        ):
            integration_service.collect_daily_metrics(
                record_date=record_date,
                config_ids=[str(config.id)],
            )

        snapshots = IntegrationDtFuzzSnapshot.objects.filter(
            config=config,
            record_date=record_date,
        ).order_by("branch")
        self.assertEqual(snapshots.count(), 2)
        self.assertEqual([item.branch for item in snapshots], ["main", "release"])
        self.assertEqual(snapshots[0].source_due_date, "2026-06-22 12:00:00")

    def test_collect_daily_metrics_falls_back_when_today_dt_fuzz_is_empty(self):
        record_date = date(2026, 6, 22)
        config = IntegrationProjectConfig.objects.create(
            name="DT Fuzz Fallback",
            enabled=True,
            enable_dt_fuzz=True,
            dt_fuzz_version_name="HarmonySpace 510 1.0.0",
            dt_fuzz_branches=["main"],
            dt_fuzz_pbi_id="pbi-1",
            dt_fuzz_domain_id="domain-1",
            dt_fuzz_project_id="project-1",
        )
        calls = []

        def fake_fetch(_fetcher, branch, due_date):
            calls.append((branch, due_date))
            if due_date == "2026-06-22 12:00:00":
                return {}
            return {"name": "fallback-root", "type": "version", "children": []}

        with patch(
            "apps.integration_report.integration_service.IntegrationDataFetcher.fetch_dt_fuzz",
            fake_fetch,
        ):
            integration_service.collect_daily_metrics(
                record_date=record_date,
                config_ids=[str(config.id)],
            )

        snapshot = IntegrationDtFuzzSnapshot.objects.get(config=config)
        self.assertEqual(
            calls,
            [
                ("main", "2026-06-22 12:00:00"),
                ("main", "2026-06-21 12:00:00"),
            ],
        )
        self.assertEqual(snapshot.source_due_date, "2026-06-21 12:00:00")
        self.assertEqual(snapshot.tree_payload["name"], "fallback-root")

    def test_history_returns_dt_fuzz_for_enabled_configs_only_and_filters_owner(self):
        record_date = date(2026, 6, 22)
        enabled_config = IntegrationProjectConfig.objects.create(
            name="Visible DT Fuzz",
            enabled=True,
            enable_dt_fuzz=True,
            dt_fuzz_version_name="HarmonySpace",
            dt_fuzz_branches=["main"],
            dt_fuzz_pbi_id="pbi-1",
            dt_fuzz_domain_id="domain-1",
            dt_fuzz_project_id="project-1",
        )
        enabled_config.managers.set([self.user])
        disabled_config = IntegrationProjectConfig.objects.create(
            name="Hidden DT Fuzz",
            enabled=True,
            enable_dt_fuzz=False,
        )
        IntegrationDtFuzzSnapshot.objects.create(
            config=enabled_config,
            record_date=record_date,
            branch="main",
            source_due_date="2026-06-22 12:00:00",
            tree_payload={
                "name": "HarmonySpace",
                "type": "version",
                "highRiskApiCover": "2469",
                "highRiskApiTotal": "7400",
                "highRiskApiCoverage": "33.36",
                "children": [{"name": "child", "type": "module", "children": []}],
            },
        )
        IntegrationDtFuzzSnapshot.objects.create(
            config=disabled_config,
            record_date=record_date,
            branch="main",
            source_due_date="2026-06-22 12:00:00",
            tree_payload={"name": "Hidden", "type": "version", "children": []},
        )

        request = self.factory.get(
            "/api/integration-report/history",
            {"start": record_date.isoformat(), "end": record_date.isoformat()},
        )
        payload = history(
            request,
            start=record_date,
            end=record_date,
            caretaker_keyword="Integration Report Tester",
        )

        self.assertEqual(len(payload.dt_fuzz_items), 1)
        item = payload.dt_fuzz_items[0]
        self.assertEqual(item.config_name, "Visible DT Fuzz")
        self.assertEqual(item.branch, "main")
        self.assertEqual(item.nodes[0].name, "HarmonySpace")
        self.assertEqual(item.nodes[0].children[0].name, "child")

    def test_code_scan_metrics_prefer_matching_submodule_tasks(self):
        record_date = timezone.now().date()
        base_time = timezone.now().replace(microsecond=0)
        scan_project = self._create_scan_project(project_key="scan-key-match")
        config = IntegrationProjectConfig.objects.create(
            name="Code Scan Config",
            enabled=True,
            code_scan_project_key=scan_project.project_key,
            valgrind_sub_modules=["engine"],
        )
        unscoped_task = self._create_scan_task(
            scan_project,
            tool_name="valgrind",
            created_at=base_time + timedelta(hours=2),
        )
        engine_task = self._create_scan_task(
            scan_project,
            tool_name="valgrind",
            sub_module="engine",
            created_at=base_time + timedelta(hours=1),
        )
        for index in range(3):
            self._create_scan_occurrence(unscoped_task, index=index + 1)
        self._create_scan_occurrence(engine_task, index=10)

        payload = integration_service._fetch_code_scan_metrics(config, record_date)

        self.assertEqual(payload["valgrind_error_num"][0], 1.0)

    def test_collect_daily_metrics_refreshes_code_scan_values(self):
        record_date = timezone.now().date()
        scan_project = self._create_scan_project(project_key="scan-key-refresh")
        config = IntegrationProjectConfig.objects.create(
            name="Code Scan Refresh Config",
            enabled=True,
            code_scan_project_key=scan_project.project_key,
            valgrind_sub_modules=["engine"],
        )
        valgrind_task = self._create_scan_task(
            scan_project,
            tool_name="valgrind",
            sub_module="engine",
        )
        tsan_task = self._create_scan_task(
            scan_project,
            tool_name="tsan",
            sub_module="engine",
        )
        self._create_scan_occurrence(valgrind_task, index=1)
        self._create_scan_occurrence(valgrind_task, index=2)
        self._create_scan_occurrence(tsan_task, index=3)

        integration_service.collect_daily_metrics(
            record_date=record_date,
            config_ids=[str(config.id)],
        )

        valgrind_value = IntegrationProjectMetricValue.objects.select_related("metric").get(
            config=config,
            record_date=record_date,
            metric__key="valgrind_error_num",
        )
        tsan_value = IntegrationProjectMetricValue.objects.select_related("metric").get(
            config=config,
            record_date=record_date,
            metric__key="tsan_error_num",
        )

        self.assertEqual(valgrind_value.value_number, 2.0)
        self.assertEqual(tsan_value.value_number, 1.0)
        self.assertIn("sub_modules=engine", valgrind_value.detail_url)
        self.assertIn("sub_modules=engine", tsan_value.detail_url)
