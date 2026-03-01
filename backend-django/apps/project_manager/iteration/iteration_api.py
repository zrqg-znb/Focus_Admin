from typing import List

from ninja import Query, Router

from common.fu_auth import BearerAuth as GlobalAuth
from apps.project_manager.utils.sync_executor import run_sync_task

from .iteration_schema import (
    IterationCreateSchema,
    IterationDashboardSchema,
    IterationDetailSchema,
    IterationManualUpdateSchema,
    IterationRequirementPageSchema,
)
from . import iteration_service

router = Router(tags=["Iteration"], auth=GlobalAuth())


@router.get("/overview", response=List[IterationDashboardSchema], summary="迭代看板概览")
def get_iteration_overview(request):
    return iteration_service.get_iteration_dashboard()


@router.get("/project/{project_id}", response=List[IterationDetailSchema], summary="获取项目迭代列表")
def list_project_iterations(request, project_id: str):
    return iteration_service.get_project_iterations(project_id)


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
        func_args=(project_id,),
    )
    return True


@router.put("/metric/{iteration_id}/manual", response=bool, summary="更新手动指标")
def update_manual_metric(request, iteration_id: str, data: IterationManualUpdateSchema):
    return iteration_service.update_manual_metric(iteration_id, data)


@router.get(
    "/iteration/{iteration_id}/requirements",
    response=IterationRequirementPageSchema,
    summary="获取迭代需求IDPCA状态列表",
)
def list_iteration_requirements(
    request,
    iteration_id: str,
    page: int = 1,
    page_size: int = 20,
    idpca_status: str = Query("", description="状态筛选：I/D/P/C/A"),
    requirement_type: str = Query("", description="类型筛选：sr/dr/ar"),
):
    return iteration_service.list_iteration_requirements(
        iteration_id=iteration_id,
        page=page,
        page_size=page_size,
        idpca_status=idpca_status,
        requirement_type=requirement_type,
    )


@router.get(
    "/iteration/{iteration_id}/unresolved-requirements",
    response=IterationRequirementPageSchema,
    summary="获取迭代未分解需求列表",
)
def list_unresolved_requirements(
    request,
    iteration_id: str,
    page: int = 1,
    page_size: int = 20,
    requirement_type: str = Query("", description="类型筛选：sr/dr/ar"),
):
    return iteration_service.list_unresolved_requirements(
        iteration_id=iteration_id,
        page=page,
        page_size=page_size,
        requirement_type=requirement_type,
    )
