from django.db import models
from common.fu_model import RootModel
from apps.project_manager.project.project_model import Project


class Milestone(RootModel):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='milestone', verbose_name="所属项目")
    qg1_date = models.DateField(null=True, blank=True, verbose_name="QG1时间")
    qg2_date = models.DateField(null=True, blank=True, verbose_name="QG2时间")
    qg3_date = models.DateField(null=True, blank=True, verbose_name="QG3时间")
    qg4_date = models.DateField(null=True, blank=True, verbose_name="QG4时间")
    qg5_date = models.DateField(null=True, blank=True, verbose_name="QG5时间")
    qg6_date = models.DateField(null=True, blank=True, verbose_name="QG6时间")
    qg7_date = models.DateField(null=True, blank=True, verbose_name="QG7时间")
    qg8_date = models.DateField(null=True, blank=True, verbose_name="QG8时间")

    class Meta:
        db_table = 'pm_milestone'
        verbose_name = '里程碑'
        verbose_name_plural = verbose_name


class MilestoneQGConfig(RootModel):
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='qg_configs', verbose_name="所属里程碑")
    qg_name = models.CharField(max_length=32, verbose_name="QG点名称")  # e.g., QG1, QG2
    target_di = models.FloatField(null=True, blank=True, verbose_name="目标DI值")
    enabled = models.BooleanField(default=True, verbose_name="是否启用")
    is_delayed = models.BooleanField(default=False, verbose_name="是否延期")

    class Meta:
        db_table = 'pm_milestone_qg_config'
        verbose_name = '里程碑QG配置'
        verbose_name_plural = verbose_name
        unique_together = ('milestone', 'qg_name')


class MilestoneRiskItem(RootModel):
    RISK_TYPE_CHOICES = (
        ('dts', 'DTS问题单'),
        ('di', 'DI值超标'),
    )
    STATUS_CHOICES = (
        ('pending', '待处理'),
        ('confirmed', '已确认'),
        ('closed', '已关闭'),
    )

    config = models.ForeignKey(MilestoneQGConfig, on_delete=models.CASCADE, related_name='risks', verbose_name="所属配置")
    record_date = models.DateField(verbose_name="记录日期")
    risk_type = models.CharField(max_length=16, choices=RISK_TYPE_CHOICES, verbose_name="风险类型")
    description = models.TextField(verbose_name="风险描述")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    
    manager_confirm_note = models.TextField(blank=True, default="", verbose_name="经理确认备注")
    manager_confirm_at = models.DateTimeField(null=True, blank=True, verbose_name="确认时间")
    manager = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="confirmed_risks", verbose_name="确认人")

    class Meta:
        db_table = 'pm_milestone_risk_item'
        verbose_name = '里程碑QG风险项'
        verbose_name_plural = verbose_name


class MilestoneRiskLog(RootModel):
    ACTION_CHOICES = (
        ('create', '创建'),
        ('update', '更新'),
        ('confirm', '确认'),
        ('close', '关闭'),
    )

    risk_item = models.ForeignKey(MilestoneRiskItem, on_delete=models.CASCADE, related_name='logs', verbose_name="所属风险项")
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name="操作类型")
    operator = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="操作人")
    note = models.TextField(blank=True, default="", verbose_name="操作备注")
    
    class Meta:
        db_table = 'pm_milestone_risk_log'
        verbose_name = '里程碑QG风险日志'
        verbose_name_plural = verbose_name

