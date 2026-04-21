import os

from celery import Celery, platforms
from celery.signals import worker_process_init
from django.conf import settings
from django.utils.log import configure_logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', "application.settings")

app = Celery(f"application")

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.conf.broker_connection_retry_on_startup = True
app.conf.worker_hijack_root_logger = False
platforms.C_FORCE_ROOT = True


@worker_process_init.connect
def apply_django_logging_to_celery_worker(**_kwargs):
    configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
