"""Agent Tools 的异步任务入口，独立队列避免与其他应用争抢 Worker。"""

import logging

from celery import shared_task
from django.conf import settings
from kombu.exceptions import OperationalError

SKILL_OPTIMIZER_QUEUE = getattr(settings, 'SKILL_OPTIMIZER_QUEUE', 'skill_optimizer')
logger = logging.getLogger(__name__)


def dispatch_agent_skill_run(task, run_id: str) -> str | None:
    """投递优化任务；队列不可用时向调用方返回可读错误。"""
    try:
        task.apply_async(args=[run_id], queue=SKILL_OPTIMIZER_QUEUE)
        return None
    except OperationalError as exc:
        logger.exception('Skill Optimizer task dispatch failed: %s', exc)
        return f'任务队列不可用，请启动 Redis 与 Celery Worker 后重试：{exc}'


@shared_task(name='agent_tools.skill_optimizer.run')
def run_agent_skill(run_id: str) -> None:
    """运行一条 Skill Optimizer 优化任务。"""
    from .skill_optimizer.services import execute_run
    execute_run(run_id)
