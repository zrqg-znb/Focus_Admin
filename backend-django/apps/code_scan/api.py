from typing import List
from ninja import Router, File, UploadedFile, Form
from django.shortcuts import get_object_or_404
from apps.code_scan.models import ScanProject, ScanTask, ScanResult, ShieldApplication
from apps.code_scan.schemas import (
    ScanProjectSchema, ScanProjectCreateSchema,
    ScanTaskSchema, ScanResultSchema,
    ShieldApplicationSchema, ShieldApplySchema, ShieldAuditSchema,
    ChunkUploadSchema
)
from apps.code_scan.services import ScanService
from common.fu_auth import BearerAuth
from common.fu_auth import ApiKey

router = Router()

# --- 项目管理 ---

@router.get("/projects", response=List[ScanProjectSchema], auth=BearerAuth())
def list_projects(request):
    return ScanProject.objects.filter(is_deleted=False)

@router.post("/projects", response=ScanProjectSchema, auth=BearerAuth())
def create_project(request, data: ScanProjectCreateSchema):
    project = ScanService.create_project(data.dict(), request.user)
    return project

# --- 任务上传 (流水线调用) ---

@router.post("/upload", response=ScanTaskSchema, auth=ApiKey())
def upload_report(request, 
                 project_key: str = Form(...), 
                 tool_name: str = Form('tscan'),
                 file: UploadedFile = File(...)):
    """
    接收流水线上传的扫描报告
    Auth: 使用 ApiKey (token=project_key) 或直接通过 Form 参数校验
    这里简单起见，假设 API Key 认证通过，或者我们直接在 View 内部校验 project_key
    """
    # 注意：如果使用了 ApiKey auth，request.auth 可能是 token 值
    # 实际业务中，project_key 应该作为认证凭证
    
    task = ScanService.handle_upload(project_key, tool_name, file)
    return task

@router.post("/upload/chunk", auth=ApiKey())
def upload_chunk(request, data: ChunkUploadSchema):
    """
    分片上传接口 (适用于受限网络环境)
    """
    result = ScanService.handle_chunk_upload(
        data.project_key, 
        data.tool_name, 
        data.chunk_index, 
        data.total_chunks, 
        data.chunk_content, 
        data.file_id
    )
    return result

# --- 任务管理 ---

@router.get("/tasks", response=List[ScanTaskSchema], auth=BearerAuth())
def list_tasks(request, project_id: str):
    return ScanTask.objects.filter(project_id=project_id, is_deleted=False)

# --- 结果管理 ---

@router.get("/results", response=List[ScanResultSchema], auth=BearerAuth())
def list_results(request, task_id: str):
    return ScanResult.objects.filter(task_id=task_id, is_deleted=False)

# --- 屏蔽申请与审批 ---

@router.post("/shield/apply", auth=BearerAuth())
def apply_shield(request, data: ShieldApplySchema):
    ScanService.apply_shield(request.user, data.result_ids, data.approver_id, data.reason)
    return {"message": "Application submitted"}

@router.get("/shield/applications", response=List[ShieldApplicationSchema], auth=BearerAuth())
def list_applications(request, mode: str = "my_apply"):
    if mode == "my_apply":
        qs = ShieldApplication.objects.filter(applicant=request.user)
    else:
        qs = ShieldApplication.objects.filter(approver=request.user)
    
    results = []
    for app in qs:
        item = ShieldApplicationSchema.from_orm(app)
        item.applicant_name = app.applicant.name or app.applicant.username
        item.approver_name = app.approver.name or app.approver.username
        results.append(item)
    return results

@router.post("/shield/audit", auth=BearerAuth())
def audit_shield(request, data: ShieldAuditSchema):
    ScanService.audit_shield(request.user, data.application_id, data.status, data.audit_comment)
    return {"message": "Audit completed"}
