#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional
from ninja import ModelSchema, Field

from common.fu_model import exclude_fields
from common.fu_schema import FuFilters
from core.operation_log.operation_log_model import OperationLog


class OperationLogFilters(FuFilters):
    request_username: Optional[str] = Field(None, q="request_username__icontains", alias="request_username")
    request_ip: Optional[str] = Field(None, q="request_ip", alias="request_ip")
    request_method: Optional[str] = Field(None, q="request_method", alias="request_method")
    request_path: Optional[str] = Field(None, q="request_path__icontains", alias="request_path")
    request_modular: Optional[str] = Field(None, q="request_modular", alias="request_modular")
    status: Optional[bool] = Field(None, q="status", alias="status")
    response_code: Optional[int] = Field(None, q="response_code", alias="response_code")
    start_datetime: Optional[str] = Field(None, q="sys_create_datetime__gte", alias="start_datetime")
    end_datetime: Optional[str] = Field(None, q="sys_create_datetime__lte", alias="end_datetime")


class OperationLogSchemaOut(ModelSchema):
    class Config:
        model = OperationLog
        model_fields = "__all__"

