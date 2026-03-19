from ninja import Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import requirement_workspace_services
from .requirement_workspace_schemas import RequirementWorkspaceLatestSchema

router = Router(tags=["RequirementWorkspace"], auth=GlobalAuth())


@router.get(
    "/latest",
    response=RequirementWorkspaceLatestSchema,
    summary="获取工作台需求交付合规快照",
)
def get_requirement_workspace_latest(request):
    return requirement_workspace_services.get_latest_requirement_workspace_snapshot()


@router.post(
    "/refresh",
    response=RequirementWorkspaceLatestSchema,
    summary="立即刷新工作台需求交付合规快照",
)
def refresh_requirement_workspace(request):
    return requirement_workspace_services.refresh_requirement_workspace_snapshot()
