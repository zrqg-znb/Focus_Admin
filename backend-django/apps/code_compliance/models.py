from common.fu_model import RootModel
from django.db import models
from core.user.user_model import User

class ComplianceRecord(RootModel):
    STATUS_CHOICES = (
        (0, '待处理'), # Unresolved
        (1, '无风险'), # No Risk
        (2, '已修复'), # Fixed
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='compliance_records', 
        db_constraint=False,
        help_text="关联用户"
    )
    change_id = models.CharField(max_length=255, help_text="ChangeId")
    title = models.CharField(max_length=500, blank=True, null=True, help_text="Title")
    update_time = models.DateTimeField(blank=True, null=True, help_text="UpdateTime")
    url = models.CharField(max_length=500, blank=True, null=True, help_text="URL")
    missing_branches = models.JSONField(default=list, help_text="Missing Branches")
    status = models.IntegerField(choices=STATUS_CHOICES, default=0, help_text="状态")
    remark = models.TextField(blank=True, null=True, help_text="备注")

    class Meta:
        db_table = "compliance_record"
        ordering = ("-update_time",)
        verbose_name = "合规风险记录"
        verbose_name_plural = verbose_name
