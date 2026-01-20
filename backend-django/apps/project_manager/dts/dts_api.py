from ninja import Router
from typing import List
from .dts_schema import DtsDashboardSchema, DtsSyncResponse, DtsProjectOverviewSchema, DtsDefectListResponseSchema
from .dts_service import sync_project_dts, get_dts_dashboard, get_dts_overview, get_mock_dts_details
from apps.project_manager.project.project_model import Project
from django.shortcuts import get_object_or_404

router = Router(tags=["DTS"])

@router.get("/details/{project_id}", response=DtsDefectListResponseSchema, summary="获取问题单详情列表")
def get_details(request, project_id: str, page: int = 1, page_size: int = 10):
    return get_mock_dts_details(project_id, page, page_size)

@router.get("/overview", response=List[DtsProjectOverviewSchema], summary="获取问题单项目概览")
def get_overview(request):
    return get_dts_overview()

from apps.project_manager.utils.sync_executor import run_sync_task

@router.post("/sync/{project_id}", response=DtsSyncResponse, summary="同步问题单数据")
def sync_dts(request, project_id: str):
    """
    异步同步问题单数据
    """
    project = get_object_or_404(Project, id=project_id)
    user_id = request.auth.id if hasattr(request, 'auth') and request.auth else None
    
    # 兼容没有 request.auth 的情况（例如内部调用）
    if not user_id:
        # 这里可以设置一个默认的系统用户ID，或者抛出异常
        # 暂时跳过
        pass

    run_sync_task(
        project_id=project_id,
        sync_type='dts',
        user_id=user_id,
        sync_func=sync_project_dts,
        func_kwargs={'project': project}
    )
    return {"success": True, "message": "同步任务已提交，请稍后查看结果"}

@router.get("/dashboard/{project_id}", response=DtsDashboardSchema, summary="获取问题单看板数据")
def get_dashboard(request, project_id: str):
    return get_dts_dashboard(project_id)
