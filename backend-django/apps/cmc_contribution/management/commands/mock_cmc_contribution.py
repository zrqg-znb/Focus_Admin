"""生成本地 CMC 看板演示数据。"""

from datetime import date

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.user.user_model import User

from ...models import CmcContributionDailyRecord


class Command(BaseCommand):
    """为人员明细表创建可重复执行的 30 条本地演示快照。"""

    def add_arguments(self, parser):
        """提供统计日期和数据量参数，默认填充当前自然日的 30 条数据。"""
        parser.add_argument("--date", dest="statistic_date", help="统计日期，格式 YYYY-MM-DD")
        parser.add_argument("--count", type=int, default=30, help="演示人员数量，默认 30")

    def handle(self, *args, **options):
        """幂等写入演示用户及其 CMC 日快照，不影响其他用户的数据。"""
        try:
            statistic_date = (
                date.fromisoformat(options["statistic_date"])
                if options.get("statistic_date")
                else timezone.now().date()
            )
        except ValueError as exc:
            raise CommandError("--date 必须为 YYYY-MM-DD 格式") from exc
        count = int(options["count"] or 0)
        if count < 1 or count > 100:
            raise CommandError("--count 必须在 1 到 100 之间")

        for index in range(1, count + 1):
            username = f"cmc_demo_user_{index:02d}"
            name = f"CMC演示成员{index:02d}"
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "name": name,
                    "password": make_password("cmc-demo-only"),
                    "user_status": 1,
                },
            )
            cnt_total = 4 + index % 17
            major = index % 5
            fatal = index % 3
            minor = 3 + index % 11
            suggestion = 8 + index % 19
            issue = index % 7
            checked_lines = 600 + index * 73
            zero_comment_count = round(cnt_total * ((index % 6) / 10))
            CmcContributionDailyRecord.objects.update_or_create(
                statistic_date=statistic_date,
                user=user,
                defaults={
                    "user_name": name,
                    "merged_login": username,
                    "cnt_total": cnt_total,
                    "major_comments_cnt": major,
                    "fatal_comments_cnt": fatal,
                    "minor_comments_cnt": minor,
                    "sugge_comments_cnt": suggestion,
                    "cmt_issue": issue,
                    "checked_mr_lines": checked_lines,
                    "cmt_lines": 400 + index * 61,
                    "not_0_comment_rate": (index % 6) / 10,
                    "zero_comment_mr_count": zero_comment_count,
                    "raw_payload": {"mock": True, "name": name, "merged_login": username},
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"已为 {statistic_date.isoformat()} 写入 {count} 条 CMC 演示数据"
            )
        )
