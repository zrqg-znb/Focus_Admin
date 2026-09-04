from django.db import models
from django.utils import timezone

from common.fu_model import RootModel


SEVERITY_CHOICES = (
    ('blocker', 'Blocker'),
    ('critical', 'Critical'),
    ('major', 'Major'),
    ('minor', 'Minor'),
    ('info', 'Info'),
)
SEVERITIES = tuple(item[0] for item in SEVERITY_CHOICES)
ACTIVE_STATUS_CHOICES = ((True, '启用'), (False, '停用'))
FINDING_SHIELD_STATUS_CHOICES = (
    ('Normal', '正常'),
    ('Pending', '屏蔽申请中'),
    ('Shielded', '已屏蔽'),
    ('Rejected', '已驳回'),
)
APPLICATION_STATUS_CHOICES = (
    ('Pending', '待审批'),
    ('Approved', '已通过'),
    ('Rejected', '已驳回'),
)


class GovernanceProject(RootModel):
    """代码问题治理项目。"""

    name = models.CharField(max_length=160, verbose_name='项目名称')
    code = models.CharField(max_length=80, unique=True, verbose_name='项目编码')
    repository = models.CharField(max_length=500, blank=True, default='', verbose_name='仓库地址')
    branch = models.CharField(max_length=160, blank=True, default='master', verbose_name='默认分支')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')

    class Meta:
        db_table = 'agent_tools_governance_project'
        ordering = ['is_deleted', '-sort', 'name']


class GovernanceResponsibility(RootModel):
    """代码问题治理责任田及其负责人、审批人范围。"""

    name = models.CharField(max_length=160, verbose_name='责任田名称')
    code = models.CharField(max_length=80, unique=True, verbose_name='责任田编码')
    owner = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='governance_responsibility_owned', verbose_name='负责人',
    )
    approvers = models.ManyToManyField(
        'core.User', blank=True, related_name='governance_responsibility_approvers',
        verbose_name='审批人员',
    )
    description = models.TextField(blank=True, default='', verbose_name='描述')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')

    class Meta:
        db_table = 'agent_tools_governance_responsibility'
        ordering = ['is_deleted', '-sort', 'name']


class GovernanceProjectResponsibility(RootModel):
    """项目与责任田的治理范围关联。"""

    project = models.ForeignKey(
        GovernanceProject, on_delete=models.CASCADE, related_name='responsibility_links', verbose_name='项目',
    )
    responsibility = models.ForeignKey(
        GovernanceResponsibility, on_delete=models.CASCADE, related_name='project_links', verbose_name='责任田',
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')
    remark = models.CharField(max_length=500, blank=True, default='', verbose_name='关联备注')

    class Meta:
        db_table = 'agent_tools_governance_project_responsibility'
        constraints = [
            models.UniqueConstraint(fields=['project', 'responsibility'], name='governance_project_resp_unique'),
        ]
        ordering = ['is_deleted', '-sort', 'project__name', 'responsibility__name']


class GovernanceScanReport(RootModel):
    """第三方扫描报告及解析摘要。"""

    STATUS_CHOICES = (('processing', '解析中'), ('success', '成功'), ('failed', '失败'))
    SOURCE_CHOICES = (('upload', '页面上传'), ('api', '接口接入'))

    project_responsibility = models.ForeignKey(
        GovernanceProjectResponsibility, on_delete=models.PROTECT, related_name='reports', verbose_name='项目责任田',
    )
    repository = models.CharField(max_length=500, blank=True, default='', verbose_name='报告仓库')
    tool_name = models.CharField(max_length=120, verbose_name='扫描工具')
    complete = models.BooleanField(default=True, verbose_name='扫描是否完成')
    raw_created_at = models.CharField(max_length=80, blank=True, default='', verbose_name='原始创建时间')
    raw_payload = models.JSONField(default=dict, verbose_name='原始 JSON')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing', db_index=True, verbose_name='解析状态')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='api', verbose_name='接入来源')
    finding_count = models.PositiveIntegerField(default=0, verbose_name='问题数')
    blocker_count = models.PositiveIntegerField(default=0, verbose_name='Blocker 数')
    critical_count = models.PositiveIntegerField(default=0, verbose_name='Critical 数')
    major_count = models.PositiveIntegerField(default=0, verbose_name='Major 数')
    minor_count = models.PositiveIntegerField(default=0, verbose_name='Minor 数')
    info_count = models.PositiveIntegerField(default=0, verbose_name='Info 数')
    error_message = models.TextField(blank=True, default='', verbose_name='错误信息')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='解析完成时间')

    class Meta:
        db_table = 'agent_tools_governance_scan_report'
        ordering = ['-sys_create_datetime']
        indexes = [
            models.Index(fields=['project_responsibility', '-sys_create_datetime'], name='governance_report_scope_idx'),
            models.Index(fields=['status', '-sys_create_datetime'], name='governance_report_status_idx'),
        ]


class GovernanceFinding(RootModel):
    """项目责任田范围内跨扫描任务稳定归并的问题。"""

    project_responsibility = models.ForeignKey(
        GovernanceProjectResponsibility, on_delete=models.CASCADE, related_name='findings', verbose_name='项目责任田',
    )
    identity_key = models.CharField(max_length=512, verbose_name='平台稳定身份')
    issue_key = models.CharField(max_length=512, blank=True, default='', verbose_name='工具 issue_key')
    fingerprint = models.CharField(max_length=512, blank=True, default='', verbose_name='指纹')
    rule_id = models.CharField(max_length=255, blank=True, default='', verbose_name='规则 ID')
    rule_version = models.CharField(max_length=80, blank=True, default='', verbose_name='规则版本')
    category = models.CharField(max_length=160, blank=True, default='', verbose_name='问题类别')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info', db_index=True, verbose_name='严重级别')
    shield_status = models.CharField(
        max_length=20, choices=FINDING_SHIELD_STATUS_CHOICES, default='Normal', db_index=True, verbose_name='屏蔽状态',
    )
    first_seen_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='首次发现时间')
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='最近发现时间')
    first_report = models.ForeignKey(
        GovernanceScanReport, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='first_findings', verbose_name='首次扫描报告',
    )
    last_report = models.ForeignKey(
        GovernanceScanReport, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='last_findings', verbose_name='最近扫描报告',
    )
    latest_tool_name = models.CharField(max_length=120, blank=True, default='', verbose_name='最近扫描工具')
    latest_file_path = models.CharField(max_length=500, blank=True, default='', verbose_name='最近文件路径')
    latest_line = models.PositiveIntegerField(default=0, verbose_name='最近行号')
    latest_message = models.TextField(blank=True, default='', verbose_name='最近问题描述')

    class Meta:
        db_table = 'agent_tools_governance_finding'
        constraints = [
            models.UniqueConstraint(fields=['project_responsibility', 'identity_key'], name='governance_scope_identity_unique'),
        ]
        indexes = [
            models.Index(fields=['project_responsibility', 'shield_status'], name='governance_finding_status_idx'),
            models.Index(fields=['project_responsibility', '-last_seen_at'], name='governance_finding_seen_idx'),
        ]
        ordering = ['severity', '-last_seen_at']


class GovernanceFindingOccurrence(RootModel):
    """单次扫描中的问题命中快照。"""

    report = models.ForeignKey(
        GovernanceScanReport, on_delete=models.CASCADE, related_name='occurrences', verbose_name='扫描报告',
    )
    finding = models.ForeignKey(
        GovernanceFinding, on_delete=models.CASCADE, related_name='occurrences', verbose_name='稳定问题',
    )
    file_path = models.CharField(max_length=500, blank=True, default='', verbose_name='文件路径')
    start_line = models.PositiveIntegerField(default=0, verbose_name='起始行')
    end_line = models.PositiveIntegerField(default=0, verbose_name='结束行')
    message = models.TextField(blank=True, default='', verbose_name='问题描述')
    evidence = models.JSONField(default=list, verbose_name='证据')
    identity = models.JSONField(default=dict, verbose_name='身份数据')
    legacy_fingerprints = models.JSONField(default=list, verbose_name='历史指纹')
    confidence = models.FloatField(null=True, blank=True, verbose_name='置信度')
    raw_finding = models.JSONField(default=dict, verbose_name='原始 finding')

    class Meta:
        db_table = 'agent_tools_governance_finding_occurrence'
        ordering = ['-sys_create_datetime']
        indexes = [
            models.Index(fields=['report', 'finding'], name='gov_occ_report_find_idx'),
            models.Index(fields=['file_path', 'start_line'], name='gov_occ_location_idx'),
        ]


class GovernanceShieldApplication(RootModel):
    """稳定问题的屏蔽申请单。"""

    project_responsibility = models.ForeignKey(
        GovernanceProjectResponsibility, on_delete=models.PROTECT, related_name='shield_applications', verbose_name='项目责任田',
    )
    finding = models.ForeignKey(
        GovernanceFinding, on_delete=models.PROTECT, related_name='shield_applications', verbose_name='稳定问题',
    )
    applicant = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='governance_applications', verbose_name='申请人')
    approver = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='governance_approvals', verbose_name='指定审批人')
    reason = models.TextField(verbose_name='屏蔽理由')
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS_CHOICES, default='Pending', db_index=True, verbose_name='申请状态')
    audit_comment = models.TextField(blank=True, default='', verbose_name='审批意见')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审批时间')

    class Meta:
        db_table = 'agent_tools_governance_shield_application'
        ordering = ['-sys_create_datetime']
        indexes = [
            models.Index(fields=['approver', 'status'], name='gov_app_approver_st_idx'),
            models.Index(fields=['finding', 'status'], name='gov_app_finding_st_idx'),
        ]


class GovernanceShieldAuditLog(RootModel):
    """屏蔽申请状态变更审计日志。"""

    ACTION_CHOICES = (('create', '提交申请'), ('approve', '审批通过'), ('reject', '审批驳回'))
    application = models.ForeignKey(
        GovernanceShieldApplication, on_delete=models.CASCADE, related_name='audit_logs', verbose_name='申请单',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='操作类型')
    operator = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='governance_audit_logs', verbose_name='操作人')
    from_status = models.CharField(max_length=20, blank=True, default='', verbose_name='原状态')
    to_status = models.CharField(max_length=20, verbose_name='新状态')
    comment = models.TextField(blank=True, default='', verbose_name='操作说明')

    class Meta:
        db_table = 'agent_tools_governance_shield_audit_log'
        ordering = ['sys_create_datetime']
