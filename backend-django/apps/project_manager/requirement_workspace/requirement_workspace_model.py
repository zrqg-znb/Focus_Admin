from django.db import models

from common.fu_model import RootModel


class RequirementWorkspaceSnapshot(RootModel):
    snapshot_date = models.DateField(db_index=True, verbose_name="快照日期")
    scope = models.CharField(max_length=64, db_index=True, verbose_name="统计范围")
    generated_at = models.DateTimeField(db_index=True, verbose_name="生成时间")
    project_count = models.IntegerField(default=0, verbose_name="项目数")
    requirement_count = models.IntegerField(default=0, verbose_name="需求数")
    payload = models.JSONField(default=dict, blank=True, verbose_name="快照载荷")

    class Meta:
        db_table = "pm_requirement_workspace_snapshot"
        verbose_name = "工作台需求交付快照"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot_date", "scope"],
                name="uniq_pm_requirement_workspace_snapshot_scope_date",
            )
        ]
        indexes = [
            models.Index(fields=["scope", "snapshot_date"]),
            models.Index(fields=["scope", "generated_at"]),
        ]

    def __str__(self):
        return f"{self.scope}:{self.snapshot_date}"


class RequirementWorkspaceRefreshTask(RootModel):
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

    scope = models.CharField(max_length=64, db_index=True, verbose_name="统计范围")
    requested_by = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requirement_workspace_refresh_tasks",
        verbose_name="发起人",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="状态",
    )
    message = models.CharField(max_length=255, blank=True, default="", verbose_name="任务提示")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    started_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="结束时间")
    snapshot_date = models.DateField(null=True, blank=True, db_index=True, verbose_name="快照日期")
    snapshot = models.ForeignKey(
        RequirementWorkspaceSnapshot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refresh_tasks",
        verbose_name="关联快照",
    )

    class Meta:
        db_table = "pm_requirement_workspace_refresh_task"
        verbose_name = "工作台需求交付刷新任务"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["scope", "status", "sys_create_datetime"]),
            models.Index(fields=["requested_by", "sys_create_datetime"]),
        ]

    def __str__(self):
        return f"{self.scope}:{self.status}:{self.id}"
