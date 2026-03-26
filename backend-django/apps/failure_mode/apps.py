from django.apps import AppConfig


class FailureModeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.failure_mode'
    verbose_name = '故障管理'

