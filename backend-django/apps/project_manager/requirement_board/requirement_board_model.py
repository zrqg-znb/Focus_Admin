from django.db import models

from common.fu_model import RootModel

STATUS_ORDER = ("I", "D", "P", "C", "A")
STATUS_LABELS = {
    "I": "初始化",
    "D": "已定义完成",
    "P": "开发中",
    "C": "已开发完成（转测）",
    "A": "测试完成（已置A）",
}
STATUS_DESCRIPTIONS = {
    "I": "需求刚创建或进入初始化阶段，尚未完成定义。",
    "D": "需求已完成定义，等待进入开发或排期推进。",
    "P": "需求正在开发处理中，尚未达到转测状态。",
    "C": "需求已开发完成并转测，等待测试验收。",
    "A": "需求已测试完成并置 A，可视为验收完成。",
}
CATEGORY_ORDER = ("AR", "DR", "SR")
VERIFICATION_POLICY_LABELS = {
    "10000001": "测试验证",
    "10000002": "设计评审",
    "10000006": "由下级分解需求验证",
    "10000009": "开发自验证",
    "10000010": "协同第三方验证",
    "10000011": "免验证",
}
VERIFICATION_POLICY_ORDER = tuple(VERIFICATION_POLICY_LABELS.keys())
TIME_FIELD_OPTIONS = (
    "planned_test_time",
    "due_date",
    "completed_time",
    "accepted_time",
)
DEFAULT_TIME_FIELD = "accepted_time"
TIME_FIELD_LABELS = {
    "planned_test_time": "计划转测时间",
    "due_date": "计划完成时间",
    "completed_time": "开发完成时间",
    "accepted_time": "测试完成时间",
}
UNKNOWN_TEAM_NAME = "未识别团队"


class RequirementBoardFilterPreference(RootModel):
    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="requirement_board_filter_preferences",
        verbose_name="用户",
    )
    payload = models.JSONField(default=dict, blank=True, verbose_name="筛选条件")
    last_applied_at = models.DateTimeField(db_index=True, verbose_name="最后应用时间")

    class Meta:
        db_table = "pm_requirement_board_filter_preference"
        verbose_name = "需求看板筛选偏好"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                name="uniq_pm_requirement_board_filter_preference_user",
            )
        ]

    def __str__(self):
        return f"{self.user_id}:{self.last_applied_at}"


class RequirementBoardQueryTask(RootModel):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
    )

    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="requirement_board_query_tasks",
        verbose_name="用户",
    )
    fingerprint = models.CharField(max_length=64, db_index=True, verbose_name="查询指纹")
    payload = models.JSONField(default=dict, blank=True, verbose_name="筛选条件")
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="状态",
    )
    message = models.CharField(max_length=255, blank=True, default="", verbose_name="任务提示")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    progress = models.IntegerField(default=0, verbose_name="进度")
    scanned_pages = models.IntegerField(default=0, verbose_name="已扫描页数")
    total_pages = models.IntegerField(default=0, verbose_name="总页数")
    matched_count = models.IntegerField(default=0, verbose_name="匹配需求数")
    result_cache_key = models.CharField(max_length=255, blank=True, default="", verbose_name="结果缓存键")
    started_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="结束时间")

    class Meta:
        db_table = "pm_requirement_board_query_task"
        verbose_name = "需求看板查询准备任务"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["user", "fingerprint", "status"]),
            models.Index(fields=["user", "sys_create_datetime"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.fingerprint}:{self.status}"
