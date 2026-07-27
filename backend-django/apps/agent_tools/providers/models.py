from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User


class AgentSkillProvider(RootModel):
    """AI 辅助工具平台共用的 OpenAI 兼容模型服务档案。

    类名和数据表名沿用首个 Skill Optimizer 版本，以保证已部署数据无需迁移；
    业务归属已提升为 ``agent_tools.providers``，后续 Agent 可直接复用。
    """

    name = models.CharField(max_length=100, unique=True, verbose_name='档案名称')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tools_agent_skill_providers', null=True, blank=True, verbose_name='所属用户')
    base_url = models.URLField(max_length=500, verbose_name='API Base URL')
    model = models.CharField(max_length=200, verbose_name='模型名称')
    api_key_encrypted = models.TextField(blank=True, default='', verbose_name='加密 API Key')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')
    description = models.TextField(blank=True, default='', verbose_name='说明')

    class Meta:
        # 仅保留历史表名，避免把已有模型配置复制到新表。
        db_table = 'tools_skill_optimizer_provider'
        ordering = ['is_deleted', '-is_active', 'name']
