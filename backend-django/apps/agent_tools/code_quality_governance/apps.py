from django.apps import AppConfig


class CodeQualityGovernanceConfig(AppConfig):
    """代码问题治理 Django 应用配置。"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agent_tools.code_quality_governance'
    label = 'code_quality_governance'
    verbose_name = '代码问题治理'
