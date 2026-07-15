from django.apps import AppConfig


class ToolsConfig(AppConfig):
    """Tools 统一应用配置。"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tools'
    verbose_name = 'Tools'
