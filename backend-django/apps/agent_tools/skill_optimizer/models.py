from django.db import models

from common.fu_model import RootModel
from ..providers.models import AgentSkillProvider


class AgentSkill(RootModel):
    """上传的技能包及其可审计的原始内容。"""

    name = models.CharField(max_length=160, db_index=True, verbose_name='技能名称')
    description = models.TextField(blank=True, default='', verbose_name='技能说明')
    original_filename = models.CharField(max_length=255, verbose_name='原始文件名')
    archive_content = models.BinaryField(verbose_name='原始 ZIP 内容')
    file_manifest = models.JSONField(default=list, verbose_name='文件清单')
    original_skill_md = models.TextField(verbose_name='原始 SKILL.md')
    latest_skill_md = models.TextField(blank=True, default='', verbose_name='最新 SKILL.md')

    class Meta:
        db_table = 'tools_skill_optimizer_skill'
        ordering = ['is_deleted', '-sys_create_datetime']


class AgentSkillRun(RootModel):
    """一次优化任务的配置、状态与结果快照。"""

    STATUS_CHOICES = [
        ('draft', '待配置'), ('queued', '排队中'), ('running', '运行中'),
        ('completed', '已完成'), ('failed', '失败'), ('cancelled', '已取消'),
    ]
    skill = models.ForeignKey(AgentSkill, on_delete=models.CASCADE, related_name='runs', verbose_name='技能')
    provider = models.ForeignKey(AgentSkillProvider, on_delete=models.PROTECT, related_name='runs', verbose_name='模型档案')
    provider_snapshot = models.JSONField(default=dict, verbose_name='模型配置快照')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True, verbose_name='状态')
    max_rounds = models.PositiveSmallIntegerField(default=5, verbose_name='最大轮数')
    scenarios = models.JSONField(default=list, verbose_name='测试场景')
    evaluations = models.JSONField(default=list, verbose_name='评估标准')
    baseline_score = models.FloatField(default=0, verbose_name='基线评分')
    final_score = models.FloatField(default=0, verbose_name='最终评分')
    original_skill_md = models.TextField(blank=True, default='', verbose_name='本次原始 SKILL.md')
    improved_skill_md = models.TextField(blank=True, default='', verbose_name='优化后 SKILL.md')
    error_message = models.TextField(blank=True, default='', verbose_name='失败信息')
    cancel_requested = models.BooleanField(default=False, verbose_name='请求取消')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'tools_skill_optimizer_run'
        indexes = [models.Index(fields=['status', '-sys_create_datetime']), models.Index(fields=['skill', '-sys_create_datetime'])]
        ordering = ['-sys_create_datetime']


class AgentSkillIteration(RootModel):
    """优化任务的基线或单轮变更记录。"""

    run = models.ForeignKey(AgentSkillRun, on_delete=models.CASCADE, related_name='iterations', verbose_name='优化任务')
    round_number = models.PositiveSmallIntegerField(verbose_name='轮次')
    status = models.CharField(max_length=20, db_index=True, verbose_name='状态')
    score_before = models.FloatField(default=0, verbose_name='变更前评分')
    score_after = models.FloatField(default=0, verbose_name='变更后评分')
    kept = models.BooleanField(default=False, verbose_name='是否保留')
    strategy = models.CharField(max_length=80, blank=True, default='', verbose_name='改写策略')
    diagnosis = models.TextField(blank=True, default='', verbose_name='失败诊断')
    description = models.TextField(blank=True, default='', verbose_name='变更说明')
    evaluation_summary = models.JSONField(default=list, verbose_name='评估汇总')

    class Meta:
        db_table = 'tools_skill_optimizer_iteration'
        unique_together = ('run', 'round_number')
        ordering = ['round_number']


class AgentSkillTrace(RootModel):
    """一次模型调用的可审计过程记录，不保存任何认证凭证。"""

    run = models.ForeignKey(AgentSkillRun, on_delete=models.CASCADE, related_name='traces', verbose_name='优化任务')
    round_number = models.PositiveSmallIntegerField(default=0, verbose_name='轮次')
    stage = models.CharField(max_length=50, db_index=True, verbose_name='调用阶段')
    status = models.CharField(max_length=20, default='running', db_index=True, verbose_name='调用状态')
    request_content = models.TextField(blank=True, default='', verbose_name='请求内容')
    response_content = models.TextField(blank=True, default='', verbose_name='响应内容')
    error_message = models.TextField(blank=True, default='', verbose_name='失败信息')
    duration_ms = models.PositiveIntegerField(default=0, verbose_name='耗时毫秒')

    class Meta:
        db_table = 'tools_skill_optimizer_trace'
        ordering = ['sys_create_datetime']
        indexes = [models.Index(fields=['run', 'sys_create_datetime'])]
