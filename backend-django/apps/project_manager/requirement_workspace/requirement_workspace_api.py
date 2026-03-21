from ninja import Query, Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import requirement_workspace_services
from .requirement_workspace_schemas import (
    RequirementWorkspaceLatestSchema,
    RequirementWorkspaceRefreshTaskSchema,
)

router = Router(tags=["RequirementWorkspace"], auth=GlobalAuth())


@router.get(
    "/latest",
    response=RequirementWorkspaceLatestSchema,
    summary="获取工作台需求交付合规快照",
)
def get_requirement_workspace_latest(request, scope: str = Query("all")):
    return requirement_workspace_services.get_latest_requirement_workspace_snapshot(
        view_scope=scope,
        user=request.auth,
    )


@router.post(
    "/refresh",
    response={202: RequirementWorkspaceRefreshTaskSchema},
    summary="立即刷新工作台需求交付合规快照",
)
def refresh_requirement_workspace(request, scope: str = Query("all")):
    task = requirement_workspace_services.submit_requirement_workspace_refresh_task(
        view_scope=scope,
        user=request.auth,
    )
    return 202, task


@router.get(
    "/refresh-task/{task_id}",
    response=RequirementWorkspaceRefreshTaskSchema,
    summary="查询工作台需求交付合规刷新任务状态",
)
def get_requirement_workspace_refresh_task(request, task_id: str):
    return requirement_workspace_services.get_requirement_workspace_refresh_task(task_id)
