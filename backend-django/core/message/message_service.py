#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Message service.
"""
from typing import Iterable, Optional

from django.db import transaction
from django.utils import timezone

from core.message.message_model import Announcement, UserMessage
from core.user.user_model import User
from core.websocket.notification import push_user_notification


ALLOWED_PRIORITIES = {
    UserMessage.PRIORITY_LOW,
    UserMessage.PRIORITY_NORMAL,
    UserMessage.PRIORITY_HIGH,
    UserMessage.PRIORITY_URGENT,
}


def normalize_priority(priority: Optional[str]) -> str:
    if priority in ALLOWED_PRIORITIES:
        return priority
    return UserMessage.PRIORITY_NORMAL


def build_message_payload(message: UserMessage) -> dict:
    sender_name = None
    sender_avatar = None
    if message.sender:
        sender_name = message.sender.name or message.sender.username
        sender_avatar = message.sender.avatar

    return {
        "id": str(message.id),
        "title": message.title,
        "content": message.content,
        "message_type": message.message_type,
        "priority": message.priority,
        "is_read": message.is_read,
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "link": message.link,
        "extra_data": message.extra_data,
        "sender_id": str(message.sender_id) if message.sender_id else None,
        "sender_name": sender_name,
        "sender_avatar": sender_avatar,
        "announcement_id": str(message.announcement_id) if message.announcement_id else None,
        "sys_create_datetime": (
            message.sys_create_datetime.isoformat() if message.sys_create_datetime else None
        ),
        "sys_update_datetime": (
            message.sys_update_datetime.isoformat() if message.sys_update_datetime else None
        ),
    }


def create_message_for_user(
    receiver: User,
    *,
    title: str,
    content: str,
    message_type: str,
    priority: str = UserMessage.PRIORITY_NORMAL,
    sender: Optional[User] = None,
    announcement: Optional[Announcement] = None,
    link: Optional[str] = None,
    extra_data: Optional[dict] = None,
) -> UserMessage:
    message = UserMessage.objects.create(
        receiver=receiver,
        sender=sender,
        announcement=announcement,
        title=title,
        content=content,
        message_type=message_type,
        priority=normalize_priority(priority),
        link=link,
        extra_data=extra_data or None,
        sys_creator=sender,
    )
    payload = build_message_payload(message)
    push_user_notification(str(receiver.id), title, {"notification": payload})
    return message


def send_internal_message(
    *,
    sender: User,
    receivers: Iterable[User],
    title: str,
    content: str,
    priority: str = UserMessage.PRIORITY_NORMAL,
    link: Optional[str] = None,
    extra_data: Optional[dict] = None,
) -> int:
    count = 0
    with transaction.atomic():
        for receiver in receivers:
            create_message_for_user(
                receiver=receiver,
                title=title,
                content=content,
                message_type=UserMessage.TYPE_INTERNAL,
                priority=priority,
                sender=sender,
                link=link,
                extra_data=extra_data,
            )
            count += 1
    return count


def publish_announcement(*, announcement: Announcement, operator: User) -> int:
    if announcement.status == Announcement.STATUS_PUBLISHED:
        return 0

    receiver_queryset = User.objects.filter(is_deleted=False, user_status=1)
    now = timezone.now()

    with transaction.atomic():
        announcement.status = Announcement.STATUS_PUBLISHED
        announcement.publish_at = now
        announcement.sys_modifier = operator
        announcement.save(
            update_fields=["status", "publish_at", "sys_modifier", "sys_update_datetime"]
        )

        count = 0
        for receiver in receiver_queryset:
            create_message_for_user(
                receiver=receiver,
                title=announcement.title,
                content=announcement.content,
                message_type=UserMessage.TYPE_ANNOUNCEMENT,
                priority=announcement.priority,
                sender=operator,
                announcement=announcement,
            )
            count += 1
    return count

