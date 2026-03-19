import logging
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from ninja.errors import HttpError

from apps.project_manager.project.project_model import Project
from apps.project_manager.requirement_board import requirement_board_services
from scheduler.module.executor import scheduler_task

from .requirement_workspace_model import RequirementWorkspaceSnapshot

logger = logging.getLogger(__name__)

DEFAULT_SCOPE = "active_configured"
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


def _serialize_snapshot(snapshot: RequirementWorkspaceSnapshot | None, *, scope: str) -> dict[str, Any]:
    if snapshot is None:
        project_count = len(list_workspace_projects(scope))
        payload = _empty_snapshot_payload(scope=scope, project_count=project_count)
        return {
            "generated_at": None,
            "scope": scope,
            "project_count": project_count,
            "requirement_count": 0,
            "field_overview": payload["field_overview"],
            "project_rows": payload["project_rows"],
            "missing_previews": payload["missing_previews"],
            "delay_previews": payload["delay_previews"],
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
        "scope": snapshot.scope,
        "project_count": int(snapshot.project_count or 0),
        "requirement_count": int(snapshot.requirement_count or 0),
        "field_overview": payload.get("field_overview") or empty_payload["field_overview"],
        "project_rows": payload.get("project_rows") or empty_payload["project_rows"],
        "missing_previews": payload.get("missing_previews") or empty_payload["missing_previews"],
        "delay_previews": payload.get("delay_previews") or empty_payload["delay_previews"],
    }


def _get_latest_snapshot(scope: str) -> RequirementWorkspaceSnapshot | None:
    return (
        RequirementWorkspaceSnapshot.objects.filter(scope=scope, is_deleted=False)
        .order_by("-snapshot_date", "-generated_at", "-sys_update_datetime")
        .first()
    )


def get_latest_requirement_workspace_snapshot(scope: str = DEFAULT_SCOPE) -> dict[str, Any]:
    normalized_scope = _validate_scope(scope)
    snapshot = _get_latest_snapshot(normalized_scope)
    return _serialize_snapshot(snapshot, scope=normalized_scope)


def refresh_requirement_workspace_snapshot(scope: str = DEFAULT_SCOPE) -> dict[str, Any]:
    normalized_scope = _validate_scope(scope)
    today = timezone.now().date()
    lock_key = f"pm:requirement-workspace:snapshot:{normalized_scope}:{today.isoformat()}:lock"
    lock_acquired = cache.add(lock_key, "1", LOCK_TTL_SECONDS)
    if not lock_acquired:
        latest_snapshot = _get_latest_snapshot(normalized_scope)
        if latest_snapshot and latest_snapshot.snapshot_date == today:
            return _serialize_snapshot(latest_snapshot, scope=normalized_scope)
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
        return _serialize_snapshot(snapshot, scope=normalized_scope)
    finally:
        if lock_acquired:
            cache.delete(lock_key)


@scheduler_task
def run_requirement_workspace_snapshot_job(
    scope: str = DEFAULT_SCOPE,
    **kwargs,
):
    actual_scope = str(kwargs.get("scope") or scope or DEFAULT_SCOPE).strip() or DEFAULT_SCOPE
    snapshot = refresh_requirement_workspace_snapshot(scope=actual_scope)
    return (
        f"scope={snapshot['scope']}, generated_at={snapshot['generated_at']}, "
        f"projects={snapshot['project_count']}, requirements={snapshot['requirement_count']}"
    )
