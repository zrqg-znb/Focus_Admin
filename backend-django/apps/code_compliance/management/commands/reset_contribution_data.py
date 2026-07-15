from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.code_compliance.models import (
    ComplianceContributionCodeBaseline,
    ComplianceContributionCollectTask,
    ComplianceContributionDailyAggregate,
    ComplianceContributionExportTask,
    ComplianceContributionRecord,
)


class Command(BaseCommand):
    help = "清空代码贡献统计数据，不删除组织、代码库、分支等主数据"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm-reset-contribution-data",
            action="store_true",
            help="确认清理贡献事实、聚合、任务、导出和基线数据",
        )
        parser.add_argument(
            "--allow-non-debug",
            action="store_true",
            help="允许在 DEBUG=False 时执行；仅在明确确认的开发环境使用",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        """在开发环境清理贡献统计数据，并输出每张表的删除数量。"""
        if not options["confirm_reset_contribution_data"]:
            raise CommandError("请添加 --confirm-reset-contribution-data 以确认删除贡献统计数据")
        if not settings.DEBUG and not options["allow_non_debug"]:
            raise CommandError("当前不是 DEBUG 环境；如确认是开发库，请额外添加 --allow-non-debug")

        models = [
            ("贡献导出任务", ComplianceContributionExportTask),
            ("贡献采集任务", ComplianceContributionCollectTask),
            ("贡献日聚合", ComplianceContributionDailyAggregate),
            ("贡献事实", ComplianceContributionRecord),
            ("代码量基线", ComplianceContributionCodeBaseline),
        ]
        total = 0
        for label, model in models:
            deleted, _ = model.objects.all().delete()
            total += deleted
            self.stdout.write(f"{label}: 删除 {deleted} 条")
        self.stdout.write(self.style.SUCCESS(f"贡献统计数据清理完成，共删除 {total} 条"))
