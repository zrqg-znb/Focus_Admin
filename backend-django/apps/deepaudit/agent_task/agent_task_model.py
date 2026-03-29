from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User

from apps.deepaudit.constants import AGENT_TASK_STATUS_CHOICES, FINDING_STATUS_CHOICES, SEVERITY_CHOICES
from apps.deepaudit.project.project_model import AuditProject


class AgentTask(RootModel):
    project = models.ForeignKey(AuditProject, on_delete=models.CASCADE, related_name='agent_tasks', verbose_name='所属项目')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deepaudit_agent_tasks', db_constraint=False, verbose_name='创建人')
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name='任务名称')
    description = models.TextField(blank=True, null=True, verbose_name='任务描述')
    task_type = models.CharField(max_length=50, default='agent_audit', verbose_name='任务类型')
    audit_scope = models.JSONField(default=dict, blank=True, verbose_name='审计范围')
    target_vulnerabilities = models.JSONField(default=list, blank=True, verbose_name='目标漏洞')
    verification_level = models.CharField(max_length=50, default='sandbox', verbose_name='验证级别')
    branch_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='分支名称')
    exclude_patterns = models.JSONField(default=list, blank=True, verbose_name='排除模式')
    target_files = models.JSONField(default=list, blank=True, verbose_name='指定文件')
    agent_config = models.JSONField(default=dict, blank=True, verbose_name='Agent 配置')
    max_iterations = models.IntegerField(default=50, verbose_name='最大迭代次数')
    timeout_seconds = models.IntegerField(default=1800, verbose_name='超时时间')
    status = models.CharField(max_length=20, choices=AGENT_TASK_STATUS_CHOICES, default='pending', db_index=True, verbose_name='状态')
    current_phase = models.CharField(max_length=50, blank=True, null=True, verbose_name='当前阶段')
    current_step = models.CharField(max_length=255, blank=True, null=True, verbose_name='当前步骤')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    total_files = models.IntegerField(default=0, verbose_name='总文件数')
    indexed_files = models.IntegerField(default=0, verbose_name='已索引文件数')
    analyzed_files = models.IntegerField(default=0, verbose_name='已分析文件数')
    files_with_findings = models.IntegerField(default=0, verbose_name='发现问题文件数')
    total_chunks = models.IntegerField(default=0, verbose_name='代码块数')
    total_iterations = models.IntegerField(default=0, verbose_name='迭代次数')
    tool_calls_count = models.IntegerField(default=0, verbose_name='工具调用次数')
    tokens_used = models.IntegerField(default=0, verbose_name='已使用 Token')
    findings_count = models.IntegerField(default=0, verbose_name='发现数')
    verified_count = models.IntegerField(default=0, verbose_name='已验证数')
    false_positive_count = models.IntegerField(default=0, verbose_name='误报数')
    critical_count = models.IntegerField(default=0, verbose_name='Critical 数')
    high_count = models.IntegerField(default=0, verbose_name='High 数')
    medium_count = models.IntegerField(default=0, verbose_name='Medium 数')
    low_count = models.IntegerField(default=0, verbose_name='Low 数')
    quality_score = models.FloatField(default=0.0, verbose_name='质量分')
    security_score = models.FloatField(default=0.0, verbose_name='安全分')
    audit_plan = models.JSONField(default=list, blank=True, verbose_name='审计计划')
    started_at = models.DateTimeField(blank=True, null=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')

    class Meta:
        db_table = 'deepaudit_agent_task'
        verbose_name = 'DeepAudit Agent 任务'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['created_by', 'status']),
        ]

    @property
    def progress_percentage(self) -> float:
        if self.status == 'completed':
            return 100.0
        if self.status in {'failed', 'cancelled'}:
            return 0.0
        if self.total_files <= 0:
            return 0.0
        return round(min(99.0, (self.analyzed_files / max(self.total_files, 1)) * 100), 2)


class AgentFinding(RootModel):
    task = models.ForeignKey(AgentTask, on_delete=models.CASCADE, related_name='findings', verbose_name='所属任务')
    vulnerability_type = models.CharField(max_length=50, db_index=True, verbose_name='漏洞类型')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='low', db_index=True, verbose_name='严重级别')
    title = models.CharField(max_length=255, verbose_name='标题')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    file_path = models.CharField(max_length=1000, blank=True, null=True, verbose_name='文件路径')
    line_start = models.IntegerField(blank=True, null=True, verbose_name='开始行')
    line_end = models.IntegerField(blank=True, null=True, verbose_name='结束行')
    code_snippet = models.TextField(blank=True, null=True, verbose_name='代码片段')
    is_verified = models.BooleanField(default=False, db_index=True, verbose_name='是否验证')
    ai_confidence = models.FloatField(default=0.5, verbose_name='置信度')
    status = models.CharField(max_length=30, choices=FINDING_STATUS_CHOICES, default='open', db_index=True, verbose_name='状态')
    suggestion = models.TextField(blank=True, null=True, verbose_name='修复建议')
    poc = models.JSONField(default=dict, blank=True, verbose_name='PoC 信息')

    class Meta:
        db_table = 'deepaudit_agent_finding'
        verbose_name = 'DeepAudit Agent 发现'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['task', 'severity']),
            models.Index(fields=['task', 'is_verified']),
        ]


class AgentEvent(RootModel):
    task = models.ForeignKey(AgentTask, on_delete=models.CASCADE, related_name='events', verbose_name='所属任务')
    event_type = models.CharField(max_length=50, db_index=True, verbose_name='事件类型')
    phase = models.CharField(max_length=50, blank=True, null=True, verbose_name='阶段')
    message = models.TextField(blank=True, null=True, verbose_name="消息")
    sequence = models.IntegerField(default=0, db_index=True, verbose_name='序号')
    tool_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='工具名称')
    tool_input = models.JSONField(default=dict, blank=True, verbose_name='工具输入')
    tool_output = models.JSONField(default=dict, blank=True, verbose_name='工具输出')
    tool_duration_ms = models.IntegerField(blank=True, null=True, verbose_name='工具耗时')
    progress_percent = models.FloatField(blank=True, null=True, verbose_name='进度')
    finding = models.ForeignKey(AgentFinding, null=True, blank=True, on_delete=models.SET_NULL, related_name='events', verbose_name='关联发现')
    tokens_used = models.IntegerField(blank=True, null=True, verbose_name='Token 数')
    event_metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')

    class Meta:
        db_table = 'deepaudit_agent_event'
        verbose_name = 'DeepAudit Agent 事件'
        verbose_name_plural = verbose_name
        ordering = ['sequence', 'sys_create_datetime']
        indexes = [
            models.Index(fields=['task', 'sequence']),
            models.Index(fields=['task', 'event_type']),
        ]


class AgentCheckpoint(RootModel):
    task = models.ForeignKey(AgentTask, on_delete=models.CASCADE, related_name='persisted_checkpoints', verbose_name='所属任务')
    agent_id = models.CharField(max_length=50, db_index=True, verbose_name='Agent ID')
    agent_name = models.CharField(max_length=255, verbose_name='Agent 名称')
    agent_type = models.CharField(max_length=50, verbose_name='Agent 类型')
    parent_agent_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='父 Agent ID')
    state_data = models.JSONField(default=dict, blank=True, verbose_name='状态快照')
    iteration = models.IntegerField(default=0, verbose_name='迭代次数')
    status = models.CharField(max_length=30, db_index=True, verbose_name='状态')
    total_tokens = models.IntegerField(default=0, verbose_name='累计 Token')
    tool_calls = models.IntegerField(default=0, verbose_name='工具调用次数')
    findings_count = models.IntegerField(default=0, verbose_name='发现数量')
    checkpoint_type = models.CharField(max_length=30, default='auto', verbose_name='检查点类型')
    checkpoint_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='检查点名称')
    checkpoint_metadata = models.JSONField(default=dict, blank=True, verbose_name='检查点元数据')

    class Meta:
        db_table = 'deepaudit_agent_checkpoint'
        verbose_name = 'DeepAudit Agent 检查点'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['task', 'agent_id']),
            models.Index(fields=['task', 'sys_create_datetime']),
            models.Index(fields=['task', 'checkpoint_type']),
        ]
