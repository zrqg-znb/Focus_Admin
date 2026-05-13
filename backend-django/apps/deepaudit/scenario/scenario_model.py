from django.db import models

from apps.deepaudit.audit_rule.audit_rule_model import AuditRuleSet
from apps.deepaudit.prompt_template.prompt_template_model import PromptTemplate
from common.fu_model import RootModel
from core.user.user_model import User


class ScenarioObjectiveType(models.TextChoices):
    AUDIT = 'audit', '漏洞审计'
    INVENTORY = 'inventory', '代码梳理'


class AuditScenarioProfile(RootModel):
    scenario_key = models.CharField(max_length=100, unique=True, db_index=True, verbose_name='场景键')
    name = models.CharField(max_length=100, db_index=True, verbose_name='场景名称')
    description = models.TextField(blank=True, null=True, verbose_name='场景描述')
    objective_type = models.CharField(
        max_length=20,
        choices=ScenarioObjectiveType.choices,
        default=ScenarioObjectiveType.AUDIT,
        db_index=True,
        verbose_name='输出目标',
    )
    prompt_template = models.ForeignKey(
        PromptTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name='deepaudit_scenarios',
        verbose_name='提示词模板',
    )
    rule_set = models.ForeignKey(
        AuditRuleSet,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name='deepaudit_scenarios',
        verbose_name='规则集',
    )
    knowledge_modules = models.JSONField(default=list, blank=True, verbose_name='知识模块')
    tool_policy = models.JSONField(default=dict, blank=True, verbose_name='工具策略')
    is_default = models.BooleanField(default=False, db_index=True, verbose_name='默认场景')
    is_system = models.BooleanField(default=False, db_index=True, verbose_name='系统场景')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name='deepaudit_scenarios',
        verbose_name='创建人',
    )

    class Meta:
        db_table = 'deepaudit_scenario_profile'
        verbose_name = 'DeepAudit 场景'
        verbose_name_plural = verbose_name
