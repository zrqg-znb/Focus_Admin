from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from kombu.exceptions import OperationalError


DEEPAUDIT_QUEUE = getattr(settings, 'DEEPAUDIT_QUEUE', 'deepaudit')
logger = logging.getLogger(__name__)


def dispatch_deepaudit_task(task, *args: str, queue: str = DEEPAUDIT_QUEUE) -> str | None:
    try:
        task.apply_async(args=list(args), queue=queue)
        return None
    except OperationalError as exc:
        logger.exception('DeepAudit task dispatch failed: %s', exc)
        return f'任务队列不可用，请启动 Redis 与 Celery Worker 后重试：{exc}'


@shared_task(name='deepaudit.run_scan_task')
def run_scan_task(task_id: str) -> None:
    from apps.deepaudit.scan_task.scan_task_services import execute_scan_task

    execute_scan_task(task_id)


@shared_task(name='deepaudit.run_agent_task')
def run_agent_task(task_id: str) -> None:
    from apps.deepaudit.agent_task.agent_task_services import execute_agent_task

    execute_agent_task(task_id)
