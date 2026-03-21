import logging
import threading
from typing import Any

from django.core.cache import cache
from django.db import close_old_connections, connection, transaction
from django.utils import timezone
from ninja.errors import HttpError

from apps.project_manager.project.project_model import Project
from apps.project_manager.requirement_board import requirement_board_services
from scheduler.module.executor import scheduler_task

from .requirement_workspace_model import (
    RequirementWorkspaceRefreshTask,
    RequirementWorkspaceSnapshot,
)

logger = logging.getLogger(__name__)

DEFAULT_SCOPE = "active_configured"
DEFAULT_VIEW_SCOPE = "all"
FAVORITES_VIEW_SCOPE = "favorites"
LOCK_TTL_SECONDS = 15 * 60
PREVIEW_LIMIT = 8
FIELD_DEFINITIONS = (
    ("planned_test_time", "计划转测时间"),
    ("due_date", "计划完成时间"),
    ("develop_users", "开发责任人"),
    ("test_users", "测试责任人"),
    ("workload_man_day", "工作量(人天)"),
    ("workload_kloc", "代码量(KLOC)"),
)
FIELD_LABEL_MAP = dict(FIELD_DEFINITIONS)
OWNER_REQUIRED_STATUS_CODES = {"P", "C", "A"}
WORKLOAD_REQUIRED_STATUS_CODES = {"C", "A"}
TASK_ACTIVE_STATUSES = {
    RequirementWorkspaceRefreshTask.STATUS_PENDING,
    RequirementWorkspaceRefreshTask.STATUS_RUNNING,
}


def _normalize_text_list(values: Any) -> list[str]:
    if values is None:
        return []
    raw_values = values if isinstance(values, list) else [values]
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _validate_scope(scope: str) -> str:
    normalized = str(scope or DEFAULT_SCOPE).strip() or DEFAULT_SCOPE
    if normalized != DEFAULT_SCOPE:
        raise HttpError(422, f"不支持的快照范围: {normalized}")
    return normalized


def _validate_view_scope(scope: str) -> str:
    normalized = str(scope or DEFAULT_VIEW_SCOPE).strip() or DEFAULT_VIEW_SCOPE
    if normalized not in {DEFAULT_VIEW_SCOPE, FAVORITES_VIEW_SCOPE}:
        raise HttpError(422, f"不支持的视图范围: {normalized}")
    return normalized


def list_workspace_projects(scope: str = DEFAULT_SCOPE) -> list[Project]:
    normalized_scope = _validate_scope(scope)
    if normalized_scope != DEFAULT_SCOPE:
        return []

    projects = list(
        Project.objects.filter(is_deleted=False, is_closed=False)
        .order_by("name")
        .only("id", "name", "design_id", "sub_teams")
    )
    return [
        project
        for project in projects
        if str(project.design_id or "").strip() and _normalize_text_list(project.sub_teams)
    ]


def _get_favorite_project_id_set(user: Any) -> set[str]:
    if not user or not getattr(user, "id", None):
        return set()
    return {
        str(project_id)
        for project_id in Project.objects.filter(
            favorited_by=user,
            is_deleted=False,
            is_closed=False,
        ).values_list("id", flat=True)
    }


def _filter_preview_map(
    preview_map: dict[str, list[dict[str, Any]]],
    allowed_project_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    filtered: dict[str, list[dict[str, Any]]] = {}
    for key, rows in (preview_map or {}).items():
        filtered[key] = [
            row
            for row in rows or []
            if str(row.get("project_id") or "") in allowed_project_ids
        ][:PREVIEW_LIMIT]
    return filtered


def _rebuild_field_overview_from_project_rows(
    project_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    field_overview_map = {
        field_key: _create_field_stat(field_key)
        for field_key, _ in FIELD_DEFINITIONS
    }

    for row in project_rows:
        fields = row.get("fields") or {}
        for field_key, _ in FIELD_DEFINITIONS:
            source = fields.get(field_key) or {}
            target = field_overview_map[field_key]
            target["applicable_count"] += int(source.get("applicable_count") or 0)
            target["filled_count"] += int(source.get("filled_count") or 0)
            target["missing_count"] += int(source.get("missing_count") or 0)

    return [
        _finalize_field_stat(field_overview_map[field_key])
        for field_key, _ in FIELD_DEFINITIONS
    ]


def _filter_snapshot_response_by_project_ids(
    snapshot_payload: dict[str, Any],
    *,
    view_scope: str,
    allowed_project_ids: set[str],
) -> dict[str, Any]:
    project_rows = [
        row
        for row in snapshot_payload.get("project_rows") or []
        if str(row.get("project_id") or "") in allowed_project_ids
    ]
    requirement_count = sum(int(row.get("total_count") or 0) for row in project_rows)

    return {
        "generated_at": snapshot_payload.get("generated_at"),
        "scope": view_scope,
        "project_count": len(project_rows),
        "requirement_count": requirement_count,
        "field_overview": _rebuild_field_overview_from_project_rows(project_rows),
        "project_rows": project_rows,
        "missing_previews": _filter_preview_map(
            snapshot_payload.get("missing_previews") or {},
            allowed_project_ids,
        ),
        "delay_previews": _filter_preview_map(
            snapshot_payload.get("delay_previews") or {},
            allowed_project_ids,
        ),
        "refresh_task": snapshot_payload.get("refresh_task"),
    }


def _create_field_stat(field_key: str) -> dict[str, Any]:
    return {
        "field_key": field_key,
        "field_label": FIELD_LABEL_MAP[field_key],
        "applicable_count": 0,
        "filled_count": 0,
        "missing_count": 0,
        "filled_rate": 0.0,
    }


def _create_project_fields() -> dict[str, dict[str, Any]]:
    return {
        field_key: {
            "applicable_count": 0,
            "filled_count": 0,
            "missing_count": 0,
            "filled_rate": 0.0,
        }
        for field_key, _ in FIELD_DEFINITIONS
    }


def _create_project_row(project_id: str, project_name: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "project_name": project_name,
        "total_count": 0,
        "fields": _create_project_fields(),
        "delay": {
            "development_count": 0,
            "development_rate": 0.0,
            "acceptance_count": 0,
            "acceptance_rate": 0.0,
        },
        "completion_score": 0.0,
    }


def _create_missing_previews() -> dict[str, list[dict[str, Any]]]:
    return {field_key: [] for field_key, _ in FIELD_DEFINITIONS}


def _create_delay_previews() -> dict[str, list[dict[str, Any]]]:
    return {"development": [], "acceptance": []}


def _finalize_field_stat(payload: dict[str, Any]) -> dict[str, Any]:
    applicable_count = int(payload.get("applicable_count") or 0)
    filled_count = int(payload.get("filled_count") or 0)
    missing_count = int(payload.get("missing_count") or 0)
    return {
        **payload,
        "applicable_count": applicable_count,
        "filled_count": filled_count,
        "missing_count": missing_count,
        "filled_rate": round((filled_count / applicable_count) if applicable_count else 0.0, 4),
    }


def _build_preview_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(item.get("project_id") or ""),
        "project_name": str(item.get("project_name") or ""),
        "team_name": str(item.get("team_name") or ""),
        "requirement_id": str(item.get("requirement_id") or ""),
        "title": str(item.get("title") or ""),
        "status_code": str(item.get("status_code") or ""),
        "status_label": str(item.get("status_label") or ""),
        "planned_test_time": item.get("planned_test_time"),
        "due_date": item.get("due_date"),
        "completed_time": item.get("completed_time"),
        "accepted_time": item.get("accepted_time"),
        "develop_user_display": str(item.get("develop_user_display") or ""),
        "test_user_display": str(item.get("test_user_display") or ""),
    }


def _append_preview(
    bucket: list[dict[str, Any]],
    preview_item: dict[str, Any],
    *,
    sort_field: str | None = None,
) -> None:
    bucket.append(preview_item)

    if sort_field:
        bucket.sort(
            key=lambda row: (
                row.get(sort_field) or "9999-12-31 23:59:59",
                row.get("project_name") or "",
                row.get("requirement_id") or "",
            )
        )
    else:
        bucket.sort(
            key=lambda row: (
                row.get("project_name") or "",
                row.get("requirement_id") or "",
            )
        )

    del bucket[PREVIEW_LIMIT:]


def _is_field_applicable(field_key: str, item: dict[str, Any]) -> bool:
    status_code = str(item.get("status_code") or "")
    if field_key in {"planned_test_time", "due_date"}:
        return True
    if field_key in {"develop_users", "test_users"}:
        return status_code in OWNER_REQUIRED_STATUS_CODES
    if field_key in {"workload_man_day", "workload_kloc"}:
        return status_code in WORKLOAD_REQUIRED_STATUS_CODES
    return False


def _is_field_filled(field_key: str, item: dict[str, Any]) -> bool:
    if field_key == "planned_test_time":
        return bool(item.get("has_planned_test_time"))
    if field_key == "due_date":
        return bool(item.get("has_due_date"))
    if field_key == "develop_users":
        return bool(item.get("has_develop_users"))
    if field_key == "test_users":
        return bool(item.get("has_test_users"))
    if field_key == "workload_man_day":
        return bool(item.get("has_workload_man_day"))
    if field_key == "workload_kloc":
        return bool(item.get("has_workload_kloc"))
    return False


def _empty_snapshot_payload(
    *,
    scope: str,
    project_count: int,
    requirement_count: int = 0,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "overview": {
            "scope": scope,
            "project_count": project_count,
            "requirement_count": requirement_count,
            "generated_at": generated_at,
        },
        "field_overview": [
            _finalize_field_stat(_create_field_stat(field_key))
            for field_key, _ in FIELD_DEFINITIONS
        ],
        "project_rows": [],
        "missing_previews": _create_missing_previews(),
        "delay_previews": _create_delay_previews(),
    }


def _serialize_refresh_task(
    task: RequirementWorkspaceRefreshTask | None,
) -> dict[str, Any] | None:
    if task is None:
        return None
    return {
        "id": str(task.id),
        "scope": str(task.scope or ""),
        "status": str(task.status or ""),
        "message": str(task.message or ""),
        "error_message": str(task.error_message or ""),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "snapshot_date": task.snapshot_date.isoformat() if task.snapshot_date else None,
        "snapshot_id": str(task.snapshot_id) if task.snapshot_id else None,
    }


def build_requirement_workspace_snapshot_payload(
    projects: list[Project],
    items: list[dict[str, Any]],
    *,
    scope: str,
    generated_at,
) -> dict[str, Any]:
    field_overview_map = {
        field_key: _create_field_stat(field_key)
        for field_key, _ in FIELD_DEFINITIONS
    }
    missing_previews = _create_missing_previews()
    delay_previews = _create_delay_previews()
    project_rows_map = {
        str(project.id): _create_project_row(str(project.id), project.name)
        for project in projects
    }

    for item in items:
        project_id = str(item.get("project_id") or "")
        project_name = str(item.get("project_name") or "未匹配项目")
        project_key = project_id or f"__unmatched__:{project_name}"
        if project_key not in project_rows_map:
            project_rows_map[project_key] = _create_project_row(project_id, project_name)
        project_row = project_rows_map[project_key]
        project_row["total_count"] += 1

        preview_item = _build_preview_item(item)
        for field_key, _ in FIELD_DEFINITIONS:
            if not _is_field_applicable(field_key, item):
                continue

            top_level_row = field_overview_map[field_key]
            project_field_row = project_row["fields"][field_key]
            top_level_row["applicable_count"] += 1
            project_field_row["applicable_count"] += 1

            if _is_field_filled(field_key, item):
                top_level_row["filled_count"] += 1
                project_field_row["filled_count"] += 1
                continue

            top_level_row["missing_count"] += 1
            project_field_row["missing_count"] += 1
            _append_preview(missing_previews[field_key], preview_item)

        if item.get("is_dev_delayed"):
            project_row["delay"]["development_count"] += 1
            _append_preview(
                delay_previews["development"],
                preview_item,
                sort_field="planned_test_time",
            )

        if item.get("is_test_delayed"):
            project_row["delay"]["acceptance_count"] += 1
            _append_preview(
                delay_previews["acceptance"],
                preview_item,
                sort_field="due_date",
            )

    field_overview = [
        _finalize_field_stat(field_overview_map[field_key])
        for field_key, _ in FIELD_DEFINITIONS
    ]

    project_rows: list[dict[str, Any]] = []
    for project_row in project_rows_map.values():
        total_count = int(project_row["total_count"] or 0)
        finalized_fields = {}
        score_parts: list[float] = []
        for field_key, _ in FIELD_DEFINITIONS:
            finalized_field = _finalize_field_stat(project_row["fields"][field_key])
            finalized_fields[field_key] = finalized_field
            score_parts.append(float(finalized_field["filled_rate"]))

        project_row["fields"] = finalized_fields
        project_row["delay"]["development_rate"] = round(
            (project_row["delay"]["development_count"] / total_count)
            if total_count
            else 0.0,
            4,
        )
        project_row["delay"]["acceptance_rate"] = round(
            (project_row["delay"]["acceptance_count"] / total_count)
            if total_count
            else 0.0,
            4,
        )
        project_row["completion_score"] = round(
            (sum(score_parts) / len(score_parts)) if score_parts else 0.0,
            4,
        )
        project_rows.append(project_row)

    project_rows.sort(
        key=lambda row: (
            -float(row.get("completion_score") or 0.0),
            -int(row.get("total_count") or 0),
            str(row.get("project_name") or ""),
        )
    )

    return {
        "overview": {
            "scope": scope,
            "project_count": len(projects),
            "requirement_count": len(items),
            "generated_at": generated_at.isoformat() if generated_at else None,
        },
        "field_overview": field_overview,
        "project_rows": project_rows,
        "missing_previews": missing_previews,
        "delay_previews": delay_previews,
    }


def _serialize_snapshot(
    snapshot: RequirementWorkspaceSnapshot | None,
    *,
    scope: str,
    project_count: int | None = None,
) -> dict[str, Any]:
    if snapshot is None:
        resolved_project_count = (
            int(project_count)
            if project_count is not None
            else len(list_workspace_projects(DEFAULT_SCOPE))
        )
        payload = _empty_snapshot_payload(
            scope=scope,
            project_count=resolved_project_count,
        )
        return {
            "generated_at": None,
            "scope": scope,
            "project_count": resolved_project_count,
            "requirement_count": 0,
            "field_overview": payload["field_overview"],
            "project_rows": payload["project_rows"],
            "missing_previews": payload["missing_previews"],
            "delay_previews": payload["delay_previews"],
            "refresh_task": None,
        }

    payload = snapshot.payload or {}
    empty_payload = _empty_snapshot_payload(
        scope=scope,
        project_count=int(snapshot.project_count or 0),
        requirement_count=int(snapshot.requirement_count or 0),
        generated_at=snapshot.generated_at.isoformat() if snapshot.generated_at else None,
    )
    return {
        "generated_at": snapshot.generated_at.isoformat() if snapshot.generated_at else None,
        "scope": scope,
        "project_count": int(snapshot.project_count or 0),
        "requirement_count": int(snapshot.requirement_count or 0),
        "field_overview": payload.get("field_overview") or empty_payload["field_overview"],
        "project_rows": payload.get("project_rows") or empty_payload["project_rows"],
        "missing_previews": payload.get("missing_previews") or empty_payload["missing_previews"],
        "delay_previews": payload.get("delay_previews") or empty_payload["delay_previews"],
        "refresh_task": None,
    }


def _get_latest_snapshot(scope: str) -> RequirementWorkspaceSnapshot | None:
    return (
        RequirementWorkspaceSnapshot.objects.filter(scope=scope, is_deleted=False)
        .order_by("-snapshot_date", "-generated_at", "-sys_update_datetime")
        .first()
    )


def _get_active_refresh_task(scope: str = DEFAULT_SCOPE) -> RequirementWorkspaceRefreshTask | None:
    return (
        RequirementWorkspaceRefreshTask.objects.filter(
            scope=scope,
            status__in=TASK_ACTIVE_STATUSES,
            is_deleted=False,
        )
        .order_by("-sys_create_datetime")
        .first()
    )


def _attach_refresh_task(
    payload: dict[str, Any],
    task: RequirementWorkspaceRefreshTask | None,
) -> dict[str, Any]:
    return {
        **payload,
        "refresh_task": _serialize_refresh_task(task),
    }


def _get_scoped_snapshot_response(
    *,
    view_scope: str,
    user: Any = None,
    snapshot: RequirementWorkspaceSnapshot | None,
) -> dict[str, Any]:
    normalized_view_scope = _validate_view_scope(view_scope)
    active_task = _get_active_refresh_task(DEFAULT_SCOPE)
    if normalized_view_scope == DEFAULT_VIEW_SCOPE:
        return _attach_refresh_task(
            _serialize_snapshot(snapshot, scope=normalized_view_scope),
            active_task,
        )

    favorite_project_ids = _get_favorite_project_id_set(user)
    if snapshot is None:
        configured_favorite_count = len(
            [
                project
                for project in list_workspace_projects(DEFAULT_SCOPE)
                if str(project.id) in favorite_project_ids
            ]
        )
        return _attach_refresh_task(
            _serialize_snapshot(
                None,
                scope=normalized_view_scope,
                project_count=configured_favorite_count,
            ),
            active_task,
        )

    base_payload = _serialize_snapshot(snapshot, scope=DEFAULT_VIEW_SCOPE)
    scoped_payload = _filter_snapshot_response_by_project_ids(
        base_payload,
        view_scope=normalized_view_scope,
        allowed_project_ids=favorite_project_ids,
    )
    return _attach_refresh_task(scoped_payload, active_task)


def get_latest_requirement_workspace_snapshot(
    view_scope: str = DEFAULT_VIEW_SCOPE,
    *,
    user: Any = None,
) -> dict[str, Any]:
    snapshot = _get_latest_snapshot(DEFAULT_SCOPE)
    return _get_scoped_snapshot_response(
        view_scope=view_scope,
        user=user,
        snapshot=snapshot,
    )


def _refresh_base_requirement_workspace_snapshot() -> RequirementWorkspaceSnapshot:
    normalized_scope = _validate_scope(DEFAULT_SCOPE)
    today = timezone.now().date()
    lock_key = f"pm:requirement-workspace:snapshot:{normalized_scope}:{today.isoformat()}:lock"
    lock_acquired = cache.add(lock_key, "1", LOCK_TTL_SECONDS)
    if not lock_acquired:
        latest_snapshot = _get_latest_snapshot(normalized_scope)
        if latest_snapshot and latest_snapshot.snapshot_date == today:
            return latest_snapshot
        raise HttpError(409, "需求交付合规快照正在生成，请稍后重试")

    try:
        generated_at = timezone.now()
        projects = list_workspace_projects(normalized_scope)
        items: list[dict[str, Any]] = []
        if projects:
            items = requirement_board_services.scan_standardized_requirement_items(
                [str(project.id) for project in projects]
            )

        payload = build_requirement_workspace_snapshot_payload(
            projects,
            items,
            scope=normalized_scope,
            generated_at=generated_at,
        )

        with transaction.atomic():
            snapshot, _ = RequirementWorkspaceSnapshot.objects.update_or_create(
                snapshot_date=today,
                scope=normalized_scope,
                defaults={
                    "generated_at": generated_at,
                    "project_count": len(projects),
                    "requirement_count": len(items),
                    "payload": payload,
                },
            )

        logger.info(
            "Requirement workspace snapshot refreshed: scope=%s, projects=%s, requirements=%s",
            normalized_scope,
            len(projects),
            len(items),
        )
        return snapshot
    finally:
        if lock_acquired:
            cache.delete(lock_key)


def refresh_requirement_workspace_snapshot(
    view_scope: str = DEFAULT_VIEW_SCOPE,
    *,
    user: Any = None,
) -> dict[str, Any]:
    snapshot = _refresh_base_requirement_workspace_snapshot()
    return _get_scoped_snapshot_response(
        view_scope=view_scope,
        user=user,
        snapshot=snapshot,
    )


def _run_requirement_workspace_refresh_task(task_id: str) -> None:
    close_old_connections()
    try:
        task = RequirementWorkspaceRefreshTask.objects.filter(
            id=task_id,
            is_deleted=False,
        ).first()
        if task is None:
            return

        RequirementWorkspaceRefreshTask.objects.filter(id=task_id).update(
            status=RequirementWorkspaceRefreshTask.STATUS_RUNNING,
            message="正在生成需求交付合规快照",
            error_message="",
            started_at=timezone.now(),
            finished_at=None,
        )

        snapshot = _refresh_base_requirement_workspace_snapshot()
        RequirementWorkspaceRefreshTask.objects.filter(id=task_id).update(
            status=RequirementWorkspaceRefreshTask.STATUS_SUCCESS,
            message="需求交付合规快照已生成",
            error_message="",
            finished_at=timezone.now(),
            snapshot_date=snapshot.snapshot_date,
            snapshot_id=snapshot.id,
        )
    except Exception as exc:
        logger.exception("Requirement workspace refresh task failed: task_id=%s", task_id)
        RequirementWorkspaceRefreshTask.objects.filter(id=task_id).update(
            status=RequirementWorkspaceRefreshTask.STATUS_FAILED,
            message="需求交付合规快照生成失败",
            error_message=str(exc),
            finished_at=timezone.now(),
        )
    finally:
        connection.close()


def _start_requirement_workspace_refresh_task_thread(task_id: str) -> None:
    thread = threading.Thread(
        target=_run_requirement_workspace_refresh_task,
        args=(task_id,),
        daemon=True,
    )
    thread.start()


def submit_requirement_workspace_refresh_task(
    view_scope: str = DEFAULT_VIEW_SCOPE,
    *,
    user: Any = None,
) -> dict[str, Any]:
    _validate_view_scope(view_scope)
    active_task = _get_active_refresh_task(DEFAULT_SCOPE)
    if active_task is not None:
        return _serialize_refresh_task(active_task) or {}

    task = RequirementWorkspaceRefreshTask.objects.create(
        scope=DEFAULT_SCOPE,
        requested_by=user if getattr(user, "id", None) else None,
        sys_creator=user if getattr(user, "id", None) else None,
        status=RequirementWorkspaceRefreshTask.STATUS_PENDING,
        message="刷新任务已提交，正在排队执行",
    )
    _start_requirement_workspace_refresh_task_thread(str(task.id))
    return _serialize_refresh_task(task) or {}


def get_requirement_workspace_refresh_task(task_id: str) -> dict[str, Any]:
    task = RequirementWorkspaceRefreshTask.objects.filter(
        id=task_id,
        is_deleted=False,
    ).first()
    if task is None:
        raise HttpError(404, "刷新任务不存在")
    return _serialize_refresh_task(task) or {}


@scheduler_task
def run_requirement_workspace_snapshot_job(
    scope: str = DEFAULT_SCOPE,
    **kwargs,
):
    actual_scope = str(kwargs.get("scope") or scope or DEFAULT_SCOPE).strip() or DEFAULT_SCOPE
    if actual_scope != DEFAULT_SCOPE:
        raise HttpError(422, f"调度任务仅支持基础快照范围: {DEFAULT_SCOPE}")
    snapshot_obj = _refresh_base_requirement_workspace_snapshot()
    snapshot = _serialize_snapshot(snapshot_obj, scope=DEFAULT_SCOPE)
    return (
        f"scope={snapshot['scope']}, generated_at={snapshot['generated_at']}, "
        f"projects={snapshot['project_count']}, requirements={snapshot['requirement_count']}"
    )
