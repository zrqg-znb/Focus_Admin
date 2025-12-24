#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dept Schema - 部门数据验证模式
"""
from typing import Optional, List
from ninja import ModelSchema, Field, Schema
from pydantic import field_validator

from common.fu_model import exclude_fields
from common.fu_schema import FuFilters
from core.dept.dept_model import Dept


class DeptFilters(FuFilters):
    """部门过滤器"""
    name: Optional[str] = Field(None, q="name__icontains", alias="name")
    code: Optional[str] = Field(None, q="code__icontains", alias="code")
    status: Optional[bool] = Field(None, q="status", alias="status")
    parent_id: Optional[str] = Field(None, q="parent_id", alias="parent_id")
    level: Optional[int] = Field(None, q="level", alias="level")


class DeptSchemaIn(ModelSchema):
    """部门输入模式"""
    parent_id: Optional[str] = Field(None, alias="parent_id")
    
    @field_validator('code', check_fields=False)
    @classmethod
    def validate_code(cls, v):
        """验证部门编码格式"""
        if v and not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('部门编码只能包含字母、数字、下划线和横线')
        return v
    
    class Config:
        model = Dept
        model_exclude = (*exclude_fields, "parent", "level", "path")


class DeptSchemaPatch(Schema):
    """部门部分更新模式（PATCH）"""
    name: Optional[str] = None
    code: Optional[str] = None
    parent_id: Optional[str] = None
    sort: Optional[int] = None
    status: Optional[bool] = None
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        """验证部门编码格式"""
        if v is not None and v and not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('部门编码只能包含字母、数字、下划线和横线')
        return v

class DeptSchemaOut(ModelSchema):
    """部门输出模式"""
    parent_id: Optional[str] = Field(None, alias="parent_id")
    
    class Config:
        model = Dept
        model_exclude = (*exclude_fields, "parent")

class DeptSchemaSimple(ModelSchema):
    """部门简单模式"""
    parent_id: Optional[str] = Field(None, alias="parent_id")

    class Config:
        model = Dept
        model_fields = ['id', 'name', 'code', 'level', 'status']

class DeptSchemaTree(DeptSchemaOut):
    """部门树形结构模式"""
    children: List['DeptSchemaTree'] = []

class DeptSchemaBatchDeleteIn(Schema):
    ids: List[str]

class DeptSchemaBatchDeleteOut(Schema):
    count: int
    failed_ids: List[str]

class DeptBatchUpdateStatusIn(Schema):
    ids: List[str]
    status: bool

class DeptBatchUpdateStatusOut(Schema):
    count: int

class DeptPathOut(Schema):
    dept_id: str
    dept_name: str
    path: List[DeptSchemaSimple]

class DeptUserSchema(Schema):
    id: str
    username: str
    name: str

class DeptUserIn(Schema):
    user_ids: List[str]

class DeptUserFilter(FuFilters):
    username: Optional[str] = None
