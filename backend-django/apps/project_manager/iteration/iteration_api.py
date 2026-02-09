from typing import List, Optional
from ninja import Router, Schema
from django.db.models import Q

from common.fu_auth import BearerAuth as GlobalAuth
from apps.project_manager.project.project_model import Project
from .iteration_model import Iteration, IterationMetric
from .iteration_schema import (
    IterationCreateSchema, 
    IterationDetailSchema, 
    IterationMetricSchema,
    IterationMetricOut,
    IterationOut,
    IterationDashboardSchema,
    IterationManualUpdateSchema
)
from . import iteration_service

router = Router(tags=["Iteration"], auth=GlobalAuth())

@router.get("/overview", response=List[IterationDashboardSchema], summary="迭代看板概览")
def get_iteration_overview(request):
    return iteration_service.get_iteration_dashboard()

@router.get("/project/{project_id}", response=List[IterationDetailSchema], summary="获取项目迭代列表")
def list_project_iterations(request, project_id: str):
    return iteration_service.get_project_iterations(project_id)

from apps.project_manager.utils.sync_executor import run_sync_task

@router.post("/project/{project_id}/refresh", response=bool, summary="刷新项目迭代数据")
def refresh_project_iteration(request, project_id: str):
    """
    异步刷新项目迭代数据
    """
    user_id = request.auth.id
    run_sync_task(
        project_id=project_id,
        sync_type='iteration',
        user_id=user_id,
        sync_func=iteration_service.refresh_project_iteration,
        func_args=(project_id,)
    )
    return True

@router.put("/metric/{iteration_id}/manual", response=bool, summary="更新手动指标")
def update_manual_metric(request, iteration_id: str, data: IterationManualUpdateSchema):
    return iteration_service.update_manual_metric(iteration_id, data)
