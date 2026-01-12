from ninja import Router
from typing import List
from .dts_schema import DtsDashboardSchema, DtsSyncResponse, DtsProjectOverviewSchema
from .dts_service import sync_project_dts, get_dts_dashboard, get_dts_overview
from apps.project_manager.project.project_model import Project
from django.shortcuts import get_object_or_404

router = Router(tags=["DTS"])

@router.get("/overview", response=List[DtsProjectOverviewSchema], summary="获取问题单项目概览")
def get_overview(request):
    return get_dts_overview()

@router.post("/sync/{project_id}", response=DtsSyncResponse, summary="同步问题单数据")
def sync_dts(request, project_id: str):
    project = get_object_or_404(Project, id=project_id)
    sync_project_dts(project)
    return {"success": True, "message": "同步成功"}

@router.get("/dashboard/{project_id}", response=DtsDashboardSchema, summary="获取问题单看板数据")
def get_dashboard(request, project_id: str):
    return get_dts_dashboard(project_id)
