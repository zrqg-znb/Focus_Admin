from typing import List
from ninja import Router, File, UploadedFile, Form
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from ninja.errors import HttpError
from apps.code_scan.models import (
    ScanProject,
    ScanTask,
    ScanResult,
    ScanResultOccurrence,
    ShieldApplication,
)
from apps.code_scan.schemas import (
    ScanProjectSchema, ScanProjectCreateSchema,
    ScanTaskSchema,
    ShieldApplicationSchema, ShieldApplySchema, ShieldAuditSchema,
    ShieldRecordSchema,
    ChunkUploadSchema, ProjectOverviewSchema, LatestScanResultSchema,
    PaginatedScanResultSchema, PaginatedScanProjectSchema, PaginatedScanTaskSchema,
    PaginatedShieldApplicationSchema, PaginatedProjectOverviewSchema
)
from apps.code_scan.services import ScanService
from common.fu_auth import BearerAuth
from common.fu_auth import ApiKey

router = Router()
SUB_MODULE_SCOPED_TOOLS = {"valgrind", "tsan"}
SHIELD_STATUS_ALIASES = {
    "normal": "Normal",
    "pending": "Pending",
    "shielded": "Shielded",
    "rejected": "Rejected",
}
SORT_ORDER_ALIASES = {
    "asc": "asc",
    "ascending": "asc",
    "desc": "desc",
    "descending": "desc",
}


def _normalize_sub_modules(raw_value: str | List[str] | None) -> list[str]:
    if not raw_value:
        return []
    values: list[str] = []
    if isinstance(raw_value, str):
        values = [item.strip() for item in raw_value.split(",")]
    elif isinstance(raw_value, (list, tuple, set)):
        values = [str(item).strip() for item in raw_value]

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(value)
    return normalized


def _normalize_tool_name(raw_value: str | None) -> str:
    return str(raw_value or "").strip().lower()


def _normalize_shield_status(raw_value: str | None) -> str | None:
    normalized = str(raw_value or "").strip().lower()
    if not normalized:
        return None
    return SHIELD_STATUS_ALIASES.get(normalized)


def _normalize_sort_order(raw_value: str | None) -> str | None:
    normalized = str(raw_value or "").strip().lower()
    if not normalized:
        return None
    return SORT_ORDER_ALIASES.get(normalized)


def _normalize_keyword(raw_value: str | None) -> str:
    return str(raw_value or "").strip()


def _select_latest_task_rows(
    task_rows: list[dict],
    tool_name: str | None = None,
    sub_modules: list[str] | None = None,
) -> list[dict]:
    normalized_tool = _normalize_tool_name(tool_name)
    module_lower_set = {item.lower() for item in (sub_modules or [])}

    if normalized_tool:
        filtered_rows = [
            row for row in task_rows
            if _normalize_tool_name(row.get("tool_name")) == normalized_tool
        ]
        if not filtered_rows:
            return []

        if normalized_tool in SUB_MODULE_SCOPED_TOOLS:
            latest_task_by_module: dict[str, dict] = {}
            unscoped_fallback: dict | None = None
            for row in filtered_rows:
                module_value = str(row.get("sub_module") or "").strip()
                if not module_value:
                    if unscoped_fallback is None:
                        unscoped_fallback = row
                    continue
                module_lower = module_value.lower()
                if module_lower_set and module_lower not in module_lower_set:
                    continue
                if module_lower in latest_task_by_module:
                    continue
                latest_task_by_module[module_lower] = row
                if module_lower_set and len(latest_task_by_module) == len(module_lower_set):
                    break

            selected_rows = list(latest_task_by_module.values())
            if selected_rows:
                return selected_rows
            if module_lower_set and unscoped_fallback:
                return [unscoped_fallback]
            if module_lower_set:
                return []
            return filtered_rows[:1]

        return filtered_rows[:1]

    latest_task_by_tool: dict[tuple[str, str], dict] = {}
    unscoped_fallback_by_tool: dict[str, dict] = {}
    module_tool_seen: set[str] = set()
    matched_module_tools: set[str] = set()
    for row in task_rows:
        current_tool = _normalize_tool_name(row.get("tool_name"))
        if not current_tool:
            continue

        current_sub_module = str(row.get("sub_module") or "").strip()
        current_sub_module_lower = current_sub_module.lower()

        if current_tool in SUB_MODULE_SCOPED_TOOLS:
            if module_lower_set:
                if current_sub_module_lower and current_sub_module_lower in module_lower_set:
                    key = (current_tool, current_sub_module_lower)
                    matched_module_tools.add(current_tool)
                else:
                    if not current_sub_module_lower and current_tool not in unscoped_fallback_by_tool:
                        unscoped_fallback_by_tool[current_tool] = row
                    continue
            elif current_sub_module_lower:
                key = (current_tool, current_sub_module_lower)
                module_tool_seen.add(current_tool)
            else:
                key = (current_tool, "")
        else:
            key = (current_tool, "")

        if key not in latest_task_by_tool:
            latest_task_by_tool[key] = row

    if module_lower_set:
        for current_tool, row in unscoped_fallback_by_tool.items():
            if current_tool in matched_module_tools:
                continue
            latest_task_by_tool.setdefault((current_tool, ""), row)

    selected_rows: list[dict] = []
    for (current_tool, current_sub_module), row in latest_task_by_tool.items():
        if current_tool in SUB_MODULE_SCOPED_TOOLS and not module_lower_set:
            if not current_sub_module and current_tool in module_tool_seen:
                continue
        selected_rows.append(row)
    return selected_rows


def _select_latest_task_ids(
    tasks_qs,
    tool_name: str | None = None,
    sub_modules: list[str] | None = None,
) -> list[str]:
    task_rows = list(
        tasks_qs
        .order_by("-sys_create_datetime")
        .values("id", "tool_name", "sub_module", "sys_create_datetime")
    )
    return [str(row["id"]) for row in _select_latest_task_rows(task_rows, tool_name, sub_modules)]


def _get_project_overview_sort_value(item: dict, sort_field: str) -> int | str | None:
    normalized_field = str(sort_field or "").strip()
    if not normalized_field:
        return None

    if normalized_field == "project_name":
        return str(item.get("project_name") or "").lower()
    if normalized_field == "total":
        value = item.get("total")
        return None if value is None else int(value)
    if normalized_field == "latest_time":
        value = item.get("latest_time")
        return str(value) if value else None

    tool_counts = item.get("tool_counts") or {}
    if not isinstance(tool_counts, dict) or normalized_field not in tool_counts:
        return None
    return int(tool_counts.get(normalized_field) or 0)


def _sort_project_overview_items(
    items: list[dict],
    sort_field: str | None = None,
    sort_order: str | None = None,
) -> list[dict]:
    normalized_field = str(sort_field or "").strip()
    normalized_order = _normalize_sort_order(sort_order)
    if not normalized_field or not normalized_order or not items:
        return items

    present_items: list[tuple[int | str, dict]] = []
    missing_items: list[dict] = []
    for item in items:
        sort_value = _get_project_overview_sort_value(item, normalized_field)
        if sort_value is None:
            missing_items.append(item)
            continue
        present_items.append((sort_value, item))

    if not present_items:
        return items

    present_items.sort(
        key=lambda entry: (
            entry[0],
            str(entry[1].get("project_name") or "").lower(),
        ),
        reverse=(normalized_order == "desc"),
    )
    return [item for _, item in present_items] + missing_items


def _occurrence_to_latest_payload(item: ScanResultOccurrence) -> dict:
    detail = item.detail
    finding = item.finding
    task = item.task
    return {
        "id": str(item.id),
        "task_id": str(item.task_id),
        "tool_name": task.tool_name,
        "sub_module": task.sub_module,
        "file_path": detail.file_path,
        "line_number": item.line_number,
        "defect_type": detail.defect_type,
        "severity": detail.severity,
        "description": detail.description,
        "fingerprint": finding.fingerprint,
        "shield_status": item.shield_status,
        "help_info": detail.help_info,
        "code_snippet": detail.code_snippet,
        "sys_create_datetime": item.created_at.isoformat(sep=" ", timespec="seconds")
        if getattr(item, "created_at", None)
        else None,
    }


def _legacy_result_to_latest_payload(item: ScanResult) -> dict:
    return {
        "id": str(item.id),
        "task_id": str(item.task_id),
        "tool_name": item.task.tool_name,
        "sub_module": item.task.sub_module,
        "file_path": item.file_path,
        "line_number": item.line_number,
        "defect_type": item.defect_type,
        "severity": item.severity,
        "description": item.description,
        "fingerprint": item.fingerprint,
        "shield_status": item.shield_status,
        "help_info": item.help_info,
        "code_snippet": item.code_snippet,
        "sys_create_datetime": item.sys_create_datetime.isoformat(sep=" ", timespec="seconds")
        if getattr(item, "sys_create_datetime", None)
        else None,
    }


def _sort_latest_payloads(items: list[dict]) -> list[dict]:
    severity_rank = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(
        items,
        key=lambda item: (
            severity_rank.get(str(item.get("severity") or ""), 99),
            str(item.get("file_path") or ""),
            int(item.get("line_number") or 0),
        ),
    )


def _apply_occurrence_filters(
    qs,
    normalized_shield_status: str | None,
    keyword_filters: dict[str, str],
):
    if normalized_shield_status:
        qs = qs.filter(shield_status=normalized_shield_status)
    occurrence_filter_map = {
        "severity": "detail__severity__icontains",
        "defect_type": "detail__defect_type__icontains",
        "file_path": "detail__file_path__icontains",
        "description": "detail__description__icontains",
    }
    for key, lookup in occurrence_filter_map.items():
        value = keyword_filters.get(key)
        if value:
            qs = qs.filter(**{lookup: value})
    return qs


def _apply_legacy_filters(
    qs,
    normalized_shield_status: str | None,
    keyword_filters: dict[str, str],
):
    if normalized_shield_status:
        qs = qs.filter(shield_status=normalized_shield_status)
    legacy_filter_map = {
        "severity": "severity__icontains",
        "defect_type": "defect_type__icontains",
        "file_path": "file_path__icontains",
        "description": "description__icontains",
    }
    for key, lookup in legacy_filter_map.items():
        value = keyword_filters.get(key)
        if value:
            qs = qs.filter(**{lookup: value})
    return qs


def _get_result_context(result_id: str):
    occurrence = None
    legacy_result = None
    if str(result_id).isdigit():
        occurrence = (
            ScanResultOccurrence.objects.select_related("task", "finding")
            .filter(
                id=result_id,
                is_deleted=False,
                task__is_deleted=False,
                task__project__is_deleted=False,
            )
            .first()
        )
    if occurrence is None:
        legacy_result = get_object_or_404(
            ScanResult.objects.select_related("task").filter(
                is_deleted=False,
                task__is_deleted=False,
                task__project__is_deleted=False,
            ),
            id=result_id,
        )
    return occurrence, legacy_result


def _application_context(app: ShieldApplication) -> dict:
    if app.occurrence_id:
        occurrence = app.occurrence
        detail = occurrence.detail
        return {
            "result_id": str(occurrence.id),
            "file_path": detail.file_path,
            "defect_description": detail.description,
            "severity": detail.severity,
            "tool_name": occurrence.task.tool_name,
            "help_info": detail.help_info,
            "code_snippet": detail.code_snippet,
        }

    result = app.result
    return {
        "result_id": str(result.id) if result else "",
        "file_path": result.file_path if result else None,
        "defect_description": result.description if result else None,
        "severity": result.severity if result else None,
        "tool_name": result.task.tool_name if result else None,
        "help_info": result.help_info if result else None,
        "code_snippet": result.code_snippet if result else None,
    }

# --- 项目管理 ---

@router.get("/projects", response=PaginatedScanProjectSchema, auth=BearerAuth(), summary="获取项目列表")
def list_projects(request, keyword: str = None, page: int = 1, pageSize: int = 20):
    qs = ScanProject.objects.filter(is_deleted=False).select_related('caretaker')
    if keyword:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=keyword) | Q(repo_url__icontains=keyword))
    
    total = qs.count()
    start = (page - 1) * pageSize
    end = start + pageSize
    items = list(qs[start:end])
    return {"items": items, "total": total}

@router.get("/projects/overview", response=PaginatedProjectOverviewSchema, auth=BearerAuth(), summary="获取项目概览")
def list_project_overview(
    request,
    page: int = 1,
    pageSize: int = 20,
    project_id: str = None,
    sub_modules: str = None,
    sort_field: str = None,
    sort_order: str = None,
):
    projects_qs = ScanProject.objects.filter(is_deleted=False)
    if project_id:
        projects_qs = projects_qs.filter(id=project_id)
    projects_qs = projects_qs.values("id", "name")

    total = projects_qs.count()
    projects = list(projects_qs)
    project_ids = [p["id"] for p in projects]

    task_rows = list(
        ScanTask.objects.filter(
            project_id__in=project_ids,
            is_deleted=False,
            project__is_deleted=False,
            status="success",
        )
        .order_by("-sys_create_datetime")
        .values("id", "project_id", "tool_name", "sub_module", "sys_create_datetime")
    )
    normalized_modules = _normalize_sub_modules(sub_modules)

    latest_rows_by_project: dict[str, list[dict]] = {p["id"]: [] for p in projects}
    project_task_rows: dict[str, list[dict]] = {p["id"]: [] for p in projects}
    for row in task_rows:
        pid = str(row["project_id"])
        if pid in project_task_rows:
            project_task_rows[pid].append(row)

    latest_task_ids: list[str] = []
    latest_time_by_project: dict[str, str | None] = {}
    for project in projects:
        pid = project["id"]
        latest_rows = _select_latest_task_rows(
            project_task_rows.get(pid, []),
            sub_modules=normalized_modules,
        )
        latest_rows_by_project[pid] = latest_rows
        if latest_rows:
            latest_dt = max(
                (row.get("sys_create_datetime") for row in latest_rows if row.get("sys_create_datetime")),
                default=None,
            )
            latest_time_by_project[pid] = (
                latest_dt.isoformat(sep=" ", timespec="seconds") if latest_dt else None
            )
            latest_task_ids.extend(str(row["id"]) for row in latest_rows)

    counts_by_task: dict[str, int] = {}
    if latest_task_ids:
        legacy_counts = (
            ScanResult.objects.filter(
                task_id__in=latest_task_ids,
                is_deleted=False,
                normalized_occurrence__isnull=True,
                task__is_deleted=False,
                task__project__is_deleted=False,
            )
            .values("task_id")
            .annotate(cnt=Count("id"))
        )
        occurrence_counts = (
            ScanResultOccurrence.objects.filter(
                task_id__in=latest_task_ids,
                is_deleted=False,
                task__is_deleted=False,
                task__project__is_deleted=False,
            )
            .values("task_id")
            .annotate(cnt=Count("id"))
        )
        for row in legacy_counts:
            task_id = str(row["task_id"])
            counts_by_task[task_id] = counts_by_task.get(task_id, 0) + int(row["cnt"])
        for row in occurrence_counts:
            task_id = str(row["task_id"])
            counts_by_task[task_id] = counts_by_task.get(task_id, 0) + int(row["cnt"])

    overview_by_project: dict[str, dict] = {
        p["id"]: {"tool_counts": {}, "total": None}
        for p in projects
    }
    for pid, latest_rows in latest_rows_by_project.items():
        tool_counts: dict[str, int] = {}
        total_count = 0
        for row in latest_rows:
            tool = _normalize_tool_name(row.get("tool_name"))
            if not tool:
                continue
            task_id = str(row["id"])
            cnt = counts_by_task.get(task_id, 0)
            tool_counts[tool] = tool_counts.get(tool, 0) + cnt
            total_count += cnt

        overview_by_project[pid]["tool_counts"] = tool_counts
        if tool_counts:
            overview_by_project[pid]["total"] = total_count

    items = [
        {
            "project_id": p["id"],
            "project_name": p["name"],
            "tool_counts": overview_by_project[p["id"]]["tool_counts"],
            "total": overview_by_project[p["id"]]["total"],
            "latest_time": latest_time_by_project.get(p["id"]),
        }
        for p in projects
    ]
    items = _sort_project_overview_items(items, sort_field, sort_order)
    start = (page - 1) * pageSize
    end = start + pageSize
    items = items[start:end]
    return {"items": items, "total": total}

@router.post("/projects", response=ScanProjectSchema, auth=BearerAuth(), summary="创建项目")
def create_project(request, data: ScanProjectCreateSchema):
    project = ScanService.create_project(data.dict(), request.auth)
    return project

@router.put("/projects/{project_id}", response=ScanProjectSchema, auth=BearerAuth(), summary="更新项目")
def update_project(request, project_id: str, data: ScanProjectCreateSchema):
    project = ScanService.update_project(project_id, data.dict(), request.auth)
    return project

@router.delete("/projects/{project_id}", response=bool, auth=BearerAuth(), summary="删除项目")
def delete_project(request, project_id: str):
    return ScanService.delete_project(project_id, request.auth)

# --- 任务上传 (流水线调用) ---

@router.post("/upload", response=ScanTaskSchema, auth=None, summary="上传扫描报告")
def upload_report(request, 
                 project_key: str = Form(...), 
                 tool_name: str = Form('tscan'),
                 sub_module: str = Form(""),
                 file: UploadedFile = File(...)):
    """
    接收流水线上传的扫描报告
    Auth: 无强制鉴权，依赖 project_key 校验
    """
    task = ScanService.handle_upload(project_key, tool_name, file, sub_module=sub_module)
    return task

@router.post("/upload/chunk", auth=None, summary="分片上传扫描报告")
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
        data.file_ext,
        data.sub_module,
    )
    return result

# --- 任务管理 ---

@router.get("/tasks", response=PaginatedScanTaskSchema, auth=BearerAuth(), summary="获取扫描任务列表")
def list_tasks(
    request,
    project_id: str = None,
    tool_name: str = None,
    status: str = None,
    page: int = 1,
    pageSize: int = 20,
):
    qs = ScanTask.objects.filter(
        is_deleted=False,
        project__is_deleted=False,
    )
    if project_id:
        qs = qs.filter(project_id=project_id)
    if tool_name:
        qs = qs.filter(tool_name=tool_name)
    if status:
        qs = qs.filter(status=status)
    total = qs.count()
    start = (page - 1) * pageSize
    end = start + pageSize
    items = list(qs[start:end])
    return {"items": items, "total": total}

# --- 结果管理 ---

@router.get("/results", auth=BearerAuth(), summary="获取任务结果列表")
def list_results(request, task_id: str):
    occurrences = list(
        ScanResultOccurrence.objects.filter(
            task_id=task_id,
            is_deleted=False,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        .select_related("task", "finding", "detail")
        .order_by("-detail__severity", "detail__file_path", "line_number")
    )
    results = list(ScanResult.objects.filter(
        task_id=task_id,
        is_deleted=False,
        normalized_occurrence__isnull=True,
        task__is_deleted=False,
        task__project__is_deleted=False,
    ).select_related("task"))
    payload = [_occurrence_to_latest_payload(item) for item in occurrences]
    payload.extend(_legacy_result_to_latest_payload(item) for item in results)
    return _sort_latest_payloads(payload)

@router.get("/results/{result_id}/shield-records", response=List[ShieldRecordSchema], auth=BearerAuth(), summary="获取屏蔽记录")
def list_result_shield_records(request, result_id: str):
    occurrence, legacy_result = _get_result_context(result_id)
    if occurrence:
        project_id = occurrence.task.project_id
        fingerprint = occurrence.finding.fingerprint
    else:
        project_id = legacy_result.task.project_id
        fingerprint = legacy_result.fingerprint

    apps = (
        ShieldApplication.objects.select_related(
            "applicant",
            "approver",
            "result",
            "result__task",
            "occurrence",
            "occurrence__finding",
            "occurrence__task",
        )
        .filter(
            is_deleted=False,
        )
        .filter(
            Q(
                result__is_deleted=False,
                result__task__is_deleted=False,
                result__task__project__is_deleted=False,
                result__task__project_id=project_id,
                result__fingerprint=fingerprint,
            )
            | Q(
                occurrence__is_deleted=False,
                occurrence__task__is_deleted=False,
                occurrence__task__project__is_deleted=False,
                occurrence__finding__project_id=project_id,
                occurrence__finding__fingerprint=fingerprint,
            )
        )
        .distinct()
        .order_by("-sys_create_datetime")
    )
    payload = []
    for app in apps:
        payload.append(
            {
                "id": str(app.id),
                "result_id": str(app.occurrence_id or app.result_id or ""),
                "status": app.status,
                "reason": app.reason,
                "audit_comment": app.audit_comment,
                "applicant_name": (app.applicant.name or app.applicant.username) if app.applicant else None,
                "approver_name": (app.approver.name or app.approver.username) if app.approver else None,
                "sys_create_datetime": app.sys_create_datetime.isoformat(sep=" ", timespec="seconds")
                if getattr(app, "sys_create_datetime", None)
                else None,
                "sys_update_datetime": app.sys_update_datetime.isoformat(sep=" ", timespec="seconds")
                if getattr(app, "sys_update_datetime", None)
                else None,
            }
        )
    return payload

@router.get("/projects/{project_id}/latest-results", response=PaginatedScanResultSchema, auth=BearerAuth(), summary="获取最新扫描结果")
def list_latest_results(
    request,
    project_id: str,
    tool_name: str = None,
    shield_status: str = None,
    sub_modules: str = None,
    severity_keyword: str = None,
    defect_type_keyword: str = None,
    file_path_keyword: str = None,
    description_keyword: str = None,
    page: int = 1,
    pageSize: int = 20,
):
    tasks_qs = ScanTask.objects.filter(
        project_id=project_id,
        is_deleted=False,
        project__is_deleted=False,
        status="success",
    )
    
    if tool_name:
        # If tool_name is specified, get latest task for that tool
        # Actually, we want latest task per tool, but filter by tool_name if provided
        tasks_qs = tasks_qs.filter(tool_name=tool_name)

    normalized_modules = _normalize_sub_modules(sub_modules)
    normalized_shield_status = _normalize_shield_status(shield_status)
    if shield_status and not normalized_shield_status:
        return {"items": [], "total": 0}

    task_ids = _select_latest_task_ids(
        tasks_qs,
        tool_name=tool_name,
        sub_modules=normalized_modules,
    )

    if not task_ids:
        return {"items": [], "total": 0}

    keyword_filters = {
        "severity": _normalize_keyword(severity_keyword),
        "defect_type": _normalize_keyword(defect_type_keyword),
        "file_path": _normalize_keyword(file_path_keyword),
        "description": _normalize_keyword(description_keyword),
    }

    start = (page - 1) * pageSize
    end = start + pageSize

    occurrence_qs = (
        ScanResultOccurrence.objects.filter(
            task_id__in=task_ids,
            is_deleted=False,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        .select_related("task", "finding", "detail")
        .order_by("-detail__severity", "detail__file_path", "line_number")
    )
    occurrence_qs = _apply_occurrence_filters(
        occurrence_qs,
        normalized_shield_status,
        keyword_filters,
    )

    legacy_qs = (
        ScanResult.objects.filter(
            task_id__in=task_ids,
            is_deleted=False,
            normalized_occurrence__isnull=True,
            task__is_deleted=False,
            task__project__is_deleted=False,
        )
        .select_related("task")
        .order_by("-severity", "file_path", "line_number")
    )
    legacy_qs = _apply_legacy_filters(
        legacy_qs,
        normalized_shield_status,
        keyword_filters,
    )

    occurrence_count = occurrence_qs.count()
    legacy_count = legacy_qs.count()
    if occurrence_count and not legacy_count:
        return {
            "items": [_occurrence_to_latest_payload(item) for item in occurrence_qs[start:end]],
            "total": occurrence_count,
        }

    if legacy_count and not occurrence_count:
        total = legacy_count
        return {
            "items": [_legacy_result_to_latest_payload(item) for item in legacy_qs[start:end]],
            "total": total,
        }

    payload = [_occurrence_to_latest_payload(item) for item in occurrence_qs]
    payload.extend(_legacy_result_to_latest_payload(item) for item in legacy_qs)
    payload = _sort_latest_payloads(payload)
    return {"items": payload[start:end], "total": len(payload)}

# --- 屏蔽申请与审批 ---

@router.post("/shield/apply", auth=BearerAuth(), summary="申请屏蔽缺陷")
def apply_shield(request, data: ShieldApplySchema):
    ScanService.apply_shield(request.auth, data.result_ids, data.approver_id, data.reason)
    return {"message": "Application submitted"}

@router.get("/shield/applications", response=PaginatedShieldApplicationSchema, auth=BearerAuth(), summary="获取屏蔽申请列表")
def list_applications(request, mode: str = "my_apply", page: int = 1, pageSize: int = 20):
    user = request.auth  # BearerAuth returns user in request.auth
    base_qs = ShieldApplication.objects.filter(
        is_deleted=False,
    ).filter(
        Q(
            result__is_deleted=False,
            result__task__is_deleted=False,
            result__task__project__is_deleted=False,
        )
        | Q(
            occurrence__is_deleted=False,
            occurrence__task__is_deleted=False,
            occurrence__task__project__is_deleted=False,
        )
    )
    if mode == "my_apply":
        qs = base_qs.filter(applicant=user)
    else:
        qs = base_qs.filter(approver=user)
    
    total = qs.count()
    start = (page - 1) * pageSize
    end = start + pageSize
    page_qs = qs[start:end]

    results = []
    for app in page_qs.select_related(
        "applicant",
        "approver",
        "result",
        "result__task",
        "occurrence",
        "occurrence__task",
        "occurrence__detail",
    ):
        context = _application_context(app)
        results.append(
            {
                "id": str(app.id),
                "result_id": context["result_id"],
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
                "file_path": context["file_path"],
                "defect_description": context["defect_description"],
                "severity": context["severity"],
                "tool_name": context["tool_name"],
                "help_info": context["help_info"],
                "code_snippet": context["code_snippet"],
            }
        )
    return {"items": results, "total": total}

@router.post("/shield/audit", auth=BearerAuth(), summary="审核屏蔽申请")
def audit_shield(request, data: ShieldAuditSchema):
    application_ids = list(data.application_ids or [])
    if data.application_id:
        application_ids.append(data.application_id)
    application_ids = list(dict.fromkeys([item for item in application_ids if item]))

    if not application_ids:
        raise HttpError(400, "application_id 或 application_ids 至少传一个")
    if data.status not in ["Approved", "Rejected"]:
        raise HttpError(400, "status 仅支持 Approved 或 Rejected")

    processed = ScanService.audit_shield_batch(
        request.auth,
        application_ids,
        data.status,
        data.audit_comment,
    )
    return {"message": "Audit completed", "processed": processed}
