from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace
from typing import Any

from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.failure_mode import failure_mode_services
from apps.project_manager.failure_mode.failure_mode_model import (
    FailureMode,
    FailureModeProduct,
    FailureModeRoleAssignment,
    FailureModeSubsystemConfig,
    FailureModeTask,
    FailureModeTaskDraft,
    FailureModeTaskLog,
    ProductFailureMode,
    ProductFailureModeHandlingLanding,
    ProductFailureModeHuatuoLanding,
    ProductFailureModeInterceptionLanding,
    ProductFailureModeObservationLanding,
    TaskFailureMode,
)
from apps.project_manager.project.project_model import Project
from core.user.user_model import User


def _format_datetime(value) -> str | None:
    if not value:
        return None
    return value.isoformat()


def _format_user(user: User | None) -> dict[str, str | None] | None:
    if not user:
        return None
    return {
        'id': str(user.id),
        'username': user.username,
        'name': getattr(user, 'name', None),
    }


TASK_STATUS_FAILURE_MODE_STATUS_MAP = {
    'CREATED': '待梳理',
    'PROCESSING': '梳理中',
    'REVIEWING': '待评审',
    'CLOSED': '已基线',
}

PLATFORM_PROJECT_TYPE = '平台项目'
LANDING_SECTION_KEYS = (
    'interception_rows',
    'handling_rows',
    'observation_rows',
    'huatuo_rows',
)


def _normalize_text(value: Any) -> str:
    return str(value or '').strip()


def _normalize_id_list(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _normalize_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text or text in {'null', 'none'}:
        return None
    if text in {'1', 'true', 'yes', 'on'}:
        return True
    if text in {'0', 'false', 'no', 'off'}:
        return False
    return None


def _filter_product_queryset_by_project_type(queryset, project_type: str | None = None):
    normalized_type = _normalize_text(project_type)
    if not normalized_type:
        return queryset
    return queryset.filter(project__type=normalized_type)


def _ensure_product_project_type(
    product: FailureModeProduct,
    project_type: str | None = None,
):
    normalized_type = _normalize_text(project_type)
    if normalized_type and getattr(product.project, 'type', None) != normalized_type:
        raise HttpError(404, '当前产品不在可配置范围内。')


def _filter_visible_role_assignments(
    product: FailureModeProduct,
    assignments: list[FailureModeRoleAssignment],
    policy: 'FailureModeAccessPolicy',
) -> list[FailureModeRoleAssignment]:
    if policy.is_admin or str(product.id) in policy.version_product_ids:
        return list(assignments)

    visible_subsystems = {
        subsystem
        for product_id, subsystem in policy.scope_pairs
        if product_id == str(product.id)
    }
    return [
        item
        for item in assignments
        if item.role == FailureModeRoleAssignment.ROLE_VERSION_SE
        or (
            item.role in {
                FailureModeRoleAssignment.ROLE_FEATURE_SE,
                FailureModeRoleAssignment.ROLE_MEMBER,
            }
            and item.subsystem in visible_subsystems
        )
    ]


def _build_role_preview(assignments: list[FailureModeRoleAssignment]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, list[dict[str, str | None]]]] = defaultdict(
        lambda: {
            'feature_se_info': [],
            'member_info': [],
        }
    )
    for item in assignments:
        if not item.subsystem:
            continue
        if item.role == FailureModeRoleAssignment.ROLE_FEATURE_SE:
            target_key = 'feature_se_info'
        elif item.role == FailureModeRoleAssignment.ROLE_MEMBER:
            target_key = 'member_info'
        else:
            continue
        user_info = _format_user(item.user)
        if not user_info:
            continue
        grouped[item.subsystem][target_key].append(user_info)

    return [
        {
            'subsystem': subsystem,
            'feature_se_info': values['feature_se_info'],
            'member_info': values['member_info'],
        }
        for subsystem, values in sorted(grouped.items(), key=lambda item: item[0])
    ]


def _serialize_product(
    product: FailureModeProduct,
    policy: 'FailureModeAccessPolicy',
) -> dict[str, Any]:
    owner_assignment = None
    prefetched = getattr(product, '_prefetched_objects_cache', {})
    assignments = prefetched.get('role_assignments') or []
    visible_assignments = _filter_visible_role_assignments(product, assignments, policy)
    if assignments is not None:
        owner_assignment = next(
            (
                item
                for item in assignments
                if item.role == FailureModeRoleAssignment.ROLE_VERSION_SE and item.is_active
            ),
            None,
        )
    return {
        'id': str(product.id),
        'project_id': str(product.project_id),
        'project_name': product.project.name if product.project else '',
        'owner_id': str(product.owner_id) if product.owner_id else None,
        'owner_info': _format_user(product.owner),
        'owner_assignment_id': str(owner_assignment.id) if owner_assignment else None,
        'can_manage_roles': policy.can_manage_product_roles(product),
        'role_preview': _build_role_preview(visible_assignments),
        'sys_create_datetime': _format_datetime(product.sys_create_datetime),
        'sys_update_datetime': _format_datetime(product.sys_update_datetime),
    }


def _serialize_role_assignment(item: FailureModeRoleAssignment) -> dict[str, Any]:
    return {
        'id': str(item.id),
        'user_id': str(item.user_id),
        'user_info': _format_user(item.user),
        'role': item.role,
        'product_id': str(item.product_id) if item.product_id else None,
        'subsystem': item.subsystem or '',
        'is_active': bool(item.is_active),
        'sys_create_datetime': _format_datetime(item.sys_create_datetime),
        'sys_update_datetime': _format_datetime(item.sys_update_datetime),
    }


def _serialize_product_failure_mode(item: ProductFailureMode) -> dict[str, Any]:
    return {
        'id': str(item.id),
        'product_id': str(item.product_id),
        'subsystem': item.subsystem,
        'failure_mode_id': str(item.failure_mode_id),
        'failure_mode_brief': item.failure_mode.brief if item.failure_mode else '',
        'is_landed': bool(getattr(item, 'is_landed', False)),
        'sys_create_datetime': _format_datetime(item.sys_create_datetime),
    }


def _build_task_available_actions(
    task: FailureModeTask,
    policy: 'FailureModeAccessPolicy',
) -> list[str]:
    actions: list[str] = []
    if task.status == 'CREATED' and policy.can_accept_task(task):
        actions.append('accept')
    if task.status == 'PROCESSING' and policy.can_process_task(task):
        actions.extend(['bind', 'submit'])
        if task.task_type != 'DELETE':
            actions.append('quick_create')
        if task.task_type == 'REVISE':
            actions.append('edit_draft')
    if task.status in {'CREATED', 'PROCESSING'} and policy.can_reassign_task(task):
        actions.append('reassign')
    if task.status == 'REVIEWING' and policy.can_recall_task(task):
        actions.append('recall')
    if task.status == 'REVIEWING' and policy.can_reject_task(task):
        actions.append('reject')
    if task.status == 'REVIEWING' and policy.can_close_task(task):
        actions.append('close')
    return actions


def _serialize_task(task: FailureModeTask, policy: 'FailureModeAccessPolicy') -> dict[str, Any]:
    return {
        'id': str(task.id),
        'task_no': task.task_no,
        'name': task.name,
        'task_type': task.task_type,
        'status': task.status,
        'product_id': str(task.product_id),
        'product_name': task.product.project.name if (task.product and task.product.project) else '',
        'subsystem': task.subsystem,
        'creator_id': str(task.creator_id) if task.creator_id else None,
        'creator_info': _format_user(task.creator),
        'assignee_id': str(task.assignee_id) if task.assignee_id else None,
        'assignee_info': _format_user(task.assignee),
        'current_processor_id': str(task.current_processor_id) if task.current_processor_id else None,
        'current_processor_info': _format_user(task.current_processor),
        'available_actions': _build_task_available_actions(task, policy),
        'review_result': task.review_result or '',
        'review_minutes_html': task.review_minutes_html or '',
        'review_attachment_ids': task.review_attachment_ids or [],
        'accepted_at': _format_datetime(task.accepted_at),
        'submitted_at': _format_datetime(task.submitted_at),
        'reviewed_at': _format_datetime(task.reviewed_at),
        'closed_at': _format_datetime(task.closed_at),
        'sys_create_datetime': _format_datetime(task.sys_create_datetime),
        'sys_update_datetime': _format_datetime(task.sys_update_datetime),
    }


def _serialize_task_log(item: FailureModeTaskLog) -> dict[str, Any]:
    return {
        'id': str(item.id),
        'action': item.action,
        'from_status': item.from_status or '',
        'to_status': item.to_status or '',
        'note': item.note or '',
        'operator_id': str(item.operator_id) if item.operator_id else None,
        'operator_info': _format_user(item.operator),
        'extra_data': item.extra_data or {},
        'sys_create_datetime': _format_datetime(item.sys_create_datetime),
    }


def _build_task_landing_row(
    *,
    resource_id: str,
    label: str,
    subtitle: str | None = None,
    group_key: str = '',
    is_landed: bool | None = None,
) -> dict[str, Any]:
    return {
        'resource_id': resource_id,
        'label': label,
        'subtitle': subtitle or None,
        'group_key': group_key,
        'is_landed': is_landed,
    }


def _extract_task_landing_status_map(rows: Any) -> dict[str, bool | None]:
    result: dict[str, bool | None] = {}
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        resource_id = _normalize_text(item.get('resource_id') or item.get('id'))
        if not resource_id:
            continue
        result[resource_id] = _normalize_optional_bool(item.get('is_landed'))
    return result


def _normalize_task_landing_rows(
    relation_items: list[dict[str, Any]] | None,
    payload_rows: Any,
    *,
    fallback_status_map: dict[str, bool | None] | None = None,
    default_group_key: str = '',
    use_subtitle_group_key: bool = False,
) -> list[dict[str, Any]]:
    payload_status_map = _extract_task_landing_status_map(payload_rows)
    rows: list[dict[str, Any]] = []
    for relation_item in relation_items or []:
        resource_id = _normalize_text(relation_item.get('id'))
        if not resource_id:
            continue
        subtitle = _normalize_text(relation_item.get('subtitle')) or None
        group_key = subtitle if use_subtitle_group_key and subtitle else default_group_key
        is_landed = payload_status_map.get(resource_id)
        if resource_id not in payload_status_map:
            is_landed = (fallback_status_map or {}).get(resource_id)
        rows.append(
            _build_task_landing_row(
                resource_id=resource_id,
                label=_normalize_text(relation_item.get('label')) or resource_id,
                subtitle=subtitle,
                group_key=group_key,
                is_landed=is_landed,
            ),
        )
    return rows


def _build_product_failure_mode_landing_maps(
    product_failure_mode: ProductFailureMode | None,
) -> dict[str, Any]:
    if not product_failure_mode:
        return {
            'interception_status_map': {},
            'handling_status_map': {},
            'observation_status_map': {},
            'huatuo_status_map': {},
        }
    return {
        'interception_status_map': {
            str(item.interception_strategy_id): bool(item.is_landed)
            for item in getattr(product_failure_mode, 'interception_landings', []).all()
        }
        if hasattr(getattr(product_failure_mode, 'interception_landings', None), 'all')
        else {},
        'handling_status_map': {
            str(item.handling_measure_id): bool(item.is_landed)
            for item in getattr(product_failure_mode, 'handling_landings', []).all()
        }
        if hasattr(getattr(product_failure_mode, 'handling_landings', None), 'all')
        else {},
        'observation_status_map': {
            str(item.observation_method_id): bool(item.is_landed)
            for item in getattr(product_failure_mode, 'observation_landings', []).all()
        }
        if hasattr(getattr(product_failure_mode, 'observation_landings', None), 'all')
        else {},
        'huatuo_status_map': {
            str(item.huatuo_diagnosis_id): bool(item.is_landed)
            for item in getattr(product_failure_mode, 'huatuo_landings', []).all()
        }
        if hasattr(getattr(product_failure_mode, 'huatuo_landings', None), 'all')
        else {},
    }


def _collect_task_landing_resource_rows(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = dict(payload or {})
    return [
        *list(payload.get('interception_rows') or []),
        *list(payload.get('handling_rows') or []),
        *list(payload.get('observation_rows') or []),
        *list(payload.get('huatuo_rows') or []),
    ]


def _derive_task_failure_mode_is_landed(payload: dict[str, Any] | None) -> bool:
    resource_rows = _collect_task_landing_resource_rows(payload)
    if not resource_rows:
        return False
    return all(
        _normalize_optional_bool(item.get('is_landed')) is True
        for item in resource_rows
    )


def _normalize_task_landing_payload_for_item(
    item: dict[str, Any],
    *,
    existing_payload: dict[str, Any] | None = None,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(existing_payload or {})
    fallback_payload = dict(fallback_payload or {})
    normalized_payload = {
        'interception_rows': _normalize_task_landing_rows(
            item.get('interception_strategy_items') or [],
            payload.get('interception_rows'),
            fallback_status_map=fallback_payload.get('interception_status_map') or {},
            default_group_key='interception',
        ),
        'handling_rows': _normalize_task_landing_rows(
            item.get('handling_measure_items') or [],
            payload.get('handling_rows'),
            fallback_status_map=fallback_payload.get('handling_status_map') or {},
            default_group_key='handling',
            use_subtitle_group_key=True,
        ),
        'observation_rows': _normalize_task_landing_rows(
            item.get('observation_method_items') or [],
            payload.get('observation_rows'),
            fallback_status_map=fallback_payload.get('observation_status_map') or {},
            default_group_key='observation',
            use_subtitle_group_key=True,
        ),
        'huatuo_rows': _normalize_task_landing_rows(
            item.get('huatuo_diagnosis_items') or [],
            payload.get('huatuo_rows'),
            fallback_status_map=fallback_payload.get('huatuo_status_map') or {},
            default_group_key='huatuo',
        ),
    }
    normalized_payload['failure_mode_is_landed'] = _derive_task_failure_mode_is_landed(
        normalized_payload,
    )
    return normalized_payload


def _merge_task_landing_payload(
    existing_payload: dict[str, Any] | None,
    incoming_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(existing_payload or {})
    incoming_payload = dict(incoming_payload or {})
    merged.pop('failure_mode_is_landed', None)
    for key in LANDING_SECTION_KEYS:
        if key in incoming_payload:
            merged[key] = incoming_payload.get(key) or []
    return merged


def _summarize_task_landing_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    resource_rows = _collect_task_landing_resource_rows(payload)
    resource_total = len(resource_rows)
    landed_count = sum(
        1 for item in resource_rows if _normalize_optional_bool(item.get('is_landed')) is True
    )
    landing_completed = all(
        _normalize_optional_bool(item.get('is_landed')) is not None for item in resource_rows
    )
    return {
        'landing_completed': landing_completed,
        'failure_mode_is_landed': _derive_task_failure_mode_is_landed(
            payload,
        ),
        'landing_resource_total': resource_total,
        'landing_resource_landed_count': landed_count,
    }


def _resolve_task_failure_mode_edit_meta(
    task: FailureModeTask,
    failure_mode: FailureMode | None,
) -> tuple[bool, str | None]:
    if task.status != 'PROCESSING' or task.task_type == 'DELETE' or not failure_mode:
        return False, None
    if task.task_type == 'REVISE':
        return True, 'draft'
    if (
        task.task_type == 'CREATE'
        and failure_mode.source_type == FailureMode.SOURCE_TYPE_TASK_QUICK_CREATE
        and str(failure_mode.source_task_id or '') == str(task.id)
    ):
        return True, 'direct_update'
    return False, None


def _attach_task_failure_mode_edit_meta(
    task: FailureModeTask,
    failure_mode: FailureMode | None,
    item: dict[str, Any],
) -> dict[str, Any]:
    editable_in_task, task_edit_mode = _resolve_task_failure_mode_edit_meta(
        task,
        failure_mode,
    )
    item['editable_in_task'] = editable_in_task
    item['task_edit_mode'] = task_edit_mode
    return item


class FailureModeAccessPolicy:
    def __init__(self, user: User):
        self.user = user
        self.user_id = str(user.id)
        self.assignments = list(
            FailureModeRoleAssignment.objects.filter(user=user, is_active=True).select_related('product')
        )
        self.is_admin = bool(
            getattr(user, 'is_superuser', False)
            or user.core_roles.filter(code='fm_admin', status=True).exists()
            or any(item.role == FailureModeRoleAssignment.ROLE_FM_ADMIN for item in self.assignments)
        )
        self.version_product_ids: set[str] = set(
            FailureModeProduct.objects.filter(owner=user).values_list('id', flat=True)
        )
        self.feature_pairs: set[tuple[str, str]] = set()
        self.member_pairs: set[tuple[str, str]] = set()

        for item in self.assignments:
            if not item.product_id:
                continue
            if item.role == FailureModeRoleAssignment.ROLE_VERSION_SE:
                self.version_product_ids.add(str(item.product_id))
            elif item.role == FailureModeRoleAssignment.ROLE_FEATURE_SE and item.subsystem:
                self.feature_pairs.add((str(item.product_id), item.subsystem))
            elif item.role == FailureModeRoleAssignment.ROLE_MEMBER and item.subsystem:
                self.member_pairs.add((str(item.product_id), item.subsystem))

        self.scope_pairs = self.feature_pairs | self.member_pairs
        self.accessible_product_ids = self.version_product_ids | {
            product_id for product_id, _ in self.scope_pairs
        }

    def _scope_q(self, product_field: str, subsystem_field: str, include_member: bool = True) -> Q:
        pairs = self.feature_pairs | self.member_pairs if include_member else self.feature_pairs
        grouped: dict[str, set[str]] = defaultdict(set)
        for product_id, subsystem in pairs:
            grouped[product_id].add(subsystem)

        query = Q()
        for product_id, subsystems in grouped.items():
            query |= Q(**{product_field: product_id, f'{subsystem_field}__in': list(subsystems)})
        return query

    def filter_products(self, queryset):
        if self.is_admin:
            return queryset
        if not self.accessible_product_ids:
            return queryset.none()
        return queryset.filter(id__in=list(self.accessible_product_ids))

    def filter_product_failure_modes(self, queryset):
        if self.is_admin:
            return queryset
        query = Q()
        if self.version_product_ids:
            query |= Q(product_id__in=list(self.version_product_ids))
        scope_q = self._scope_q('product_id', 'subsystem')
        if scope_q.children:
            query |= scope_q
        return queryset.filter(query) if query.children else queryset.none()

    def filter_tasks(self, queryset):
        if self.is_admin:
            return queryset
        query = Q(assignee=self.user) | Q(current_processor=self.user)
        if self.version_product_ids:
            query |= Q(product_id__in=list(self.version_product_ids))
        scope_q = self._scope_q('product_id', 'subsystem')
        if scope_q.children:
            query |= scope_q
        return queryset.filter(query).distinct() if query.children else queryset.none()

    def can_view_product(self, product: FailureModeProduct) -> bool:
        return self.is_admin or str(product.id) in self.accessible_product_ids

    def can_manage_product_roles(self, product: FailureModeProduct) -> bool:
        return self.is_admin or str(product.id) in self.version_product_ids

    def can_view_product_roles(self, product: FailureModeProduct) -> bool:
        return self.can_view_product(product)

    def can_create_task(self, product: FailureModeProduct) -> bool:
        return self.is_admin or str(product.id) in self.version_product_ids

    def can_view_task(self, task: FailureModeTask) -> bool:
        if self.is_admin:
            return True
        if task.assignee_id and str(task.assignee_id) == self.user_id:
            return True
        if task.current_processor_id and str(task.current_processor_id) == self.user_id:
            return True
        if str(task.product_id) in self.version_product_ids:
            return True
        return (str(task.product_id), task.subsystem or '') in self.scope_pairs

    def can_accept_task(self, task: FailureModeTask) -> bool:
        return bool(task.assignee_id and str(task.assignee_id) == self.user_id)

    def can_process_task(self, task: FailureModeTask) -> bool:
        return bool(task.assignee_id and str(task.assignee_id) == self.user_id)

    def can_recall_task(self, task: FailureModeTask) -> bool:
        return bool(task.assignee_id and str(task.assignee_id) == self.user_id)

    def can_reject_task(self, task: FailureModeTask) -> bool:
        return self.is_admin or str(task.product_id) in self.version_product_ids

    def can_close_task(self, task: FailureModeTask) -> bool:
        return self.can_reject_task(task)

    def can_reassign_task(self, task: FailureModeTask) -> bool:
        return self.can_close_task(task)

    def can_assign_feature_user(self, product: FailureModeProduct, subsystem: str, user_id: str) -> bool:
        return FailureModeRoleAssignment.objects.filter(
            product=product,
            role=FailureModeRoleAssignment.ROLE_FEATURE_SE,
            subsystem=subsystem,
            user_id=user_id,
            is_active=True,
        ).exists()

    def visible_subsystems(self, product: FailureModeProduct) -> list[str]:
        values: set[str] = set()
        if self.is_admin or str(product.id) in self.version_product_ids:
            values.update(
                FailureModeSubsystemConfig.objects.exclude(subsystem='').values_list('subsystem', flat=True)
            )
            values.update(
                FailureMode.objects.exclude(subsystem__isnull=True).exclude(subsystem='').values_list('subsystem', flat=True)
            )
            values.update(
                ProductFailureMode.objects.filter(product=product).exclude(subsystem='').values_list('subsystem', flat=True)
            )
            values.update(
                FailureModeTask.objects.filter(product=product).exclude(subsystem='').values_list('subsystem', flat=True)
            )
            values.update(
                FailureModeRoleAssignment.objects.filter(product=product, is_active=True)
                .exclude(subsystem='')
                .values_list('subsystem', flat=True)
            )
        else:
            values.update(
                FailureModeRoleAssignment.objects.filter(
                    product=product,
                    user=self.user,
                    is_active=True,
                )
                .exclude(subsystem='')
                .values_list('subsystem', flat=True)
            )
        return sorted({item for item in values if item})


class ProductWorkflowService:
    @classmethod
    def sync_projects(cls):
        existing_map = {
            str(item.project_id): item
            for item in FailureModeProduct.objects.select_related('owner').all()
        }
        products_to_create: list[FailureModeProduct] = []
        for project in Project.objects.all():
            product = existing_map.get(str(project.id))
            if product is None:
                products_to_create.append(FailureModeProduct(project=project))
        if products_to_create:
            FailureModeProduct.objects.bulk_create(products_to_create)
        for product in FailureModeProduct.objects.select_related('owner').all():
            cls._sync_owner_assignment(product)

    @classmethod
    def _sync_owner_assignment(cls, product: FailureModeProduct):
        FailureModeRoleAssignment.objects.filter(
            product=product,
            role=FailureModeRoleAssignment.ROLE_VERSION_SE,
        ).exclude(user=product.owner).delete()

        if not product.owner_id:
            FailureModeRoleAssignment.objects.filter(
                product=product,
                role=FailureModeRoleAssignment.ROLE_VERSION_SE,
            ).delete()
            return

        assignment, created = FailureModeRoleAssignment.objects.get_or_create(
            user=product.owner,
            product=product,
            role=FailureModeRoleAssignment.ROLE_VERSION_SE,
            subsystem='',
            defaults={'is_active': True, 'sys_creator': product.sys_modifier or product.sys_creator},
        )
        if not created and not assignment.is_active:
            assignment.is_active = True
            assignment.save(update_fields=['is_active', 'sys_update_datetime'])

    @classmethod
    def list_products(
        cls,
        user: User,
        owner_id: str | None = None,
        project_type: str | None = None,
    ) -> list[dict[str, Any]]:
        cls.sync_projects()
        policy = FailureModeAccessPolicy(user)
        queryset = FailureModeProduct.objects.select_related('project', 'owner').prefetch_related(
            Prefetch('role_assignments', queryset=FailureModeRoleAssignment.objects.filter(is_active=True).select_related('user'))
        )
        queryset = policy.filter_products(queryset)
        queryset = _filter_product_queryset_by_project_type(queryset, project_type)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        return [
            _serialize_product(item, policy)
            for item in queryset.order_by('project__name', '-sys_create_datetime')
        ]

    @classmethod
    def update_product_owner(cls, user: User, product_id: str, owner_id: str | None = None) -> dict[str, Any]:
        cls.sync_projects()
        policy = FailureModeAccessPolicy(user)
        product = get_object_or_404(
            FailureModeProduct.objects.select_related('project', 'owner').prefetch_related('role_assignments'),
            id=product_id,
        )
        _ensure_product_project_type(product, PLATFORM_PROJECT_TYPE)
        if not policy.can_manage_product_roles(product):
            raise HttpError(403, '只有管理员或当前产品主版本SE可以设置主版本SE。')
        product.owner = User.objects.get(id=owner_id) if owner_id else None
        product.sys_modifier = user
        product.save()
        cls._sync_owner_assignment(product)
        product.refresh_from_db()
        product = FailureModeProduct.objects.select_related('project', 'owner').prefetch_related(
            Prefetch('role_assignments', queryset=FailureModeRoleAssignment.objects.filter(is_active=True).select_related('user'))
        ).get(id=product.id)
        return _serialize_product(product, policy)

    @classmethod
    def list_product_failure_modes(
        cls,
        user: User,
        product_id: str,
        subsystem: str | None = None,
    ) -> list[dict[str, Any]]:
        cls.sync_projects()
        policy = FailureModeAccessPolicy(user)
        product = get_object_or_404(FailureModeProduct.objects.select_related('project', 'owner'), id=product_id)
        if not policy.can_view_product(product):
            raise HttpError(403, '无权查看当前产品基线。')

        queryset = ProductFailureMode.objects.filter(product_id=product_id).select_related('failure_mode')
        queryset = policy.filter_product_failure_modes(queryset)
        if subsystem:
            queryset = queryset.filter(subsystem=subsystem)
        return [_serialize_product_failure_mode(item) for item in queryset.order_by('subsystem', '-sys_create_datetime')]

    @classmethod
    def list_product_role_assignments(cls, user: User, product_id: str) -> list[dict[str, Any]]:
        cls.sync_projects()
        policy = FailureModeAccessPolicy(user)
        product = get_object_or_404(FailureModeProduct.objects.select_related('project', 'owner'), id=product_id)
        _ensure_product_project_type(product, PLATFORM_PROJECT_TYPE)
        if not policy.can_view_product_roles(product):
            raise HttpError(403, '无权查看当前产品角色配置。')

        queryset = FailureModeRoleAssignment.objects.filter(product=product, is_active=True).select_related('user')
        visible_rows = _filter_visible_role_assignments(product, list(queryset), policy)
        return [
            _serialize_role_assignment(item)
            for item in sorted(
                visible_rows,
                key=lambda item: (
                    item.role,
                    item.subsystem,
                    getattr(item.user, 'name', '') or '',
                    item.user.username,
                ),
            )
        ]

    @classmethod
    @transaction.atomic
    def save_product_role_assignments(
        cls,
        user: User,
        product_id: str,
        assignments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        cls.sync_projects()
        policy = FailureModeAccessPolicy(user)
        product = get_object_or_404(FailureModeProduct.objects.select_related('project', 'owner'), id=product_id)
        _ensure_product_project_type(product, PLATFORM_PROJECT_TYPE)
        if not policy.can_manage_product_roles(product):
            raise HttpError(403, '无权管理当前产品角色配置。')

        rows: list[FailureModeRoleAssignment] = []
        seen: set[tuple[str, str, str]] = set()
        allowed_roles = {
            FailureModeRoleAssignment.ROLE_FEATURE_SE,
            FailureModeRoleAssignment.ROLE_MEMBER,
        }

        for raw_item in assignments:
            role = _normalize_text(raw_item.get('role'))
            subsystem = _normalize_text(raw_item.get('subsystem'))
            user_id = _normalize_text(raw_item.get('user_id'))
            if role not in allowed_roles:
                raise HttpError(422, f'不支持的产品角色: {role}')
            if not subsystem:
                raise HttpError(422, '特性SE和普通成员必须绑定子系统。')
            if not user_id:
                raise HttpError(422, '角色配置缺少用户。')
            cache_key = (user_id, role, subsystem)
            if cache_key in seen:
                continue
            seen.add(cache_key)
            rows.append(
                FailureModeRoleAssignment(
                    user_id=user_id,
                    product=product,
                    role=role,
                    subsystem=subsystem,
                    is_active=True,
                    sys_creator=user,
                    sys_modifier=user,
                )
            )

        missing_user_ids = set(item.user_id for item in rows) - set(
            User.objects.filter(id__in=[item.user_id for item in rows]).values_list('id', flat=True)
        )
        if missing_user_ids:
            raise HttpError(422, f'用户不存在: {sorted(missing_user_ids)[0]}')

        FailureModeRoleAssignment.objects.filter(
            product=product,
            role__in=list(allowed_roles),
        ).delete()
        if rows:
            FailureModeRoleAssignment.objects.bulk_create(rows)

        queryset = FailureModeRoleAssignment.objects.filter(product=product, is_active=True).select_related('user')
        return [
            _serialize_role_assignment(item)
            for item in queryset.order_by('role', 'subsystem', 'user__name', 'user__username')
        ]

    @classmethod
    def list_visible_subsystems(cls, user: User, product_id: str) -> list[dict[str, str]]:
        cls.sync_projects()
        policy = FailureModeAccessPolicy(user)
        product = get_object_or_404(FailureModeProduct, id=product_id)
        if not policy.can_view_product(product):
            raise HttpError(403, '无权查看当前产品。')
        return [{'label': item, 'value': item} for item in policy.visible_subsystems(product)]


class TaskWorkflowService:
    @classmethod
    def _task_queryset(cls):
        return FailureModeTask.objects.select_related(
            'product__project',
            'product__owner',
            'creator',
            'assignee',
            'current_processor',
        )

    @classmethod
    def _task_log_queryset(cls):
        return FailureModeTaskLog.objects.select_related('operator')

    @classmethod
    def _get_task_or_404(cls, task_id: str) -> FailureModeTask:
        return get_object_or_404(cls._task_queryset(), id=task_id)

    @classmethod
    def _log(
        cls,
        *,
        task: FailureModeTask,
        operator: User,
        action: str,
        from_status: str = '',
        to_status: str = '',
        note: str = '',
        extra_data: dict[str, Any] | None = None,
    ):
        FailureModeTaskLog.objects.create(
            task=task,
            operator=operator,
            action=action,
            from_status=from_status,
            to_status=to_status,
            note=note,
            extra_data=extra_data or {},
            sys_creator=operator,
            sys_modifier=operator,
        )

    @classmethod
    def _resolve_failure_mode_status_for_task(cls, task: FailureModeTask) -> str | None:
        return TASK_STATUS_FAILURE_MODE_STATUS_MAP.get(task.status)

    @classmethod
    def _sync_task_created_failure_mode_status(cls, task: FailureModeTask):
        status = cls._resolve_failure_mode_status_for_task(task)
        if not status:
            return
        FailureMode.objects.filter(
            source_type=FailureMode.SOURCE_TYPE_TASK_QUICK_CREATE,
            source_task=task,
        ).update(status=status)

    @classmethod
    def _load_baseline_failure_mode_ids(
        cls,
        product: FailureModeProduct,
        subsystem: str,
    ) -> list[str]:
        return [
            str(item)
            for item in ProductFailureMode.objects.filter(
                product=product,
                subsystem=subsystem,
            )
            .order_by('sys_create_datetime', 'id')
            .values_list('failure_mode_id', flat=True)
        ]

    @classmethod
    def _get_task_selected_failure_mode_ids(cls, task: FailureModeTask) -> list[str]:
        return [
            str(item)
            for item in TaskFailureMode.objects.filter(task=task)
            .order_by('sys_create_datetime', 'id')
            .values_list('failure_mode_id', flat=True)
        ]

    @classmethod
    def _product_failure_mode_queryset(cls):
        return ProductFailureMode.objects.select_related(
            'failure_mode',
            'product__project',
            'product__owner',
        ).prefetch_related(
            'interception_landings',
            'handling_landings',
            'observation_landings',
            'huatuo_landings',
        )

    @classmethod
    def _get_product_failure_mode_binding(
        cls,
        task: FailureModeTask,
        failure_mode_id: str,
    ) -> ProductFailureMode | None:
        return cls._product_failure_mode_queryset().filter(
            product=task.product,
            subsystem=task.subsystem,
            failure_mode_id=failure_mode_id,
        ).first()

    @classmethod
    def _get_task_failure_mode_binding_or_404(
        cls,
        task: FailureModeTask,
        failure_mode_id: str,
    ) -> TaskFailureMode:
        return get_object_or_404(
            TaskFailureMode.objects.select_related('failure_mode'),
            task=task,
            failure_mode_id=failure_mode_id,
        )

    @classmethod
    def _serialize_task_failure_mode_landing(
        cls,
        task: FailureModeTask,
        failure_mode: FailureMode,
        *,
        item: dict[str, Any] | None = None,
        existing_payload: dict[str, Any] | None = None,
        product_failure_mode: ProductFailureMode | None = None,
    ) -> dict[str, Any]:
        current_item = item or failure_mode_services._serialize_failure_mode(failure_mode)
        normalized_payload = _normalize_task_landing_payload_for_item(
            current_item,
            existing_payload=existing_payload,
            fallback_payload=_build_product_failure_mode_landing_maps(
                product_failure_mode,
            ),
        )
        summary = _summarize_task_landing_payload(normalized_payload)
        return {
            'task_id': str(task.id),
            'failure_mode_id': str(failure_mode.id),
            'failure_mode_brief': current_item.get('brief') or failure_mode.brief,
            'failure_mode_is_landed': summary['failure_mode_is_landed'],
            'landing_completed': summary['landing_completed'],
            'interception_rows': normalized_payload['interception_rows'],
            'handling_rows': normalized_payload['handling_rows'],
            'observation_rows': normalized_payload['observation_rows'],
            'huatuo_rows': normalized_payload['huatuo_rows'],
        }

    @classmethod
    def _attach_task_landing_summary(
        cls,
        item: dict[str, Any],
        landing_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        item.update(_summarize_task_landing_payload(landing_payload))
        return item

    @classmethod
    def _build_task_landing_payload_for_binding(
        cls,
        task: FailureModeTask,
        failure_mode: FailureMode | dict[str, Any],
        *,
        existing_payload: dict[str, Any] | None = None,
        product_failure_mode: ProductFailureMode | None = None,
    ) -> dict[str, Any]:
        current_item = (
            failure_mode
            if isinstance(failure_mode, dict)
            else failure_mode_services._serialize_failure_mode(failure_mode)
        )
        return _normalize_task_landing_payload_for_item(
            current_item,
            existing_payload=existing_payload,
            fallback_payload=_build_product_failure_mode_landing_maps(
                product_failure_mode,
            ),
        )

    @classmethod
    def _validate_task_landing_payloads(
        cls,
        task: FailureModeTask,
    ) -> tuple[list[str], dict[str, dict[str, Any]]]:
        active_drafts = {
            str(item.failure_mode_id): item
            for item in FailureModeTaskDraft.objects.filter(task=task, is_active=True)
        }
        normalized_payloads: dict[str, dict[str, Any]] = {}
        incomplete_briefs: list[str] = []
        for binding in (
            TaskFailureMode.objects.filter(task=task)
            .select_related('failure_mode')
            .order_by('sys_create_datetime', 'id')
        ):
            failure_mode = binding.failure_mode
            draft = active_drafts.get(str(binding.failure_mode_id))
            item = (
                failure_mode_services.merge_failure_mode_snapshot(
                    failure_mode,
                    draft.draft_payload_json,
                )
                if draft
                else failure_mode_services._serialize_failure_mode(failure_mode)
            )
            normalized_payload = _normalize_task_landing_payload_for_item(
                item,
                existing_payload=binding.landing_payload_json,
            )
            normalized_payloads[str(binding.failure_mode_id)] = normalized_payload
            if not _summarize_task_landing_payload(normalized_payload)['landing_completed']:
                incomplete_briefs.append(failure_mode.brief)
        return incomplete_briefs, normalized_payloads

    @classmethod
    def _sync_product_failure_mode_landings(
        cls,
        product_failure_mode: ProductFailureMode,
        landing_payload: dict[str, Any],
        operator: User,
    ):
        ProductFailureModeInterceptionLanding.objects.filter(
            product_failure_mode=product_failure_mode,
        ).delete()
        ProductFailureModeHandlingLanding.objects.filter(
            product_failure_mode=product_failure_mode,
        ).delete()
        ProductFailureModeObservationLanding.objects.filter(
            product_failure_mode=product_failure_mode,
        ).delete()
        ProductFailureModeHuatuoLanding.objects.filter(
            product_failure_mode=product_failure_mode,
        ).delete()

        interception_rows = [
            ProductFailureModeInterceptionLanding(
                product_failure_mode=product_failure_mode,
                interception_strategy_id=item['resource_id'],
                is_landed=bool(item['is_landed']),
                sys_creator=operator,
                sys_modifier=operator,
            )
            for item in landing_payload.get('interception_rows') or []
        ]
        handling_rows = [
            ProductFailureModeHandlingLanding(
                product_failure_mode=product_failure_mode,
                handling_measure_id=item['resource_id'],
                is_landed=bool(item['is_landed']),
                sys_creator=operator,
                sys_modifier=operator,
            )
            for item in landing_payload.get('handling_rows') or []
        ]
        observation_rows = [
            ProductFailureModeObservationLanding(
                product_failure_mode=product_failure_mode,
                observation_method_id=item['resource_id'],
                is_landed=bool(item['is_landed']),
                sys_creator=operator,
                sys_modifier=operator,
            )
            for item in landing_payload.get('observation_rows') or []
        ]
        huatuo_rows = [
            ProductFailureModeHuatuoLanding(
                product_failure_mode=product_failure_mode,
                huatuo_diagnosis_id=item['resource_id'],
                is_landed=bool(item['is_landed']),
                sys_creator=operator,
                sys_modifier=operator,
            )
            for item in landing_payload.get('huatuo_rows') or []
        ]
        if interception_rows:
            ProductFailureModeInterceptionLanding.objects.bulk_create(
                interception_rows,
            )
        if handling_rows:
            ProductFailureModeHandlingLanding.objects.bulk_create(handling_rows)
        if observation_rows:
            ProductFailureModeObservationLanding.objects.bulk_create(
                observation_rows,
            )
        if huatuo_rows:
            ProductFailureModeHuatuoLanding.objects.bulk_create(huatuo_rows)

    @classmethod
    def _sync_product_failure_mode_landing_cache(
        cls,
        product_failure_mode: ProductFailureMode,
        landing_payload: dict[str, Any] | None,
        operator: User,
    ):
        derived_is_landed = _derive_task_failure_mode_is_landed(landing_payload)
        product_failure_mode.is_landed = derived_is_landed
        product_failure_mode.sys_modifier = operator
        product_failure_mode.save(update_fields=['is_landed', 'sys_modifier', 'sys_update_datetime'])

    @classmethod
    def _persist_binding_landing_payload(
        cls,
        task: FailureModeTask,
        failure_mode_id: str,
        normalized_payload: dict[str, Any],
        operator: User,
    ):
        TaskFailureMode.objects.filter(
            task=task,
            failure_mode_id=failure_mode_id,
        ).update(
            landing_payload_json=normalized_payload,
            sys_modifier_id=operator.id,
        )

    @classmethod
    def _ensure_revise_task_initialized(
        cls,
        task: FailureModeTask,
        operator: User | None = None,
    ) -> FailureModeTask:
        if task.task_type != 'REVISE':
            return task
        has_workset = TaskFailureMode.objects.filter(task=task).exists()
        if task.baseline_snapshot_ids or has_workset:
            return task

        baseline_ids = cls._load_baseline_failure_mode_ids(task.product, task.subsystem)
        if not baseline_ids:
            return task

        task.baseline_snapshot_ids = baseline_ids
        if operator:
            task.sys_modifier = operator
        task.save()
        product_failure_mode_map = {
            str(item.failure_mode_id): item
            for item in cls._product_failure_mode_queryset().filter(
                product=task.product,
                subsystem=task.subsystem,
                failure_mode_id__in=baseline_ids,
            )
        }
        TaskFailureMode.objects.bulk_create(
            [
                TaskFailureMode(
                    task=task,
                    failure_mode_id=failure_mode_id,
                    landing_payload_json=cls._build_task_landing_payload_for_binding(
                        task,
                        product_failure_mode_map[str(failure_mode_id)].failure_mode,
                        product_failure_mode=product_failure_mode_map.get(
                            str(failure_mode_id),
                        ),
                    ),
                    sys_creator=operator or task.creator or task.sys_creator,
                    sys_modifier=operator or task.creator or task.sys_creator,
                )
                for failure_mode_id in baseline_ids
                if str(failure_mode_id) in product_failure_mode_map
            ]
        )
        return cls._get_task_or_404(str(task.id))

    @classmethod
    def _build_task_failure_mode_rows(cls, task: FailureModeTask) -> list[dict[str, Any]]:
        selected_ids = cls._get_task_selected_failure_mode_ids(task)
        selected_set = set(selected_ids)
        active_drafts = {
            str(item.failure_mode_id): item
            for item in FailureModeTaskDraft.objects.filter(task=task, is_active=True)
        }

        if task.task_type == 'DELETE':
            baseline_relations = (
                cls._product_failure_mode_queryset()
                .filter(product=task.product, subsystem=task.subsystem)
                .order_by('sys_create_datetime', 'id')
            )
            rows: list[dict[str, Any]] = []
            for relation in baseline_relations:
                if not relation.failure_mode_id:
                    continue
                item = failure_mode_services._serialize_failure_mode(relation.failure_mode)
                item['task_change_type'] = (
                    'delete_candidate'
                    if str(relation.failure_mode_id) in selected_set
                    else 'baseline'
                )
                item['has_task_draft'] = False
                cls._attach_task_landing_summary(
                    item,
                    cls._build_task_landing_payload_for_binding(
                        task,
                        relation.failure_mode,
                        product_failure_mode=relation,
                    ),
                )
                _attach_task_failure_mode_edit_meta(task, relation.failure_mode, item)
                rows.append(item)
            return rows

        bindings = (
            TaskFailureMode.objects.filter(task=task)
            .select_related('failure_mode')
            .order_by('sys_create_datetime', 'id')
        )
        baseline_snapshot_set = {str(item) for item in (task.baseline_snapshot_ids or [])}
        rows = []
        for binding in bindings:
            failure_mode = binding.failure_mode
            draft = active_drafts.get(str(binding.failure_mode_id))
            item = (
                failure_mode_services.merge_failure_mode_snapshot(
                    failure_mode,
                    draft.draft_payload_json,
                )
                if draft
                else failure_mode_services._serialize_failure_mode(failure_mode)
            )
            if task.task_type == 'REVISE' and draft:
                change_type = 'edited'
            elif str(binding.failure_mode_id) in baseline_snapshot_set:
                change_type = 'baseline'
            else:
                change_type = 'new'
            landing_payload = _normalize_task_landing_payload_for_item(
                item,
                existing_payload=binding.landing_payload_json,
            )
            item['task_change_type'] = change_type
            item['has_task_draft'] = bool(draft)
            cls._attach_task_landing_summary(item, landing_payload)
            _attach_task_failure_mode_edit_meta(task, failure_mode, item)
            rows.append(item)
        return rows

    @classmethod
    def _apply_revise_drafts(cls, task: FailureModeTask, operator: User):
        draft_queryset = FailureModeTaskDraft.objects.filter(task=task, is_active=True).select_related('failure_mode')
        for draft in draft_queryset:
            failure_mode_services.apply_failure_mode_snapshot(
                draft.failure_mode,
                draft.draft_payload_json or {},
                operator,
            )
        draft_queryset.update(is_active=False, sys_modifier_id=operator.id)

    @classmethod
    def list_tasks(
        cls,
        user: User,
        *,
        status: str | None = None,
        product_id: str | None = None,
    ) -> list[dict[str, Any]]:
        ProductWorkflowService.sync_projects()
        policy = FailureModeAccessPolicy(user)
        queryset = policy.filter_tasks(cls._task_queryset())
        if status:
            queryset = queryset.filter(status=status)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return [_serialize_task(item, policy) for item in queryset.order_by('-sys_create_datetime')]

    @classmethod
    def get_task_detail(cls, user: User, task_id: str) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_view_task(task):
            raise HttpError(403, '无权查看当前任务。')
        return _serialize_task(task, policy)

    @classmethod
    @transaction.atomic
    def create_task(cls, user: User, data: dict[str, Any]) -> dict[str, Any]:
        ProductWorkflowService.sync_projects()
        policy = FailureModeAccessPolicy(user)
        product = get_object_or_404(FailureModeProduct.objects.select_related('project', 'owner'), id=data['product_id'])
        if not policy.can_create_task(product):
            raise HttpError(403, '只有该产品主版本SE或管理员可以发起任务。')

        task_type = _normalize_text(data.get('task_type'))
        subsystem = _normalize_text(data.get('subsystem'))
        assignee_id = _normalize_text(data.get('assignee_id'))
        if task_type not in {'CREATE', 'REVISE', 'DELETE'}:
            raise HttpError(422, '任务类型非法。')
        if not subsystem:
            raise HttpError(422, '子系统不能为空。')
        if not assignee_id:
            raise HttpError(422, '责任人不能为空。')
        if not policy.can_assign_feature_user(product, subsystem, assignee_id):
            raise HttpError(422, '责任人必须是当前产品子系统下的特性SE。')

        baseline_ids = cls._load_baseline_failure_mode_ids(product, subsystem)
        if task_type in {'REVISE', 'DELETE'} and not baseline_ids:
            raise HttpError(422, '当前产品子系统下暂无已生效基线，不能发起修订或删除任务。')

        task = FailureModeTask.objects.create(
            name=_normalize_text(data.get('name')),
            task_type=task_type,
            status='CREATED',
            product=product,
            subsystem=subsystem,
            creator=user,
            assignee_id=assignee_id,
            current_processor_id=assignee_id,
            baseline_snapshot_ids=baseline_ids if task_type == 'REVISE' else [],
            sys_creator=user,
            sys_modifier=user,
        )
        if task_type == 'REVISE' and baseline_ids:
            product_failure_mode_map = {
                str(item.failure_mode_id): item
                for item in cls._product_failure_mode_queryset().filter(
                    product=product,
                    subsystem=subsystem,
                    failure_mode_id__in=baseline_ids,
                )
            }
            TaskFailureMode.objects.bulk_create(
                [
                    TaskFailureMode(
                        task=task,
                        failure_mode_id=failure_mode_id,
                        landing_payload_json=cls._build_task_landing_payload_for_binding(
                            task,
                            product_failure_mode_map[str(failure_mode_id)].failure_mode,
                            product_failure_mode=product_failure_mode_map.get(
                                str(failure_mode_id),
                            ),
                        ),
                        sys_creator=user,
                        sys_modifier=user,
                    )
                    for failure_mode_id in baseline_ids
                    if str(failure_mode_id) in product_failure_mode_map
                ]
            )
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_CREATE,
            to_status=task.status,
            note='创建任务',
            extra_data={
                'assignee_id': assignee_id,
                'assignee_info': _format_user(task.assignee),
                'baseline_failure_mode_count': len(baseline_ids),
            },
        )
        task = cls._get_task_or_404(str(task.id))
        return _serialize_task(task, FailureModeAccessPolicy(user))

    @classmethod
    def get_task_failure_modes(cls, user: User, task_id: str) -> list[dict[str, Any]]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_view_task(task):
            raise HttpError(403, '无权查看当前任务。')
        task = cls._ensure_revise_task_initialized(task, user)
        return cls._build_task_failure_mode_rows(task)

    @classmethod
    def get_task_failure_mode_landing(
        cls,
        user: User,
        task_id: str,
        failure_mode_id: str,
    ) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        task = cls._ensure_revise_task_initialized(task, user)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_view_task(task):
            raise HttpError(403, '无权查看当前任务。')
        product_failure_mode = cls._get_product_failure_mode_binding(task, failure_mode_id)
        if task.task_type == 'DELETE':
            if not product_failure_mode or not product_failure_mode.failure_mode:
                raise HttpError(404, '当前故障模式不存在于产品基线中。')
            return cls._serialize_task_failure_mode_landing(
                task,
                product_failure_mode.failure_mode,
                existing_payload=None,
                product_failure_mode=product_failure_mode,
            )

        binding = cls._get_task_failure_mode_binding_or_404(task, failure_mode_id)
        draft = FailureModeTaskDraft.objects.filter(
            task=task,
            failure_mode_id=failure_mode_id,
            is_active=True,
        ).first()
        current_item = (
            failure_mode_services.merge_failure_mode_snapshot(
                binding.failure_mode,
                draft.draft_payload_json,
            )
            if draft
            else None
        )
        landing = cls._serialize_task_failure_mode_landing(
            task,
            binding.failure_mode,
            item=current_item,
            existing_payload=binding.landing_payload_json,
            product_failure_mode=product_failure_mode,
        )
        return landing

    @classmethod
    @transaction.atomic
    def save_task_failure_mode_landing(
        cls,
        user: User,
        task_id: str,
        failure_mode_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        task = cls._ensure_revise_task_initialized(task, user)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_process_task(task):
            raise HttpError(403, '只有当前任务责任人可以保存落地配置。')
        if task.status != 'PROCESSING':
            raise HttpError(422, '只有梳理/修订中的任务可以保存落地配置。')
        if task.task_type == 'DELETE':
            raise HttpError(422, '删除任务不支持维护落地配置。')

        binding = cls._get_task_failure_mode_binding_or_404(task, failure_mode_id)
        draft = FailureModeTaskDraft.objects.filter(
            task=task,
            failure_mode_id=failure_mode_id,
            is_active=True,
        ).first()
        current_item = (
            failure_mode_services.merge_failure_mode_snapshot(
                binding.failure_mode,
                draft.draft_payload_json,
            )
            if draft
            else binding.failure_mode
        )
        merged_payload = _merge_task_landing_payload(
            binding.landing_payload_json,
            payload,
        )
        normalized_payload = cls._build_task_landing_payload_for_binding(
            task,
            current_item,
            existing_payload=merged_payload,
            product_failure_mode=cls._get_product_failure_mode_binding(
                task,
                failure_mode_id,
            ),
        )
        cls._persist_binding_landing_payload(
            task,
            failure_mode_id,
            normalized_payload,
            user,
        )
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_SAVE_LANDING,
            from_status=task.status,
            to_status=task.status,
            note=f'保存落地配置: {binding.failure_mode.brief}',
            extra_data={'failure_mode_id': str(binding.failure_mode_id)},
        )
        summary = _summarize_task_landing_payload(normalized_payload)
        return {
            'task_id': str(task.id),
            'failure_mode_id': str(binding.failure_mode_id),
            'failure_mode_brief': binding.failure_mode.brief,
            'failure_mode_is_landed': summary['failure_mode_is_landed'],
            'landing_completed': summary['landing_completed'],
            'interception_rows': normalized_payload['interception_rows'],
            'handling_rows': normalized_payload['handling_rows'],
            'observation_rows': normalized_payload['observation_rows'],
            'huatuo_rows': normalized_payload['huatuo_rows'],
        }

    @classmethod
    @transaction.atomic
    def accept_task(cls, user: User, task_id: str) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_accept_task(task):
            raise HttpError(403, '只有当前任务责任人可以接收任务。')
        if task.status != 'CREATED':
            raise HttpError(422, '只有创建态任务可以接收。')
        from_status = task.status
        task.status = 'PROCESSING'
        task.accepted_at = timezone.now()
        task.current_processor_id = task.assignee_id
        task.sys_modifier = user
        task.save()
        cls._sync_task_created_failure_mode_status(task)
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_ACCEPT,
            from_status=from_status,
            to_status=task.status,
            note='接收任务',
        )
        return _serialize_task(cls._get_task_or_404(task_id), FailureModeAccessPolicy(user))

    @classmethod
    @transaction.atomic
    def bind_failure_modes(cls, user: User, task_id: str, failure_mode_ids: list[str]):
        task = cls._get_task_or_404(task_id)
        task = cls._ensure_revise_task_initialized(task, user)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_process_task(task):
            raise HttpError(403, '只有当前任务责任人可以维护任务故障模式。')
        if task.status != 'PROCESSING':
            raise HttpError(422, '只有梳理/修订中的任务可以绑定故障模式。')

        normalized_ids = _normalize_id_list(failure_mode_ids)
        found_ids = set(FailureMode.objects.filter(id__in=normalized_ids).values_list('id', flat=True))
        missing_ids = [item_id for item_id in normalized_ids if item_id not in found_ids]
        if missing_ids:
            raise HttpError(422, f'故障模式不存在: {missing_ids[0]}')

        if task.task_type == 'DELETE':
            baseline_ids = set(cls._load_baseline_failure_mode_ids(task.product, task.subsystem))
            invalid_ids = [item_id for item_id in normalized_ids if item_id not in baseline_ids]
            if invalid_ids:
                raise HttpError(422, '删除任务只能选择当前产品子系统已生效基线中的故障模式。')

        existing_binding_map = {
            str(item.failure_mode_id): item.landing_payload_json or {}
            for item in TaskFailureMode.objects.filter(task=task)
        }
        product_failure_mode_map = {
            str(item.failure_mode_id): item
            for item in cls._product_failure_mode_queryset().filter(
                product=task.product,
                subsystem=task.subsystem,
                failure_mode_id__in=normalized_ids,
            )
        }
        failure_mode_map = {
            str(item.id): item
            for item in failure_mode_services._failure_mode_queryset().filter(
                id__in=normalized_ids,
            )
        }
        TaskFailureMode.objects.filter(task=task).delete()
        if normalized_ids:
            TaskFailureMode.objects.bulk_create(
                [
                    TaskFailureMode(
                        task=task,
                        failure_mode_id=item_id,
                        landing_payload_json=(
                            cls._build_task_landing_payload_for_binding(
                                task,
                                failure_mode_map[item_id],
                                existing_payload=existing_binding_map.get(item_id),
                                product_failure_mode=product_failure_mode_map.get(
                                    item_id,
                                ),
                            )
                            if task.task_type != 'DELETE'
                            else {}
                        ),
                        sys_creator=user,
                        sys_modifier=user,
                    )
                    for item_id in normalized_ids
                    if item_id in failure_mode_map
                ]
            )

        if task.task_type == 'REVISE':
            FailureModeTaskDraft.objects.filter(task=task, is_active=True).exclude(
                failure_mode_id__in=normalized_ids,
            ).update(is_active=False, sys_modifier_id=user.id)

        bind_note = (
            f'选择待删除故障模式 {len(normalized_ids)} 条'
            if task.task_type == 'DELETE'
            else f'绑定故障模式 {len(normalized_ids)} 条'
        )
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_BIND_FAILURE_MODES,
            from_status=task.status,
            to_status=task.status,
            note=bind_note,
            extra_data={'failure_mode_ids': normalized_ids},
        )

    @classmethod
    @transaction.atomic
    def save_failure_mode_draft(
        cls,
        user: User,
        task_id: str,
        failure_mode_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        task = cls._ensure_revise_task_initialized(task, user)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_process_task(task):
            raise HttpError(403, '只有当前任务责任人可以保存修订草稿。')
        if task.status != 'PROCESSING':
            raise HttpError(422, '只有梳理/修订中的任务可以保存修订草稿。')
        if task.task_type != 'REVISE':
            raise HttpError(422, '只有修订任务支持编辑已有故障模式草稿。')

        if not TaskFailureMode.objects.filter(task=task, failure_mode_id=failure_mode_id).exists():
            raise HttpError(422, '当前故障模式未加入该任务工作集。')

        failure_mode = get_object_or_404(
            failure_mode_services._failure_mode_queryset(),
            id=failure_mode_id,
        )
        draft_payload = failure_mode_services.prepare_failure_mode_task_draft_payload(
            failure_mode,
            payload,
            user,
        )

        draft = FailureModeTaskDraft.objects.filter(task=task, failure_mode=failure_mode).first()
        if draft:
            draft.draft_payload_json = draft_payload
            draft.is_active = True
            draft.sys_modifier = user
            draft.save()
        else:
            FailureModeTaskDraft.objects.create(
                task=task,
                failure_mode=failure_mode,
                draft_payload_json=draft_payload,
                is_active=True,
                sys_creator=user,
                sys_modifier=user,
            )

        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_SAVE_DRAFT,
            from_status=task.status,
            to_status=task.status,
            note=f'保存修订草稿: {failure_mode.brief}',
            extra_data={'failure_mode_id': str(failure_mode.id)},
        )

        item = failure_mode_services.merge_failure_mode_snapshot(failure_mode, draft_payload)
        landing_payload = _normalize_task_landing_payload_for_item(
            item,
            existing_payload=TaskFailureMode.objects.filter(
                task=task,
                failure_mode_id=failure_mode_id,
            )
            .values_list('landing_payload_json', flat=True)
            .first()
            or {},
        )
        cls._persist_binding_landing_payload(task, failure_mode_id, landing_payload, user)
        item['task_change_type'] = 'edited'
        item['has_task_draft'] = True
        cls._attach_task_landing_summary(item, landing_payload)
        _attach_task_failure_mode_edit_meta(task, failure_mode, item)
        return item

    @classmethod
    @transaction.atomic
    def update_task_created_failure_mode(
        cls,
        user: User,
        task_id: str,
        failure_mode_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_process_task(task):
            raise HttpError(403, '只有当前任务责任人可以编辑任务内故障模式。')
        if task.status != 'PROCESSING':
            raise HttpError(422, '只有梳理/修订中的任务可以编辑故障模式。')
        if task.task_type != 'CREATE':
            raise HttpError(422, '只有创建任务支持直接编辑任务内新增故障模式。')
        if not TaskFailureMode.objects.filter(task=task, failure_mode_id=failure_mode_id).exists():
            raise HttpError(422, '当前故障模式未加入该任务工作集。')

        failure_mode = get_object_or_404(
            failure_mode_services._failure_mode_queryset(),
            id=failure_mode_id,
        )
        editable_in_task, task_edit_mode = _resolve_task_failure_mode_edit_meta(
            task,
            failure_mode,
        )
        if not editable_in_task or task_edit_mode != 'direct_update':
            raise HttpError(422, '当前故障模式不支持在创建任务中直接编辑。')

        filtered_payload = {
            key: value
            for key, value in dict(payload or {}).items()
            if key in failure_mode_services.FAILURE_MODE_TASK_DRAFT_ALLOWED_FIELDS
        }
        item = failure_mode_services.apply_failure_mode_snapshot(
            failure_mode,
            filtered_payload,
            user,
        )
        landing_payload = _normalize_task_landing_payload_for_item(
            item,
            existing_payload=TaskFailureMode.objects.filter(
                task=task,
                failure_mode_id=failure_mode_id,
            )
            .values_list('landing_payload_json', flat=True)
            .first()
            or {},
        )
        cls._persist_binding_landing_payload(task, failure_mode_id, landing_payload, user)
        item['task_change_type'] = 'new'
        item['has_task_draft'] = False
        cls._attach_task_landing_summary(item, landing_payload)
        _attach_task_failure_mode_edit_meta(task, failure_mode, item)

        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_EDIT_FAILURE_MODE,
            from_status=task.status,
            to_status=task.status,
            note=f'编辑任务内故障模式: {item.get("brief") or failure_mode.brief}',
            extra_data={'failure_mode_id': str(failure_mode.id)},
        )
        return item

    @classmethod
    @transaction.atomic
    def delete_failure_mode_draft(cls, user: User, task_id: str, failure_mode_id: str):
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_process_task(task):
            raise HttpError(403, '只有当前任务责任人可以撤销修订草稿。')
        if task.status != 'PROCESSING':
            raise HttpError(422, '只有梳理/修订中的任务可以撤销修订草稿。')
        if task.task_type != 'REVISE':
            raise HttpError(422, '只有修订任务支持撤销修订草稿。')

        draft = FailureModeTaskDraft.objects.filter(
            task=task,
            failure_mode_id=failure_mode_id,
            is_active=True,
        ).first()
        if draft:
            draft.is_active = False
            draft.sys_modifier = user
            draft.save()
            cls._log(
                task=task,
                operator=user,
                action=FailureModeTaskLog.ACTION_DELETE_DRAFT,
                from_status=task.status,
                to_status=task.status,
                note='撤销修订草稿',
                extra_data={'failure_mode_id': failure_mode_id},
            )

    @classmethod
    @transaction.atomic
    def quick_create_failure_mode(cls, request, task_id: str, data) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(request.auth)
        if not policy.can_process_task(task):
            raise HttpError(403, '只有当前任务责任人可以快速新增故障模式。')
        if task.status != 'PROCESSING':
            raise HttpError(422, '只有梳理/修订中的任务可以快速新增故障模式。')

        payload = data.dict()
        if not _normalize_text(payload.get('subsystem')):
            payload['subsystem'] = task.subsystem
        payload['status'] = cls._resolve_failure_mode_status_for_task(task)
        payload['source_type'] = FailureMode.SOURCE_TYPE_TASK_QUICK_CREATE
        payload['source_task_id'] = str(task.id)
        if not _normalize_id_list(payload.get('author_ids')):
            payload['author_ids'] = [str(request.auth.id)]
        shim = SimpleNamespace(dict=lambda **kwargs: payload)
        created_item = failure_mode_services.create_failure_mode(request, shim)
        TaskFailureMode.objects.get_or_create(
            task=task,
            failure_mode_id=created_item['id'],
            defaults={
                'landing_payload_json': _normalize_task_landing_payload_for_item(
                    created_item,
                ),
                'sys_creator': request.auth,
                'sys_modifier': request.auth,
            },
        )
        cls._attach_task_landing_summary(
            created_item,
            _normalize_task_landing_payload_for_item(created_item),
        )
        cls._log(
            task=task,
            operator=request.auth,
            action=FailureModeTaskLog.ACTION_QUICK_CREATE_FAILURE_MODE,
            from_status=task.status,
            to_status=task.status,
            note=f'快速新增故障模式: {created_item["brief"]}',
            extra_data={'failure_mode_id': created_item['id']},
        )
        return created_item

    @classmethod
    @transaction.atomic
    def submit_task(cls, user: User, task_id: str) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_process_task(task):
            raise HttpError(403, '只有当前任务责任人可以提交评审。')
        if task.status != 'PROCESSING':
            raise HttpError(422, '只有梳理/修订中的任务可以提交评审。')
        if task.task_type in {'CREATE', 'REVISE'}:
            incomplete_briefs, normalized_payloads = cls._validate_task_landing_payloads(task)
            if incomplete_briefs:
                raise HttpError(
                    422,
                    f'以下故障模式的落地情况尚未补齐: {"、".join(incomplete_briefs[:5])}',
                )
            for failure_mode_id, landing_payload in normalized_payloads.items():
                cls._persist_binding_landing_payload(task, failure_mode_id, landing_payload, user)
        from_status = task.status
        task.status = 'REVIEWING'
        task.submitted_at = timezone.now()
        task.current_processor_id = task.creator_id
        task.sys_modifier = user
        task.save()
        cls._sync_task_created_failure_mode_status(task)
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_SUBMIT,
            from_status=from_status,
            to_status=task.status,
            note='提交评审',
            extra_data={
                'from_processor_info': _format_user(task.assignee),
                'to_processor_info': _format_user(task.creator),
            },
        )
        return _serialize_task(cls._get_task_or_404(task_id), FailureModeAccessPolicy(user))

    @classmethod
    @transaction.atomic
    def recall_task(cls, user: User, task_id: str, reason: str = '') -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_recall_task(task):
            raise HttpError(403, '只有当前任务责任特性SE可以撤回任务。')
        if task.status != 'REVIEWING':
            raise HttpError(422, '只有评审中的任务可以撤回。')

        from_status = task.status
        previous_processor_id = str(task.current_processor_id) if task.current_processor_id else None
        task.status = 'PROCESSING'
        task.current_processor_id = task.assignee_id
        task.sys_modifier = user
        task.save()
        cls._sync_task_created_failure_mode_status(task)
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_RECALL,
            from_status=from_status,
            to_status=task.status,
            note='撤回评审',
            extra_data={
                'reason': _normalize_text(reason),
                'from_processor_id': previous_processor_id,
                'to_processor_id': str(task.assignee_id) if task.assignee_id else None,
                'from_processor_info': _format_user(task.creator),
                'to_processor_info': _format_user(task.assignee),
            },
        )
        return _serialize_task(cls._get_task_or_404(task_id), FailureModeAccessPolicy(user))

    @classmethod
    @transaction.atomic
    def reject_task(cls, user: User, task_id: str, reason: str) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_reject_task(task):
            raise HttpError(403, '只有主版本SE或管理员可以驳回任务。')
        if task.status != 'REVIEWING':
            raise HttpError(422, '只有评审中的任务可以驳回。')

        reason = _normalize_text(reason)
        if not reason:
            raise HttpError(422, '驳回原因不能为空。')

        from_status = task.status
        previous_processor_id = str(task.current_processor_id) if task.current_processor_id else None
        task.status = 'PROCESSING'
        task.current_processor_id = task.assignee_id
        task.sys_modifier = user
        task.save()
        cls._sync_task_created_failure_mode_status(task)
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_REJECT,
            from_status=from_status,
            to_status=task.status,
            note='评审驳回',
            extra_data={
                'reason': reason,
                'from_processor_id': previous_processor_id,
                'to_processor_id': str(task.assignee_id) if task.assignee_id else None,
                'from_processor_info': _format_user(task.creator),
                'to_processor_info': _format_user(task.assignee),
            },
        )
        return _serialize_task(cls._get_task_or_404(task_id), FailureModeAccessPolicy(user))

    @classmethod
    @transaction.atomic
    def close_task(
        cls,
        user: User,
        task_id: str,
        *,
        review_result: str,
        review_minutes_html: str,
        review_attachment_ids: list[str],
    ) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        task = cls._ensure_revise_task_initialized(task, user)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_close_task(task):
            raise HttpError(403, '只有主版本SE或管理员可以关闭任务。')
        if task.status != 'REVIEWING':
            raise HttpError(422, '只有评审中的任务可以关闭。')

        review_minutes_html = _normalize_text(review_minutes_html)
        if not review_minutes_html:
            raise HttpError(422, '评审纪要不能为空。')
        if review_result and review_result != 'approved':
            raise HttpError(422, '当前版本仅支持评审通过后关闭任务。')
        normalized_landing_payloads: dict[str, dict[str, Any]] = {}
        if task.task_type in {'CREATE', 'REVISE'}:
            incomplete_briefs, normalized_landing_payloads = cls._validate_task_landing_payloads(task)
            if incomplete_briefs:
                raise HttpError(
                    422,
                    f'以下故障模式的落地情况尚未补齐: {"、".join(incomplete_briefs[:5])}',
                )

        from_status = task.status
        task.status = 'CLOSED'
        task.review_result = 'approved'
        task.review_minutes_html = review_minutes_html
        task.review_attachment_ids = _normalize_id_list(review_attachment_ids)
        task.reviewed_at = timezone.now()
        task.closed_at = task.reviewed_at
        task.current_processor = None
        task.sys_modifier = user
        task.save()
        cls._sync_task_created_failure_mode_status(task)

        task_failure_modes = cls._get_task_selected_failure_mode_ids(task)
        baseline_sync_result = {
            'selected_failure_mode_ids': task_failure_modes,
            'added_failure_mode_ids': [],
            'removed_failure_mode_ids': [],
        }
        if task.task_type == 'CREATE':
            for failure_mode_id in task_failure_modes:
                landing_payload = normalized_landing_payloads.get(failure_mode_id) or {}
                product_failure_mode, _ = ProductFailureMode.objects.get_or_create(
                    product=task.product,
                    subsystem=task.subsystem,
                    failure_mode_id=failure_mode_id,
                    defaults={
                        'sys_creator': user,
                        'sys_modifier': user,
                    },
                )
                cls._sync_product_failure_mode_landings(
                    product_failure_mode,
                    landing_payload,
                    user,
                )
                cls._sync_product_failure_mode_landing_cache(
                    product_failure_mode,
                    landing_payload,
                    user,
                )
            baseline_sync_result['added_failure_mode_ids'] = task_failure_modes
        elif task.task_type == 'REVISE':
            cls._apply_revise_drafts(task, user)
            baseline_snapshot_ids = [str(item) for item in (task.baseline_snapshot_ids or [])]
            current_failure_mode_set = set(task_failure_modes)
            add_ids = [
                failure_mode_id
                for failure_mode_id in task_failure_modes
                if failure_mode_id not in baseline_snapshot_ids
            ]
            remove_ids = [
                failure_mode_id
                for failure_mode_id in baseline_snapshot_ids
                if failure_mode_id not in current_failure_mode_set
            ]

            failure_mode_map = {
                str(item.id): item
                for item in failure_mode_services._failure_mode_queryset().filter(
                    id__in=task_failure_modes,
                )
            }
            for failure_mode_id in current_failure_mode_set:
                landing_payload = cls._build_task_landing_payload_for_binding(
                    task,
                    failure_mode_map[failure_mode_id],
                    existing_payload=normalized_landing_payloads.get(failure_mode_id),
                )
                product_failure_mode, _ = ProductFailureMode.objects.get_or_create(
                    product=task.product,
                    subsystem=task.subsystem,
                    failure_mode_id=failure_mode_id,
                    defaults={
                        'sys_creator': user,
                        'sys_modifier': user,
                    },
                )
                cls._sync_product_failure_mode_landings(
                    product_failure_mode,
                    landing_payload,
                    user,
                )
                cls._sync_product_failure_mode_landing_cache(
                    product_failure_mode,
                    landing_payload,
                    user,
                )
            if remove_ids:
                ProductFailureMode.objects.filter(
                    product=task.product,
                    subsystem=task.subsystem,
                    failure_mode_id__in=remove_ids,
                ).delete()
            baseline_sync_result['added_failure_mode_ids'] = add_ids
            baseline_sync_result['removed_failure_mode_ids'] = remove_ids
        elif task.task_type == 'DELETE':
            ProductFailureMode.objects.filter(
                product=task.product,
                subsystem=task.subsystem,
                failure_mode_id__in=task_failure_modes,
            ).delete()
            baseline_sync_result['removed_failure_mode_ids'] = task_failure_modes

        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_CLOSE,
            from_status=from_status,
            to_status=task.status,
            note='评审通过并关闭任务',
            extra_data={
                'review_result': task.review_result,
                'review_attachment_ids': task.review_attachment_ids,
                'failure_mode_ids': task_failure_modes,
                'baseline_sync_result': baseline_sync_result,
            },
        )
        return _serialize_task(cls._get_task_or_404(task_id), FailureModeAccessPolicy(user))

    @classmethod
    @transaction.atomic
    def reassign_task(cls, user: User, task_id: str, assignee_id: str) -> dict[str, Any]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_reassign_task(task):
            raise HttpError(403, '只有主版本SE或管理员可以改派任务。')
        if task.status not in ['CREATED', 'PROCESSING']:
            raise HttpError(422, '只有创建态和梳理/修订中的任务可以改派。')

        assignee_id = _normalize_text(assignee_id)
        if not assignee_id:
            raise HttpError(422, '新的责任人不能为空。')
        if not policy.can_assign_feature_user(task.product, task.subsystem, assignee_id):
            raise HttpError(422, '新的责任人必须是当前产品子系统下的特性SE。')

        old_assignee_id = str(task.assignee_id) if task.assignee_id else None
        old_assignee_info = _format_user(task.assignee)
        new_assignee = User.objects.filter(id=assignee_id).first()
        from_status = task.status
        task.assignee_id = assignee_id
        task.current_processor_id = assignee_id
        if from_status == 'PROCESSING' and old_assignee_id != assignee_id:
            task.status = 'CREATED'
            task.accepted_at = None
            task.submitted_at = None
        task.sys_modifier = user
        task.save()
        cls._sync_task_created_failure_mode_status(task)
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_REASSIGN,
            from_status=from_status,
            to_status=task.status,
            note='改派责任人',
            extra_data={
                'from_assignee_id': old_assignee_id,
                'to_assignee_id': assignee_id,
                'from_processor_info': old_assignee_info,
                'to_processor_info': _format_user(new_assignee),
            },
        )
        return _serialize_task(cls._get_task_or_404(task_id), FailureModeAccessPolicy(user))

    @classmethod
    def list_task_logs(cls, user: User, task_id: str) -> list[dict[str, Any]]:
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_view_task(task):
            raise HttpError(403, '无权查看当前任务日志。')
        queryset = cls._task_log_queryset().filter(task=task).order_by('-sys_create_datetime')
        return [_serialize_task_log(item) for item in queryset]
