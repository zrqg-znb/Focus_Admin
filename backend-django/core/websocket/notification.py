#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket notification publisher.
"""
import logging
from typing import Any, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def push_user_notification(user_id: str, message: str, data: Optional[dict[str, Any]] = None):
    """
    Push notification event to a specific user's websocket group.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("channel_layer is not configured, skip websocket push")
        return

    async_to_sync(channel_layer.group_send)(
        f"notifications_user_{user_id}",
        {
            "type": "notification_message",
            "message": message,
            "data": data or {},
        },
    )

