from django.apps import AppConfig


class CmcContributionConfig(AppConfig):
    """CMC 贡献看板应用配置。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cmc_contribution"
    verbose_name = "CMC贡献看板"
