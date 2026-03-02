from typing import List, Optional
from ninja import Router

from common.fu_auth import BearerAuth as GlobalAuth
from .code_quality_schema import (
    ModuleConfigSchema,
    CodeModuleOut,
    ModuleQualityDetailSchema,
    NodeOwnerUpdateSchema,
    ProjectQualitySummarySchema,
)
from . import code_quality_service

router = Router(tags=["CodeQuality"], auth=GlobalAuth())

@router.get("/overview", response=List[ProjectQualitySummarySchema], summary="代码质量看板概览")
def get_quality_overview(request):
    return code_quality_service.get_quality_overview()


@router.get(
    "/project/{project_id}/record-dates",
    response=List[str],
    summary="获取项目代码质量可选日期",
)
def get_project_quality_record_dates(request, project_id: str):
    return code_quality_service.get_project_record_dates(project_id)

@router.post("/modules", response=CodeModuleOut, summary="配置代码模块")
def config_module(request, data: ModuleConfigSchema):
    return code_quality_service.config_module(request, data)

@router.get("/project/{project_id}/details", response=List[ModuleQualityDetailSchema], summary="获取项目代码质量详情(模块列表)")
def get_project_quality_details(
    request,
    project_id: str,
    lite: bool = False,
    record_date: Optional[str] = None,
):
    parsed_record_date = code_quality_service.parse_record_date(record_date)
    return code_quality_service.get_project_quality_details(
        project_id,
        include_tree=not lite,
        record_date=parsed_record_date,
    )

from apps.project_manager.utils.sync_executor import run_sync_task

@router.post("/project/{project_id}/refresh", response=bool, summary="刷新项目代码质量数据")
def refresh_project_quality(request, project_id: str):
    """
    异步刷新项目代码质量数据
    """
    user_id = request.auth.id
    run_sync_task(
        project_id=project_id,
        sync_type='code_quality',
        user_id=user_id,
        sync_func=code_quality_service.refresh_project_quality,
        func_args=(project_id,)
    )
    return True


@router.put("/node-owner", response=bool, summary="更新代码质量节点责任人")
def update_node_owner(request, data: NodeOwnerUpdateSchema):
    return code_quality_service.update_node_owner(data)
