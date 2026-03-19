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
