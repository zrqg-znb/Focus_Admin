from datetime import datetime
from typing import Optional

from ninja import Query, Router

from . import missing_merge_services as services
from .missing_merge_schemas import (
    MissingMergeRecordOut,
    MissingMergeRecordStatusIn,
    MissingMergeOptionsOut,
    MissingMergeScanRunIn,
    MissingMergeScanTaskOut,
    PaginatedMissingMergeRecordOut,
    PaginatedMissingMergeScanTaskOut,
)


router = Router()


@router.get("/records", response=PaginatedMissingMergeRecordOut, summary="查询漏合风险列表")
def list_missing_merge_records(
    request,
    page: int = Query(1),
    pageSize: int = Query(20),
    organization_id: Optional[str] = Query(None),
    repository_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    author_username: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    trunk_branch: Optional[str] = Query(None),
    release_branch: Optional[str] = Query(None),
    merged_after: Optional[datetime] = Query(None),
    merged_before: Optional[datetime] = Query(None),
    detected_after: Optional[datetime] = Query(None),
    detected_before: Optional[datetime] = Query(None),
):
    """分页查询漏合风险，支持组织、代码库、分支、状态和时间范围筛选。"""
    return services.list_missing_merge_records(
        page=page,
        page_size=pageSize,
        organization_id=organization_id,
        repository_id=repository_id,
        status=status,
        author_username=author_username,
        keyword=keyword,
        trunk_branch=trunk_branch,
        release_branch=release_branch,
        merged_after=merged_after,
        merged_before=merged_before,
        detected_after=detected_after,
        detected_before=detected_before,
    )


@router.get("/records/options", response=MissingMergeOptionsOut, summary="获取漏合风险筛选选项")
def list_missing_merge_options(request):
    """返回漏合风险页面使用的组织和代码库选项。"""
    return services.list_filter_options()


@router.get("/records/{record_id}", response=MissingMergeRecordOut, summary="获取漏合风险详情")
def get_missing_merge_record(request, record_id: str):
    """读取单条漏合风险详情。"""
    return services.get_missing_merge_record(record_id)


@router.put("/records/{record_id}/status", response=MissingMergeRecordOut, summary="更新漏合风险状态")
def update_missing_merge_status(request, record_id: str, payload: MissingMergeRecordStatusIn):
    """人工更新漏合风险处理状态和备注。"""
    return services.update_missing_merge_status(request.auth, record_id, payload)


@router.get("/scan-tasks", response=PaginatedMissingMergeScanTaskOut, summary="查询漏合检测任务")
def list_missing_merge_scan_tasks(
    request,
    page: int = Query(1),
    pageSize: int = Query(20),
    status: Optional[str] = Query(None),
    trigger_type: Optional[str] = Query(None),
):
    """分页查询漏合检测同步任务历史。"""
    return services.list_scan_tasks(
        page=page,
        page_size=pageSize,
        status=status,
        trigger_type=trigger_type,
    )


@router.post("/scan-tasks/run", response=MissingMergeScanTaskOut, summary="手动触发漏合检测")
def run_missing_merge_scan(request, payload: MissingMergeScanRunIn):
    """手动触发一次漏合检测，返回任务执行结果。"""
    return services.run_missing_merge_scan(request.auth, payload)
