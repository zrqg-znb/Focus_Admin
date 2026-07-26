"""CMC 贡献数据的本地快照与同步任务模型。"""

from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User


SYNC_TRIGGER_SCHEDULED = "scheduled"
SYNC_TRIGGER_MANUAL = "manual"
SYNC_TRIGGER_CHOICES = ((SYNC_TRIGGER_SCHEDULED, "定时"), (SYNC_TRIGGER_MANUAL, "手动"))
SYNC_STATUS_PENDING = "pending"
SYNC_STATUS_RUNNING = "running"
SYNC_STATUS_SUCCESS = "success"
SYNC_STATUS_FAILED = "failed"
SYNC_STATUS_CHOICES = (
    (SYNC_STATUS_PENDING, "待执行"),
    (SYNC_STATUS_RUNNING, "执行中"),
    (SYNC_STATUS_SUCCESS, "成功"),
    (SYNC_STATUS_FAILED, "失败"),
)


class CmcContributionDailyRecord(RootModel):
    """数据湖返回的人员每日 CMC 贡献快照。"""

    statistic_date = models.DateField(db_index=True, verbose_name="统计日期")
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name="cmc_contribution_daily_records",
        verbose_name="系统用户",
    )
    user_name = models.CharField(max_length=255, db_index=True, verbose_name="人员姓名")
    merged_login = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
        verbose_name="数据湖登录名",
    )
    cnt_total = models.IntegerField(default=0, verbose_name="合入MR总数")
    major_comments_cnt = models.IntegerField(default=0, verbose_name="严重检视意见数")
    fatal_comments_cnt = models.IntegerField(default=0, verbose_name="致命检视意见数")
    minor_comments_cnt = models.IntegerField(default=0, verbose_name="一般检视意见数")
    sugge_comments_cnt = models.IntegerField(default=0, verbose_name="建议检视意见数")
    cmt_issue = models.IntegerField(default=0, verbose_name="提交Issue总数")
    checked_mr_lines = models.IntegerField(default=0, verbose_name="检视代码行数")
    cmt_lines = models.IntegerField(default=0, verbose_name="提交MR代码量")
    not_0_comment_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0, verbose_name="零检视MR比例")
    zero_comment_mr_count = models.IntegerField(default=0, verbose_name="零检视MR数")
    raw_payload = models.JSONField(default=dict, blank=True, verbose_name="上游原始行")

    class Meta:
        db_table = "cmc_contribution_daily_record"
        ordering = ("-statistic_date", "user_name")
        constraints = [
            models.UniqueConstraint(
                fields=("statistic_date", "user"),
                name="cmc_contribution_daily_user_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=("statistic_date", "user"),
                name="cmc_contrib_day_user_idx",
            )
        ]


class CmcContributionSyncTask(RootModel):
    """CMC 数据湖日数据同步任务，用于审计和页面轮询。"""

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name="cmc_contribution_sync_tasks", verbose_name="发起用户")
    trigger_type = models.CharField(max_length=16, choices=SYNC_TRIGGER_CHOICES, db_index=True, verbose_name="触发方式")
    status = models.CharField(max_length=16, choices=SYNC_STATUS_CHOICES, default=SYNC_STATUS_PENDING, db_index=True, verbose_name="任务状态")
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(verbose_name="结束日期")
    requested_dates = models.JSONField(default=list, blank=True, verbose_name="请求日期")
    fetched_pages = models.IntegerField(default=0, verbose_name="拉取页数")
    fetched_rows = models.IntegerField(default=0, verbose_name="拉取行数")
    synced_dates = models.JSONField(default=list, blank=True, verbose_name="成功日期")
    error_message = models.TextField(default="", blank=True, verbose_name="错误信息")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")

    class Meta:
        db_table = "cmc_contribution_sync_task"
        ordering = ("-sys_create_datetime",)
        indexes = [models.Index(fields=("status", "trigger_type"), name="cmc_contrib_task_status_idx")]
