#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PL 资源组 API。"""
from typing import List

from ninja import Query, Router
from ninja.pagination import paginate

from common.fu_pagination import MyPagination
from common.fu_schema import response_success
from core.pl.pl_schemas import (
    PlGroupBatchDeleteIn,
    PlGroupBatchDeleteOut,
    PlGroupBatchUpdateStatusIn,
    PlGroupBatchUpdateStatusOut,
    PlGroupFilters,
    PlGroupIn,
    PlGroupOut,
    PlGroupPatch,
    PlGroupSimple,
    PlGroupUserFilter,
    PlGroupUserIn,
    PlGroupUserOut,
)
from core.pl.pl_services import (
    add_pl_group_users,
    batch_delete_pl_groups,
    batch_update_pl_group_status,
    build_pl_group_queryset,
    create_pl_group,
    delete_pl_group,
    get_pl_group_detail,
    get_pl_group_users,
    list_all_pl_groups,
    remove_pl_group_users,
    update_pl_group,
)

router = Router()


@router.post('/pl', response=PlGroupOut, summary='创建PL资源组')
def create_pl(request, data: PlGroupIn):
    return create_pl_group(request, data)


@router.get('/pl', response=List[PlGroupOut], summary='获取PL资源组列表（分页）')
@paginate(MyPagination)
def list_pl(request, filters: PlGroupFilters = Query(...)):
    return build_pl_group_queryset(filters)


@router.get('/pl/all', response=List[PlGroupSimple], summary='获取所有启用的PL资源组')
def list_all_pl(request):
    return list_all_pl_groups()


@router.get('/pl/{pl_id}', response=PlGroupOut, summary='获取PL资源组详情')
def get_pl(request, pl_id: str):
    return get_pl_group_detail(pl_id)


@router.put('/pl/{pl_id}', response=PlGroupOut, summary='更新PL资源组（完全替换）')
def put_pl(request, pl_id: str, data: PlGroupIn):
    return update_pl_group(request, pl_id, data, partial=False)


@router.patch('/pl/{pl_id}', response=PlGroupOut, summary='部分更新PL资源组')
def patch_pl(request, pl_id: str, data: PlGroupPatch):
    return update_pl_group(request, pl_id, data, partial=True)


@router.delete('/pl/{pl_id}', response=PlGroupOut, summary='删除PL资源组')
def drop_pl(request, pl_id: str):
    return delete_pl_group(pl_id)


@router.post('/pl/batch/delete', response=PlGroupBatchDeleteOut, summary='批量删除PL资源组')
def batch_delete_pl(request, data: PlGroupBatchDeleteIn):
    count, failed_ids = batch_delete_pl_groups(data.ids)
    return PlGroupBatchDeleteOut(count=count, failed_ids=failed_ids)


@router.post('/pl/batch/update-status', response=PlGroupBatchUpdateStatusOut, summary='批量更新PL资源组状态')
def batch_update_pl_status(request, data: PlGroupBatchUpdateStatusIn):
    count = batch_update_pl_group_status(data.ids, data.status)
    return PlGroupBatchUpdateStatusOut(count=count)


@router.get('/pl/users/{pl_id}', response=List[PlGroupUserOut], summary='获取PL资源组成员')
@paginate(MyPagination)
def list_pl_users(request, pl_id: str, filters: PlGroupUserFilter = Query(...)):
    return get_pl_group_users(pl_id, name=filters.name)


@router.post('/pl/users/{pl_id}', summary='为PL资源组添加成员')
def create_pl_users(request, pl_id: str, data: PlGroupUserIn):
    user_ids = data.user_ids if data.user_ids else ([data.user_id] if data.user_id else [])
    added_count = add_pl_group_users(pl_id, user_ids)
    return response_success(f'成功添加 {added_count} 个用户')


@router.delete('/pl/users/{pl_id}', summary='从PL资源组移除成员')
def delete_pl_users(request, pl_id: str, data: PlGroupUserIn):
    user_ids = data.user_ids if data.user_ids else ([data.user_id] if data.user_id else [])
    removed_count = remove_pl_group_users(pl_id, user_ids)
    return response_success(f'成功移除 {removed_count} 个用户')
