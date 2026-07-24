from django.apps import AppConfig


class ToolsConfig(AppConfig):
    """Agent Tools 统一应用配置。"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agent_tools'
    # 保持历史 migration label，避免已部署的 tools 迁移被视为新应用。
    label = 'tools'
    verbose_name = 'Agent Tools'
