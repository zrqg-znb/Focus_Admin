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
from apps.integration_report.integration_fetcher import IntegrationDataFetcher
from apps.integration_report.integration_models import (
    IntegrationDomainDirectoryRule,
    IntegrationDomainDirectorySet,
    IntegrationDtFuzzSnapshot,
    IntegrationEmailSubscription,
    IntegrationMetricDefinition,
    IntegrationProjectConfig,
    IntegrationProjectMetricValue,
)
from apps.integration_report.integration_schema import DomainDirectorySetUpsertIn, ProjectConfigUpsertIn
from apps.integration_report.integration_schema import (
    DomainDirectoryRuleIn,
    SubscriptionManagementProjectQueryIn,
    SubscriptionSubscriberQueryIn,
)
from apps.project_manager.project.project_model import Project
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
        self.history_project_index = 0

    def _create_history_config(
        self,
        *,
        config_name: str,
        project_name: str,
        record_date: date,
        managers=None,
        enable_dt_fuzz: bool = False,
    ) -> IntegrationProjectConfig:
        integration_service.ensure_default_metric_definitions()
        self.history_project_index += 1
        project = Project.objects.create(
            name=project_name,
            domain="vehicle",
            type="platform",
            code=f"history-project-{self.history_project_index}",
        )
        config = IntegrationProjectConfig.objects.create(
            project=project,
            name=config_name,
            enabled=True,
            enable_dt_fuzz=enable_dt_fuzz,
        )
        if managers:
            config.managers.set(managers)
        metric = IntegrationMetricDefinition.objects.get(key="codecheck_error_num")
        IntegrationProjectMetricValue.objects.create(
            config=config,
            record_date=record_date,
            metric=metric,
            value_number=1,
            value_text="",
            detail_url="",
        )
        if enable_dt_fuzz:
            IntegrationDtFuzzSnapshot.objects.create(
                config=config,
                record_date=record_date,
                branch="main",
                source_due_date=f"{record_date.isoformat()} 12:00:00",
                tree_payload={"name": config_name, "type": "version", "children": []},
            )
        return config

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

    def test_domain_directory_set_allows_same_directory_in_multiple_domains(self):
        payload = DomainDirectorySetUpsertIn(
            name="Shared Directory Set",
            description="domain directory mapping",
            enabled=True,
            rules=[
                DomainDirectoryRuleIn(
                    domain_name="座舱",
                    directory="/repo/common",
                    sort_order=0,
                    enabled=True,
                ),
                DomainDirectoryRuleIn(
                    domain_name="车控",
                    directory="/repo/common",
                    sort_order=1,
                    enabled=True,
                ),
            ],
        )

        set_id = integration_service.create_domain_directory_set(payload)
        detail = integration_service.get_domain_directory_set_detail(set_id)

        self.assertEqual(detail["domain_count"], 2)
        self.assertEqual(detail["directory_count"], 2)
        self.assertEqual(
            IntegrationDomainDirectoryRule.objects.filter(
                directory_set_id=set_id,
                directory="/repo/common",
                is_deleted=False,
            ).count(),
            2,
        )

    def test_config_supports_domain_metrics_and_multiple_task_ids(self):
        directory_set = IntegrationDomainDirectorySet.objects.create(
            name="Project Domain Directories",
            enabled=True,
        )
        payload = ProjectConfigUpsertIn(
            project_id=None,
            name="Domain Metrics Config",
            managers=[],
            enabled=True,
            code_check_task_id="legacy-codecheck",
            dt_bin_task_id="legacy-dt-bin",
            cooddy_check_task_id="legacy-cooddy",
            bin_scope_task_id="legacy-bin-scope",
            enable_domain_metrics=True,
            domain_directory_set_id=str(directory_set.id),
            code_check_task_ids=["codecheck-1", "codecheck-2", "codecheck-1"],
            dt_bin_task_ids=["dt-bin-1", "dt-bin-2"],
            cooddy_check_task_ids=["cooddy-1"],
            bin_scope_task_ids=["bin-scope-1", "bin-scope-2"],
        )

        request = self.factory.post("/api/integration-report/configs")
        config_id = create_config(request, payload)

        config = IntegrationProjectConfig.objects.get(id=config_id)
        self.assertTrue(config.enable_domain_metrics)
        self.assertEqual(config.domain_directory_set_id, str(directory_set.id))
        self.assertEqual(config.code_check_task_ids, ["codecheck-1", "codecheck-2"])
        self.assertEqual(config.dt_bin_task_ids, ["dt-bin-1", "dt-bin-2"])

    def test_domain_metric_task_ids_fall_back_to_legacy_single_id(self):
        directory_set = IntegrationDomainDirectorySet.objects.create(
            name="Fallback Directories",
            enabled=True,
        )
        payload = ProjectConfigUpsertIn(
            project_id=None,
            name="Fallback Domain Config",
            managers=[],
            enabled=True,
            code_check_task_id="legacy-codecheck",
            enable_domain_metrics=True,
            domain_directory_set_id=str(directory_set.id),
            code_check_task_ids=[],
        )

        request = self.factory.post("/api/integration-report/configs")
        config_id = create_config(request, payload)

        config = IntegrationProjectConfig.objects.get(id=config_id)
        self.assertEqual(config.code_check_task_ids, ["legacy-codecheck"])

    def test_fetcher_sums_multiple_domain_metric_task_ids(self):
        directory_set = IntegrationDomainDirectorySet.objects.create(
            name="Fetch Directories",
            enabled=True,
        )
        IntegrationDomainDirectoryRule.objects.create(
            directory_set=directory_set,
            domain_name="座舱",
            directory="/repo/cockpit",
            sort_order=1,
        )
        IntegrationDomainDirectoryRule.objects.create(
            directory_set=directory_set,
            domain_name="车控",
            directory="/repo/body",
            sort_order=2,
        )
        config = IntegrationProjectConfig.objects.create(
            name="Fetch Sum Config",
            enabled=True,
            enable_domain_metrics=True,
            domain_directory_set=directory_set,
            code_check_task_ids=["codecheck-1", "codecheck-2"],
        )
        fetcher = IntegrationDataFetcher(config)

        with patch.object(
            fetcher,
            "_fetch_domain_directory_single_metric",
            side_effect=[
                (1.0, "url-1"),
                (2.0, "url-2"),
                (3.0, "url-3"),
                (4.0, "url-4"),
            ],
        ):
            value, url = fetcher._fetch_metric(
                config.code_check_task_id,
                config.code_check_task_ids,
                "codecheck",
                lambda: 0.0,
            )

        self.assertEqual(value, 10.0)
        self.assertEqual(url, "url-1\nurl-2\nurl-3\nurl-4")

    def test_fetcher_keeps_legacy_single_id_metric_when_domain_disabled(self):
        config = IntegrationProjectConfig.objects.create(
            name="Legacy Single Config",
            enabled=True,
            enable_domain_metrics=False,
            code_check_task_id="legacy-codecheck",
            code_check_task_ids=["hidden-codecheck-1", "hidden-codecheck-2"],
        )
        fetcher = IntegrationDataFetcher(config)

        with patch.object(
            fetcher,
            "_fetch_single_metric",
            return_value=(7.0, "legacy-url"),
        ) as fetch_single:
            value, url = fetcher._fetch_metric(
                config.code_check_task_id,
                config.code_check_task_ids,
                "codecheck",
                lambda: 0.0,
            )

        self.assertEqual(value, 7.0)
        self.assertEqual(url, "legacy-url")
        fetch_single.assert_called_once()
        self.assertEqual(fetch_single.call_args.args[0], "legacy-codecheck")

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

    def test_history_keywords_default_to_intersection(self):
        record_date = date(2026, 7, 20)
        self._create_history_config(
            config_name="Alpha Integration",
            project_name="Vehicle Platform",
            record_date=record_date,
        )
        self._create_history_config(
            config_name="Alpha Integration",
            project_name="Cloud Platform",
            record_date=record_date,
        )
        self._create_history_config(
            config_name="Gamma Integration",
            project_name="Vehicle Platform",
            record_date=record_date,
        )

        request = self.factory.get(
            "/api/integration-report/history",
            {"start": record_date.isoformat(), "end": record_date.isoformat()},
        )
        payload = history(
            request,
            start=record_date,
            end=record_date,
            keywords=["Alpha", "Vehicle"],
        )

        self.assertEqual(len(payload.items), 1)
        self.assertEqual(payload.items[0].config_name, "Alpha Integration")
        self.assertEqual(payload.items[0].project_name, "Vehicle Platform")

    def test_history_keywords_can_use_union_mode(self):
        record_date = date(2026, 7, 20)
        self._create_history_config(
            config_name="Alpha Integration",
            project_name="Cloud Platform",
            record_date=record_date,
        )
        self._create_history_config(
            config_name="Gamma Integration",
            project_name="Vehicle Platform",
            record_date=record_date,
        )
        self._create_history_config(
            config_name="Quiet Integration",
            project_name="Desktop Platform",
            record_date=record_date,
        )

        request = self.factory.get(
            "/api/integration-report/history",
            {"start": record_date.isoformat(), "end": record_date.isoformat()},
        )
        payload = history(
            request,
            start=record_date,
            end=record_date,
            keywords=["Alpha", "Vehicle"],
            keyword_match_mode="any",
        )

        names = {(item.config_name, item.project_name) for item in payload.items}
        self.assertEqual(
            names,
            {
                ("Alpha Integration", "Cloud Platform"),
                ("Gamma Integration", "Vehicle Platform"),
            },
        )

    def test_history_caretaker_keywords_support_intersection_and_union(self):
        record_date = date(2026, 7, 20)
        alice = User.objects.create(
            username="alice-owner",
            password="secret",
            name="Alice Owner",
            is_active=True,
        )
        bob = User.objects.create(
            username="bob-owner",
            password="secret",
            name="Bob Owner",
            is_active=True,
        )
        self._create_history_config(
            config_name="Both Owners",
            project_name="Both Project",
            record_date=record_date,
            managers=[alice, bob],
        )
        self._create_history_config(
            config_name="Alice Only",
            project_name="Alice Project",
            record_date=record_date,
            managers=[alice],
        )
        self._create_history_config(
            config_name="Bob Only",
            project_name="Bob Project",
            record_date=record_date,
            managers=[bob],
        )

        request = self.factory.get(
            "/api/integration-report/history",
            {"start": record_date.isoformat(), "end": record_date.isoformat()},
        )
        intersection_payload = history(
            request,
            start=record_date,
            end=record_date,
            caretaker_keywords=["Alice", "Bob"],
        )
        union_payload = history(
            request,
            start=record_date,
            end=record_date,
            caretaker_keywords=["Alice", "Bob"],
            keyword_match_mode="any",
        )

        self.assertEqual(len(intersection_payload.items), 1)
        self.assertEqual(intersection_payload.items[0].config_name, "Both Owners")
        self.assertEqual(
            {item.config_name for item in union_payload.items},
            {"Both Owners", "Alice Only", "Bob Only"},
        )

    def test_history_merges_legacy_and_array_keywords_and_filters_dt_fuzz(self):
        record_date = date(2026, 7, 20)
        self._create_history_config(
            config_name="Alpha DT Fuzz",
            project_name="Vehicle Platform",
            record_date=record_date,
            enable_dt_fuzz=True,
        )
        self._create_history_config(
            config_name="Alpha DT Fuzz",
            project_name="Cloud Platform",
            record_date=record_date,
            enable_dt_fuzz=True,
        )

        request = self.factory.get(
            "/api/integration-report/history",
            {"start": record_date.isoformat(), "end": record_date.isoformat()},
        )
        payload = history(
            request,
            start=record_date,
            end=record_date,
            keyword="Alpha",
            keywords=["Vehicle", "Alpha"],
        )

        self.assertEqual(len(payload.items), 1)
        self.assertEqual(payload.items[0].project_name, "Vehicle Platform")
        self.assertEqual(len(payload.dt_fuzz_items), 1)
        self.assertEqual(payload.dt_fuzz_items[0].project_name, "Vehicle Platform")

    def test_history_accepts_bracket_array_keyword_params(self):
        record_date = date(2026, 7, 20)
        self._create_history_config(
            config_name="MCU Integration",
            project_name="Vehicle Platform",
            record_date=record_date,
        )
        self._create_history_config(
            config_name="Cloud Integration",
            project_name="Vehicle Platform",
            record_date=record_date,
        )

        request = self.factory.get(
            "/api/integration-report/history",
            {
                "start": record_date.isoformat(),
                "end": record_date.isoformat(),
                "keywords[]": ["MCU", "Vehicle"],
            },
        )
        payload = history(request, start=record_date, end=record_date)

        self.assertEqual(len(payload.items), 1)
        self.assertEqual(payload.items[0].config_name, "MCU Integration")

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
        base_time = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
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

    def test_subscription_management_project_list_counts_subscribers_and_missing_email(self):
        manager = User.objects.create(
            username="subscription-manager",
            password="secret",
            name="Subscription Manager",
            email="manager@example.com",
            is_active=True,
        )
        missing_email_user = User.objects.create(
            username="missing-email-user",
            password="secret",
            name="Missing Email User",
            is_active=True,
        )
        project = Project.objects.create(
            name="Managed Project",
            domain="vehicle",
            type="platform",
            code="managed-project",
        )
        project.managers.set([manager])
        config = IntegrationProjectConfig.objects.create(
            project=project,
            name="Managed Config",
            enabled=True,
        )
        config.managers.set([manager])
        IntegrationEmailSubscription.objects.create(
            config=config,
            user=manager,
            enabled=True,
        )
        IntegrationEmailSubscription.objects.create(
            config=config,
            user=missing_email_user,
            enabled=True,
        )

        rows, count, page, page_size = integration_service.query_subscription_management_projects(
            SubscriptionManagementProjectQueryIn(
                keyword="Managed",
                has_missing_email=True,
                page=1,
                page_size=20,
            )
        )

        self.assertEqual(count, 1)
        self.assertEqual(page, 1)
        self.assertEqual(page_size, 20)
        self.assertEqual(rows[0]["id"], str(config.id))
        self.assertEqual(rows[0]["subscriber_count"], 2)
        self.assertEqual(rows[0]["missing_email_count"], 1)
        self.assertEqual(rows[0]["managers"], "Subscription Manager")
        self.assertEqual(rows[0]["project_managers"], "Subscription Manager")

    def test_subscription_management_batch_add_does_not_duplicate_subscriptions(self):
        config = IntegrationProjectConfig.objects.create(
            name="Batch Add Config",
            enabled=True,
        )
        user = User.objects.create(
            username="batch-add-user",
            password="secret",
            name="Batch Add User",
            email="batch-add@example.com",
            is_active=True,
        )

        first_count = integration_service.add_subscription_users(config.id, [user.id])
        second_count = integration_service.add_subscription_users(config.id, [user.id])

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 0)
        self.assertEqual(
            IntegrationEmailSubscription.objects.filter(config=config, user=user).count(),
            1,
        )

    def test_subscription_management_batch_add_users_to_multiple_configs(self):
        first_config = IntegrationProjectConfig.objects.create(
            name="Batch Config One",
            enabled=True,
        )
        second_config = IntegrationProjectConfig.objects.create(
            name="Batch Config Two",
            enabled=True,
        )
        user = User.objects.create(
            username="batch-project-user",
            password="secret",
            name="Batch Project User",
            email="batch-project@example.com",
            is_active=True,
        )

        changed_count = integration_service.batch_add_subscription_users(
            [first_config.id, second_config.id],
            [user.id],
        )
        duplicate_count = integration_service.batch_add_subscription_users(
            [first_config.id, second_config.id],
            [user.id],
        )

        self.assertEqual(changed_count, 2)
        self.assertEqual(duplicate_count, 0)
        self.assertTrue(
            IntegrationEmailSubscription.objects.filter(
                config=first_config,
                user=user,
                enabled=True,
                is_deleted=False,
            ).exists()
        )
        self.assertTrue(
            IntegrationEmailSubscription.objects.filter(
                config=second_config,
                user=user,
                enabled=True,
                is_deleted=False,
            ).exists()
        )

    def test_subscription_management_replace_enables_requested_and_removes_others(self):
        config = IntegrationProjectConfig.objects.create(
            name="Replace Config",
            enabled=True,
        )
        kept_user = User.objects.create(
            username="kept-user",
            password="secret",
            name="Kept User",
            email="kept@example.com",
            is_active=True,
        )
        removed_user = User.objects.create(
            username="removed-user",
            password="secret",
            name="Removed User",
            email="removed@example.com",
            is_active=True,
        )
        restored_user = User.objects.create(
            username="restored-user",
            password="secret",
            name="Restored User",
            email="restored@example.com",
            is_active=True,
        )
        IntegrationEmailSubscription.objects.create(
            config=config,
            user=kept_user,
            enabled=True,
        )
        IntegrationEmailSubscription.objects.create(
            config=config,
            user=removed_user,
            enabled=True,
        )
        IntegrationEmailSubscription.objects.create(
            config=config,
            user=restored_user,
            enabled=False,
            is_deleted=True,
        )

        integration_service.replace_subscription_users(
            config.id,
            [kept_user.id, restored_user.id],
        )

        kept = IntegrationEmailSubscription.objects.get(config=config, user=kept_user)
        removed = IntegrationEmailSubscription.objects.get(config=config, user=removed_user)
        restored = IntegrationEmailSubscription.objects.get(config=config, user=restored_user)
        self.assertTrue(kept.enabled)
        self.assertFalse(kept.is_deleted)
        self.assertFalse(removed.enabled)
        self.assertTrue(removed.is_deleted)
        self.assertTrue(restored.enabled)
        self.assertFalse(restored.is_deleted)

    def test_subscription_management_missing_config_or_user_raises_error(self):
        config = IntegrationProjectConfig.objects.create(
            name="Missing Validation Config",
            enabled=True,
        )

        with self.assertRaises(ValueError):
            integration_service.query_subscription_subscribers(
                "not-exists",
                SubscriptionSubscriberQueryIn(page=1, page_size=20),
            )

        with self.assertRaises(ValueError):
            integration_service.add_subscription_users(config.id, ["not-exists"])
