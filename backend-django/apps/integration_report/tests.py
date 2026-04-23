from datetime import date
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.integration_report import integration_service
from apps.integration_report.integration_api import create_config, history, update_config
from apps.integration_report.integration_email import CODE_COLUMNS
from apps.integration_report.integration_models import (
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
