"""CMC 贡献看板核心口径与同步边界测试。"""

from datetime import date
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from ninja.errors import HttpError

from . import services
from .models import CmcContributionDailyRecord


class CmcContributionServiceTests(TestCase):
    """验证本地聚合、日快照替换和数据湖分页。"""

    def test_replace_snapshot_and_range_metrics(self):
        """同日重跑覆盖旧行，跨日密度和零意见数按既定口径汇总。"""
        first_day = date(2026, 7, 20)
        second_day = date(2026, 7, 21)
        services.replace_day_snapshot(first_day, [{"user": "张三", "cnt_total": 33, "not_0_comment_rate": "48.26%", "major_comments_cnt": 1, "fatal_comments_cnt": 2, "minor_comments_cnt": 3, "sugge_comments_cnt": 4, "cmt_issue": 5, "checked_mr_lines": 100, "cmt_lines": 88}])
        services.replace_day_snapshot(second_day, [{"user": "张三", "cnt_total": 2, "not_0_comment_rate": "50%", "checked_mr_lines": 0, "cmt_lines": 6}])
        # 替换首日快照不能保留已经从上游消失的人员或旧数值。
        services.replace_day_snapshot(first_day, [{"user": "张三", "cnt_total": 10, "not_0_comment_rate": "50%", "major_comments_cnt": 1, "checked_mr_lines": 100}])
        summary = services.get_summary(first_day, second_day)
        self.assertEqual(CmcContributionDailyRecord.objects.filter(statistic_date=first_day).count(), 1)
        self.assertEqual(summary["cnt_total"], 12)
        self.assertEqual(summary["zero_comment_mr_count"], 6)
        self.assertEqual(summary["effective_comment_count"], 1)
        self.assertEqual(summary["effective_comment_density"], 0.01)

    @override_settings(CMC_CONTRIBUTION_API_URL="https://cmc.example.test/api", CMC_CONTRIBUTION_MAX_PAGES=5)
    @patch("apps.cmc_contribution.services.requests.post")
    def test_fetch_day_walks_pages_until_empty(self, post):
        """上游未返回总页数时，客户端应持续请求直到空页。"""
        responses = []
        for body in ({"data": [{"user": "张三"}]}, {"data": [{"user": "李四"}]}, {"data": []}):
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = body
            responses.append(response)
        post.side_effect = responses
        rows, pages = services.fetch_day(date(2026, 7, 20))
        self.assertEqual((len(rows), pages), (2, 3))
        self.assertEqual(post.call_args_list[0].kwargs["json"]["START_PAGE"], 1)
        self.assertEqual(post.call_args_list[1].kwargs["json"]["START_PAGE"], 2)

    def test_manual_sync_rejects_non_admin_and_long_range(self):
        """手动补数必须由管理员在 31 天窗口内发起。"""
        class User:
            is_superuser = False
        with self.assertRaises(HttpError):
            services.create_manual_task(User(), date(2026, 7, 1), date(2026, 7, 1))
        class Admin:
            is_superuser = True
            id = None
        with self.assertRaises(HttpError):
            services.create_manual_task(Admin(), date(2026, 7, 1), date(2026, 8, 1))
