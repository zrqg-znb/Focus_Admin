from django.db import models
from common.fu_model import RootModel
from core.user.user_model import User

class TScanProject(RootModel):
    name = models.CharField(max_length=100, verbose_name="项目名称", help_text="项目名称")
    repo_url = models.CharField(max_length=255, verbose_name="代码仓地址", help_text="代码仓地址")
    branch = models.CharField(max_length=100, default="master", verbose_name="分支", help_text="分支")
    build_cmd = models.TextField(verbose_name="编译命令", help_text="编译命令，例如: make -j4")
    docker_image = models.CharField(max_length=255, verbose_name="Docker镜像", help_text="用于编译和扫描的Docker镜像")
    description = models.TextField(null=True, blank=True, verbose_name="描述", help_text="项目描述")

    class Meta:
        db_table = 'tscan_project'
        verbose_name = 'TScan项目'
        verbose_name_plural = verbose_name
        ordering = ['-sys_create_datetime']

class TScanTask(RootModel):
    STATUS_CHOICES = (
        ('pending', '等待中'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    )
    project = models.ForeignKey(TScanProject, on_delete=models.CASCADE, related_name='tasks', verbose_name="项目")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    log = models.TextField(null=True, blank=True, verbose_name="执行日志")
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    trigger_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="触发人")

    class Meta:
        db_table = 'tscan_task'
        verbose_name = 'TScan任务'
        verbose_name_plural = verbose_name
        ordering = ['-sys_create_datetime']

class TScanResult(RootModel):
    SEVERITY_CHOICES = (
        ('High', '高'),
        ('Medium', '中'),
        ('Low', '低'),
    )
    SHIELD_STATUS_CHOICES = (
        ('Normal', '正常'),
        ('Pending', '屏蔽申请中'),
        ('Shielded', '已屏蔽'),
        ('Rejected', '已驳回'),
    )
    task = models.ForeignKey(TScanTask, on_delete=models.CASCADE, related_name='results', verbose_name="任务")
    file_path = models.CharField(max_length=500, verbose_name="文件路径")
    line_number = models.IntegerField(verbose_name="行号")
    defect_type = models.CharField(max_length=100, verbose_name="缺陷类型")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, verbose_name="严重程度")
    description = models.TextField(verbose_name="缺陷描述")
    fingerprint = models.CharField(max_length=255, db_index=True, verbose_name="缺陷指纹")
    shield_status = models.CharField(max_length=20, choices=SHIELD_STATUS_CHOICES, default='Normal', verbose_name="屏蔽状态")

    class Meta:
        db_table = 'tscan_result'
        verbose_name = 'TScan结果'
        verbose_name_plural = verbose_name
        ordering = ['-severity', 'file_path']

class TScanShieldApplication(RootModel):
    STATUS_CHOICES = (
        ('Pending', '待审批'),
        ('Approved', '已通过'),
        ('Rejected', '已驳回'),
    )
    result = models.ForeignKey(TScanResult, on_delete=models.CASCADE, related_name='shield_applications', verbose_name="关联结果")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tscan_applications', verbose_name="申请人")
    approver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tscan_audits', verbose_name="审批人")
    reason = models.TextField(verbose_name="屏蔽理由")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', verbose_name="申请状态")
    audit_comment = models.TextField(null=True, blank=True, verbose_name="审批意见")

    class Meta:
        db_table = 'tscan_shield_application'
        verbose_name = 'TScan屏蔽申请'
        verbose_name_plural = verbose_name
        ordering = ['-sys_create_datetime']
