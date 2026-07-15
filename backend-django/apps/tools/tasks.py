"""Tools 的异步任务入口，独立队列避免与其他应用争抢 Worker。"""

import logging

from celery import shared_task
from django.conf import settings
from kombu.exceptions import OperationalError

AGENT_SKILLS_QUEUE = getattr(settings, 'AGENT_SKILLS_QUEUE', 'agent_skills')
logger = logging.getLogger(__name__)


def dispatch_agent_skill_run(task, run_id: str) -> str | None:
    """投递优化任务；队列不可用时向调用方返回可读错误。"""
    try:
        task.apply_async(args=[run_id], queue=AGENT_SKILLS_QUEUE)
        return None
    except OperationalError as exc:
        logger.exception('Agent Skills task dispatch failed: %s', exc)
        return f'任务队列不可用，请启动 Redis 与 Celery Worker 后重试：{exc}'


@shared_task(name='tools.agent_skills.run')
def run_agent_skill(run_id: str) -> None:
    """运行一条 Agent Skills 优化任务。"""
    from .agent_skills.services import execute_run
    execute_run(run_id)
