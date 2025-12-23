#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import List
from django.shortcuts import get_object_or_404
from ninja import Router, Query
from ninja.pagination import paginate

from common.fu_crud import retrieve
from common.fu_pagination import MyPagination
from common.fu_schema import response_success
from core.operation_log.operation_log_model import OperationLog
from core.operation_log.operation_log_schema import OperationLogFilters, OperationLogSchemaOut


router = Router()


@router.get("/operation-log", response=List[OperationLogSchemaOut], summary="获取操作日志列表")
@paginate(MyPagination)
def list_operation_logs(request, filters: OperationLogFilters = Query(...)):
    qs = retrieve(request, OperationLog, filters)
    return qs.order_by('-sys_create_datetime')


@router.get("/operation-log/{log_id}", response=OperationLogSchemaOut, summary="获取操作日志详情")
def get_operation_log(request, log_id: str):
    log = get_object_or_404(OperationLog, id=log_id)
    return log


@router.delete("/operation-log/{log_id}", summary="删除操作日志")
def delete_operation_log(request, log_id: str):
    log = get_object_or_404(OperationLog, id=log_id)
    log.delete()
    return response_success("操作日志已删除")


@router.delete("/operation-log/batch/delete", summary="批量删除操作日志")
def batch_delete_operation_logs(request, ids: List[str] = Query(...)):
    deleted_count, _ = OperationLog.objects.filter(id__in=ids).delete()
    return response_success(f"成功删除 {deleted_count} 条操作日志")

