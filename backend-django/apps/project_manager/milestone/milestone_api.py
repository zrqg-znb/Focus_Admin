from typing import List, Optional
from ninja import Router, Query
from common.fu_auth import BearerAuth as GlobalAuth
from .milestone_schema import MilestoneBoardSchema, MilestoneUpdateSchema, MilestoneOut
from . import milestone_service

router = Router(tags=["Milestone"], auth=GlobalAuth())

@router.get("/overview", response=List[MilestoneBoardSchema], summary="获取里程碑看板")
def get_milestone_board(
    request, 
    keyword: Optional[str] = None,
    project_type: Optional[str] = None,
    manager_id: Optional[str] = None
):
    filters = {}
    if keyword:
        filters['keyword'] = keyword
    if project_type:
        filters['project_type'] = project_type
    if manager_id:
        filters['manager_id'] = manager_id
        
    return milestone_service.get_milestone_board(filters)

@router.put("/project/{project_id}", response=MilestoneOut, summary="更新里程碑节点")
def update_milestone(request, project_id: str, data: MilestoneUpdateSchema):
    return milestone_service.update_milestone(request, project_id, data)
