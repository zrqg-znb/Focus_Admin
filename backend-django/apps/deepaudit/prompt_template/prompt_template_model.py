from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User


class PromptTemplate(RootModel):
    name = models.CharField(max_length=100, db_index=True, verbose_name='模板名称')
    description = models.TextField(blank=True, null=True, verbose_name='模板描述')
    template_type = models.CharField(max_length=50, default='system', verbose_name='模板类型')
    content_zh = models.TextField(blank=True, null=True, verbose_name='中文提示词')
    content_en = models.TextField(blank=True, null=True, verbose_name='英文提示词')
    variables = models.JSONField(default=dict, blank=True, verbose_name='模板变量')
    is_default = models.BooleanField(default=False, db_index=True, verbose_name='默认模板')
    is_system = models.BooleanField(default=False, db_index=True, verbose_name='系统模板')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name='deepaudit_prompt_templates', verbose_name='创建人')

    class Meta:
        db_table = 'deepaudit_prompt_template'
        verbose_name = 'DeepAudit 提示词模板'
        verbose_name_plural = verbose_name
