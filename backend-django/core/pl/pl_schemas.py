#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PL 资源组 Schema。"""
from typing import List, Optional

from ninja import Field, Schema
from pydantic import field_validator

from common.fu_schema import FuFilters


class PlGroupFilters(FuFilters):
    """PL 资源组过滤器。"""

    name: Optional[str] = Field(None, q='name__icontains', alias='name')
    code: Optional[str] = Field(None, q='code__icontains', alias='code')
    status: Optional[bool] = Field(None, q='status', alias='status')


class PlGroupIn(Schema):
    name: str
    code: Optional[str] = None
    status: bool = True
    description: Optional[str] = None
    sort: int = 0
    pl_user_id: str

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError('资源组名称不能为空')
        if len(value) > 64:
            raise ValueError('资源组名称长度不能超过64个字符')
        return value

    @field_validator('code')
    @classmethod
    def validate_code(cls, value: Optional[str]):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > 32:
            raise ValueError('资源组编码长度不能超过32个字符')
        if not all(ch.isalnum() or ch in '_-' for ch in value):
            raise ValueError('资源组编码只能包含字母、数字、下划线和横线')
        return value

    @field_validator('description')
    @classmethod
    def validate_description(cls, value: Optional[str]):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > 200:
            raise ValueError('资源组描述长度不能超过200个字符')
        return value


class PlGroupPatch(Schema):
    name: Optional[str] = None
    code: Optional[str] = None
    status: Optional[bool] = None
    description: Optional[str] = None
    sort: Optional[int] = None
    pl_user_id: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: Optional[str]):
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError('资源组名称不能为空')
        if len(value) > 64:
            raise ValueError('资源组名称长度不能超过64个字符')
        return value

    @field_validator('code')
    @classmethod
    def validate_code(cls, value: Optional[str]):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > 32:
            raise ValueError('资源组编码长度不能超过32个字符')
        if not all(ch.isalnum() or ch in '_-' for ch in value):
            raise ValueError('资源组编码只能包含字母、数字、下划线和横线')
        return value

    @field_validator('description')
    @classmethod
    def validate_description(cls, value: Optional[str]):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > 200:
            raise ValueError('资源组描述长度不能超过200个字符')
        return value


class PlGroupOut(Schema):
    id: str
    name: str
    code: Optional[str]
    status: bool
    description: Optional[str]
    sort: int
    pl_user_id: str
    pl_user_name: Optional[str]
    pl_user_username: str
    member_count: int
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_pl_user_id(obj):
        return str(obj.pl_user_id)

    @staticmethod
    def resolve_pl_user_name(obj):
        return obj.pl_user.name if obj.pl_user else None

    @staticmethod
    def resolve_pl_user_username(obj):
        return obj.pl_user.username if obj.pl_user else ''

    @staticmethod
    def resolve_member_count(obj):
        annotated_count = getattr(obj, 'member_count', None)
        if annotated_count is not None:
            return annotated_count
        return obj.get_member_count()

    @staticmethod
    def resolve_sys_create_datetime(obj):
        return obj.sys_create_datetime.isoformat() if obj.sys_create_datetime else None

    @staticmethod
    def resolve_sys_update_datetime(obj):
        return obj.sys_update_datetime.isoformat() if obj.sys_update_datetime else None


class PlGroupSimple(Schema):
    id: str
    name: str
    code: Optional[str]
    status: bool
    pl_user_name: Optional[str]
    member_count: int

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_pl_user_name(obj):
        return obj.pl_user.name if obj.pl_user else None

    @staticmethod
    def resolve_member_count(obj):
        annotated_count = getattr(obj, 'member_count', None)
        if annotated_count is not None:
            return annotated_count
        return obj.get_member_count()


class PlGroupBatchDeleteIn(Schema):
    ids: List[str]


class PlGroupBatchDeleteOut(Schema):
    count: int
    failed_ids: List[str] = Field(default_factory=list)


class PlGroupBatchUpdateStatusIn(Schema):
    ids: List[str]
    status: bool


class PlGroupBatchUpdateStatusOut(Schema):
    count: int


class PlGroupUserOut(Schema):
    id: str
    username: str
    name: Optional[str]
    avatar: Optional[str]
    email: Optional[str]
    dept_name: Optional[str] = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_dept_name(obj):
        return obj.dept.name if obj.dept else None


class PlGroupUserIn(Schema):
    user_ids: List[str] = Field(default_factory=list)
    user_id: Optional[str] = None


class PlGroupUserFilter(FuFilters):
    name: Optional[str] = None
