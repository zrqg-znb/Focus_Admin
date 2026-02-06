from django.db import models
from common.fu_model import RootModel
from core.user.user_model import User
import uuid

class ScanProject(RootModel):
    name = models.CharField(max_length=100, verbose_name="项目名称", help_text="项目名称")
    repo_url = models.CharField(max_length=255, verbose_name="代码仓地址", help_text="代码仓地址")
    branch = models.CharField(max_length=100, default="master", verbose_name="分支", help_text="分支")
    project_key = models.CharField(max_length=64, unique=True, default=uuid.uuid4, verbose_name="项目标识", help_text="用于流水线认证的唯一标识")
    description = models.TextField(null=True, blank=True, verbose_name="描述", help_text="项目描述")
    caretaker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='scan_projects', verbose_name="数据看护责任人")

    class Meta:
        db_table = 'scan_project'
        verbose_name = '代码扫描项目'
        verbose_name_plural = verbose_name
        ordering = ['-sys_create_datetime']

class ScanTask(RootModel):
    STATUS_CHOICES = (
        ('pending', '等待中'),
        ('processing', '解析中'),
        ('success', '成功'),
        ('failed', '失败'),
    )
    SOURCE_CHOICES = (
        ('pipeline', '流水线上传'),
        ('manual', '手动触发'),
    )
    project = models.ForeignKey(ScanProject, on_delete=models.CASCADE, related_name='tasks', verbose_name="项目")
    tool_name = models.CharField(max_length=50, default='tscan', verbose_name="扫描工具", help_text="如: tscan, cppcheck")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual', verbose_name="来源")
    
    report_file = models.CharField(max_length=500, null=True, blank=True, verbose_name="报告文件路径")
    log = models.TextField(null=True, blank=True, verbose_name="处理日志")
    
    scan_time = models.DateTimeField(null=True, blank=True, verbose_name="扫描时间")
    processed_time = models.DateTimeField(null=True, blank=True, verbose_name="解析完成时间")

    class Meta:
        db_table = 'scan_task'
        verbose_name = '扫描任务'
        verbose_name_plural = verbose_name
        ordering = ['-sys_create_datetime']

class ScanResult(RootModel):
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
    task = models.ForeignKey(ScanTask, on_delete=models.CASCADE, related_name='results', verbose_name="任务")
    
    file_path = models.CharField(max_length=500, verbose_name="文件路径")
    line_number = models.IntegerField(verbose_name="行号")
    defect_type = models.CharField(max_length=100, verbose_name="缺陷类型")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, verbose_name="严重程度")
    description = models.TextField(verbose_name="缺陷描述")
    
    fingerprint = models.CharField(max_length=255, db_index=True, verbose_name="缺陷指纹")
    shield_status = models.CharField(max_length=20, choices=SHIELD_STATUS_CHOICES, default='Normal', verbose_name="屏蔽状态")
    
    # 增强字段
    help_info = models.TextField(null=True, blank=True, verbose_name="修复建议")
    code_snippet = models.TextField(null=True, blank=True, verbose_name="代码片段")

    class Meta:
        db_table = 'scan_result'
        verbose_name = '扫描结果'
        verbose_name_plural = verbose_name
        ordering = ['-severity', 'file_path']

class ShieldApplication(RootModel):
    STATUS_CHOICES = (
        ('Pending', '待审批'),
        ('Approved', '已通过'),
        ('Rejected', '已驳回'),
    )
    result = models.ForeignKey(ScanResult, on_delete=models.CASCADE, related_name='shield_applications', verbose_name="关联结果")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scan_applications', verbose_name="申请人")
    approver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scan_audits', null=True, blank=True, verbose_name="审批人")
    reason = models.TextField(verbose_name="屏蔽理由")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', verbose_name="申请状态")
    audit_comment = models.TextField(null=True, blank=True, verbose_name="审批意见")

    class Meta:
        db_table = 'scan_shield_application'
        verbose_name = '屏蔽申请'
        verbose_name_plural = verbose_name
        ordering = ['-sys_create_datetime']
