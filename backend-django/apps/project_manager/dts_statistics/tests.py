from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest import mock

from django.test import TransactionTestCase
from django.utils import timezone

from .dts_statistics_model import DtsExtension
from .dts_statistics_schemas import (
    DtsResponsibilityQualityQuerySchema,
    DtsStatisticsQuerySchema,
)
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

    def test_default_fields_include_low_level_reason_fields(self):
        for field in (
            "dts004ReasonAnalysis",
            "dts009ReasonAnalyses",
            "sAchieveDescibe",
        ):
            self.assertIn(field, dts_statistics_services._DEFAULT_FIELDS)

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
        dev_owner_name: str = "",
        dev_status: str = "处理中",
        dts004_reason_analysis: str = "",
        dts009_reason_analyses: str = "",
        s_achieve_descibe: str = "",
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
            "dev_owner_name": dev_owner_name,
            "currentHandler": handler,
            "projectName": project_name,
            "sProdCName": project_name,
            "sConfigFlowType": flow_type,
            "dev_status": dev_status,
            "iNumOfCloseDays": close_days,
            "dts004ReasonAnalysis": dts004_reason_analysis,
            "dts009ReasonAnalyses": dts009_reason_analyses,
            "sAchieveDescibe": s_achieve_descibe,
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

    def test_normalize_source_row_keeps_low_level_reason_fields(self):
        raw_row = {
            "dtsBizNo": "D-1",
            "briefDesc": "示例缺陷",
            "dtsStatusName": "处理中",
            "serverityNoName": "一般",
            "updateAt": "2026-05-01 10:00:00",
            "parentNo": "DP-1",
            "createAt": "2026-04-25 10:00:00",
            "dCloseTime": "",
            "uQbiCloseTypeName": "",
            "sDeptOneNoName": "研发A组",
            "currentHandler": "张三",
            "creator": "creator1",
            "sSubmitUserName": "提交人1",
            "sSubsystemNoName": "子系统1",
            "sConfigFlowType": "标准",
            "sProdCName": "座舱项目",
            "sProdFamilyNoName": "产品族1",
            "sProdXtdNoName": "产品1",
            "iTestBackCount": "1",
            "sSuggestByReviewer": "<p>建议</p>",
            "sTestReport": "<p>报告</p>",
            "sTestSuggest": "<p>测试建议</p>",
            "sModifyDocument": "<ul><li>doc.md</li></ul>",
            "sTestorTestReport": "<p>mock report</p>",
            "last_dts009_handler": "dev_user1",
            "last_dts010_handler": "review_user1",
            "last_dts013_handler": "test_user1",
            "iNumOfCloseDays": "1",
            "iNumOfFirmDays": "2",
            "iNumOfLocateDays": "3",
            "iNumofModifyDays": "4",
            "iNumofTestDays": "5",
            "dts009ReasonAnalysis": "<p>原字段</p>",
            "dts004ReasonAnalysis": "<p>内存泄露定位</p>",
            "dts009ReasonAnalyses": "<div>数据未校验说明</div>",
            "sAchieveDescibe": "<span>修复达成描述</span>",
        }

        normalized = dts_statistics_services._normalize_source_row(
            raw_row,
            product_id="250539396",
        )

        self.assertIsNotNone(normalized)
        normalized = normalized or {}
        self.assertEqual(normalized["dts004ReasonAnalysis"], "<p>内存泄露定位</p>")
        self.assertEqual(
            normalized["dts009ReasonAnalyses"],
            "<div>数据未校验说明</div>",
        )
        self.assertEqual(
            normalized["sAchieveDescibe"],
            "<span>修复达成描述</span>",
        )

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._resolve_runtime_defects"
    )
    def test_summary_low_level_issue_count_matches_any_keyword_hit(
        self,
        mocked_resolve,
    ):
        defects = [
            self._defect(
                "D-1",
                dts004_reason_analysis="<p>存在内存泄露风险</p>",
            ),
            self._defect(
                "D-2",
                dts009_reason_analyses="数据未校验",
            ),
            self._defect(
                "D-3",
                s_achieve_descibe="<div>正常说明</div>",
            ),
            self._defect(
                "D-4",
                dts004_reason_analysis="<span>数组越界</span>",
                dts009_reason_analyses="<p>空指针</p>",
                s_achieve_descibe="<div>内存不足</div>",
            ),
        ]
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 5, 1), self._ms(2026, 5, 3, 23, 59))
        )

        self.assertEqual(summary["low_level_count"], 3)
        self.assertEqual(summary["low_level_rate"], 0.75)

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
    def test_summary_pl_group_severity_matrix_top_8_and_severity_columns(
        self,
        mocked_resolve,
    ):
        severity_cycle = ["关键", "严重", "一般", "提示", "未知"]
        pl_group_specs = [
            ("PL-A", 9),
            ("PL-B", 8),
            ("PL-C", 7),
            ("PL-D", 6),
            ("PL-E", 5),
            ("PL-F", 4),
            ("PL-G", 3),
            ("PL-H", 2),
            ("PL-I", 1),
        ]
        defects: list[dict[str, str]] = []
        for pl_group, count in pl_group_specs:
            for index in range(count):
                defects.append(
                    self._defect(
                        f"{pl_group}-{index}",
                        pl_group=pl_group,
                        severity=severity_cycle[index % len(severity_cycle)],
                        status="已关闭" if index % 2 == 0 else "处理中",
                        update_at=f"2026-05-{(index % 5) + 1:02d} 09:00:00",
                    )
                )
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 5, 1), self._ms(2026, 5, 31, 23, 59))
        )
        matrix = summary["pl_group_severity_matrix"]

        self.assertEqual(matrix["columns"], ["关键", "严重", "一般", "提示", "未填写"])
        self.assertEqual(len(matrix["rows"]), 8)
        self.assertEqual(matrix["rows"][0]["label"], "PL-A")
        self.assertEqual(matrix["rows"][0]["values"], [2, 2, 2, 2, 1])
        self.assertEqual(matrix["rows"][1]["label"], "PL-B")
        self.assertEqual(matrix["rows"][1]["values"], [2, 2, 2, 1, 1])
        self.assertNotIn("PL-I", [row["label"] for row in matrix["rows"]])

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._resolve_runtime_defects"
    )
    def test_summary_pl_group_dev_completion_dist_uses_dev_owner_name_only(
        self,
        mocked_resolve,
    ):
        defects = [
            self._defect(
                "D-1",
                pl_group="PL-A",
                dev_owner_name="张三",
                dev_status="",
            ),
            self._defect(
                "D-2",
                pl_group="PL-A",
                dev_owner_name="",
                dev_status="已完成",
            ),
            self._defect(
                "D-3",
                pl_group="PL-A",
                dev_owner_name="",
                dev_status="待处理",
            ),
            self._defect(
                "D-4",
                pl_group="PL-B",
                dev_owner_name="李四",
                dev_status="待处理",
            ),
            self._defect(
                "D-5",
                pl_group="",
                dev_owner_name="王五",
                dev_status="",
            ),
            self._defect(
                "D-6",
                pl_group="",
                dev_owner_name="",
                dev_status="已完成",
            ),
        ]
        mocked_resolve.return_value = (defects, None)

        summary = dts_statistics_services.get_dts_statistics_summary(
            self._query(self._ms(2026, 5, 1), self._ms(2026, 5, 10))
        )

        self.assertEqual(
            summary["pl_group_dev_completion_dist"],
            [
                {
                    "label": "PL-B",
                    "filled_count": 1,
                    "total_count": 1,
                    "filled_rate": 1.0,
                },
                {
                    "label": "未识别PL领域",
                    "filled_count": 1,
                    "total_count": 2,
                    "filled_rate": 0.5,
                },
                {
                    "label": "PL-A",
                    "filled_count": 1,
                    "total_count": 3,
                    "filled_rate": 0.3333,
                },
            ],
        )


class DtsStatisticsResponsibilityQualityTests(TransactionTestCase):
    def _dt(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
    ) -> datetime.datetime:
        return timezone.make_aware(
            datetime.datetime(year, month, day, hour, minute),
            timezone.get_current_timezone(),
        )

    def _normalized_defect(
        self,
        month: str,
        process_quality_type: str,
        pl_group_label: str = "通信组",
    ) -> dict[str, str]:
        return {
            "month": month,
            "dtsBizNo": f"D-{month}-{process_quality_type}",
            "pl_group_label": pl_group_label,
            "process_quality_type": process_quality_type,
        }

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services.CacheManager.get",
        return_value=None,
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services.CacheManager.set"
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._load_quality_report_defects"
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._build_quality_group_specs_for_report"
    )
    def test_report_exact_match_process_quality_type_only(
        self,
        mocked_groups,
        mocked_load_defects,
        mocked_cache_set,
        _mocked_cache_get,
    ):
        month_ranges = dts_statistics_services._build_quality_month_ranges(
            reference_dt=self._dt(2026, 5, 19),
        )
        current_month = month_ranges[-1]["month"]
        mocked_groups.return_value = [
            {"id": "1", "label": "通信组", "owner_name": "徐鸣字", "sort": 1},
        ]
        mocked_load_defects.return_value = [
            self._normalized_defect(current_month, "CI打断问题数"),
            self._normalized_defect(current_month, "CI打断问题数（噪声）"),
            self._normalized_defect(current_month, "<p>问题重犯</p>"),
        ]

        response = dts_statistics_services.get_dts_responsibility_quality_report(
            DtsResponsibilityQualityQuerySchema(
                productId="250539396",
                month=current_month,
            ),
            user=SimpleNamespace(id=1),
        )

        self.assertEqual(len(response["month_reports"]), 1)
        self.assertEqual(response["month_reports"][0]["month"], current_month)
        latest_report = response["month_reports"][0]
        ci_row = latest_report["rows"][1]
        self.assertEqual(ci_row["cells"][0]["current_value"], 1.0)
        self.assertEqual(ci_row["cells"][0]["cumulative_value"], 1.0)
        self.assertEqual(ci_row["cells"][0]["cumulative_deduction"], -2.0)
        self.assertEqual(latest_report["score_items"][0]["score"], 117.0)
        self.assertEqual(len(response["month_options"]), len(month_ranges))
        mocked_cache_set.assert_called_once()

    def test_report_uses_rolling_12_month_window(self):
        month_ranges = dts_statistics_services._build_quality_month_ranges(
            reference_dt=self._dt(2026, 5, 19),
        )
        pl_groups = [
            {"id": "1", "label": "通信组", "owner_name": "徐鸣字", "sort": 1},
        ]
        defects = [
            self._normalized_defect(
                month_ranges[-(index + 1)]["month"],
                "CI打断问题数",
            )
            for index in range(13)
        ]

        counts = dts_statistics_services._build_quality_counts_from_rows(
            defects,
            month_ranges=month_ranges,
            pl_group_specs=pl_groups,
        )
        payload = dts_statistics_services._build_quality_report_payload(
            month_ranges=month_ranges,
            pl_group_specs=pl_groups,
            counts=counts,
        )

        latest_report = payload["month_reports"][0]
        ci_row = latest_report["rows"][1]
        self.assertEqual(ci_row["cells"][0]["current_value"], 1.0)
        self.assertEqual(ci_row["cells"][0]["cumulative_value"], 12.0)
        self.assertEqual(ci_row["cells"][0]["cumulative_deduction"], -24.0)
        self.assertEqual(latest_report["score_items"][0]["score"], 96.0)

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services.CacheManager.get",
        return_value=None,
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services.CacheManager.set"
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._load_quality_report_defects"
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._build_quality_group_specs_for_report"
    )
    def test_report_unknown_pl_group_falls_back_to_unknown(
        self,
        mocked_groups,
        mocked_load_defects,
        mocked_cache_set,
        _mocked_cache_get,
    ):
        month_ranges = dts_statistics_services._build_quality_month_ranges(
            reference_dt=self._dt(2026, 5, 19),
        )
        current_month = month_ranges[-1]["month"]
        mocked_groups.return_value = [
            {"id": "1", "label": "通信组", "owner_name": "徐鸣字", "sort": 1},
        ]
        mocked_load_defects.return_value = [
            self._normalized_defect(
                current_month,
                "CI打断问题数",
                pl_group_label="未命中责任田",
            )
        ]

        response = dts_statistics_services.get_dts_responsibility_quality_report(
            DtsResponsibilityQualityQuerySchema(
                productId="250539396",
                month=current_month,
            ),
            user=SimpleNamespace(id=1),
        )

        self.assertEqual(
            [item["label"] for item in response["pl_groups"]],
            ["通信组", "未识别PL领域"],
        )
        self.assertEqual(len(response["month_reports"]), 1)
        self.assertEqual(response["month_reports"][0]["month"], current_month)
        self.assertEqual(response["month_reports"][0]["score_items"][1]["label"], "未识别PL领域")
        self.assertEqual(response["month_reports"][0]["score_items"][1]["score"], 118.0)
        self.assertEqual(
            response["month_reports"][0]["rows"][1]["cells"][1]["current_value"],
            1.0,
        )
        mocked_cache_set.assert_called_once()

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services.CacheManager.get",
        return_value=None,
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services.CacheManager.set"
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._load_quality_report_defects",
        return_value=[],
    )
    def test_report_mock_mode_returns_renderable_payload(
        self,
        mocked_load_defects,
        mocked_cache_set,
        _mocked_cache_get,
    ):
        month_ranges = dts_statistics_services._build_quality_month_ranges(
            reference_dt=self._dt(2026, 5, 19),
        )
        current_month = month_ranges[-1]["month"]
        response = dts_statistics_services.get_dts_responsibility_quality_report(
            DtsResponsibilityQualityQuerySchema(
                productId="250539396",
                month=current_month,
            ),
            user=SimpleNamespace(id=1),
        )

        self.assertEqual(len(response["month_options"]), 24)
        self.assertEqual(len(response["month_reports"]), 1)
        self.assertEqual(response["month_reports"][0]["month"], current_month)
        self.assertGreater(len(response["pl_groups"]), 0)
        self.assertEqual(
            len(response["month_reports"][0]["rows"]),
            len(dts_statistics_services._RESPONSIBILITY_QUALITY_ROW_SPECS),
        )
        self.assertEqual(
            len(response["month_reports"][0]["score_items"]),
            len(response["pl_groups"]),
        )
        mocked_cache_set.assert_called_once()

    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services.CacheManager.get",
        return_value=None,
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services.CacheManager.set"
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._load_quality_report_defects"
    )
    @mock.patch(
        "apps.project_manager.dts_statistics.dts_statistics_services._build_quality_group_specs_for_report"
    )
    def test_report_returns_requested_month_slice(
        self,
        mocked_groups,
        mocked_load_defects,
        mocked_cache_set,
        _mocked_cache_get,
    ):
        mocked_groups.return_value = [
            {"id": "1", "label": "通信组", "owner_name": "徐鸣字", "sort": 1},
        ]
        mocked_load_defects.return_value = [
            self._normalized_defect("2026-05", "CI打断问题数"),
            self._normalized_defect("2026-04", "CI打断问题数"),
        ]

        response = dts_statistics_services.get_dts_responsibility_quality_report(
            DtsResponsibilityQualityQuerySchema(
                productId="250539396",
                month="2026-04",
            ),
            user=SimpleNamespace(id=1),
        )

        self.assertEqual(len(response["month_reports"]), 1)
        self.assertEqual(response["month_reports"][0]["month"], "2026-04")
        self.assertEqual(response["month_reports"][0]["rows"][1]["cells"][0]["current_value"], 1.0)
        mocked_cache_set.assert_called_once()
