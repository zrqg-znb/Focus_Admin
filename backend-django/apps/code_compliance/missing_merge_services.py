from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable

from django.conf import settings
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from scheduler.module.executor import scheduler_task

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
    MISSING_MERGE_STATUS_CHOICES,
    MISSING_MERGE_STATUS_FIXED,
    MISSING_MERGE_STATUS_IGNORED,
    MISSING_MERGE_STATUS_OPEN,
    ComplianceMissingMergeRecord,
    ComplianceMissingMergeScanTask,
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
SUPPORTED_RECORD_STATUSES = {
    MISSING_MERGE_STATUS_OPEN,
    MISSING_MERGE_STATUS_FIXED,
    MISSING_MERGE_STATUS_IGNORED,
}


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


def _clean_text(value: Any) -> str:
    """把页面查询和数据湖字段统一转换成去空格字符串。"""
    if value is None:
        return ""
    return str(value).strip()


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


def serialize_missing_merge_record(item: ComplianceMissingMergeRecord) -> dict:
    """把漏合风险模型序列化为前端列表/详情数据。"""
    handled_by = getattr(item, "handled_by", None)
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
    qs = ComplianceMissingMergeRecord.objects.filter(is_deleted=False).select_related(
        "organization",
        "repository",
        "handled_by",
    )
    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    if repository_id:
        qs = qs.filter(repository_id=repository_id)
    if status:
        qs = qs.filter(status=_normalize_status(status))
    if author_username:
        qs = qs.filter(author_username__icontains=_clean_text(author_username))
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

    total = qs.count()
    offset = max(page - 1, 0) * page_size
    items = list(qs.order_by("-detected_at", "-merged_at")[offset : offset + page_size])
    return {"items": [serialize_missing_merge_record(item) for item in items], "total": total}


def get_missing_merge_record(record_id: str) -> dict:
    """读取单条漏合风险详情。"""
    item = get_object_or_404(
        ComplianceMissingMergeRecord.objects.select_related(
            "organization",
            "repository",
            "handled_by",
        ),
        id=record_id,
        is_deleted=False,
    )
    return serialize_missing_merge_record(item)


def update_missing_merge_status(user, record_id: str, payload) -> dict:
    """人工更新漏合风险处理状态和处理备注。"""
    item = get_object_or_404(ComplianceMissingMergeRecord, id=record_id, is_deleted=False)
    data = payload.dict()
    item.status = _normalize_status(data.get("status"))
    item.handle_remark = _clean_text(data.get("handle_remark"))
    item.handled_by = user if getattr(user, "id", None) else None
    item.handled_at = _to_model_datetime(timezone.now())
    _apply_audit_fields(item, user)
    item.save()
    return get_missing_merge_record(str(item.id))


def list_scan_tasks(
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    trigger_type: str | None = None,
) -> dict:
    """分页查询漏合检测任务历史。"""
    qs = ComplianceMissingMergeScanTask.objects.filter(is_deleted=False)
    if status:
        qs = qs.filter(status=_clean_text(status))
    if trigger_type:
        qs = qs.filter(trigger_type=_clean_text(trigger_type))
    total = qs.count()
    offset = max(page - 1, 0) * page_size
    items = list(qs.order_by("-sys_create_datetime")[offset : offset + page_size])
    return {"items": [serialize_scan_task(item) for item in items], "total": total}


def list_filter_options() -> dict:
    """返回漏合风险页筛选和手动同步弹窗所需的组织、代码库选项。"""
    repositories = base_services.list_repositories(page=1, page_size=10000)
    return {
        "organizations": base_services.list_organization_tree(),
        "repositories": repositories["items"],
    }


def run_missing_merge_scan(user, payload, *, trigger_type: str = MISSING_MERGE_SCAN_TRIGGER_MANUAL) -> dict:
    """创建并执行一次漏合检测任务，失败时保留任务记录供页面排障。"""
    data = payload.dict()
    merged_after = _to_model_datetime(data["merged_after"])
    merged_before = _to_model_datetime(data["merged_before"])
    if merged_after > merged_before:
        raise HttpError(400, "merged_after 不能晚于 merged_before")

    task = ComplianceMissingMergeScanTask.objects.create(
        trigger_type=trigger_type,
        status=MISSING_MERGE_SCAN_STATUS_RUNNING,
        merged_after=merged_after,
        merged_before=merged_before,
        filter_payload={
            "organization_id": data.get("organization_id") or "",
            "repository_id": data.get("repository_id") or "",
        },
        started_at=_to_model_datetime(timezone.now()),
    )
    _apply_audit_fields(task, user, is_create=True)
    task.save()

    try:
        counters = _execute_scan(
            user=user,
            merged_after=merged_after,
            merged_before=merged_before,
            organization_id=data.get("organization_id"),
            repository_id=data.get("repository_id"),
        )
        _finish_task(task, counters, MISSING_MERGE_SCAN_STATUS_SUCCESS)
    except Exception as exc:  # noqa: BLE001 - 任务失败需要落库给前端展示完整原因。
        logger.exception("CodeCompliance missing merge scan failed")
        task.status = MISSING_MERGE_SCAN_STATUS_FAILED
        task.finished_at = _to_model_datetime(timezone.now())
        task.error_message = str(exc)
        task.save()
    return serialize_scan_task(task)


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
    merged_after,
    merged_before,
    organization_id: str | None = None,
    repository_id: str | None = None,
) -> ScanCounters:
    """执行完整检测流程：加载配置、拉取数据、差异比对并更新风险表。"""
    pairs = _load_scan_pairs(organization_id=organization_id, repository_id=repository_id)
    counters = ScanCounters(
        scanned_organization_count=len({str(pair.repository.organization_id) for pair in pairs}),
        scanned_repository_count=len({str(repository.id) for repository in _iter_pair_repositories(pairs)}),
        scanned_branch_pair_count=len(pairs),
    )
    if not pairs:
        return counters

    client = CodeComplianceCRClient()
    per_page = int(getattr(settings, "CODE_COMPLIANCE_CR_PAGE_SIZE", DEFAULT_PAGE_SIZE) or DEFAULT_PAGE_SIZE)

    for org_id, org_pairs in _group_pairs_by_organization(pairs).items():
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
            branch_names=branch_names,
            project_ids=project_ids,
            merged_after=merged_after,
            merged_before=merged_before,
            per_page=per_page,
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
                    pair=pair,
                    row=trunk_rows[change_key],
                )
                if created:
                    counters.created_count += 1
                else:
                    counters.updated_count += 1
            counters.fixed_count += _mark_fixed_records(
                user=user,
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
    repository_id: str | None = None,
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
    if repository_id:
        qs = qs.filter(id=repository_id)

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
    """将扫描配对按组织分组，以便符合数据湖 projects 参数约定。"""
    grouped: dict[str, list[ScanPair]] = defaultdict(list)
    for pair in pairs:
        grouped[str(pair.repository.organization_id)].append(pair)
    return grouped


def _fetch_branch_rows(
    *,
    client: CodeComplianceCRClient,
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


def _upsert_missing_record(*, user, pair: ScanPair, row: dict[str, Any]) -> bool:
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
        "author_username": _clean_text(row.get("author_username")),
        "detected_at": now,
        "is_deleted": False,
    }

    item = ComplianceMissingMergeRecord.objects.filter(**lookup).first()
    created = item is None
    if created:
        item = ComplianceMissingMergeRecord(**lookup)
        item.status = MISSING_MERGE_STATUS_OPEN
        _apply_audit_fields(item, user, is_create=True)
    for field, value in defaults.items():
        setattr(item, field, value)

    if not created and item.status != MISSING_MERGE_STATUS_IGNORED:
        # 之前已补合的 CR 如果再次缺失，需要重新进入未处理状态。
        item.status = MISSING_MERGE_STATUS_OPEN
        item.handled_by = None
        item.handled_at = None
        item.handle_remark = ""
    _apply_audit_fields(item, user)
    item.save()
    return created


def _mark_fixed_records(*, user, pair: ScanPair, release_keys: set[str]) -> int:
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
    ids = list(qs.values_list("id", flat=True))
    if not ids:
        return 0
    ComplianceMissingMergeRecord.objects.filter(id__in=ids).update(
        status=MISSING_MERGE_STATUS_FIXED,
        handled_by_id=_audit_user_id(user),
        handled_at=now,
        handle_remark="系统检测到发布分支已包含该 CR，自动标记已补合",
        sys_update_datetime=now,
    )
    return len(ids)


@scheduler_task
def run_scheduled_missing_merge_scan(**kwargs):
    """定时任务入口，默认扫描最近一天的 CR 合入窗口。"""
    days = int(getattr(settings, "CODE_COMPLIANCE_CR_SCHEDULE_WINDOW_DAYS", 1) or 1)
    merged_before = _to_model_datetime(timezone.now())
    merged_after = merged_before - timedelta(days=max(days, 1))

    class _Payload:
        def dict(self):
            return {
                "merged_after": merged_after,
                "merged_before": merged_before,
                "organization_id": None,
                "repository_id": None,
            }

    return run_missing_merge_scan(
        None,
        _Payload(),
        trigger_type=MISSING_MERGE_SCAN_TRIGGER_SCHEDULED,
    )
