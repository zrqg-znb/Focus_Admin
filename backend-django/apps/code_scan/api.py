from typing import List
from ninja import Router, File, UploadedFile, Form
from django.shortcuts import get_object_or_404
from apps.code_scan.models import ScanProject, ScanTask, ScanResult, ShieldApplication
from apps.code_scan.schemas import (
    ScanProjectSchema, ScanProjectCreateSchema,
    ScanTaskSchema, ScanResultSchema,
    ShieldApplicationSchema, ShieldApplySchema, ShieldAuditSchema,
    ChunkUploadSchema, ProjectOverviewSchema, LatestScanResultSchema,
    PaginatedScanResultSchema
)
from apps.code_scan.services import ScanService
from common.fu_auth import BearerAuth
from common.fu_auth import ApiKey

router = Router()

# --- 项目管理 ---

@router.get("/projects", response=List[ScanProjectSchema], auth=BearerAuth())
def list_projects(request, keyword: str = None):
    qs = ScanProject.objects.filter(is_deleted=False).select_related('caretaker')
    if keyword:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=keyword) | Q(repo_url__icontains=keyword))
    return qs

@router.get("/projects/overview", response=List[ProjectOverviewSchema], auth=BearerAuth())
def list_project_overview(request):
    projects = list(ScanProject.objects.filter(is_deleted=False).values("id", "name"))
    project_ids = [p["id"] for p in projects]

    tasks = (
        ScanTask.objects.filter(project_id__in=project_ids, is_deleted=False, status="success")
        .order_by("-sys_create_datetime")
        .values("id", "project_id", "tool_name", "sys_create_datetime")
    )

    latest_task_by_proj_tool: dict[tuple[str, str], dict] = {}
    latest_time_by_project: dict[str, str] = {}
    for t in tasks:
        key = (t["project_id"], t["tool_name"])
        if key not in latest_task_by_proj_tool:
            latest_task_by_proj_tool[key] = t
        if t["project_id"] not in latest_time_by_project:
            latest_time_by_project[t["project_id"]] = (
                t["sys_create_datetime"].isoformat(sep=" ", timespec="seconds")
                if t.get("sys_create_datetime")
                else None
            )

    latest_task_ids = [str(v["id"]) for v in latest_task_by_proj_tool.values()]
    counts_by_task: dict[str, int] = {}
    if latest_task_ids:
        from django.db.models import Count

        qs = (
            ScanResult.objects.filter(task_id__in=latest_task_ids, is_deleted=False)
            .exclude(shield_status="Shielded")
            .values("task_id")
            .annotate(cnt=Count("id"))
        )
        counts_by_task = {str(x["task_id"]): int(x["cnt"]) for x in qs}

    overview_by_project: dict[str, dict] = {p["id"]: {"tool_counts": {}, "total": 0} for p in projects}
    for (pid, tool), t in latest_task_by_proj_tool.items():
        task_id = str(t["id"])
        cnt = counts_by_task.get(task_id, 0)
        overview_by_project[pid]["tool_counts"][tool] = cnt
        overview_by_project[pid]["total"] += cnt

    return [
        {
            "project_id": p["id"],
            "project_name": p["name"],
            "tool_counts": overview_by_project[p["id"]]["tool_counts"],
            "total": overview_by_project[p["id"]]["total"],
            "latest_time": latest_time_by_project.get(p["id"]),
        }
        for p in projects
    ]

@router.post("/projects", response=ScanProjectSchema, auth=BearerAuth())
def create_project(request, data: ScanProjectCreateSchema):
    project = ScanService.create_project(data.dict(), request.auth)
    return project

@router.put("/projects/{project_id}", response=ScanProjectSchema, auth=BearerAuth())
def update_project(request, project_id: str, data: ScanProjectCreateSchema):
    project = ScanService.update_project(project_id, data.dict(), request.auth)
    return project

# --- 任务上传 (流水线调用) ---

@router.post("/upload", response=ScanTaskSchema, auth=None)
def upload_report(request, 
                 project_key: str = Form(...), 
                 tool_name: str = Form('tscan'),
                 file: UploadedFile = File(...)):
    """
    接收流水线上传的扫描报告
    Auth: 无强制鉴权，依赖 project_key 校验
    """
    task = ScanService.handle_upload(project_key, tool_name, file)
    return task

@router.post("/upload/chunk", auth=None)
def upload_chunk(request, data: ChunkUploadSchema):
    """
    分片上传接口 (适用于受限网络环境)
    Auth: 无强制鉴权，依赖 project_key 校验
    """
    result = ScanService.handle_chunk_upload(
        data.project_key, 
        data.tool_name, 
        data.chunk_index, 
        data.total_chunks, 
        data.chunk_content, 
        data.file_id,
        data.file_ext
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

@router.get("/projects/{project_id}/latest-results", response=PaginatedScanResultSchema, auth=BearerAuth())
def list_latest_results(request, project_id: str, tool_name: str = None, page: int = 1, pageSize: int = 20):
    tasks_qs = ScanTask.objects.filter(project_id=project_id, is_deleted=False, status="success")
    
    if tool_name:
        # If tool_name is specified, get latest task for that tool
        # Actually, we want latest task per tool, but filter by tool_name if provided
        tasks_qs = tasks_qs.filter(tool_name=tool_name)

    tasks = (
        tasks_qs
        .order_by("-sys_create_datetime")
        .values("id", "tool_name", "sys_create_datetime")
    )

    latest_task_by_tool: dict[str, str] = {}
    for t in tasks:
        tool = t["tool_name"]
        if tool not in latest_task_by_tool:
            latest_task_by_tool[tool] = str(t["id"])

    task_ids = list(latest_task_by_tool.values())
    if not task_ids:
        return {"items": [], "total": 0}

    results_qs = (
        ScanResult.objects.filter(task_id__in=task_ids, is_deleted=False)
        .select_related("task")
        .order_by("-severity", "file_path", "line_number")
    )
    
    total = results_qs.count()
    start = (page - 1) * pageSize
    end = start + pageSize
    results = results_qs[start:end]

    payload = []
    for r in results:
        payload.append(
            {
                "id": str(r.id),
                "task_id": str(r.task_id),
                "tool_name": r.task.tool_name,
                "file_path": r.file_path,
                "line_number": r.line_number,
                "defect_type": r.defect_type,
                "severity": r.severity,
                "description": r.description,
                "fingerprint": r.fingerprint,
                "shield_status": r.shield_status,
                "help_info": r.help_info,
                "code_snippet": r.code_snippet,
                "sys_create_datetime": r.sys_create_datetime.isoformat(sep=" ", timespec="seconds")
                if getattr(r, "sys_create_datetime", None)
                else None,
            }
        )
    return {"items": payload, "total": total}

# --- 屏蔽申请与审批 ---

@router.post("/shield/apply", auth=BearerAuth())
def apply_shield(request, data: ShieldApplySchema):
    ScanService.apply_shield(request.auth, data.result_ids, data.approver_id, data.reason)
    return {"message": "Application submitted"}

@router.get("/shield/applications", response=List[ShieldApplicationSchema], auth=BearerAuth())
def list_applications(request, mode: str = "my_apply"):
    user = request.auth  # BearerAuth returns user in request.auth
    if mode == "my_apply":
        qs = ShieldApplication.objects.filter(applicant=user)
    else:
        qs = ShieldApplication.objects.filter(approver=user)
    
    results = []
    for app in qs.select_related("applicant", "approver", "result", "result__task"):
        results.append(
            {
                "id": str(app.id),
                "result_id": str(app.result_id),
                "applicant_id": str(app.applicant_id),
                "approver_id": str(app.approver_id) if app.approver_id else None,
                "reason": app.reason,
                "status": app.status,
                "audit_comment": app.audit_comment,
                "applicant_name": (app.applicant.name or app.applicant.username) if app.applicant else None,
                "approver_name": (app.approver.name or app.approver.username) if app.approver else None,
                "sys_create_datetime": app.sys_create_datetime.isoformat(sep=" ", timespec="seconds")
                if getattr(app, "sys_create_datetime", None)
                else None,
                "file_path": app.result.file_path,
                "defect_description": app.result.description,
                "severity": app.result.severity,
                "tool_name": app.result.task.tool_name,
                "help_info": app.result.help_info,
                "code_snippet": app.result.code_snippet,
            }
        )
    return results

@router.post("/shield/audit", auth=BearerAuth())
def audit_shield(request, data: ShieldAuditSchema):
    ScanService.audit_shield(request.auth, data.application_id, data.status, data.audit_comment)
    return {"message": "Audit completed"}
