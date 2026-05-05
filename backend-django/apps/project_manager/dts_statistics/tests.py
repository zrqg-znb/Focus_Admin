from __future__ import annotations

import datetime
from unittest import mock

from django.test import TransactionTestCase
from django.utils import timezone

from .dts_statistics_model import DtsExtension
from .dts_statistics_schemas import DtsStatisticsQuerySchema
from . import dts_statistics_services


class DtsStatisticsSummaryTests(TransactionTestCase):
    def _ms(self, year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
        dt = datetime.datetime(year, month, day, hour, minute)
        aware = timezone.make_aware(dt, timezone.get_current_timezone())
        return int(aware.timestamp() * 1000)

    def _query(self, begin_ms: int, end_ms: int) -> DtsStatisticsQuerySchema:
        return DtsStatisticsQuerySchema(
            updateTimeBegin=begin_ms,
            updateTimeEnd=end_ms,
        )

    def test_local_runtime_filters_include_dev_asset_type_values(self):
        query = DtsStatisticsQuerySchema(
            updateTimeBegin=self._ms(2026, 5, 1),
            updateTimeEnd=self._ms(2026, 5, 3),
            dev_asset_type_values=["用例", "脚本"],
        )

        local_filters = dts_statistics_services._resolve_local_runtime_filters(query)

        self.assertIn("dev_asset_type_values", local_filters)
        self.assertEqual(local_filters["dev_asset_type_values"], ["用例", "脚本"])

    def _defect(
        self,
        defect_no: str,
        *,
        team: str = "研发A组",
        severity: str = "一般",
        status: str = "处理中",
        flow_type: str = "标准",
        source: str = "手工提单",
        handler: str = "张三",
        project_name: str = "座舱项目",
        pl_group: str = "PL-A",
        update_at: str = "2026-05-01 10:00:00",
        create_at: str = "2026-04-25 10:00:00",
        close_time: str = "",
        close_type: str = "",
        close_days: str = "",
    ) -> dict[str, str]:
        return {
            "dtsBizNo": defect_no,
            "dtsStatusName": status,
            "serverityNoName": severity,
            "updateAt": update_at,
            "createAt": create_at,
            "dCloseTime": close_time,
            "uQbiCloseTypeName": close_type,
            "sDeptOneNoName": team,
            "auto_source_type": source,
            "auto_pl_group_name": pl_group,
            "currentHandler": handler,
            "projectName": project_name,
            "sProdCName": project_name,
            "sConfigFlowType": flow_type,
            "iNumOfCloseDays": close_days,
        }

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._resolve_runtime_defects"
    )
    def test_summary_flow_type_dist_is_independent_from_status_dist(
        self,
        mocked_resolve,
    ):
        defects = [
            self._defect("D-1", status="处理中", flow_type="简易"),
            self._defect("D-2", status="已关闭", flow_type="标准"),
            self._defect("D-3", status="已关闭", flow_type="简易"),
        ]
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 5, 1), self._ms(2026, 5, 3, 23, 59))
        )

        self.assertEqual(
            summary["status_dist"],
            [
                {"label": "已关闭", "value": 2},
                {"label": "处理中", "value": 1},
            ],
        )
        self.assertEqual(
            summary["flow_type_dist"],
            [
                {"label": "简易", "value": 2},
                {"label": "标准", "value": 1},
            ],
        )
        self.assertNotIn("stage_dist", summary)

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._resolve_runtime_defects"
    )
    def test_summary_update_trend_uses_day_buckets_with_short_range(
        self,
        mocked_resolve,
    ):
        defects = [
            self._defect("D-1", severity="关键", status="已关闭", update_at="2026-05-01 09:00:00"),
            self._defect("D-2", severity="一般", status="处理中", update_at="2026-05-01 12:00:00"),
            self._defect("D-3", severity="关键", status="已关闭", update_at="2026-05-03 15:00:00"),
        ]
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 5, 1), self._ms(2026, 5, 3, 23, 59))
        )
        trend = summary["update_trend"]

        self.assertIsNotNone(trend)
        self.assertEqual(trend["granularity"], "day")
        self.assertEqual(
            trend["labels"],
            ["2026-05-01", "2026-05-02", "2026-05-03"],
        )
        self.assertEqual(trend["total_values"], [2, 0, 1])
        self.assertEqual(trend["closed_values"], [1, 0, 1])
        self.assertEqual(trend["major_values"], [0, 0, 0])
        self.assertEqual(trend["critical_values"], [1, 0, 1])

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._resolve_runtime_defects"
    )
    def test_summary_update_trend_uses_week_buckets_for_long_range(
        self,
        mocked_resolve,
    ):
        defects = [
            self._defect("D-1", severity="关键", status="已关闭", update_at="2026-03-02 09:00:00"),
            self._defect("D-2", severity="严重", status="处理中", update_at="2026-03-08 09:00:00"),
            self._defect("D-3", severity="一般", status="已关闭", update_at="2026-03-09 09:00:00"),
        ]
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 3, 1), self._ms(2026, 5, 5, 23, 59))
        )
        trend = summary["update_trend"]

        self.assertIsNotNone(trend)
        self.assertEqual(trend["granularity"], "week")
        self.assertEqual(trend["labels"][1], "2026-03-02~2026-03-08")
        self.assertEqual(trend["labels"][2], "2026-03-09~2026-03-15")
        self.assertEqual(trend["total_values"][1], 2)
        self.assertEqual(trend["total_values"][2], 1)
        self.assertEqual(trend["closed_values"][1], 1)
        self.assertEqual(trend["closed_values"][2], 1)
        self.assertEqual(trend["major_values"][1], 1)
        self.assertEqual(trend["major_values"][2], 0)
        self.assertEqual(trend["critical_values"][1], 1)
        self.assertEqual(trend["critical_values"][2], 0)

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._resolve_runtime_defects"
    )
    def test_summary_process_days_bucket_dist_uses_fixed_bins(
        self,
        mocked_resolve,
    ):
        defects = [
            self._defect("D-1", close_days="0"),
            self._defect("D-2", close_days="3"),
            self._defect("D-3", close_days="4"),
            self._defect("D-4", close_days="7"),
            self._defect("D-5", close_days="8"),
            self._defect("D-6", close_days="14"),
            self._defect("D-7", close_days="15"),
            self._defect("D-8", close_days="30"),
            self._defect("D-9", close_days="31"),
            self._defect("D-10"),
        ]
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 5, 1), self._ms(2026, 5, 10))
        )

        self.assertEqual(
            summary["process_days_bucket_dist"],
            [
                {"label": "0-3天", "value": 2},
                {"label": "4-7天", "value": 2},
                {"label": "8-14天", "value": 2},
                {"label": "15-30天", "value": 2},
                {"label": "30天以上", "value": 1},
                {"label": "未填写", "value": 1},
            ],
        )

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._resolve_runtime_defects"
    )
    def test_summary_uses_separate_dev_and_test_action_status_distributions(
        self,
        mocked_resolve,
    ):
        defects = [
            self._defect("D-1"),
            self._defect("D-2"),
            self._defect("D-3"),
        ]
        DtsExtension.objects.create(
            defect_no="D-1",
            issue_intro_stage="需求评审",
            dev_status="已完成",
            test_status="待确认",
            dev_sub_category=["子类A"],
            test_miss_reason=["原因A"],
        )
        DtsExtension.objects.create(
            defect_no="D-2",
            issue_intro_stage="开发实现",
            dev_status="待处理",
            test_status="已完成",
            dev_sub_category=["子类A", "子类B"],
            test_miss_reason=["原因A", "原因B"],
        )
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 5, 1), self._ms(2026, 5, 3))
        )

        self.assertEqual(
            summary["issue_intro_stage_dist"],
            [
                {"label": "需求评审", "value": 1},
                {"label": "开发实现", "value": 1},
            ],
        )
        self.assertEqual(
            summary["dev_action_status_dist"],
            [
                {"label": "已完成", "value": 1},
                {"label": "待处理", "value": 1},
            ],
        )
        self.assertEqual(
            summary["test_action_status_dist"],
            [
                {"label": "待确认", "value": 1},
                {"label": "已完成", "value": 1},
            ],
        )

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._resolve_runtime_defects"
    )
    def test_summary_team_severity_matrix_top_8_and_severity_columns(
        self,
        mocked_resolve,
    ):
        severity_cycle = ["关键", "严重", "一般", "提示", "未知"]
        team_specs = [
            ("Team-A", 9),
            ("Team-B", 8),
            ("Team-C", 7),
            ("Team-D", 6),
            ("Team-E", 5),
            ("Team-F", 4),
            ("Team-G", 3),
            ("Team-H", 2),
            ("Team-I", 1),
        ]
        defects: list[dict[str, str]] = []
        for team, count in team_specs:
            for index in range(count):
                defects.append(
                    self._defect(
                        f"{team}-{index}",
                        team=team,
                        severity=severity_cycle[index % len(severity_cycle)],
                        status="已关闭" if index % 2 == 0 else "处理中",
                        update_at=f"2026-05-{(index % 5) + 1:02d} 09:00:00",
                    )
                )
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 5, 1), self._ms(2026, 5, 31, 23, 59))
        )
        matrix = summary["team_severity_matrix"]

        self.assertEqual(matrix["columns"], ["关键", "严重", "一般", "提示", "未填写"])
        self.assertEqual(len(matrix["rows"]), 8)
        self.assertEqual(matrix["rows"][0]["label"], "Team-A")
        self.assertEqual(matrix["rows"][0]["values"], [2, 2, 2, 2, 1])
        self.assertEqual(matrix["rows"][1]["label"], "Team-B")
        self.assertEqual(matrix["rows"][1]["values"], [2, 2, 2, 1, 1])
        self.assertNotIn("Team-I", [row["label"] for row in matrix["rows"]])
