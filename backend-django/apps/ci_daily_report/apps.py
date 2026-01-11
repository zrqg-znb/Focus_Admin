from django.apps import AppConfig

class DataReportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ci_daily_report'
    verbose_name = 'CI 每日集成报告'
