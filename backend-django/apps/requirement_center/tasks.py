import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_requirement_email_notification_task(
    self,
    to_email: str,
    subject: str,
    content: str,
) -> bool:
    if not to_email:
        return False

    email_host = str(getattr(settings, "EMAIL_HOST", "") or "").strip()
    host_user = str(getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    host_password = str(getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip()

    if not email_host or not host_user or not host_password:
        logger.info("SMTP 未完整配置，跳过邮件发送: to=%s, subject=%s", to_email, subject)
        return False

    send_mail(
        subject=subject,
        message=content,
        from_email=host_user,
        recipient_list=[to_email],
        fail_silently=False,
    )
    return True
