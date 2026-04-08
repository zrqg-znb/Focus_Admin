from django.apps import AppConfig


class AutoTestReportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auto_test_report'
    label = 'auto_test_report'
    verbose_name = '自动化测试日报'
