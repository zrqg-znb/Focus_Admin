import logging
from collections import defaultdict
from datetime import timedelta
from typing import Iterable, Optional

from django.db import transaction
from django.db.models import BooleanField, Case, Count, Q, Value, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.requirement_center.tasks import send_requirement_email_notification_task
from core.message.message_model import UserMessage
from core.message.message_service import create_message_for_user, normalize_priority
from core.user.user_model import User

from .requirement_model import (
    Requirement,
    RequirementAction,
    RequirementComment,
    RequirementLog,
    RequirementStatus,
    RequirementWatcher,
)

logger = logging.getLogger(__name__)

REVIEW_DUE_DEFAULT_DAYS = 2
DEV_DUE_DEFAULT_DAYS = 10
SPLIT_ALLOWED_PARENT_STATUS = {
    RequirementStatus.ACCEPTED,
    RequirementStatus.PLANNED,
    RequirementStatus.IN_DEV,
    RequirementStatus.IN_ACCEPTANCE,
}
PARENT_STATUS_BLOCK_ORDER = [
    RequirementStatus.NEED_INFO,
    RequirementStatus.SUBMITTED,
    RequirementStatus.ACCEPTED,
    RequirementStatus.PLANNED,
    RequirementStatus.IN_DEV,
    RequirementStatus.IN_ACCEPTANCE,
]


def _is_admin(user: Optional[User]) -> bool:
    return bool(user and getattr(user, "is_superuser", False))


def _now():
    return timezone.now()


def _clean_ids(ids: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for item in ids or []:
        text = str(item or "").strip()
        if text:
            cleaned.append(text)
    return list(dict.fromkeys(cleaned))


def _user_display_name(user: Optional[User]) -> str:
    if not user:
        return "系统"
    return user.name or user.username


def _require_admin(user: User):
    if not _is_admin(user):
        raise HttpError(403, "仅管理员可执行该操作")


def _get_active_user_or_400(user_id: str) -> User:
    user = User.objects.filter(id=user_id, is_deleted=False, user_status=1).first()
    if not user:
        raise HttpError(400, f"用户不存在或不可用: {user_id}")
    return user


def _get_requirement_or_404(requirement_id: str) -> Requirement:
    return get_object_or_404(
        Requirement.objects.select_related("submitter", "reviewer", "owner", "parent"),
        id=requirement_id,
        is_deleted=False,
    )


def _refresh_overdue_flags(requirement_ids: Optional[list[str]] = None) -> None:
    now = _now()
    query = Requirement.objects.filter(is_deleted=False)
    if requirement_ids:
        query = query.filter(id__in=requirement_ids)
    review_pending = list(RequirementStatus.REVIEW_PENDING)
    dev_pending = list(RequirementStatus.DEV_PENDING)
    query.update(
        is_review_overdue=Case(
            When(
                is_leaf=True,
                status__in=review_pending,
                review_due_at__lt=now,
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        ),
        is_dev_overdue=Case(
            When(
                is_leaf=True,
                status__in=dev_pending,
                dev_due_at__lt=now,
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )


def _build_tree_path(parent: Optional[Requirement], requirement_id: str) -> str:
    if parent:
        base = parent.tree_path or f"/{parent.id}/"
        return f"{base}{requirement_id}/"
    return f"/{requirement_id}/"


def _sync_leaf_cache(requirement: Requirement) -> tuple[int, bool]:
    children_count = Requirement.objects.filter(
        parent_id=requirement.id,
        is_deleted=False,
    ).count()
    is_leaf = children_count == 0
    updates = {}
    if requirement.child_count != children_count:
        updates["child_count"] = children_count
    if requirement.is_leaf != is_leaf:
        updates["is_leaf"] = is_leaf
    if updates:
        Requirement.objects.filter(id=requirement.id, is_deleted=False).update(**updates)
        requirement.child_count = updates.get("child_count", requirement.child_count)
        requirement.is_leaf = updates.get("is_leaf", requirement.is_leaf)
    return children_count, is_leaf


def _ensure_leaf_action(requirement: Requirement, action_label: str) -> None:
    _, is_leaf = _sync_leaf_cache(requirement)
    if not is_leaf:
        raise HttpError(400, f"非叶子需求不允许执行{action_label}操作")


def _calculate_parent_summary_status(node: Requirement) -> str:
    leaf_rows = list(
        Requirement.objects.filter(
            is_deleted=False,
            root_id=node.root_id,
            tree_path__startswith=node.tree_path,
            is_leaf=True,
        )
        .values("status")
        .annotate(count=Count("id"))
    )
    if not leaf_rows:
        return RequirementStatus.ACCEPTED

    status_counts = {str(item["status"]): int(item["count"]) for item in leaf_rows}
    leaf_total = sum(status_counts.values())
    archived_count = status_counts.get(RequirementStatus.ARCHIVED, 0)
    done_count = status_counts.get(RequirementStatus.DONE, 0)
    rejected_count = status_counts.get(RequirementStatus.REJECTED, 0)

    if archived_count == leaf_total:
        return RequirementStatus.ARCHIVED
    if done_count > 0 and (done_count + archived_count) == leaf_total:
        return RequirementStatus.DONE
    if rejected_count == leaf_total:
        return RequirementStatus.REJECTED

    for status in PARENT_STATUS_BLOCK_ORDER:
        if status_counts.get(status, 0) > 0:
            return status
    return RequirementStatus.ACCEPTED


def _create_log(
    *,
    requirement: Requirement,
    action: str,
    operator: Optional[User],
    note: str = "",
    from_status: str = "",
    to_status: str = "",
) -> RequirementLog:
    return RequirementLog.objects.create(
        requirement=requirement,
        action=action,
        from_status=from_status or "",
        to_status=to_status or "",
        operator=operator,
        note=note or "",
        sys_creator=operator,
    )


def _ensure_watcher(requirement: Requirement, user: Optional[User], operator: Optional[User]) -> None:
    if not user:
        return
    RequirementWatcher.objects.get_or_create(
        requirement=requirement,
        user=user,
        defaults={"sys_creator": operator},
    )


def _ensure_role_watchers(requirement: Requirement, operator: Optional[User]) -> None:
    _ensure_watcher(requirement, requirement.submitter, operator)
    _ensure_watcher(requirement, requirement.reviewer, operator)
    _ensure_watcher(requirement, requirement.owner, operator)


def _notify_receivers(
    *,
    requirement: Requirement,
    operator: Optional[User],
    title: str,
    content: str,
    receiver_ids: list[str],
    event: str,
) -> None:
    unique_ids = _clean_ids(receiver_ids)
    if operator:
        unique_ids = [item for item in unique_ids if item != str(operator.id)]
    if not unique_ids:
        return

    users = list(User.objects.filter(id__in=unique_ids, is_deleted=False, user_status=1))
    if not users:
        return

    link = f"/requirement-center/requirement/detail/{requirement.id}"
    extra_data = {
        "requirement_id": str(requirement.id),
        "requirement_status": requirement.status,
        "event": event,
    }

    priority = normalize_priority(UserMessage.PRIORITY_NORMAL)
    for user in users:
        create_message_for_user(
            receiver=user,
            title=title,
            content=content,
            message_type=UserMessage.TYPE_INTERNAL,
            priority=priority,
            sender=operator,
            link=link,
            extra_data=extra_data,
        )

        if user.email:
            try:
                send_requirement_email_notification_task.delay(
                    user.email,
                    title,
                    content,
                )
            except Exception as exc:
                logger.exception("提交需求邮件任务失败: %s", exc)


def _collect_default_notify_ids(requirement: Requirement) -> list[str]:
    ids = []
    if requirement.submitter_id:
        ids.append(str(requirement.submitter_id))
    if requirement.reviewer_id:
        ids.append(str(requirement.reviewer_id))
    if requirement.owner_id:
        ids.append(str(requirement.owner_id))
    ids.extend(
        [str(item.user_id) for item in requirement.watchers.filter(is_deleted=False).only("user_id")]
    )
    return _clean_ids(ids)


def _can_submit_or_edit(user: User, requirement: Requirement) -> bool:
    if _is_admin(user):
        return True
    return str(requirement.submitter_id or "") == str(user.id)


def _can_reviewer_operate(user: User, requirement: Requirement) -> bool:
    if _is_admin(user):
        return True
    return str(requirement.reviewer_id or "") == str(user.id)


def _can_owner_operate(user: User, requirement: Requirement) -> bool:
    if _is_admin(user):
        return True
    return str(requirement.owner_id or "") == str(user.id)


def create_requirement(request, data) -> Requirement:
    user = request.auth
    reviewer = _get_active_user_or_400(data.reviewer_id) if data.reviewer_id else None
    owner = _get_active_user_or_400(data.owner_id) if data.owner_id else None

    requirement = Requirement(
        title=(data.title or "").strip(),
        description=data.description or "",
        business_value=data.business_value or "",
        acceptance_criteria=data.acceptance_criteria or "",
        type=data.type or "",
        source=data.source or "",
        priority=data.priority or "medium",
        reviewer=reviewer,
        owner=owner,
        attachments=list(data.attachments or []),
        review_due_at=data.review_due_at,
        dev_due_at=data.dev_due_at,
        submitter=user,
        status=RequirementStatus.DRAFT,
        sys_creator=user,
        level=0,
        child_count=0,
        is_leaf=True,
    )
    requirement.root_id = str(requirement.id)
    requirement.tree_path = _build_tree_path(None, str(requirement.id))
    requirement.save()
    _ensure_role_watchers(requirement, user)
    _create_log(
        requirement=requirement,
        action=RequirementAction.CREATE,
        operator=user,
        note="创建需求",
        to_status=RequirementStatus.DRAFT,
    )
    return requirement


def update_requirement(request, requirement_id: str, data) -> Requirement:
    user = request.auth
    requirement = _get_requirement_or_404(requirement_id)

    if not _can_submit_or_edit(user, requirement):
        raise HttpError(403, "仅提单人或管理员可编辑")

    if not _is_admin(user) and requirement.status not in {
        RequirementStatus.DRAFT,
        RequirementStatus.NEED_INFO,
    }:
        raise HttpError(400, "当前状态不允许编辑")

    payload = data.dict(exclude_unset=True)
    if "reviewer_id" in payload:
        reviewer_id = str(payload.pop("reviewer_id") or "").strip()
        requirement.reviewer = _get_active_user_or_400(reviewer_id) if reviewer_id else None
    if "owner_id" in payload:
        owner_id = str(payload.pop("owner_id") or "").strip()
        requirement.owner = _get_active_user_or_400(owner_id) if owner_id else None

    for key, value in payload.items():
        setattr(requirement, key, value)

    requirement.sys_modifier = user
    requirement.save()
    _ensure_role_watchers(requirement, user)
    _create_log(
        requirement=requirement,
        action=RequirementAction.UPDATE,
        operator=user,
        note="更新需求信息",
        from_status=requirement.status,
        to_status=requirement.status,
    )
    return requirement


def get_requirement(requirement_id: str) -> Requirement:
    _refresh_overdue_flags([requirement_id])
    return _get_requirement_or_404(requirement_id)


def _apply_requirement_filters(query, filters):
    if filters.keyword:
        keyword = str(filters.keyword).strip()
        query = query.filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(business_value__icontains=keyword)
        )
    if filters.status:
        query = query.filter(status=filters.status)
    if filters.priority:
        query = query.filter(priority=filters.priority)
    if filters.type:
        query = query.filter(type=filters.type)
    if filters.source:
        query = query.filter(source=filters.source)
    if filters.reviewer_id:
        query = query.filter(reviewer_id=filters.reviewer_id)
    if filters.owner_id:
        query = query.filter(owner_id=filters.owner_id)
    if filters.overdue is True:
        query = query.filter(Q(is_review_overdue=True) | Q(is_dev_overdue=True))
    if filters.overdue is False:
        query = query.filter(is_review_overdue=False, is_dev_overdue=False)
    root_id = str(getattr(filters, "root_id", "") or "").strip()
    if root_id:
        query = query.filter(root_id=root_id)
    return query


def _tree_sort_key(item: Requirement):
    create_ts = item.sys_create_datetime.timestamp() if item.sys_create_datetime else 0
    return (-int(item.sort or 0), -create_ts, str(item.id))


def list_requirements(filters) -> "QuerySet":
    _refresh_overdue_flags()
    query = Requirement.objects.filter(is_deleted=False).select_related(
        "submitter",
        "reviewer",
        "owner",
        "parent",
    ).prefetch_related("watchers")
    query = _apply_requirement_filters(query, filters)
    return query.order_by("-sort", "-sys_create_datetime")


def query_requirement_tree(filters):
    _refresh_overdue_flags()
    base_query = Requirement.objects.filter(is_deleted=False).select_related(
        "submitter",
        "reviewer",
        "owner",
        "parent",
    ).prefetch_related("watchers")
    matched_rows = list(
        _apply_requirement_filters(base_query, filters).values("id", "parent_id")
    )
    if not matched_rows:
        return []

    keep_ids = {str(item["id"]) for item in matched_rows}
    parent_ids = {
        str(item["parent_id"])
        for item in matched_rows
        if item.get("parent_id")
    }

    while parent_ids:
        parent_rows = list(
            Requirement.objects.filter(
                id__in=parent_ids,
                is_deleted=False,
            ).values("id", "parent_id")
        )
        next_parent_ids: set[str] = set()
        for row in parent_rows:
            row_id = str(row["id"])
            if row_id not in keep_ids:
                keep_ids.add(row_id)
            if row.get("parent_id"):
                next_parent_ids.add(str(row["parent_id"]))
        parent_ids = {item for item in next_parent_ids if item not in keep_ids}

    nodes = list(
        Requirement.objects.filter(
            id__in=keep_ids,
            is_deleted=False,
        )
        .select_related("submitter", "reviewer", "owner", "parent")
        .prefetch_related("watchers")
        .order_by("level", "-sort", "-sys_create_datetime")
    )
    node_map = {str(item.id): item for item in nodes}
    children_map: dict[str, list[Requirement]] = defaultdict(list)
    roots: list[Requirement] = []

    for node in nodes:
        node.children_items = []
    for node in nodes:
        parent_id = str(node.parent_id) if node.parent_id else ""
        if parent_id and parent_id in node_map:
            children_map[parent_id].append(node)
        else:
            roots.append(node)

    for parent_id, children in children_map.items():
        children.sort(key=_tree_sort_key)
        node_map[parent_id].children_items = children
    roots.sort(key=_tree_sort_key)
    return roots


def list_requirement_children(parent_id: str):
    _refresh_overdue_flags()
    _get_requirement_or_404(parent_id)
    return (
        Requirement.objects.filter(
            is_deleted=False,
            parent_id=parent_id,
        )
        .select_related("submitter", "reviewer", "owner", "parent")
        .prefetch_related("watchers")
        .order_by("-sort", "-sys_create_datetime")
    )


def _ensure_split_permission(operator: User, parent: Requirement):
    if parent.status not in SPLIT_ALLOWED_PARENT_STATUS:
        raise HttpError(400, "当前父需求状态不允许拆解子需求")

    if parent.status in {RequirementStatus.ACCEPTED, RequirementStatus.PLANNED}:
        if not (_can_reviewer_operate(operator, parent) or _is_admin(operator)):
            raise HttpError(403, "当前状态仅评审人或管理员可拆解")
        return
    if parent.status in {RequirementStatus.IN_DEV, RequirementStatus.IN_ACCEPTANCE}:
        if not (_can_owner_operate(operator, parent) or _is_admin(operator)):
            raise HttpError(403, "当前状态仅责任人或管理员可拆解")
        return

    raise HttpError(400, "当前父需求状态不允许拆解子需求")


def refresh_ancestor_status(requirement_id: str, operator: Optional[User] = None) -> None:
    current = _get_requirement_or_404(requirement_id)
    parent_id = str(current.parent_id or "")
    now = _now()
    visited: set[str] = set()

    while parent_id and parent_id not in visited:
        visited.add(parent_id)
        parent = Requirement.objects.select_related("parent").filter(
            id=parent_id,
            is_deleted=False,
        ).first()
        if not parent:
            break

        _, is_leaf = _sync_leaf_cache(parent)
        update_fields: list[str] = []

        if not is_leaf:
            to_status = _calculate_parent_summary_status(parent)
            from_status = parent.status
            if from_status != to_status:
                parent.status = to_status
                update_fields.append("status")
                if to_status == RequirementStatus.DONE and not parent.done_at:
                    parent.done_at = now
                    update_fields.append("done_at")
                _create_log(
                    requirement=parent,
                    action=RequirementAction.TRANSITION,
                    operator=operator,
                    note="子需求状态汇总自动更新",
                    from_status=from_status,
                    to_status=to_status,
                )

            if parent.is_review_overdue:
                parent.is_review_overdue = False
                update_fields.append("is_review_overdue")
            if parent.is_dev_overdue:
                parent.is_dev_overdue = False
                update_fields.append("is_dev_overdue")
        if update_fields:
            parent.sys_modifier = operator
            update_fields.extend(["sys_modifier", "sys_update_datetime"])
            parent.save(update_fields=list(dict.fromkeys(update_fields)))

        parent_id = str(parent.parent_id or "")


def rebuild_tree_meta(root_id: Optional[str] = None) -> int:
    query = Requirement.objects.filter(is_deleted=False).only(
        "id",
        "parent_id",
        "root_id",
        "level",
        "tree_path",
        "child_count",
        "is_leaf",
    )
    if root_id:
        root_text = str(root_id).strip()
        if not root_text:
            return 0
        query = query.filter(
            Q(id=root_text)
            | Q(root_id=root_text)
            | Q(tree_path__contains=f"/{root_text}/")
        )

    nodes = list(query)
    if not nodes:
        return 0

    node_map = {str(item.id): item for item in nodes}
    children_map: dict[Optional[str], list[Requirement]] = defaultdict(list)
    for item in nodes:
        parent_key = str(item.parent_id) if item.parent_id and str(item.parent_id) in node_map else None
        children_map[parent_key].append(item)

    visited: set[str] = set()
    changed_nodes: list[Requirement] = []

    def walk(node: Requirement, root_key: str, level: int, tree_path: str):
        node_id = str(node.id)
        if node_id in visited:
            raise HttpError(400, "检测到需求树存在环路，请联系管理员处理")
        visited.add(node_id)

        children = children_map.get(node_id, [])
        child_count = len(children)
        is_leaf = child_count == 0
        has_change = (
            str(node.root_id or "") != root_key
            or int(node.level or 0) != level
            or str(node.tree_path or "") != tree_path
            or int(node.child_count or 0) != child_count
            or bool(node.is_leaf) != is_leaf
        )
        node.root_id = root_key
        node.level = level
        node.tree_path = tree_path
        node.child_count = child_count
        node.is_leaf = is_leaf
        if has_change:
            changed_nodes.append(node)

        for child in children:
            walk(child, root_key, level + 1, f"{tree_path}{child.id}/")

    roots = children_map.get(None, [])
    for root in roots:
        walk(root, str(root.id), 0, f"/{root.id}/")

    for node in nodes:
        node_id = str(node.id)
        if node_id in visited:
            continue
        node.parent_id = None
        walk(node, node_id, 0, f"/{node_id}/")

    if changed_nodes:
        Requirement.objects.bulk_update(
            changed_nodes,
            ["parent", "root_id", "level", "tree_path", "child_count", "is_leaf", "sys_update_datetime"],
        )
    return len(changed_nodes)


@transaction.atomic
def create_child_requirement(request, parent_id: str, data) -> Requirement:
    operator = request.auth
    parent = _get_requirement_or_404(parent_id)
    _ensure_split_permission(operator, parent)

    payload = data.dict(exclude_unset=True)
    reviewer = parent.reviewer
    owner = parent.owner
    if "reviewer_id" in payload and payload.get("reviewer_id"):
        reviewer = _get_active_user_or_400(str(payload["reviewer_id"]))
    if "owner_id" in payload and payload.get("owner_id"):
        owner = _get_active_user_or_400(str(payload["owner_id"]))

    child = Requirement(
        parent=parent,
        root_id=parent.root_id or str(parent.id),
        level=int(parent.level or 0) + 1,
        tree_path="",
        child_count=0,
        is_leaf=True,
        title=(data.title or "").strip(),
        description=data.description or "",
        business_value=data.business_value or "",
        acceptance_criteria=data.acceptance_criteria or "",
        type=data.type if data.type is not None else parent.type,
        source=data.source if data.source is not None else parent.source,
        priority=data.priority if data.priority is not None else parent.priority,
        submitter=parent.submitter or operator,
        reviewer=reviewer,
        owner=owner,
        attachments=list(data.attachments or []),
        status=RequirementStatus.ACCEPTED,
        accepted_at=_now(),
        dev_due_at=data.dev_due_at or parent.dev_due_at or (_now() + timedelta(days=DEV_DUE_DEFAULT_DAYS)),
        is_review_overdue=False,
        is_dev_overdue=False,
        sys_creator=operator,
    )
    child.tree_path = _build_tree_path(parent, str(child.id))
    child.save()
    _ensure_role_watchers(child, operator)

    _create_log(
        requirement=child,
        action=RequirementAction.CREATE,
        operator=operator,
        note=f"拆解自父需求 {parent.id}",
        to_status=RequirementStatus.ACCEPTED,
    )
    _create_log(
        requirement=parent,
        action=RequirementAction.SPLIT_CHILD,
        operator=operator,
        note=f"拆解创建子需求 {child.id}",
        from_status=parent.status,
        to_status=parent.status,
    )

    _sync_leaf_cache(parent)
    refresh_ancestor_status(str(child.id), operator)

    title = f"需求拆解：{parent.title}"
    content = f"{_user_display_name(operator)} 从该需求拆解出子需求：{child.title}"
    notify_ids = _collect_default_notify_ids(parent)
    if child.reviewer_id:
        notify_ids.append(str(child.reviewer_id))
    if child.owner_id:
        notify_ids.append(str(child.owner_id))
    _notify_receivers(
        requirement=parent,
        operator=operator,
        title=title,
        content=content,
        receiver_ids=_clean_ids(notify_ids),
        event=RequirementAction.SPLIT_CHILD,
    )
    return child


@transaction.atomic
def submit_requirement(request, requirement_id: str, note: str = "") -> Requirement:
    user = request.auth
    requirement = _get_requirement_or_404(requirement_id)
    _ensure_leaf_action(requirement, "提交")

    if not _can_submit_or_edit(user, requirement):
        raise HttpError(403, "仅提单人或管理员可提交")
    if requirement.status not in {RequirementStatus.DRAFT, RequirementStatus.NEED_INFO}:
        raise HttpError(400, "仅草稿/待补充状态可提交")
    if not requirement.reviewer_id:
        raise HttpError(400, "提交前必须指定评审人")

    from_status = requirement.status
    now = _now()
    requirement.status = RequirementStatus.SUBMITTED
    requirement.submitted_at = now
    requirement.review_due_at = requirement.review_due_at or (now + timedelta(days=REVIEW_DUE_DEFAULT_DAYS))
    requirement.is_review_overdue = False
    requirement.sys_modifier = user
    requirement.save()
    _ensure_role_watchers(requirement, user)

    _create_log(
        requirement=requirement,
        action=RequirementAction.SUBMIT,
        operator=user,
        note=note or "提交评审",
        from_status=from_status,
        to_status=requirement.status,
    )

    title = f"需求待评审：{requirement.title}"
    content = f"{_user_display_name(user)} 提交了需求，请尽快评审。"
    _notify_receivers(
        requirement=requirement,
        operator=user,
        title=title,
        content=content,
        receiver_ids=[str(requirement.reviewer_id)],
        event=RequirementAction.SUBMIT,
    )
    refresh_ancestor_status(str(requirement.id), user)
    return requirement


@transaction.atomic
def review_requirement(request, requirement_id: str, action: str, note: str = "") -> Requirement:
    user = request.auth
    requirement = _get_requirement_or_404(requirement_id)
    _ensure_leaf_action(requirement, "评审")

    if requirement.status != RequirementStatus.SUBMITTED:
        raise HttpError(400, "仅待评审状态可执行评审动作")
    if not _can_reviewer_operate(user, requirement):
        raise HttpError(403, "仅评审人或管理员可执行评审")

    action = str(action or "").strip().lower()
    status_map = {
        "accept": RequirementStatus.ACCEPTED,
        "reject": RequirementStatus.REJECTED,
        "need_info": RequirementStatus.NEED_INFO,
    }
    to_status = status_map.get(action)
    if not to_status:
        raise HttpError(400, "评审动作不支持，仅支持 accept/reject/need_info")

    from_status = requirement.status
    now = _now()
    requirement.status = to_status
    requirement.is_review_overdue = False
    if to_status == RequirementStatus.ACCEPTED:
        requirement.accepted_at = now
        requirement.dev_due_at = requirement.dev_due_at or (now + timedelta(days=DEV_DUE_DEFAULT_DAYS))
    if to_status in RequirementStatus.CLOSED:
        requirement.is_dev_overdue = False
    requirement.sys_modifier = user
    requirement.save()
    _ensure_role_watchers(requirement, user)

    _create_log(
        requirement=requirement,
        action=RequirementAction.REVIEW,
        operator=user,
        note=note or f"评审动作: {action}",
        from_status=from_status,
        to_status=to_status,
    )

    title = f"需求评审结果：{requirement.title}"
    action_text_map = {
        "accept": "已接纳",
        "reject": "已拒绝",
        "need_info": "需补充信息",
    }
    content = f"评审人 {_user_display_name(user)} 已将需求评审为「{action_text_map.get(action, action)}」。"
    notify_ids = _collect_default_notify_ids(requirement)
    _notify_receivers(
        requirement=requirement,
        operator=user,
        title=title,
        content=content,
        receiver_ids=notify_ids,
        event=RequirementAction.REVIEW,
    )
    refresh_ancestor_status(str(requirement.id), user)
    return requirement


@transaction.atomic
def transfer_reviewer(request, requirement_id: str, reviewer_id: str, note: str = "") -> Requirement:
    user = request.auth
    requirement = _get_requirement_or_404(requirement_id)
    if not _can_reviewer_operate(user, requirement):
        raise HttpError(403, "仅评审人或管理员可转审")

    reviewer = _get_active_user_or_400(reviewer_id)
    old_reviewer_id = str(requirement.reviewer_id or "")
    requirement.reviewer = reviewer
    requirement.sys_modifier = user
    requirement.save(update_fields=["reviewer", "sys_modifier", "sys_update_datetime"])
    _ensure_watcher(requirement, reviewer, user)

    _create_log(
        requirement=requirement,
        action=RequirementAction.TRANSFER_REVIEWER,
        operator=user,
        note=note or f"评审人转交: {old_reviewer_id} -> {reviewer.id}",
        from_status=requirement.status,
        to_status=requirement.status,
    )

    title = f"需求转评审：{requirement.title}"
    content = f"{_user_display_name(user)} 将需求评审责任转交给你。"
    _notify_receivers(
        requirement=requirement,
        operator=user,
        title=title,
        content=content,
        receiver_ids=[str(reviewer.id)],
        event=RequirementAction.TRANSFER_REVIEWER,
    )
    return requirement


@transaction.atomic
def assign_owner(request, requirement_id: str, owner_id: str, note: str = "") -> Requirement:
    user = request.auth
    requirement = _get_requirement_or_404(requirement_id)
    if not (_can_reviewer_operate(user, requirement) or _is_admin(user)):
        raise HttpError(403, "仅评审人或管理员可分配责任人")

    owner = _get_active_user_or_400(owner_id)
    requirement.owner = owner
    requirement.sys_modifier = user
    requirement.save(update_fields=["owner", "sys_modifier", "sys_update_datetime"])
    _ensure_watcher(requirement, owner, user)

    _create_log(
        requirement=requirement,
        action=RequirementAction.ASSIGN_OWNER,
        operator=user,
        note=note or f"分配责任人: {owner.id}",
        from_status=requirement.status,
        to_status=requirement.status,
    )

    title = f"需求已分配：{requirement.title}"
    content = f"{_user_display_name(user)} 已将该需求指派给你负责。"
    _notify_receivers(
        requirement=requirement,
        operator=user,
        title=title,
        content=content,
        receiver_ids=[str(owner.id)],
        event=RequirementAction.ASSIGN_OWNER,
    )
    return requirement


@transaction.atomic
def transition_requirement(request, requirement_id: str, action: str, note: str = "") -> Requirement:
    user = request.auth
    requirement = _get_requirement_or_404(requirement_id)
    _ensure_leaf_action(requirement, "流转")

    action = str(action or "").strip().lower()
    transition_map = {
        RequirementStatus.ACCEPTED: {"planned": RequirementStatus.PLANNED},
        RequirementStatus.PLANNED: {"in_dev": RequirementStatus.IN_DEV},
        RequirementStatus.IN_DEV: {"in_acceptance": RequirementStatus.IN_ACCEPTANCE},
        RequirementStatus.IN_ACCEPTANCE: {"done": RequirementStatus.DONE},
        RequirementStatus.DONE: {"archive": RequirementStatus.ARCHIVED},
        RequirementStatus.REJECTED: {"archive": RequirementStatus.ARCHIVED},
    }

    to_status = transition_map.get(requirement.status, {}).get(action)
    if not to_status:
        raise HttpError(400, "非法状态流转")

    if action == "planned":
        if not (_can_reviewer_operate(user, requirement) or _is_admin(user)):
            raise HttpError(403, "仅评审人或管理员可执行排期")
        if not requirement.owner_id:
            raise HttpError(400, "进入已排期前必须指定责任人")
    elif action in {"in_dev", "in_acceptance", "done"}:
        if not _can_owner_operate(user, requirement):
            raise HttpError(403, "仅责任人或管理员可推进开发状态")
    elif action == "archive":
        _require_admin(user)

    from_status = requirement.status
    now = _now()
    requirement.status = to_status
    if to_status == RequirementStatus.PLANNED:
        requirement.planned_at = now
    if to_status == RequirementStatus.IN_DEV:
        requirement.dev_started_at = now
    if to_status == RequirementStatus.DONE:
        requirement.done_at = now
    if to_status in RequirementStatus.CLOSED:
        requirement.is_review_overdue = False
        requirement.is_dev_overdue = False
    requirement.sys_modifier = user
    requirement.save()
    _ensure_role_watchers(requirement, user)

    _create_log(
        requirement=requirement,
        action=RequirementAction.TRANSITION,
        operator=user,
        note=note or f"状态流转: {action}",
        from_status=from_status,
        to_status=to_status,
    )

    title = f"需求状态更新：{requirement.title}"
    content = f"{_user_display_name(user)} 将需求状态从「{from_status}」更新为「{to_status}」。"
    _notify_receivers(
        requirement=requirement,
        operator=user,
        title=title,
        content=content,
        receiver_ids=_collect_default_notify_ids(requirement),
        event=RequirementAction.TRANSITION,
    )
    refresh_ancestor_status(str(requirement.id), user)
    return requirement


@transaction.atomic
def create_comment(request, requirement_id: str, content: str, mention_ids: list[str]):
    user = request.auth
    requirement = _get_requirement_or_404(requirement_id)
    text = str(content or "").strip()
    if not text:
        raise HttpError(400, "评论内容不能为空")

    mention_ids = _clean_ids(mention_ids or [])
    comment = RequirementComment.objects.create(
        requirement=requirement,
        commenter=user,
        content=text,
        mentions=mention_ids,
        sys_creator=user,
    )
    _ensure_watcher(requirement, user, user)

    _create_log(
        requirement=requirement,
        action=RequirementAction.COMMENT,
        operator=user,
        note=text[:200],
        from_status=requirement.status,
        to_status=requirement.status,
    )

    title = f"需求评论更新：{requirement.title}"
    content_text = f"{_user_display_name(user)} 发表评论：{text[:80]}"
    notify_ids = _collect_default_notify_ids(requirement) + mention_ids
    _notify_receivers(
        requirement=requirement,
        operator=user,
        title=title,
        content=content_text,
        receiver_ids=_clean_ids(notify_ids),
        event=RequirementAction.COMMENT,
    )
    return comment


def list_comments(requirement_id: str):
    return (
        RequirementComment.objects.select_related("commenter")
        .filter(requirement_id=requirement_id, is_deleted=False)
        .order_by("sys_create_datetime")
    )


def list_logs(requirement_id: str):
    return (
        RequirementLog.objects.select_related("operator")
        .filter(requirement_id=requirement_id, is_deleted=False)
        .order_by("-sys_create_datetime")
    )


def _query_batch_requirements(requirement_ids: list[str]):
    valid_ids = _clean_ids(requirement_ids)
    if not valid_ids:
        raise HttpError(400, "requirement_ids 不能为空")
    query = Requirement.objects.filter(id__in=valid_ids, is_deleted=False).select_related(
        "submitter",
        "reviewer",
        "owner",
    )
    return list(query), valid_ids


@transaction.atomic
def batch_assign_reviewer(request, requirement_ids: list[str], reviewer_id: str, note: str = ""):
    user = request.auth
    _require_admin(user)
    reviewer = _get_active_user_or_400(reviewer_id)

    requirements, valid_ids = _query_batch_requirements(requirement_ids)
    touched_ids: list[str] = []
    for item in requirements:
        item.reviewer = reviewer
        item.sys_modifier = user
        item.save(update_fields=["reviewer", "sys_modifier", "sys_update_datetime"])
        _ensure_watcher(item, reviewer, user)
        _create_log(
            requirement=item,
            action=RequirementAction.BATCH_ASSIGN_REVIEWER,
            operator=user,
            note=note or f"批量设置评审人: {reviewer.id}",
            from_status=item.status,
            to_status=item.status,
        )
        touched_ids.append(str(item.id))

    return {
        "msg": "批量分配评审人完成",
        "count": len(touched_ids),
        "skipped_ids": [item for item in valid_ids if item not in set(touched_ids)],
    }


@transaction.atomic
def batch_assign_owner(request, requirement_ids: list[str], owner_id: str, note: str = ""):
    user = request.auth
    _require_admin(user)
    owner = _get_active_user_or_400(owner_id)

    requirements, valid_ids = _query_batch_requirements(requirement_ids)
    touched_ids: list[str] = []
    for item in requirements:
        item.owner = owner
        item.sys_modifier = user
        item.save(update_fields=["owner", "sys_modifier", "sys_update_datetime"])
        _ensure_watcher(item, owner, user)
        _create_log(
            requirement=item,
            action=RequirementAction.BATCH_ASSIGN_OWNER,
            operator=user,
            note=note or f"批量设置责任人: {owner.id}",
            from_status=item.status,
            to_status=item.status,
        )
        touched_ids.append(str(item.id))

    return {
        "msg": "批量分配责任人完成",
        "count": len(touched_ids),
        "skipped_ids": [item for item in valid_ids if item not in set(touched_ids)],
    }


@transaction.atomic
def batch_update_priority(request, requirement_ids: list[str], priority: str, note: str = ""):
    user = request.auth
    _require_admin(user)

    requirements, valid_ids = _query_batch_requirements(requirement_ids)
    touched_ids: list[str] = []
    for item in requirements:
        item.priority = priority
        item.sys_modifier = user
        item.save(update_fields=["priority", "sys_modifier", "sys_update_datetime"])
        _create_log(
            requirement=item,
            action=RequirementAction.BATCH_PRIORITY,
            operator=user,
            note=note or f"批量调整优先级: {priority}",
            from_status=item.status,
            to_status=item.status,
        )
        touched_ids.append(str(item.id))

    return {
        "msg": "批量调整优先级完成",
        "count": len(touched_ids),
        "skipped_ids": [item for item in valid_ids if item not in set(touched_ids)],
    }


@transaction.atomic
def batch_archive(request, requirement_ids: list[str], note: str = ""):
    user = request.auth
    _require_admin(user)
    requirements, valid_ids = _query_batch_requirements(requirement_ids)
    touched_ids: list[str] = []
    skipped_ids: list[str] = []
    for item in requirements:
        if item.status not in {RequirementStatus.DONE, RequirementStatus.REJECTED}:
            skipped_ids.append(str(item.id))
            continue
        from_status = item.status
        item.status = RequirementStatus.ARCHIVED
        item.is_review_overdue = False
        item.is_dev_overdue = False
        item.sys_modifier = user
        item.save(update_fields=["status", "is_review_overdue", "is_dev_overdue", "sys_modifier", "sys_update_datetime"])
        _create_log(
            requirement=item,
            action=RequirementAction.BATCH_ARCHIVE,
            operator=user,
            note=note or "批量归档",
            from_status=from_status,
            to_status=RequirementStatus.ARCHIVED,
        )
        touched_ids.append(str(item.id))
        refresh_ancestor_status(str(item.id), user)

    skipped_ids.extend([item for item in valid_ids if item not in set(touched_ids + skipped_ids)])
    return {
        "msg": "批量归档处理完成",
        "count": len(touched_ids),
        "skipped_ids": _clean_ids(skipped_ids),
    }


def _build_stat_items(rows, key_field: str, label_map: dict[str, str]):
    return [
        {
            "key": str(item.get(key_field) or ""),
            "label": label_map.get(str(item.get(key_field) or ""), str(item.get(key_field) or "-")),
            "count": int(item.get("count") or 0),
        }
        for item in rows
    ]


def get_dashboard_summary():
    _refresh_overdue_flags()
    query = Requirement.objects.filter(is_deleted=False)

    total_count = query.count()
    open_count = query.exclude(status__in=RequirementStatus.CLOSED).count()
    closed_count = query.filter(status__in=RequirementStatus.CLOSED).count()
    review_overdue_count = query.filter(is_review_overdue=True).count()
    dev_overdue_count = query.filter(is_dev_overdue=True).count()
    overdue_count = query.filter(Q(is_review_overdue=True) | Q(is_dev_overdue=True)).count()

    status_rows = list(query.values("status").annotate(count=Count("id")).order_by("-count"))
    priority_rows = list(query.values("priority").annotate(count=Count("id")).order_by("-count"))

    reviewer_rows = list(
        query.exclude(reviewer_id__isnull=True)
        .values("reviewer_id", "reviewer__name", "reviewer__username")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    owner_rows = list(
        query.exclude(owner_id__isnull=True)
        .values("owner_id", "owner__name", "owner__username")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    status_label_map = dict(RequirementStatus.CHOICES)
    status_stats = _build_stat_items(status_rows, "status", status_label_map)
    priority_stats = _build_stat_items(priority_rows, "priority", {})

    reviewer_stats = [
        {
            "key": str(item["reviewer_id"]),
            "label": item.get("reviewer__name") or item.get("reviewer__username") or str(item["reviewer_id"]),
            "count": int(item["count"]),
        }
        for item in reviewer_rows
    ]
    owner_stats = [
        {
            "key": str(item["owner_id"]),
            "label": item.get("owner__name") or item.get("owner__username") or str(item["owner_id"]),
            "count": int(item["count"]),
        }
        for item in owner_rows
    ]

    return {
        "total_count": total_count,
        "open_count": open_count,
        "closed_count": closed_count,
        "overdue_count": overdue_count,
        "review_overdue_count": review_overdue_count,
        "dev_overdue_count": dev_overdue_count,
        "status_stats": status_stats,
        "priority_stats": priority_stats,
        "reviewer_stats": reviewer_stats,
        "owner_stats": owner_stats,
    }
