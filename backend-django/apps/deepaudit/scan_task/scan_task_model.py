from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User

from apps.deepaudit.constants import ISSUE_STATUS_CHOICES, REPOSITORY_TYPE_CHOICES, SCAN_TYPE_CHOICES, SEVERITY_CHOICES, TASK_STATUS_CHOICES
from apps.deepaudit.project.project_model import AuditProject


class AuditTask(RootModel):
    project = models.ForeignKey(AuditProject, on_delete=models.CASCADE, related_name='tasks', verbose_name='所属项目')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deepaudit_tasks', db_constraint=False, verbose_name='创建人')
    task_type = models.CharField(max_length=20, choices=SCAN_TYPE_CHOICES, default='repository', verbose_name='任务类型')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending', db_index=True, verbose_name='任务状态')
    repository_url = models.CharField(max_length=1000, blank=True, null=True, verbose_name='仓库地址快照')
    repository_type = models.CharField(max_length=20, choices=REPOSITORY_TYPE_CHOICES, default='single', verbose_name='仓库类型快照')
    branch_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='分支名称')
    manifest_xml = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Manifest XML')
    group = models.CharField(max_length=255, blank=True, null=True, verbose_name='Group')
    exclude_patterns = models.JSONField(default=list, blank=True, verbose_name='排除模式')
    scan_config = models.JSONField(default=dict, blank=True, verbose_name='扫描配置')
    total_files = models.IntegerField(default=0, verbose_name='总文件数')
    scanned_files = models.IntegerField(default=0, verbose_name='已扫描文件数')
    total_lines = models.IntegerField(default=0, verbose_name='总行数')
    issues_count = models.IntegerField(default=0, verbose_name='问题数')
    quality_score = models.FloatField(default=0.0, verbose_name='质量得分')
    started_at = models.DateTimeField(blank=True, null=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')

    class Meta:
        db_table = 'deepaudit_task'
        verbose_name = 'DeepAudit 扫描任务'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['created_by', 'status']),
        ]


class AuditIssue(RootModel):
    task = models.ForeignKey(AuditTask, on_delete=models.CASCADE, related_name='issues', verbose_name='所属任务')
    file_path = models.CharField(max_length=1000, verbose_name='文件路径')
    line_number = models.IntegerField(blank=True, null=True, verbose_name='行号')
    column_number = models.IntegerField(blank=True, null=True, verbose_name='列号')
    issue_type = models.CharField(max_length=50, db_index=True, verbose_name='问题类型')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='low', db_index=True, verbose_name='严重级别')
    title = models.CharField(max_length=255, verbose_name='问题标题')
    message = models.TextField(blank=True, null=True, verbose_name="兼容消息")
    description = models.TextField(blank=True, null=True, verbose_name='问题描述')
    suggestion = models.TextField(blank=True, null=True, verbose_name='修复建议')
    code_snippet = models.TextField(blank=True, null=True, verbose_name='代码片段')
    ai_explanation = models.JSONField(default=dict, blank=True, verbose_name='AI 解释')
    status = models.CharField(max_length=30, choices=ISSUE_STATUS_CHOICES, default='open', db_index=True, verbose_name='问题状态')
    resolved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name='deepaudit_resolved_issues', verbose_name='处理人')
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name='处理时间')

    class Meta:
        db_table = 'deepaudit_issue'
        verbose_name = 'DeepAudit 问题'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['task', 'severity']),
            models.Index(fields=['task', 'status']),
        ]


class AuditArtifact(RootModel):
    project = models.ForeignKey(AuditProject, null=True, blank=True, on_delete=models.CASCADE, related_name='artifacts', verbose_name='所属项目')
    task = models.ForeignKey(AuditTask, null=True, blank=True, on_delete=models.CASCADE, related_name='artifacts', verbose_name='所属任务')
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name='deepaudit_artifacts', verbose_name='上传者')
    kind = models.CharField(max_length=50, db_index=True, verbose_name='产物类型')
    display_name = models.CharField(max_length=255, verbose_name='显示名称')
    file_path = models.CharField(max_length=1000, verbose_name='文件路径')
    mime_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='MIME 类型')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')

    class Meta:
        db_table = 'deepaudit_artifact'
        verbose_name = 'DeepAudit 产物'
        verbose_name_plural = verbose_name


class InstantAnalysisRecord(RootModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deepaudit_instant_records', db_constraint=False, verbose_name='所属用户')
    language = models.CharField(max_length=50, verbose_name='编程语言')
    code_content = models.TextField(blank=True, default='', verbose_name='代码内容')
    analysis_result = models.JSONField(default=dict, blank=True, verbose_name='分析结果')
    issues_count = models.IntegerField(default=0, verbose_name='问题数')
    quality_score = models.FloatField(default=0.0, verbose_name='质量得分')
    analysis_time = models.FloatField(default=0.0, verbose_name='分析耗时')

    class Meta:
        db_table = 'deepaudit_instant_analysis'
        verbose_name = 'DeepAudit 即时分析记录'
        verbose_name_plural = verbose_name
