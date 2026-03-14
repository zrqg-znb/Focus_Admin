#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PL 资源组模型。"""
from django.db import models
from django.core.validators import RegexValidator

from common.fu_model import RootModel


class PlGroup(RootModel):
    """PL 资源组。"""

    name = models.CharField(
        max_length=64,
        help_text="资源组名称",
        db_index=True,
    )
    code = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        help_text="资源组编码",
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_-]+$',
                message='资源组编码只能包含字母、数字、下划线和横线',
            )
        ],
    )
    status = models.BooleanField(
        default=True,
        help_text="资源组状态（启用/禁用）",
        db_index=True,
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="资源组描述",
    )
    pl_user = models.ForeignKey(
        to='core.User',
        on_delete=models.PROTECT,
        db_constraint=False,
        help_text='PL负责人',
        related_name='lead_pl_groups',
        db_index=True,
    )
    members = models.ManyToManyField(
        to='core.User',
        db_constraint=False,
        blank=True,
        help_text='资源组成员',
        related_name='pl_groups',
    )

    class Meta:
        db_table = 'core_pl_group'
        ordering = ('-status', '-sort', 'name')
        verbose_name = 'PL资源组'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['status', 'sort']),
            models.Index(fields=['pl_user', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code or '-'})"

    def get_member_count(self):
        return self.members.count()
