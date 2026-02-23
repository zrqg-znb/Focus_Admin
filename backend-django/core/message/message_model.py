#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Message models.
"""
from django.db import models

from common.fu_model import RootModel


class Announcement(RootModel):
    """System announcement."""

    STATUS_DRAFT = 0
    STATUS_PUBLISHED = 1
    STATUS_REVOKED = 2
    STATUS_CHOICES = [
        (STATUS_DRAFT, "草稿"),
        (STATUS_PUBLISHED, "已发布"),
        (STATUS_REVOKED, "已撤回"),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "低"),
        (PRIORITY_NORMAL, "普通"),
        (PRIORITY_HIGH, "高"),
        (PRIORITY_URGENT, "紧急"),
    ]

    title = models.CharField(max_length=200, help_text="公告标题", db_index=True)
    content = models.TextField(help_text="公告内容")
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        help_text="公告状态",
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
        help_text="优先级",
    )
    publish_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="发布时间",
        db_index=True,
    )
    expire_at = models.DateTimeField(null=True, blank=True, help_text="失效时间")

    class Meta:
        db_table = "core_announcement"
        ordering = ("-publish_at", "-sys_create_datetime")

    def __str__(self):
        return f"{self.title}"


class UserMessage(RootModel):
    """In-app message for a specific user."""

    TYPE_SYSTEM = "system"
    TYPE_INTERNAL = "internal"
    TYPE_ANNOUNCEMENT = "announcement"
    MESSAGE_TYPE_CHOICES = [
        (TYPE_SYSTEM, "系统消息"),
        (TYPE_INTERNAL, "站内信"),
        (TYPE_ANNOUNCEMENT, "公告"),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "低"),
        (PRIORITY_NORMAL, "普通"),
        (PRIORITY_HIGH, "高"),
        (PRIORITY_URGENT, "紧急"),
    ]

    receiver = models.ForeignKey(
        to="core.User",
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="received_messages",
        help_text="接收人",
        db_index=True,
    )
    sender = models.ForeignKey(
        to="core.User",
        on_delete=models.SET_NULL,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="sent_messages",
        help_text="发送人",
    )
    announcement = models.ForeignKey(
        to="core.Announcement",
        on_delete=models.SET_NULL,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="messages",
        help_text="关联公告",
    )
    title = models.CharField(max_length=200, help_text="消息标题", db_index=True)
    content = models.TextField(help_text="消息内容")
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default=TYPE_SYSTEM,
        help_text="消息类型",
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
        help_text="优先级",
    )
    is_read = models.BooleanField(default=False, help_text="是否已读", db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, help_text="阅读时间", db_index=True)
    link = models.CharField(max_length=255, null=True, blank=True, help_text="跳转链接")
    extra_data = models.JSONField(null=True, blank=True, help_text="扩展数据")

    class Meta:
        db_table = "core_user_message"
        ordering = ("-sys_create_datetime",)
        indexes = [
            models.Index(fields=["receiver", "is_read"], name="msg_receiver_read_idx"),
            models.Index(fields=["receiver", "sys_create_datetime"], name="msg_receiver_time_idx"),
        ]

    def __str__(self):
        return f"{self.title} -> {self.receiver_id}"
