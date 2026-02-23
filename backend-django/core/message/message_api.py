#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Message API.
"""
from typing import List, Optional

from django.db.models import CharField, F, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import paginate

from common.fu_pagination import MyPagination
from core.message.message_model import Announcement, UserMessage
from core.message.message_schema import (
    AnnouncementFilters,
    AnnouncementSchemaIn,
    AnnouncementSchemaOut,
    AnnouncementSchemaPatch,
    InternalMessageSendIn,
    MessageActionOut,
    UnreadCountOut,
    UserMessageOut,
)
from core.message.message_service import (
    normalize_priority,
    publish_announcement,
    send_internal_message,
)
from core.user.user_model import User

router = Router()


def _require_superuser(request):
    user = request.auth
    if not user or not getattr(user, "is_superuser", False):
        raise HttpError(403, "仅超级管理员可执行该操作")
    return user


@router.get("/message/inbox", response=List[UserMessageOut], summary="获取当前用户消息列表")
@paginate(MyPagination)
def list_user_messages(
    request,
    is_read: Optional[bool] = Query(None),
    message_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
):
    queryset = UserMessage.objects.filter(receiver_id=request.auth.id)

    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    if message_type:
        queryset = queryset.filter(message_type=message_type)
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword) | Q(content__icontains=keyword)
        )

    queryset = queryset.annotate(
        sender_name=Coalesce(
            F("sender__name"),
            F("sender__username"),
            output_field=CharField(),
        ),
        sender_avatar=F("sender__avatar"),
    ).values(
        "id",
        "title",
        "content",
        "message_type",
        "priority",
        "is_read",
        "read_at",
        "link",
        "extra_data",
        "sender_id",
        "sender_name",
        "sender_avatar",
        "announcement_id",
        "sys_create_datetime",
        "sys_update_datetime",
    )

    return queryset


@router.get("/message/unread/count", response=UnreadCountOut, summary="获取当前用户未读数")
def get_unread_count(request):
    unread_count = UserMessage.objects.filter(
        receiver_id=request.auth.id,
        is_read=False,
    ).count()
    return {"unread_count": unread_count}


@router.post("/message/send", response=MessageActionOut, summary="发送站内信")
def send_message(request, data: InternalMessageSendIn):
    operator = _require_superuser(request)

    receiver_ids = list(set(data.receiver_ids))
    if not receiver_ids:
        raise HttpError(400, "receiver_ids 不能为空")

    receivers = list(
        User.objects.filter(id__in=receiver_ids, is_deleted=False, user_status=1)
    )
    if not receivers:
        raise HttpError(400, "接收用户不存在或不可用")

    count = send_internal_message(
        sender=operator,
        receivers=receivers,
        title=data.title,
        content=data.content,
        priority=normalize_priority(data.priority),
        link=data.link,
        extra_data=data.extra_data,
    )
    return {"msg": "站内信发送成功", "count": count}


@router.post("/message/{message_id}/read", response=MessageActionOut, summary="标记单条已读")
def mark_message_read(request, message_id: str):
    message = get_object_or_404(UserMessage, id=message_id, receiver_id=request.auth.id)
    if not message.is_read:
        message.is_read = True
        message.read_at = timezone.now()
        message.sys_modifier = request.auth
        message.save(update_fields=["is_read", "read_at", "sys_modifier", "sys_update_datetime"])
    return {"msg": "已标记为已读", "count": 1}


@router.post("/message/read/all", response=MessageActionOut, summary="标记全部已读")
def mark_all_messages_read(request):
    now = timezone.now()
    count = UserMessage.objects.filter(receiver_id=request.auth.id, is_read=False).update(
        is_read=True,
        read_at=now,
    )
    return {"msg": "全部消息已标记为已读", "count": count}


@router.delete("/message/{message_id}", response=MessageActionOut, summary="删除消息")
def delete_message(request, message_id: str):
    message = get_object_or_404(UserMessage, id=message_id, receiver_id=request.auth.id)
    message.delete()
    return {"msg": "删除成功", "count": 1}


@router.delete("/message/clear/all", response=MessageActionOut, summary="清空当前用户消息")
def clear_messages(request):
    count, _ = UserMessage.objects.filter(receiver_id=request.auth.id).delete()
    return {"msg": "消息已清空", "count": count}


@router.get("/announcement", response=List[AnnouncementSchemaOut], summary="获取公告列表")
@paginate(MyPagination)
def list_announcements(request, filters: AnnouncementFilters = Query(...)):
    queryset = Announcement.objects.all()
    if not getattr(request.auth, "is_superuser", False):
        queryset = queryset.filter(status=Announcement.STATUS_PUBLISHED)
    queryset = filters.filter(queryset)
    return queryset


@router.post("/announcement", response=AnnouncementSchemaOut, summary="创建公告")
def create_announcement(request, data: AnnouncementSchemaIn):
    operator = _require_superuser(request)
    announcement = Announcement.objects.create(
        title=data.title,
        content=data.content,
        priority=normalize_priority(data.priority),
        expire_at=data.expire_at,
        sys_creator=operator,
    )
    return announcement


@router.put("/announcement/{announcement_id}", response=AnnouncementSchemaOut, summary="更新公告")
def update_announcement(request, announcement_id: str, data: AnnouncementSchemaPatch):
    operator = _require_superuser(request)
    announcement = get_object_or_404(Announcement, id=announcement_id)

    payload = data.dict(exclude_none=True)
    if "priority" in payload:
        payload["priority"] = normalize_priority(payload["priority"])

    for key, value in payload.items():
        setattr(announcement, key, value)
    announcement.sys_modifier = operator
    announcement.save()
    return announcement


@router.post("/announcement/{announcement_id}/publish", response=MessageActionOut, summary="发布公告")
def do_publish_announcement(request, announcement_id: str):
    operator = _require_superuser(request)
    announcement = get_object_or_404(Announcement, id=announcement_id)
    count = publish_announcement(announcement=announcement, operator=operator)
    if count == 0:
        return {"msg": "公告已发布，无需重复发布", "count": 0}
    return {"msg": "公告发布成功", "count": count}


@router.post("/announcement/{announcement_id}/revoke", response=MessageActionOut, summary="撤回公告")
def revoke_announcement(request, announcement_id: str):
    operator = _require_superuser(request)
    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.status = Announcement.STATUS_REVOKED
    announcement.sys_modifier = operator
    announcement.save(update_fields=["status", "sys_modifier", "sys_update_datetime"])
    return {"msg": "公告已撤回", "count": 1}


@router.delete("/announcement/{announcement_id}", response=MessageActionOut, summary="删除公告")
def delete_announcement(request, announcement_id: str):
    _require_superuser(request)
    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.delete()
    return {"msg": "公告已删除", "count": 1}
