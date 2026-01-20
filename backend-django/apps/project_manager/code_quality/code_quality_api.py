from typing import List, Dict
from ninja import Router, Schema
from datetime import date, timedelta
from django.utils import timezone

from common.fu_auth import BearerAuth as GlobalAuth
from .code_quality_schema import (
    ModuleConfigSchema, 
    CodeModuleOut,
    CodeMetricSchema,
    CodeMetricOut,
    ModuleQualityDetailSchema,
    ProjectQualitySummarySchema
)
from .code_quality_model import CodeModule, CodeMetric
from . import code_quality_service

router = Router(tags=["CodeQuality"], auth=GlobalAuth())

@router.get("/overview", response=List[ProjectQualitySummarySchema], summary="代码质量看板概览")
def get_quality_overview(request):
    return code_quality_service.get_quality_overview()

@router.post("/modules", response=CodeModuleOut, summary="配置代码模块")
def config_module(request, data: ModuleConfigSchema):
    return code_quality_service.config_module(request, data)

@router.get("/project/{project_id}/details", response=List[ModuleQualityDetailSchema], summary="获取项目代码质量详情(模块列表)")
def get_project_quality_details(request, project_id: str):
    return code_quality_service.get_project_quality_details(project_id)

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
