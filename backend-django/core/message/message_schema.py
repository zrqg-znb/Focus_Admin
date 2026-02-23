#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Message schemas.
"""
from datetime import datetime
from typing import Any, Optional

from ninja import Field, FilterSchema, ModelSchema, Schema

from core.message.message_model import Announcement


class AnnouncementFilters(FilterSchema):
    title: Optional[str] = Field(None, q="title__icontains", alias="title")
    status: Optional[int] = Field(None, alias="status")


class AnnouncementSchemaIn(Schema):
    title: str = Field(..., max_length=200, description="公告标题")
    content: str = Field(..., description="公告内容")
    priority: str = Field("normal", description="优先级")
    expire_at: Optional[datetime] = Field(None, description="失效时间")


class AnnouncementSchemaPatch(Schema):
    title: Optional[str] = Field(None, max_length=200, description="公告标题")
    content: Optional[str] = Field(None, description="公告内容")
    priority: Optional[str] = Field(None, description="优先级")
    expire_at: Optional[datetime] = Field(None, description="失效时间")


class AnnouncementSchemaOut(ModelSchema):
    class Config:
        model = Announcement
        model_fields = "__all__"


class InternalMessageSendIn(Schema):
    receiver_ids: list[str] = Field(..., description="接收用户ID列表")
    title: str = Field(..., max_length=200, description="消息标题")
    content: str = Field(..., description="消息内容")
    priority: str = Field("normal", description="优先级")
    link: Optional[str] = Field(None, description="跳转链接")
    extra_data: Optional[dict[str, Any]] = Field(None, description="扩展字段")


class UserMessageOut(Schema):
    id: str
    title: str
    content: str
    message_type: str
    priority: str
    is_read: bool
    read_at: Optional[datetime] = None
    link: Optional[str] = None
    extra_data: Optional[dict[str, Any]] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    sender_avatar: Optional[str] = None
    announcement_id: Optional[str] = None
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class MessageActionOut(Schema):
    msg: str
    count: Optional[int] = None


class UnreadCountOut(Schema):
    unread_count: int
