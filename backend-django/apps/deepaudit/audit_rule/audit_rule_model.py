from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User

from apps.deepaudit.constants import SEVERITY_CHOICES


class AuditRuleSet(RootModel):
    name = models.CharField(max_length=100, db_index=True, verbose_name='规则集名称')
    description = models.TextField(blank=True, null=True, verbose_name='规则集描述')
    language = models.CharField(max_length=50, default='all', verbose_name='适用语言')
    rule_type = models.CharField(max_length=50, default='custom', verbose_name='规则集类型')
    severity_weights = models.JSONField(default=dict, blank=True, verbose_name='严重级别权重')
    is_default = models.BooleanField(default=False, db_index=True, verbose_name='默认规则集')
    is_system = models.BooleanField(default=False, db_index=True, verbose_name='系统规则集')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name='deepaudit_rule_sets', verbose_name='创建人')

    class Meta:
        db_table = 'deepaudit_rule_set'
        verbose_name = 'DeepAudit 规则集'
        verbose_name_plural = verbose_name


class AuditRule(RootModel):
    rule_set = models.ForeignKey(AuditRuleSet, on_delete=models.CASCADE, related_name='rules', verbose_name='规则集')
    rule_code = models.CharField(max_length=50, db_index=True, verbose_name='规则编码')
    name = models.CharField(max_length=200, verbose_name='规则名称')
    description = models.TextField(blank=True, null=True, verbose_name='规则描述')
    category = models.CharField(max_length=50, verbose_name='规则分类')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium', verbose_name='严重等级')
    custom_prompt = models.TextField(blank=True, null=True, verbose_name='自定义提示词')
    fix_suggestion = models.TextField(blank=True, null=True, verbose_name='修复建议')
    reference_url = models.CharField(max_length=500, blank=True, null=True, verbose_name='参考链接')
    enabled = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')

    class Meta:
        db_table = 'deepaudit_rule'
        verbose_name = 'DeepAudit 规则'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=['rule_set', 'rule_code'], name='uniq_deepaudit_rule_code'),
        ]
