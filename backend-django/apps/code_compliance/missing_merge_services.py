from __future__ import annotations

import logging
import re
import threading
from collections import Counter
from collections import defaultdict
from collections.abc import Iterable as RuntimeIterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from scheduler.module.executor import scheduler_task
from core.pl.pl_model import PlGroup
from core.user.user_model import User

from . import base_services
from .missing_merge_client import CodeComplianceCRClient, DEFAULT_PAGE_SIZE
from .models import (
    COMPLIANCE_BRANCH_TYPE_RELEASE,
    COMPLIANCE_BRANCH_TYPE_TRUNK,
    MISSING_MERGE_SCAN_STATUS_FAILED,
    MISSING_MERGE_SCAN_STATUS_PENDING,
    MISSING_MERGE_SCAN_STATUS_RUNNING,
    MISSING_MERGE_SCAN_STATUS_SUCCESS,
    MISSING_MERGE_SCAN_TRIGGER_CHOICES,
    MISSING_MERGE_SCAN_TRIGGER_MANUAL,
    MISSING_MERGE_SCAN_TRIGGER_SCHEDULED,
    MISSING_MERGE_OPERATION_AUTO_CLOSED,
    MISSING_MERGE_OPERATION_CHOICES,
    MISSING_MERGE_OPERATION_DETECTED,
    MISSING_MERGE_OPERATION_MANUAL_HANDLE,
    MISSING_MERGE_OPERATION_REOPENED,
    MISSING_MERGE_OPERATION_SOURCE_CHOICES,
    MISSING_MERGE_OPERATION_SOURCE_MANUAL,
    MISSING_MERGE_OPERATION_SOURCE_SYSTEM,
    MISSING_MERGE_STATUS_CHOICES,
    MISSING_MERGE_STATUS_FIXED,
    MISSING_MERGE_STATUS_IGNORED,
    MISSING_MERGE_STATUS_OPEN,
    ComplianceMissingMergeOperationLog,
    ComplianceMissingMergeRecord,
    ComplianceMissingMergeScanTask,
    ComplianceOrganization,
    ComplianceRepository,
    ComplianceRepositoryBranch,
)


logger = logging.getLogger(__name__)

STATUS_LABELS = dict(MISSING_MERGE_STATUS_CHOICES)
SCAN_STATUS_LABELS = {
    MISSING_MERGE_SCAN_STATUS_PENDING: "待执行",
    MISSING_MERGE_SCAN_STATUS_RUNNING: "执行中",
    MISSING_MERGE_SCAN_STATUS_SUCCESS: "成功",
    MISSING_MERGE_SCAN_STATUS_FAILED: "失败",
}
SCAN_TRIGGER_LABELS = dict(MISSING_MERGE_SCAN_TRIGGER_CHOICES)
OPERATION_LABELS = dict(MISSING_MERGE_OPERATION_CHOICES)
OPERATION_SOURCE_LABELS = dict(MISSING_MERGE_OPERATION_SOURCE_CHOICES)
SUPPORTED_RECORD_STATUSES = {
    MISSING_MERGE_STATUS_OPEN,
    MISSING_MERGE_STATUS_FIXED,
    MISSING_MERGE_STATUS_IGNORED,
}
HANDLE_REMARK_MIN_LENGTH = 5
HANDLE_REMARK_MAX_LENGTH = 500
HANDLE_REMARK_FORBIDDEN_RE = re.compile(r"[\x00-\x1f\x7f<>`{}]")
AUTO_CLOSED_REMARK = "后续自动数据刷新中检测到漏合风险已完成补合"
DEFAULT_SCHEDULE_WINDOW_DAYS = 1
UNKNOWN_PL_GROUP_ID = "unknown"
UNKNOWN_PL_GROUP_NAME = "非底软领域"


@dataclass
class ScanPair:
    repository: ComplianceRepository
    trunk_branch: str
    release_branch: str


@dataclass
class ScanCounters:
    scanned_organization_count: int = 0
    scanned_repository_count: int = 0
    scanned_branch_pair_count: int = 0
    detected_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    fixed_count: int = 0


@dataclass(frozen=True)
class AuthorPlAssignment:
    user_id: str | None
    user_name: str
    pl_group_id: str | None
    pl_group_name: str


def _clean_text(value: Any) -> str:
    """把页面查询和数据湖字段统一转换成去空格字符串。"""
    if value is None:
        return ""
    return str(value).strip()


def _normalize_id_list(values: Any) -> list[str]:
    """把前端多选 ID 或旧逗号字符串统一成去重后的 ID 列表。"""
    if not values:
        return []
    if isinstance(values, str):
        candidates = values.split(",")
    elif isinstance(values, RuntimeIterable):
        candidates = values
    else:
        candidates = [values]

    result: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        value = _clean_text(item)
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _default_author_pl_assignment() -> AuthorPlAssignment:
    """返回未匹配用户或未命中启用 PL 组时的统一归属。"""
    return AuthorPlAssignment(
        user_id=None,
        user_name="",
        pl_group_id=None,
        pl_group_name=UNKNOWN_PL_GROUP_NAME,
    )


def _load_author_pl_assignments(usernames: Iterable[str]) -> dict[str, AuthorPlAssignment]:
    """按 CR 创建人 username 批量解析 Focus 用户和启用 PL 组归属。"""
    unique_usernames = _normalize_id_list([_clean_text(item) for item in usernames])
    if not unique_usernames:
        return {}

    users = {
        _clean_text(row["username"]): row
        for row in User.objects.filter(username__in=unique_usernames).values("id", "username", "name")
    }
    group_rows = (
        PlGroup.objects.filter(status=True, members__username__in=unique_usernames)
        .values("id", "name", "sort", "members__username")
        .order_by("-sort", "name", "id")
    )
    group_by_username: dict[str, dict[str, Any]] = {}
    for row in group_rows:
        username = _clean_text(row.get("members__username"))
        if username and username not in group_by_username:
            group_by_username[username] = row

    result: dict[str, AuthorPlAssignment] = {}
    for username in unique_usernames:
        user_row = users.get(username)
        group_row = group_by_username.get(username)
        if not user_row:
            result[username] = _default_author_pl_assignment()
            continue
        result[username] = AuthorPlAssignment(
            user_id=str(user_row["id"]),
            user_name=_clean_text(user_row.get("name")) or _clean_text(user_row.get("username")),
            pl_group_id=str(group_row["id"]) if group_row else None,
            pl_group_name=_clean_text(group_row.get("name")) if group_row else UNKNOWN_PL_GROUP_NAME,
        )
    return result


def _resolve_author_pl_assignment(
    username: str,
    assignments: dict[str, AuthorPlAssignment] | None = None,
) -> AuthorPlAssignment:
    """从批量映射中读取作者归属，缺失时兜底为非底软领域。"""
    clean_username = _clean_text(username)
    if not clean_username:
        return _default_author_pl_assignment()
    if assignments is None:
        assignments = _load_author_pl_assignments([clean_username])
    return assignments.get(clean_username, _default_author_pl_assignment())


def _expand_organization_ids_with_descendants(organization_ids: list[str]) -> list[str]:
    """展开组织筛选范围：选中父组织时包含其全部下级组织。"""
    selected_ids = _normalize_id_list(organization_ids)
    if not selected_ids:
        return []

    rows = ComplianceOrganization.objects.filter(is_deleted=False).values_list("id", "parent_id")
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    active_ids: set[str] = set()
    for org_id, parent_id in rows:
        org_id_text = str(org_id)
        active_ids.add(org_id_text)
        if parent_id:
            children_by_parent[str(parent_id)].append(org_id_text)

    expanded: list[str] = []
    visited: set[str] = set()
    stack = [org_id for org_id in selected_ids if org_id in active_ids]
    while stack:
        org_id = stack.pop()
        if org_id in visited:
            continue
        visited.add(org_id)
        expanded.append(org_id)
        stack.extend(children_by_parent.get(org_id, []))
    return expanded


def _audit_user_id(user) -> str | None:
    """从 request.auth 中提取审计用户 ID。"""
    return str(getattr(user, "id", "") or "") or None


def _apply_audit_fields(instance, user, *, is_create: bool = False) -> None:
    """在服务层补齐 RootModel 的创建人和修改人。"""
    user_id = _audit_user_id(user)
    if not user_id:
        return
    if is_create and hasattr(instance, "sys_creator_id"):
        instance.sys_creator_id = user_id
    if hasattr(instance, "sys_modifier_id"):
        instance.sys_modifier_id = user_id


def _to_model_datetime(value: Any):
    """根据 USE_TZ 配置把时间转换成 Django/MySQL 可保存的形态。"""
    if value is None:
        return None
    if settings.USE_TZ:
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value
    if timezone.is_aware(value):
        return timezone.localtime(value, timezone.get_current_timezone()).replace(tzinfo=None)
    return value


def _normalize_status(status: str) -> str:
    """校验漏合风险处理状态。"""
    value = _clean_text(status).lower()
    if value not in SUPPORTED_RECORD_STATUSES:
        raise HttpError(400, "处理状态仅支持 open/fixed/ignored")
    return value


def validate_handle_remark(value: Any) -> str:
    """校验人工处理备注，防止无说明或高风险字符进入处理台账。"""
    remark = _clean_text(value)
    if len(remark) < HANDLE_REMARK_MIN_LENGTH:
        raise HttpError(400, "处理备注不能为空，且不少于 5 个字符")
    if len(remark) > HANDLE_REMARK_MAX_LENGTH:
        raise HttpError(400, "处理备注不能超过 500 个字符")
    if HANDLE_REMARK_FORBIDDEN_RE.search(remark):
        raise HttpError(400, "处理备注不能包含控制字符或 < > ` { } 等特殊字符")
    return remark


def _status_label(status: str) -> str:
    """把状态编码转换为页面可读文案。"""
    if not status:
        return ""
    return STATUS_LABELS.get(status, status)


def _operator_name(user, source: str) -> str:
    """按操作来源生成操作人快照。"""
    if source == MISSING_MERGE_OPERATION_SOURCE_SYSTEM:
        return "系统"
    if not user:
        return "人工处理"
    return getattr(user, "name", None) or getattr(user, "username", None) or "人工处理"


def _create_operation_log(
    *,
    record: ComplianceMissingMergeRecord,
    operation_type: str,
    source: str,
    from_status: str,
    to_status: str,
    remark: str,
    user=None,
    scan_task: ComplianceMissingMergeScanTask | None = None,
    operated_at=None,
) -> ComplianceMissingMergeOperationLog:
    """统一写入漏合风险操作历史，保证系统和人工操作轨迹一致。"""
    operated_time = _to_model_datetime(operated_at or timezone.now())
    item = ComplianceMissingMergeOperationLog(
        record=record,
        scan_task=scan_task,
        operation_type=operation_type,
        source=source,
        from_status=from_status or "",
        to_status=to_status or "",
        operator=user if source == MISSING_MERGE_OPERATION_SOURCE_MANUAL and getattr(user, "id", None) else None,
        operator_name=_operator_name(user, source),
        remark=_clean_text(remark),
        operated_at=operated_time,
    )
    _apply_audit_fields(item, user, is_create=True)
    item.save()
    return item


def serialize_operation_log(item: ComplianceMissingMergeOperationLog) -> dict:
    """把操作历史序列化为详情抽屉的时间轴数据。"""
    return {
        "id": str(item.id),
        "operation_type": item.operation_type,
        "operation_type_label": OPERATION_LABELS.get(item.operation_type, item.operation_type),
        "source": item.source,
        "source_label": OPERATION_SOURCE_LABELS.get(item.source, item.source),
        "from_status": item.from_status or "",
        "from_status_label": _status_label(item.from_status),
        "to_status": item.to_status or "",
        "to_status_label": _status_label(item.to_status),
        "operator_id": str(item.operator_id) if item.operator_id else None,
        "operator_name": item.operator_name or _operator_name(getattr(item, "operator", None), item.source),
        "remark": item.remark or "",
        "operated_at": item.operated_at,
    }


def serialize_missing_merge_record(item: ComplianceMissingMergeRecord, *, include_logs: bool = False) -> dict:
    """把漏合风险模型序列化为前端列表/详情数据。"""
    handled_by = getattr(item, "handled_by", None)
    if include_logs:
        logs = getattr(item, "active_operation_logs", None)
        if logs is None:
            logs = item.operation_logs.filter(is_deleted=False).select_related("operator").order_by(
                "-operated_at",
                "-sys_create_datetime",
            )
        operation_logs = [serialize_operation_log(log) for log in logs]
    else:
        operation_logs = []
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id) if item.organization_id else None,
        "organization_group_id": item.organization_group_id,
        "organization_name": item.organization_name,
        "repository_id": str(item.repository_id) if item.repository_id else None,
        "repository_project_id": item.repository_project_id,
        "repository_name": item.repository_name,
        "project_id": item.project_id,
        "trunk_branch": item.trunk_branch,
        "release_branch": item.release_branch,
        "change_request_iid": item.change_request_iid,
        "change_key": item.change_key,
        "title": item.title,
        "description": item.description,
        "web_url": item.web_url,
        "added_lines": item.added_lines,
        "removed_lines": item.removed_lines,
        "merged_at": item.merged_at,
        "target_branch": item.target_branch,
        "author_username": item.author_username,
        "author_user_id": str(item.author_user_id) if item.author_user_id else None,
        "author_user_name": item.author_user_name or "",
        "author_pl_group_id": str(item.author_pl_group_id) if item.author_pl_group_id else None,
        "author_pl_group_name": item.author_pl_group_name or UNKNOWN_PL_GROUP_NAME,
        "detected_at": item.detected_at,
        "status": item.status,
        "status_label": STATUS_LABELS.get(item.status, item.status),
        "handled_by_id": str(item.handled_by_id) if item.handled_by_id else None,
        "handled_by_name": (
            getattr(handled_by, "name", None) or getattr(handled_by, "username", None)
            if handled_by
            else None
        ),
        "handled_at": item.handled_at,
        "handle_remark": item.handle_remark or "",
        "operation_logs": operation_logs,
        "sys_create_datetime": item.sys_create_datetime,
        "sys_update_datetime": item.sys_update_datetime,
    }


def serialize_scan_task(item: ComplianceMissingMergeScanTask) -> dict:
    """把同步任务序列化为前端任务历史数据。"""
    return {
        "id": str(item.id),
        "trigger_type": item.trigger_type,
        "trigger_type_label": SCAN_TRIGGER_LABELS.get(item.trigger_type, item.trigger_type),
        "status": item.status,
        "status_label": SCAN_STATUS_LABELS.get(item.status, item.status),
        "merged_after": item.merged_after,
        "merged_before": item.merged_before,
        "filter_payload": item.filter_payload or {},
        "started_at": item.started_at,
        "finished_at": item.finished_at,
        "scanned_organization_count": item.scanned_organization_count,
        "scanned_repository_count": item.scanned_repository_count,
        "scanned_branch_pair_count": item.scanned_branch_pair_count,
        "detected_count": item.detected_count,
        "created_count": item.created_count,
        "updated_count": item.updated_count,
        "fixed_count": item.fixed_count,
        "error_message": item.error_message or "",
        "sys_create_datetime": item.sys_create_datetime,
        "sys_update_datetime": item.sys_update_datetime,
    }


def list_missing_merge_records(
    *,
    page: int = 1,
    page_size: int = 20,
    organization_id: str | None = None,
    repository_id: str | None = None,
    organization_ids: Any = None,
    repository_ids: Any = None,
    pl_group_ids: Any = None,
    status: str | None = None,
    author_username: str | None = None,
    keyword: str | None = None,
    trunk_branch: str | None = None,
    release_branch: str | None = None,
    merged_after: Any = None,
    merged_before: Any = None,
    detected_after: Any = None,
    detected_before: Any = None,
) -> dict:
    """分页查询漏合风险列表，支持页面筛选条件。"""
    qs = _build_missing_merge_record_queryset(
        organization_id=organization_id,
        repository_id=repository_id,
        organization_ids=organization_ids,
        repository_ids=repository_ids,
        pl_group_ids=pl_group_ids,
        status=status,
        author_username=author_username,
        keyword=keyword,
        trunk_branch=trunk_branch,
        release_branch=release_branch,
        merged_after=merged_after,
        merged_before=merged_before,
        detected_after=detected_after,
        detected_before=detected_before,
    ).select_related(
        "organization",
        "repository",
        "handled_by",
        "author_user",
        "author_pl_group",
    )
    total = qs.count()
    offset = max(page - 1, 0) * page_size
    items = list(qs.order_by("-detected_at", "-merged_at")[offset : offset + page_size])
    return {"items": [serialize_missing_merge_record(item) for item in items], "total": total}


def _build_missing_merge_record_queryset(
    *,
    organization_id: str | None = None,
    repository_id: str | None = None,
    organization_ids: Any = None,
    repository_ids: Any = None,
    pl_group_ids: Any = None,
    status: str | None = None,
    author_username: str | None = None,
    keyword: str | None = None,
    trunk_branch: str | None = None,
    release_branch: str | None = None,
    merged_after: Any = None,
    merged_before: Any = None,
    detected_after: Any = None,
    detected_before: Any = None,
):
    """构建漏合风险查询集，供列表和 PL 看板复用同一套筛选口径。"""
    qs = ComplianceMissingMergeRecord.objects.filter(is_deleted=False)
    selected_organization_ids = _normalize_id_list(organization_ids)
    selected_repository_ids = _normalize_id_list(repository_ids)
    selected_pl_group_ids = _normalize_id_list(pl_group_ids)
    if selected_organization_ids or selected_repository_ids:
        # 新级联筛选按并集处理：命中任一组织子树或任一精确代码库即可返回。
        scope_filter = None
        expanded_org_ids = _expand_organization_ids_with_descendants(selected_organization_ids)
        if expanded_org_ids:
            scope_filter = Q(organization_id__in=expanded_org_ids)
        if selected_repository_ids:
            repo_filter = Q(repository_id__in=selected_repository_ids)
            scope_filter = repo_filter if scope_filter is None else scope_filter | repo_filter
        if scope_filter is not None:
            qs = qs.filter(scope_filter)
        else:
            qs = qs.none()
    elif organization_id:
        qs = qs.filter(organization_id=organization_id)
    if not (selected_organization_ids or selected_repository_ids) and repository_id:
        qs = qs.filter(repository_id=repository_id)
    if selected_pl_group_ids:
        real_pl_group_ids = [item for item in selected_pl_group_ids if item != UNKNOWN_PL_GROUP_ID]
        pl_filter = Q(author_pl_group_id__in=real_pl_group_ids) if real_pl_group_ids else None
        if UNKNOWN_PL_GROUP_ID in selected_pl_group_ids:
            unknown_filter = Q(author_pl_group_id__isnull=True) | Q(author_pl_group_name=UNKNOWN_PL_GROUP_NAME)
            pl_filter = unknown_filter if pl_filter is None else pl_filter | unknown_filter
        qs = qs.filter(pl_filter) if pl_filter is not None else qs.none()
    if status:
        qs = qs.filter(status=_normalize_status(status))
    if author_username:
        # 参数名保持 author_username 兼容旧前端，实际语义扩展为姓名/工号均可搜索。
        word = _clean_text(author_username)
        qs = qs.filter(Q(author_username__icontains=word) | Q(author_user_name__icontains=word))
    if trunk_branch:
        qs = qs.filter(trunk_branch__icontains=_clean_text(trunk_branch))
    if release_branch:
        qs = qs.filter(release_branch__icontains=_clean_text(release_branch))
    if keyword:
        word = _clean_text(keyword)
        qs = qs.filter(
            Q(change_key__icontains=word)
            | Q(change_request_iid__icontains=word)
            | Q(title__icontains=word)
            | Q(repository_name__icontains=word)
        )
    if merged_after:
        qs = qs.filter(merged_at__gte=_to_model_datetime(merged_after))
    if merged_before:
        qs = qs.filter(merged_at__lte=_to_model_datetime(merged_before))
    if detected_after:
        qs = qs.filter(detected_at__gte=_to_model_datetime(detected_after))
    if detected_before:
        qs = qs.filter(detected_at__lte=_to_model_datetime(detected_before))
    return qs


def get_missing_merge_record(record_id: str) -> dict:
    """读取单条漏合风险详情。"""
    item = get_object_or_404(
        ComplianceMissingMergeRecord.objects.select_related(
            "organization",
            "repository",
            "handled_by",
            "author_user",
            "author_pl_group",
        ).prefetch_related(
            Prefetch(
                "operation_logs",
                queryset=ComplianceMissingMergeOperationLog.objects.filter(is_deleted=False)
                .select_related("operator")
                .order_by("-operated_at", "-sys_create_datetime"),
                to_attr="active_operation_logs",
            )
        ),
        id=record_id,
        is_deleted=False,
    )
    return serialize_missing_merge_record(item, include_logs=True)


def update_missing_merge_status(user, record_id: str, payload) -> dict:
    """人工更新漏合风险处理状态和处理备注。"""
    data = payload.dict()
    next_status = _normalize_status(data.get("status"))
    remark = validate_handle_remark(data.get("handle_remark"))
    with transaction.atomic():
        item = get_object_or_404(ComplianceMissingMergeRecord, id=record_id, is_deleted=False)
        previous_status = item.status
        handled_at = _to_model_datetime(timezone.now())
        item.status = next_status
        item.handle_remark = remark
        item.handled_by = user if getattr(user, "id", None) else None
        item.handled_at = handled_at
        _apply_audit_fields(item, user)
        item.save()
        _create_operation_log(
            record=item,
            operation_type=MISSING_MERGE_OPERATION_MANUAL_HANDLE,
            source=MISSING_MERGE_OPERATION_SOURCE_MANUAL,
            from_status=previous_status,
            to_status=next_status,
            remark=remark,
            user=user,
            operated_at=handled_at,
        )
    return get_missing_merge_record(str(item.id))


def list_scan_tasks(
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    trigger_type: str | None = None,
    merged_after: Any = None,
    merged_before: Any = None,
    started_after: Any = None,
    started_before: Any = None,
) -> dict:
    """分页查询漏合检测任务历史。"""
    qs = ComplianceMissingMergeScanTask.objects.filter(is_deleted=False)
    if status:
        qs = qs.filter(status=_clean_text(status))
    if trigger_type:
        qs = qs.filter(trigger_type=_clean_text(trigger_type))
    if merged_after:
        qs = qs.filter(merged_after__gte=_to_model_datetime(merged_after))
    if merged_before:
        qs = qs.filter(merged_before__lte=_to_model_datetime(merged_before))
    if started_after:
        qs = qs.filter(started_at__gte=_to_model_datetime(started_after))
    if started_before:
        qs = qs.filter(started_at__lte=_to_model_datetime(started_before))
    total = qs.count()
    offset = max(page - 1, 0) * page_size
    items = list(qs.order_by("-sys_create_datetime")[offset : offset + page_size])
    return {"items": [serialize_scan_task(item) for item in items], "total": total}


def get_scan_task(task_id: str) -> dict:
    """读取单条漏合检测任务详情。"""
    item = get_object_or_404(ComplianceMissingMergeScanTask, id=task_id, is_deleted=False)
    return serialize_scan_task(item)


def list_filter_options() -> dict:
    """返回漏合风险页筛选和手动同步弹窗所需的组织、代码库选项。"""
    repositories = base_services.list_repositories(page=1, page_size=10000)
    return {
        "organizations": base_services.list_organization_tree(),
        "repositories": repositories["items"],
        "pl_groups": list_pl_group_options(),
    }


def list_pl_group_options() -> list[dict[str, str | None]]:
    """返回漏合风险筛选项使用的启用 PL 组，并追加非底软领域。"""
    rows = [
        {
            "id": str(item.id),
            "name": item.name,
            "code": item.code or "",
        }
        for item in PlGroup.objects.filter(status=True).order_by("-sort", "name", "id")
    ]
    rows.append({"id": UNKNOWN_PL_GROUP_ID, "name": UNKNOWN_PL_GROUP_NAME, "code": ""})
    return rows


def list_repository_options(
    *,
    page: int = 1,
    page_size: int = 20,
    organization_id: str | None = None,
    keyword: str | None = None,
) -> dict:
    """分页返回漏合风险手动同步弹窗可选代码库，避免一次性加载全量仓库。"""
    return base_services.list_repositories(
        page=page,
        page_size=page_size,
        organization_id=organization_id,
        keyword=keyword,
    )


def _month_start(value) -> Any:
    """把时间归到当月第一天，用于 PL 看板默认月份窗口。"""
    local_value = timezone.localtime(value, timezone.get_current_timezone()) if timezone.is_aware(value) else value
    return local_value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(value, months: int):
    """不引入额外依赖的月份加减工具。"""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return value.replace(year=year, month=month)


def _month_key(value) -> str:
    """按主干合入时间生成 YYYY-MM 月份键。"""
    local_value = timezone.localtime(value, timezone.get_current_timezone()) if timezone.is_aware(value) else value
    return local_value.strftime("%Y-%m")


def _dashboard_time_range(merged_after: Any = None, merged_before: Any = None):
    """看板默认展示最近 12 个自然月；显式时间范围优先。"""
    if merged_after or merged_before:
        start = _to_model_datetime(merged_after) if merged_after else None
        end = _to_model_datetime(merged_before) if merged_before else None
        if start is None and end is not None:
            start = _to_model_datetime(_add_months(_month_start(end), -11))
        if end is None:
            end = _to_model_datetime(timezone.now())
    else:
        end = _to_model_datetime(timezone.now())
        start = _to_model_datetime(_add_months(_month_start(end), -11))
    return start, end


def _build_month_labels(start, end) -> list[str]:
    """生成看板横轴月份，避免前端自己推导时间窗口。"""
    if not start or not end:
        return []
    labels: list[str] = []
    current = _month_start(start)
    end_month = _month_start(end)
    while current <= end_month:
        labels.append(current.strftime("%Y-%m"))
        current = _add_months(current, 1)
    return labels


def get_pl_dashboard(
    *,
    organization_id: str | None = None,
    repository_id: str | None = None,
    organization_ids: Any = None,
    repository_ids: Any = None,
    pl_group_ids: Any = None,
    status: str | None = None,
    author_username: str | None = None,
    keyword: str | None = None,
    trunk_branch: str | None = None,
    release_branch: str | None = None,
    merged_after: Any = None,
    merged_before: Any = None,
    detected_after: Any = None,
    detected_before: Any = None,
) -> dict:
    """按 PL 组和主干合入月份聚合漏合风险，用于漏合风险看板。"""
    dashboard_merged_after, dashboard_merged_before = _dashboard_time_range(merged_after, merged_before)
    qs = _build_missing_merge_record_queryset(
        organization_id=organization_id,
        repository_id=repository_id,
        organization_ids=organization_ids,
        repository_ids=repository_ids,
        pl_group_ids=pl_group_ids,
        status=status,
        author_username=author_username,
        keyword=keyword,
        trunk_branch=trunk_branch,
        release_branch=release_branch,
        detected_after=detected_after,
        detected_before=detected_before,
    )
    # 看板汇总保留 merged_at 为空的记录；趋势图只统计落在月份窗口内的记录。
    if dashboard_merged_after:
        qs = qs.filter(Q(merged_at__gte=dashboard_merged_after) | Q(merged_at__isnull=True))
    if dashboard_merged_before:
        qs = qs.filter(Q(merged_at__lte=dashboard_merged_before) | Q(merged_at__isnull=True))

    rows = list(
        qs.values(
            "id",
            "status",
            "merged_at",
            "detected_at",
            "author_pl_group_id",
            "author_pl_group_name",
        )
    )
    months = _build_month_labels(dashboard_merged_after, dashboard_merged_before)
    month_set = set(months)
    status_counter: Counter[str] = Counter()
    trend_counter: dict[str, Counter[str]] = defaultdict(Counter)
    pl_group_counter: dict[str, Counter[str]] = defaultdict(Counter)
    latest_detected_at: dict[str, Any] = {}
    pl_group_names: dict[str, str] = {}
    missing_merged_at_count = 0

    for row in rows:
        status_value = _clean_text(row.get("status"))
        group_id = str(row.get("author_pl_group_id") or UNKNOWN_PL_GROUP_ID)
        group_name = _clean_text(row.get("author_pl_group_name")) or UNKNOWN_PL_GROUP_NAME
        pl_group_names[group_id] = group_name
        status_counter[status_value] += 1
        pl_group_counter[group_id]["total"] += 1
        pl_group_counter[group_id][status_value] += 1

        detected_at = row.get("detected_at")
        if detected_at and (group_id not in latest_detected_at or detected_at > latest_detected_at[group_id]):
            latest_detected_at[group_id] = detected_at

        merged_at = row.get("merged_at")
        if not merged_at:
            missing_merged_at_count += 1
            continue
        month = _month_key(merged_at)
        if month in month_set:
            trend_counter[group_id][month] += 1

    pl_groups = []
    for group_id, counter in pl_group_counter.items():
        pl_groups.append(
            {
                "pl_group_id": None if group_id == UNKNOWN_PL_GROUP_ID else group_id,
                "pl_group_name": pl_group_names.get(group_id) or UNKNOWN_PL_GROUP_NAME,
                "total_count": int(counter["total"]),
                "open_count": int(counter[MISSING_MERGE_STATUS_OPEN]),
                "fixed_count": int(counter[MISSING_MERGE_STATUS_FIXED]),
                "ignored_count": int(counter[MISSING_MERGE_STATUS_IGNORED]),
                "latest_detected_at": latest_detected_at.get(group_id),
            }
        )
    pl_groups.sort(key=lambda item: (-item["total_count"], item["pl_group_name"]))

    trend_series = [
        {
            "pl_group_id": None if group_id == UNKNOWN_PL_GROUP_ID else group_id,
            "pl_group_name": pl_group_names.get(group_id) or UNKNOWN_PL_GROUP_NAME,
            "data": [int(counter.get(month, 0)) for month in months],
        }
        for group_id, counter in sorted(
            trend_counter.items(),
            key=lambda item: (-sum(item[1].values()), pl_group_names.get(item[0]) or UNKNOWN_PL_GROUP_NAME),
        )
    ]

    return {
        "summary": {
            "total_count": len(rows),
            "open_count": int(status_counter[MISSING_MERGE_STATUS_OPEN]),
            "fixed_count": int(status_counter[MISSING_MERGE_STATUS_FIXED]),
            "ignored_count": int(status_counter[MISSING_MERGE_STATUS_IGNORED]),
            "pl_group_count": len(pl_group_counter),
            "missing_merged_at_count": missing_merged_at_count,
            "merged_after": dashboard_merged_after,
            "merged_before": dashboard_merged_before,
        },
        "months": months,
        "trend_series": trend_series,
        "status_distribution": [
            {
                "status": value,
                "status_label": STATUS_LABELS.get(value, value),
                "count": int(status_counter[value]),
            }
            for value in [MISSING_MERGE_STATUS_OPEN, MISSING_MERGE_STATUS_FIXED, MISSING_MERGE_STATUS_IGNORED]
        ],
        "pl_groups": pl_groups,
    }


def _normalize_scan_payload(payload) -> dict:
    """校验并标准化扫描入参，供手动和定时任务共同使用。"""
    data = payload.dict()
    merged_after = _to_model_datetime(data["merged_after"])
    merged_before = _to_model_datetime(data["merged_before"])
    repository_ids = _normalize_id_list(data.get("repository_ids"))
    if not repository_ids and data.get("repository_id"):
        repository_ids = _normalize_id_list([data.get("repository_id")])
    if merged_after > merged_before:
        raise HttpError(400, "merged_after 不能晚于 merged_before")
    return {
        "merged_after": merged_after,
        "merged_before": merged_before,
        "organization_id": data.get("organization_id") or "",
        "repository_ids": repository_ids,
    }


def _get_active_scan_task() -> ComplianceMissingMergeScanTask | None:
    """返回当前未完成的漏合扫描任务，手动提交时用于并发保护。"""
    return (
        ComplianceMissingMergeScanTask.objects.filter(
            is_deleted=False,
            status__in=[MISSING_MERGE_SCAN_STATUS_PENDING, MISSING_MERGE_SCAN_STATUS_RUNNING],
        )
        .order_by("-sys_create_datetime")
        .first()
    )


def create_scan_task(user, payload, *, trigger_type: str = MISSING_MERGE_SCAN_TRIGGER_MANUAL) -> ComplianceMissingMergeScanTask:
    """创建一条待执行扫描任务，不在接口线程里执行耗时扫描。"""
    normalized = _normalize_scan_payload(payload)
    task = ComplianceMissingMergeScanTask.objects.create(
        trigger_type=trigger_type,
        status=MISSING_MERGE_SCAN_STATUS_PENDING,
        merged_after=normalized["merged_after"],
        merged_before=normalized["merged_before"],
        filter_payload={
            "organization_id": normalized["organization_id"],
            "repository_ids": normalized["repository_ids"],
        },
    )
    _apply_audit_fields(task, user, is_create=True)
    task.save()
    return task


def execute_scan_task(task_id: str, user_id: str | None = None) -> dict:
    """执行已创建的扫描任务，并把成功或失败状态完整回写到任务表。"""
    user = User.objects.filter(id=user_id).first() if user_id else None
    task = get_object_or_404(ComplianceMissingMergeScanTask, id=task_id, is_deleted=False)
    task.status = MISSING_MERGE_SCAN_STATUS_RUNNING
    task.started_at = _to_model_datetime(timezone.now())
    task.error_message = ""
    task.save()
    payload = task.filter_payload or {}
    try:
        counters = _execute_scan(
            user=user,
            task=task,
            merged_after=task.merged_after,
            merged_before=task.merged_before,
            organization_id=payload.get("organization_id") or None,
            repository_ids=_normalize_id_list(payload.get("repository_ids")),
        )
        _finish_task(task, counters, MISSING_MERGE_SCAN_STATUS_SUCCESS)
    except Exception as exc:  # noqa: BLE001 - 任务失败需要落库给前端展示完整原因。
        logger.exception("CodeCompliance missing merge scan failed")
        task.status = MISSING_MERGE_SCAN_STATUS_FAILED
        task.finished_at = _to_model_datetime(timezone.now())
        task.error_message = str(exc)
        task.save()
    return serialize_scan_task(task)


def _start_scan_task_thread(task_id: str, user_id: str | None) -> None:
    """启动进程内后台线程执行手动同步，避免 API 请求等待完整扫描。"""
    def _worker():
        close_old_connections()
        try:
            execute_scan_task(task_id, user_id)
        finally:
            close_old_connections()

    threading.Thread(
        target=_worker,
        name=f"code-compliance-missing-merge-{task_id}",
        daemon=True,
    ).start()


def run_missing_merge_scan(user, payload, *, trigger_type: str = MISSING_MERGE_SCAN_TRIGGER_MANUAL) -> dict:
    """提交一次手动漏合检测任务，后台异步执行并立即返回任务记录。"""
    if trigger_type == MISSING_MERGE_SCAN_TRIGGER_MANUAL:
        active_task = _get_active_scan_task()
        if active_task:
            return {
                "accepted": False,
                "message": "已有漏合同步任务正在执行，请稍后再试",
                "task": serialize_scan_task(active_task),
            }
    task = create_scan_task(user, payload, trigger_type=trigger_type)
    _start_scan_task_thread(str(task.id), _audit_user_id(user))
    return {
        "accepted": True,
        "message": "漏合同步任务已提交，后台正在执行",
        "task": serialize_scan_task(task),
    }


def _finish_task(
    task: ComplianceMissingMergeScanTask,
    counters: ScanCounters,
    status: str,
) -> None:
    """把扫描计数回写到任务记录。"""
    task.status = status
    task.finished_at = _to_model_datetime(timezone.now())
    task.scanned_organization_count = counters.scanned_organization_count
    task.scanned_repository_count = counters.scanned_repository_count
    task.scanned_branch_pair_count = counters.scanned_branch_pair_count
    task.detected_count = counters.detected_count
    task.created_count = counters.created_count
    task.updated_count = counters.updated_count
    task.fixed_count = counters.fixed_count
    task.error_message = ""
    task.save()


def _execute_scan(
    *,
    user,
    task: ComplianceMissingMergeScanTask | None = None,
    merged_after,
    merged_before,
    organization_id: str | None = None,
    repository_ids: list[str] | None = None,
) -> ScanCounters:
    """执行完整检测流程：加载配置、拉取数据、差异比对并更新风险表。"""
    pairs = _load_scan_pairs(organization_id=organization_id, repository_ids=repository_ids)
    counters = ScanCounters(
        scanned_organization_count=len({str(pair.repository.organization_id) for pair in pairs}),
        scanned_repository_count=len({str(repository.id) for repository in _iter_pair_repositories(pairs)}),
        scanned_branch_pair_count=len(pairs),
    )
    if not pairs:
        return counters

    client = CodeComplianceCRClient()
    per_page = DEFAULT_PAGE_SIZE

    for group_id, org_pairs in _group_pairs_by_organization(pairs).items():
        project_ids = sorted({pair.repository.project_id for pair in org_pairs if pair.repository.project_id})
        branch_names = sorted(
            {
                branch_name
                for pair in org_pairs
                for branch_name in (pair.trunk_branch, pair.release_branch)
                if branch_name
            }
        )
        branch_project_rows = _fetch_branch_rows(
            client=client,
            group_id=group_id,
            branch_names=branch_names,
            project_ids=project_ids,
            merged_after=merged_after,
            merged_before=merged_before,
            per_page=per_page,
        )
        author_assignments = _load_author_pl_assignments(
            _clean_text(row.get("author_username"))
            for branch_rows in branch_project_rows.values()
            for project_rows in branch_rows.values()
            for row in project_rows.values()
        )
        # 同一组织的一批项目共用数据湖请求结果，再按 project_id 分流到具体代码库。
        for pair in org_pairs:
            trunk_rows = branch_project_rows[pair.trunk_branch].get(pair.repository.project_id, {})
            release_rows = branch_project_rows[pair.release_branch].get(pair.repository.project_id, {})
            trunk_keys = set(trunk_rows)
            release_keys = set(release_rows)
            missing_keys = trunk_keys - release_keys

            counters.detected_count += len(missing_keys)
            for change_key in sorted(missing_keys):
                created = _upsert_missing_record(
                    user=user,
                    task=task,
                    pair=pair,
                    row=trunk_rows[change_key],
                    author_assignments=author_assignments,
                )
                if created:
                    counters.created_count += 1
                else:
                    counters.updated_count += 1
            counters.fixed_count += _mark_fixed_records(
                user=user,
                task=task,
                pair=pair,
                release_keys=release_keys,
            )
    return counters


def _iter_pair_repositories(pairs: Iterable[ScanPair]) -> Iterable[ComplianceRepository]:
    """返回扫描配对中的代码库对象，供统计去重。"""
    for pair in pairs:
        yield pair.repository


def _load_scan_pairs(
    *,
    organization_id: str | None = None,
    repository_ids: list[str] | None = None,
) -> list[ScanPair]:
    """按现有绑定关系自动组合每个代码库下的主干-发布分支对。"""
    branch_link_qs = ComplianceRepositoryBranch.objects.filter(
        is_deleted=False,
        branch__is_deleted=False,
    ).select_related("branch")
    qs = (
        ComplianceRepository.objects.filter(is_deleted=False, organization__is_deleted=False)
        .select_related("organization")
        .prefetch_related(Prefetch("branch_links", queryset=branch_link_qs, to_attr="active_branch_links"))
    )
    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    if repository_ids:
        qs = qs.filter(id__in=repository_ids)

    pairs: list[ScanPair] = []
    for repository in qs:
        trunks: list[str] = []
        releases: list[str] = []
        for link in getattr(repository, "active_branch_links", []):
            branch = link.branch
            if branch.branch_type == COMPLIANCE_BRANCH_TYPE_TRUNK:
                trunks.append(branch.branch_name)
            elif branch.branch_type == COMPLIANCE_BRANCH_TYPE_RELEASE:
                releases.append(branch.branch_name)
        # 本期不配置显式配对，按代码库内主干和发布分支类型自动组合。
        for trunk_branch in sorted(set(trunks)):
            for release_branch in sorted(set(releases)):
                pairs.append(
                    ScanPair(
                        repository=repository,
                        trunk_branch=trunk_branch,
                        release_branch=release_branch,
                    )
                )
    return pairs


def _group_pairs_by_organization(pairs: list[ScanPair]) -> dict[str, list[ScanPair]]:
    """将扫描配对按公司代码库系统 group_id 分组，用于数据湖路径参数。"""
    grouped: dict[str, list[ScanPair]] = defaultdict(list)
    for pair in pairs:
        grouped[str(pair.repository.organization.group_id)].append(pair)
    return grouped


def _fetch_branch_rows(
    *,
    client: CodeComplianceCRClient,
    group_id: str,
    branch_names: Iterable[str],
    project_ids: list[str],
    merged_after,
    merged_before,
    per_page: int,
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """拉取组织下各目标分支 CR，并按 branch/project/change_key 建索引。"""
    branch_project_rows: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
    for branch_name in branch_names:
        rows = client.fetch_all(
            group_id=group_id,
            target_branch=branch_name,
            projects=project_ids,
            merged_after=merged_after,
            merged_before=merged_before,
            per_page=per_page,
        )
        for row in rows:
            project_id = _clean_text(row.get("project_id"))
            change_key = _clean_text(row.get("change_key"))
            if not project_id or not change_key:
                continue
            branch_project_rows[branch_name][project_id][change_key] = row
    return branch_project_rows


def _upsert_missing_record(
    *,
    user,
    task: ComplianceMissingMergeScanTask | None = None,
    pair: ScanPair,
    row: dict[str, Any],
    author_assignments: dict[str, AuthorPlAssignment] | None = None,
) -> bool:
    """新增或更新单条漏合风险，已忽略记录只刷新 CR 信息不改处理状态。"""
    now = _to_model_datetime(timezone.now())
    repository = pair.repository
    organization = repository.organization
    lookup = {
        "repository": repository,
        "trunk_branch": pair.trunk_branch,
        "release_branch": pair.release_branch,
        "change_key": row["change_key"],
    }
    author_username = _clean_text(row.get("author_username"))
    author_assignment = _resolve_author_pl_assignment(author_username, author_assignments)
    defaults = {
        "organization": organization,
        "organization_group_id": organization.group_id,
        "organization_name": organization.name,
        "repository_project_id": repository.project_id,
        "repository_name": repository.project_name,
        "project_id": repository.project_id,
        "change_request_iid": _clean_text(row.get("change_request_iid")),
        "title": _clean_text(row.get("title")),
        "description": _clean_text(row.get("description")),
        "web_url": _clean_text(row.get("web_url")),
        "added_lines": int(row.get("added_lines") or 0),
        "removed_lines": int(row.get("removed_lines") or 0),
        "merged_at": _to_model_datetime(row.get("merged_at")),
        "target_branch": _clean_text(row.get("target_branch")) or pair.trunk_branch,
        "author_username": author_username,
        "author_user_id": author_assignment.user_id,
        "author_user_name": author_assignment.user_name,
        "author_pl_group_id": author_assignment.pl_group_id,
        "author_pl_group_name": author_assignment.pl_group_name,
        "detected_at": now,
        "is_deleted": False,
    }

    item = ComplianceMissingMergeRecord.objects.filter(**lookup).first()
    created = item is None
    previous_status = ""
    if created:
        item = ComplianceMissingMergeRecord(**lookup)
        item.status = MISSING_MERGE_STATUS_OPEN
        _apply_audit_fields(item, user, is_create=True)
    else:
        previous_status = item.status
    for field, value in defaults.items():
        setattr(item, field, value)

    should_reopen = False
    if not created and item.status != MISSING_MERGE_STATUS_IGNORED:
        # 之前已补合的 CR 如果再次缺失，需要重新进入未处理状态。
        should_reopen = item.status != MISSING_MERGE_STATUS_OPEN
        item.status = MISSING_MERGE_STATUS_OPEN
        item.handled_by = None
        item.handled_at = None
        item.handle_remark = ""
    _apply_audit_fields(item, user)
    item.save()
    if created:
        _create_operation_log(
            record=item,
            scan_task=task,
            operation_type=MISSING_MERGE_OPERATION_DETECTED,
            source=MISSING_MERGE_OPERATION_SOURCE_SYSTEM,
            from_status="",
            to_status=MISSING_MERGE_STATUS_OPEN,
            remark="系统首次自动检测到漏合风险",
            user=user,
            operated_at=now,
        )
    elif should_reopen:
        _create_operation_log(
            record=item,
            scan_task=task,
            operation_type=MISSING_MERGE_OPERATION_REOPENED,
            source=MISSING_MERGE_OPERATION_SOURCE_SYSTEM,
            from_status=previous_status,
            to_status=MISSING_MERGE_STATUS_OPEN,
            remark="后续自动数据刷新中再次检测到该漏合风险",
            user=user,
            operated_at=now,
        )
    return created


def _mark_fixed_records(
    *,
    user,
    task: ComplianceMissingMergeScanTask | None = None,
    pair: ScanPair,
    release_keys: set[str],
) -> int:
    """把本轮已出现在发布分支的历史未处理风险自动标记为已补合。"""
    if not release_keys:
        return 0
    now = _to_model_datetime(timezone.now())
    qs = ComplianceMissingMergeRecord.objects.filter(
        is_deleted=False,
        repository=pair.repository,
        trunk_branch=pair.trunk_branch,
        release_branch=pair.release_branch,
        status=MISSING_MERGE_STATUS_OPEN,
        change_key__in=release_keys,
    )
    items = list(qs)
    if not items:
        return 0
    for item in items:
        previous_status = item.status
        item.status = MISSING_MERGE_STATUS_FIXED
        item.handled_by = None
        item.handled_at = now
        item.handle_remark = AUTO_CLOSED_REMARK
        _apply_audit_fields(item, user)
        item.save()
        _create_operation_log(
            record=item,
            scan_task=task,
            operation_type=MISSING_MERGE_OPERATION_AUTO_CLOSED,
            source=MISSING_MERGE_OPERATION_SOURCE_SYSTEM,
            from_status=previous_status,
            to_status=MISSING_MERGE_STATUS_FIXED,
            remark=AUTO_CLOSED_REMARK,
            user=user,
            operated_at=now,
        )
    return len(items)


@scheduler_task
def run_scheduled_missing_merge_scan(**kwargs):
    """定时任务入口，默认扫描最近一天的 CR 合入窗口。"""
    merged_before = _to_model_datetime(timezone.now())
    merged_after = merged_before - timedelta(days=DEFAULT_SCHEDULE_WINDOW_DAYS)

    class _Payload:
        def dict(self):
            return {
                "merged_after": merged_after,
                "merged_before": merged_before,
                "organization_id": None,
                "repository_ids": [],
            }

    task = create_scan_task(
        None,
        _Payload(),
        trigger_type=MISSING_MERGE_SCAN_TRIGGER_SCHEDULED,
    )
    return execute_scan_task(str(task.id))
