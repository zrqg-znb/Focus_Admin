#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dept Model - 部门模型
用于管理组织架构中的部门信息
"""
from django.db import models
from common.fu_model import RootModel


class Dept(RootModel):
    """
    部门模型 - 用于组织架构管理
    """
    
    # 部门名称
    name = models.CharField(
        max_length=64,
        help_text="部门名称",
        db_index=True,
    )
    
    # 部门编码
    code = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        help_text="部门编码",
        db_index=True,
    )
    
    # 父部门
    parent = models.ForeignKey(
        to='self',
        on_delete=models.CASCADE,
        db_constraint=False,
        null=True,
        blank=True,
        help_text="父部门",
        related_name="children",
    )
    
    # 部门状态
    status = models.BooleanField(
        default=True,
        help_text="部门状态（启用/禁用）",
        db_index=True,
    )
    
    # 部门层级（自动计算）
    level = models.IntegerField(
        default=0,
        help_text="部门层级（0为顶层）",
        db_index=True,
    )
    
    # 部门路径（便于查询，格式：/1/2/3/）
    path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="部门路径",
        db_index=True,
    )
    
    class Meta:
        db_table = "core_dept"
        ordering = ("sort", "sys_create_datetime")
        verbose_name = "部门"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['parent', 'status']),
            models.Index(fields=['level', 'status']),
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_child_count(self):
        """获取子部门数量"""
        return self.children.count()

    def get_user_count(self):
        """获取用户数量"""
        # User模型中dept字段的related_name为core_users
        return self.core_users.count()

    def is_leaf(self):
        """是否是叶子节点"""
        return not self.children.exists()

    def can_delete(self):
        """是否可以删除"""
        # 只有叶子节点且没有用户的部门才能删除
        return self.is_leaf() and self.get_user_count() == 0

    def get_ancestors(self):
        """获取所有祖先部门"""
        ancestors = []
        current = self
        while current.parent:
            ancestors.append(current.parent)
            current = current.parent
        return ancestors[::-1]
