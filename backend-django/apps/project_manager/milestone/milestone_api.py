from typing import List, Optional
from ninja import Router, Query
from common.fu_auth import BearerAuth as GlobalAuth
from .milestone_schema import MilestoneBoardSchema, MilestoneUpdateSchema, MilestoneOut, QGConfigOut, QGConfigIn, RiskItemOut, RiskConfirmIn
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


# --- QG Config ---

@router.get("/{project_id}/qg-configs", response=List[QGConfigOut], summary="获取QG配置(By Project ID)")
def list_qg_configs(request, project_id: str):
    return milestone_service.get_qg_configs(project_id)

@router.post("/{project_id}/qg-configs", response=QGConfigOut, summary="保存QG配置(By Project ID)")
def save_qg_config(request, project_id: str, payload: QGConfigIn):
    return milestone_service.upsert_qg_config(
        project_id=project_id,
        qg_name=payload.qg_name,
        target_di=payload.target_di,
        enabled=payload.enabled
    )

# --- Risks ---

@router.get("/risks/pending", response=List[RiskItemOut], summary="获取待处理风险(工作台)")
def list_pending_risks(request):
    return milestone_service.list_pending_risks()

@router.post("/risks/{risk_id}/confirm", response=bool, summary="确认/关闭风险")
def confirm_risk(request, risk_id: str, payload: RiskConfirmIn):
    return milestone_service.confirm_risk(risk_id, request.auth, payload.note, payload.action)

@router.post("/mock/daily-check", response=bool, summary="手动触发每日检查(测试用)")
def trigger_daily_check(request):
    milestone_service.check_qg_risks_daily()
    return True
