from typing import List
from ninja import Router, Query
from django.shortcuts import get_object_or_404
from apps.tscan.models import TScanProject, TScanTask, TScanResult, TScanShieldApplication
from apps.tscan.schemas import (
    TScanProjectSchema, TScanProjectCreateSchema,
    TScanTaskSchema, TScanResultSchema,
    TScanShieldApplicationSchema, ShieldApplySchema, ShieldAuditSchema
)
from apps.tscan.services import TScanService
from core.user.user_model import User
from common.fu_auth import BearerAuth

router = Router()

# --- 项目管理 ---

@router.get("/projects", response=List[TScanProjectSchema], auth=BearerAuth())
def list_projects(request):
    return TScanProject.objects.filter(is_deleted=False)

@router.post("/projects", response=TScanProjectSchema, auth=BearerAuth())
def create_project(request, data: TScanProjectCreateSchema):
    project = TScanProject.objects.create(**data.dict(), sys_creator=request.user)
    return project

# --- 任务管理 ---

@router.get("/tasks", response=List[TScanTaskSchema], auth=BearerAuth())
def list_tasks(request, project_id: str):
    return TScanTask.objects.filter(project_id=project_id, is_deleted=False)

@router.post("/tasks/{project_id}/run", auth=BearerAuth())
def run_scan_task(request, project_id: str):
    project = get_object_or_404(TScanProject, id=project_id)
    task = TScanTask.objects.create(
        project=project,
        status='pending',
        trigger_user=request.user,
        sys_creator=request.user
    )
    # 异步执行扫描（此处暂用同步模拟，实际应放入 Celery）
    TScanService.run_task(task.id)
    return {"message": "Task started", "task_id": str(task.id)}

# --- 结果管理 ---

@router.get("/results", response=List[TScanResultSchema], auth=BearerAuth())
def list_results(request, task_id: str):
    return TScanResult.objects.filter(task_id=task_id, is_deleted=False)

# --- 屏蔽申请与审批 ---

@router.post("/shield/apply", auth=BearerAuth())
def apply_shield(request, data: ShieldApplySchema):
    TScanService.apply_shield(request.user, data.result_ids, data.approver_id, data.reason)
    return {"message": "Application submitted"}

@router.get("/shield/applications", response=List[TScanShieldApplicationSchema], auth=BearerAuth())
def list_applications(request, mode: str = "my_apply"):
    """
    mode: my_apply (我申请的), my_audit (待我审批的)
    """
    if mode == "my_apply":
        qs = TScanShieldApplication.objects.filter(applicant=request.user)
    else:
        qs = TScanShieldApplication.objects.filter(approver=request.user)
    
    results = []
    for app in qs:
        item = TScanShieldApplicationSchema.from_orm(app)
        item.applicant_name = app.applicant.name or app.applicant.username
        item.approver_name = app.approver.name or app.approver.username
        results.append(item)
    return results

@router.post("/shield/audit", auth=BearerAuth())
def audit_shield(request, data: ShieldAuditSchema):
    TScanService.audit_shield(request.user, data.application_id, data.status, data.audit_comment)
    return {"message": "Audit completed"}
