import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.exceptions import InvalidChannelLayerError
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


TASK_GROUP_PREFIX = 'deepaudit_task_'


def task_group_name(task_id: str) -> str:
    return f'{TASK_GROUP_PREFIX}{task_id}'



def push_task_event(task_id: str, payload: dict[str, Any]) -> None:
    try:
        channel_layer = get_channel_layer()
    except (ImportError, InvalidChannelLayerError, ModuleNotFoundError) as exc:
        logger.warning('deepaudit websocket backend unavailable, skip push: %s', exc)
        return
    if channel_layer is None:
        logger.warning('channel_layer is not configured, skip deepaudit websocket push')
        return
    try:
        async_to_sync(channel_layer.group_send)(
            task_group_name(task_id),
            {
                'type': 'deepaudit.task.event',
                'payload': payload,
            },
        )
    except Exception as exc:
        logger.warning('deepaudit websocket push failed, skip event delivery: %s', exc)
