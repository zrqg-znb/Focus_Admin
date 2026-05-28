from __future__ import annotations

from datetime import timedelta
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
TENGWU_REQUIREMENT_NUMBERS_FIELD = 'tengwu_requirement_numbers'
TENGWU_REQUIREMENT_NUMBER_ALIASES = (
    TENGWU_REQUIREMENT_NUMBERS_FIELD,
    'tengwu_requirement_nos',
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


def _normalize_tengwu_requirement_numbers(values: Any) -> list[str]:
    return failure_mode_services._normalize_text_list(values)


def _read_tengwu_requirement_numbers(item: dict[str, Any] | None) -> list[str]:
    if not isinstance(item, dict):
        return []
    for key in TENGWU_REQUIREMENT_NUMBER_ALIASES:
        if key in item:
            return _normalize_tengwu_requirement_numbers(item.get(key))
    return []


def _normalize_tengwu_requirement_numbers_for_status(
    landing_status: Any,
    values: Any,
) -> list[str]:
    if (
        failure_mode_services._normalize_landing_status(landing_status)
        != failure_mode_services.LANDING_STATUS_LANDED
    ):
        return []
    return _normalize_tengwu_requirement_numbers(values)


def _extract_resource_row_tengwu_requirement_numbers(item: dict[str, Any]) -> list[str]:
    for product_row in item.get('product_rows') or []:
        if not isinstance(product_row, dict):
            continue
        for key in TENGWU_REQUIREMENT_NUMBER_ALIASES:
            if key in product_row:
                return _normalize_tengwu_requirement_numbers(product_row.get(key))
    return _read_tengwu_requirement_numbers(item)


def _normalize_resource_row_landing_status(item: dict[str, Any]) -> str:
    return (
        failure_mode_services._normalize_landing_status(
            item.get('landing_status')
            if 'landing_status' in item
            else item.get('is_landed'),
        )
        or failure_mode_services.LANDING_STATUS_NOT_LANDED
    )


def _normalize_resource_row_tengwu_requirement_numbers(
    item: dict[str, Any],
) -> list[str]:
    return _normalize_tengwu_requirement_numbers_for_status(
        _normalize_resource_row_landing_status(item),
        _extract_resource_row_tengwu_requirement_numbers(item),
    )


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


TASK_LANDING_PAYLOAD_SOURCE_KEY = '_task_landing_source'
TASK_LANDING_PAYLOAD_SOURCE_MANUAL = 'manual'
TASK_LANDING_PAYLOAD_SOURCE_SEED = 'seed'
TASK_LANDING_PAYLOAD_SOURCE_SEED_GRACE = timedelta(seconds=1)


def _annotate_task_landing_payload_source(
    payload: dict[str, Any] | None,
    source: str,
) -> dict[str, Any]:
    normalized = dict(payload or {})
    normalized[TASK_LANDING_PAYLOAD_SOURCE_KEY] = source
    return normalized


def _task_landing_payload_source(payload: dict[str, Any] | None) -> str:
    return _normalize_text((payload or {}).get(TASK_LANDING_PAYLOAD_SOURCE_KEY))


def _is_task_landing_payload_manual(binding: TaskFailureMode | None) -> bool:
    if not binding:
        return False
    source = _task_landing_payload_source(binding.landing_payload_json)
    if source == TASK_LANDING_PAYLOAD_SOURCE_MANUAL:
        return True
    if source == TASK_LANDING_PAYLOAD_SOURCE_SEED:
        return False
    create_dt = getattr(binding, 'sys_create_datetime', None)
    update_dt = getattr(binding, 'sys_update_datetime', None)
    if create_dt and update_dt and (update_dt - create_dt) > TASK_LANDING_PAYLOAD_SOURCE_SEED_GRACE:
        return True
    return False


def _get_task_landing_payload_for_binding(
    binding: TaskFailureMode | None,
    *,
    task: FailureModeTask | None = None,
) -> dict[str, Any] | None:
    if not binding:
        return None
    payload = dict(binding.landing_payload_json or {})
    payload.pop(TASK_LANDING_PAYLOAD_SOURCE_KEY, None)
    if task and task.task_type in {'CREATE', 'DELETE'}:
        return payload
    if not _is_task_landing_payload_manual(binding):
        return None
    return payload


def _get_manual_task_landing_payload_for_binding(
    binding: TaskFailureMode | None,
) -> dict[str, Any] | None:
    if not binding or not _is_task_landing_payload_manual(binding):
        return None
    payload = dict(binding.landing_payload_json or {})
    payload.pop(TASK_LANDING_PAYLOAD_SOURCE_KEY, None)
    return payload


def _get_task_landing_payload_snapshot_for_binding(
    binding: TaskFailureMode | None,
) -> dict[str, Any] | None:
    if not binding:
        return None
    payload = dict(binding.landing_payload_json or {})
    payload.pop(TASK_LANDING_PAYLOAD_SOURCE_KEY, None)
    return payload


def _task_scope_is_complete(task: FailureModeTask) -> bool:
    return bool(_normalize_text(getattr(task, 'product_id', None)) and _normalize_text(getattr(task, 'subsystem', None)))


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
        'product_id': str(task.product_id) if task.product_id else None,
        'product_name': task.product.project.name if (task.product and task.product.project) else None,
        'subsystem': task.subsystem or None,
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


def _build_task_landing_product_row(
    *,
    product_id: str,
    product_name: str,
    landing_status: str | None = None,
    subsystems: list[str] | None = None,
    tengwu_requirement_numbers: Any = None,
) -> dict[str, Any]:
    return {
        'product_id': product_id,
        'product_name': product_name,
        'subsystems': list(subsystems or []),
        'landing_status': landing_status,
        TENGWU_REQUIREMENT_NUMBERS_FIELD: _normalize_tengwu_requirement_numbers_for_status(
            landing_status,
            tengwu_requirement_numbers,
        ),
    }


def _build_task_landing_resource_row(
    *,
    resource_id: str,
    label: str,
    subtitle: str | None = None,
    group_key: str = '',
    landing_status: str | None = None,
    product_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        'resource_id': resource_id,
        'label': label,
        'subtitle': subtitle or None,
        'group_key': group_key,
        'landing_status': landing_status,
        'product_rows': list(product_rows or []),
    }


def _extract_task_landing_product_status_map(rows: Any) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        product_id = _normalize_text(item.get('product_id') or item.get('id'))
        if not product_id:
            continue
        result[product_id] = failure_mode_services._normalize_landing_status(
            item.get('landing_status') if 'landing_status' in item else item.get('status')
        )
    return result


def _extract_task_landing_product_tengwu_map(rows: Any) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        product_id = _normalize_text(item.get('product_id') or item.get('id'))
        if not product_id:
            continue
        for key in TENGWU_REQUIREMENT_NUMBER_ALIASES:
            if key in item:
                result[product_id] = _normalize_tengwu_requirement_numbers(item.get(key))
                break
    return result


def _merge_landing_subsystems(*value_groups: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for values in value_groups:
        for value in values or []:
            text = _normalize_text(value)
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
    return result


def _group_scope_binding_products(
    item: dict[str, Any],
    *,
    fallback_subsystem: str = '',
) -> list[dict[str, Any]]:
    grouped_products: dict[str, dict[str, Any]] = {}
    for binding in item.get('scope_bindings') or []:
        if not isinstance(binding, dict):
            continue
        product_id = _normalize_text(binding.get('product_id'))
        if not product_id:
            continue
        product_row = grouped_products.get(product_id)
        if product_row is None:
            product_row = {
                'product_id': product_id,
                'product_name': _normalize_text(binding.get('product_name')) or product_id,
                'subsystems': [],
            }
            grouped_products[product_id] = product_row
        subsystem = _normalize_text(binding.get('subsystem')) or fallback_subsystem
        if subsystem and subsystem not in product_row['subsystems']:
            product_row['subsystems'].append(subsystem)
    return list(grouped_products.values())


def _normalize_target_products(
    item: dict[str, Any],
    *,
    existing_payload: dict[str, Any] | None = None,
    fallback_payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    existing_payload = dict(existing_payload or {})
    fallback_payload = dict(fallback_payload or {})
    fallback_subsystem = _normalize_text(item.get('subsystem'))
    current_products = _group_scope_binding_products(
        item,
        fallback_subsystem=fallback_subsystem,
    )

    base_products = current_products
    if not base_products:
        base_products = [
            dict(product_item)
            for product_item in list(fallback_payload.get('products') or [])
            if isinstance(product_item, dict)
            and _normalize_text(product_item.get('product_id'))
        ]

    existing_products = {
        _normalize_text(product_item.get('product_id')): product_item
        for product_item in list(existing_payload.get('products') or [])
        if isinstance(product_item, dict)
        and _normalize_text(product_item.get('product_id'))
    }
    fallback_products = {
        _normalize_text(product_item.get('product_id')): product_item
        for product_item in list(fallback_payload.get('products') or [])
        if isinstance(product_item, dict)
        and _normalize_text(product_item.get('product_id'))
    }

    target_products: list[dict[str, Any]] = []
    for product_item in base_products:
        product_id = _normalize_text(product_item.get('product_id'))
        if not product_id:
            continue
        existing_product = existing_products.get(product_id) or {}
        fallback_product = fallback_products.get(product_id) or {}
        target_products.append(
            _build_task_landing_product_row(
                product_id=product_id,
                product_name=(
                    _normalize_text(product_item.get('product_name'))
                    or _normalize_text(existing_product.get('product_name'))
                    or _normalize_text(fallback_product.get('product_name'))
                    or product_id
                ),
                landing_status=(
                    failure_mode_services._normalize_landing_status(
                        existing_product.get('landing_status'),
                    )
                    or failure_mode_services._normalize_landing_status(
                        fallback_product.get('landing_status'),
                    )
                ),
                subsystems=_merge_landing_subsystems(
                    product_item.get('subsystems'),
                    existing_product.get('subsystems'),
                    fallback_product.get('subsystems'),
                ),
            ),
        )
    return target_products


def _normalize_task_landing_product_rows(
    target_products: list[dict[str, Any]],
    payload_rows: Any,
    *,
    fallback_status_map: dict[str, str | None] | None = None,
    fallback_tengwu_numbers_map: dict[str, list[str]] | None = None,
    legacy_status: Any = None,
) -> list[dict[str, Any]]:
    payload_status_map = _extract_task_landing_product_status_map(payload_rows)
    payload_tengwu_numbers_map = _extract_task_landing_product_tengwu_map(payload_rows)
    has_explicit_product_status = len(payload_status_map) > 0
    legacy_status_text = failure_mode_services._normalize_landing_status(legacy_status)
    rows: list[dict[str, Any]] = []
    for product_item in target_products or []:
        product_id = _normalize_text(product_item.get('product_id'))
        if not product_id:
            continue
        status = payload_status_map.get(product_id)
        if status is None:
            status = (fallback_status_map or {}).get(product_id)
        if status is None and not has_explicit_product_status:
            status = legacy_status_text
        if status is None:
            status = failure_mode_services.LANDING_STATUS_NOT_LANDED
        if product_id in payload_tengwu_numbers_map:
            tengwu_requirement_numbers = payload_tengwu_numbers_map[product_id]
        else:
            tengwu_requirement_numbers = (fallback_tengwu_numbers_map or {}).get(
                product_id,
                [],
            )
        rows.append(
            _build_task_landing_product_row(
                product_id=product_id,
                product_name=_normalize_text(product_item.get('product_name')) or product_id,
                landing_status=status,
                subsystems=list(product_item.get('subsystems') or []),
                tengwu_requirement_numbers=tengwu_requirement_numbers,
            ),
        )
    return rows


def _normalize_task_landing_rows(
    relation_items: list[dict[str, Any]] | None,
    payload_rows: Any,
    target_products: list[dict[str, Any]],
    *,
    fallback_status_map_by_product: dict[str, dict[str, str | None]] | None = None,
    fallback_tengwu_numbers_map_by_product: dict[str, dict[str, list[str]]] | None = None,
    default_group_key: str = '',
    use_subtitle_group_key: bool = False,
) -> list[dict[str, Any]]:
    payload_rows_by_id: dict[str, dict[str, Any]] = {}
    for item in payload_rows or []:
        if not isinstance(item, dict):
            continue
        resource_id = _normalize_text(item.get('resource_id') or item.get('id'))
        if not resource_id:
            continue
        payload_rows_by_id[resource_id] = item

    rows: list[dict[str, Any]] = []
    for relation_item in relation_items or []:
        resource_id = _normalize_text(relation_item.get('id'))
        if not resource_id:
            continue
        subtitle = _normalize_text(relation_item.get('subtitle')) or None
        group_key = subtitle if use_subtitle_group_key and subtitle else default_group_key
        payload_row = payload_rows_by_id.get(resource_id) or {}
        fallback_status_map_for_resource: dict[str, str | None] = {}
        fallback_tengwu_numbers_map_for_resource: dict[str, list[str]] = {}
        for product_id, resource_status_map in (fallback_status_map_by_product or {}).items():
            if not isinstance(resource_status_map, dict):
                continue
            fallback_status = resource_status_map.get(resource_id)
            if fallback_status is not None:
                fallback_status_map_for_resource[product_id] = fallback_status
        for product_id, resource_tengwu_numbers_map in (
            fallback_tengwu_numbers_map_by_product or {}
        ).items():
            if not isinstance(resource_tengwu_numbers_map, dict):
                continue
            if resource_id in resource_tengwu_numbers_map:
                fallback_tengwu_numbers_map_for_resource[product_id] = (
                    _normalize_tengwu_requirement_numbers(
                        resource_tengwu_numbers_map.get(resource_id),
                    )
                )
        product_rows = _normalize_task_landing_product_rows(
            target_products,
            payload_row.get('product_rows') or [],
            fallback_status_map=fallback_status_map_for_resource,
            fallback_tengwu_numbers_map=fallback_tengwu_numbers_map_for_resource,
            legacy_status=payload_row.get('landing_status')
            if 'landing_status' in payload_row
            else payload_row.get('is_landed'),
        )
        landing_status = failure_mode_services._aggregate_landing_status(
            [item.get('landing_status') for item in product_rows],
            allow_partial=True,
            default=failure_mode_services.LANDING_STATUS_NOT_LANDED,
        ) or failure_mode_services.LANDING_STATUS_NOT_LANDED
        rows.append(
            _build_task_landing_resource_row(
                resource_id=resource_id,
                label=_normalize_text(relation_item.get('label')) or resource_id,
                subtitle=subtitle,
                group_key=group_key,
                landing_status=landing_status,
                product_rows=product_rows,
            ),
        )
    return rows


def _build_product_failure_mode_landing_maps(
    product_failure_modes: list[ProductFailureMode] | ProductFailureMode | None,
) -> dict[str, Any]:
    if product_failure_modes is None:
        product_failure_modes = []
    if isinstance(product_failure_modes, ProductFailureMode):
        product_failure_modes = [product_failure_modes]
    product_failure_mode_list = [item for item in product_failure_modes if item and item.product]
    if not product_failure_mode_list:
        return {
            'products': [],
            'interception_status_map_by_product': {},
            'handling_status_map_by_product': {},
            'observation_status_map_by_product': {},
            'huatuo_status_map_by_product': {},
            'interception_tengwu_numbers_map_by_product': {},
            'handling_tengwu_numbers_map_by_product': {},
            'observation_tengwu_numbers_map_by_product': {},
            'huatuo_tengwu_numbers_map_by_product': {},
        }

    grouped_products: dict[str, dict[str, Any]] = {}
    grouped_statuses = {
        'interception': defaultdict(lambda: defaultdict(list)),
        'handling': defaultdict(lambda: defaultdict(list)),
        'observation': defaultdict(lambda: defaultdict(list)),
        'huatuo': defaultdict(lambda: defaultdict(list)),
    }
    grouped_tengwu_numbers = {
        'interception': defaultdict(lambda: defaultdict(list)),
        'handling': defaultdict(lambda: defaultdict(list)),
        'observation': defaultdict(lambda: defaultdict(list)),
        'huatuo': defaultdict(lambda: defaultdict(list)),
    }

    def append_landing_cache(
        section_key: str,
        product_id: str,
        resource_id: str,
        landing: Any,
    ):
        grouped_statuses[section_key][product_id][resource_id].append(
            failure_mode_services._normalize_landing_status(
                getattr(landing, 'landing_status', None)
                if getattr(landing, 'landing_status', None) is not None
                else landing.is_landed,
            )
        )
        grouped_tengwu_numbers[section_key][product_id][resource_id].extend(
            _normalize_tengwu_requirement_numbers(
                getattr(landing, TENGWU_REQUIREMENT_NUMBERS_FIELD, []),
            )
        )

    for product_failure_mode in product_failure_mode_list:
        product = product_failure_mode.product
        product_id = str(product.id)
        product_row = grouped_products.get(product_id)
        if product_row is None:
            product_row = {
                'product_id': product_id,
                'product_name': product.project.name if product.project else '',
                'subsystems': [],
            }
            grouped_products[product_id] = product_row
        subsystem = failure_mode_services._normalize_optional_text(
            product_failure_mode.subsystem,
        )
        if subsystem and subsystem not in product_row['subsystems']:
            product_row['subsystems'].append(subsystem)

        for landing in getattr(product_failure_mode, 'interception_landings', []).all():
            if landing.is_deleted:
                continue
            append_landing_cache(
                'interception',
                product_id,
                str(landing.interception_strategy_id),
                landing,
            )
        for landing in getattr(product_failure_mode, 'handling_landings', []).all():
            if landing.is_deleted:
                continue
            append_landing_cache(
                'handling',
                product_id,
                str(landing.handling_measure_id),
                landing,
            )
        for landing in getattr(product_failure_mode, 'observation_landings', []).all():
            if landing.is_deleted:
                continue
            append_landing_cache(
                'observation',
                product_id,
                str(landing.observation_method_id),
                landing,
            )
        for landing in getattr(product_failure_mode, 'huatuo_landings', []).all():
            if landing.is_deleted:
                continue
            append_landing_cache(
                'huatuo',
                product_id,
                str(landing.huatuo_diagnosis_id),
                landing,
            )

    products = sorted(
        grouped_products.values(),
        key=lambda item: (item['product_name'], item['product_id']),
    )

    def finalize_status_map(section_key: str) -> dict[str, dict[str, str | None]]:
        section_map: dict[str, dict[str, str | None]] = {}
        for product_id, resource_map in grouped_statuses[section_key].items():
            section_map[product_id] = {
                resource_id: (
                    failure_mode_services._aggregate_landing_status(
                        statuses,
                        allow_partial=False,
                        default=failure_mode_services.LANDING_STATUS_NOT_LANDED,
                    )
                    or failure_mode_services.LANDING_STATUS_NOT_LANDED
                )
                for resource_id, statuses in resource_map.items()
            }
        return section_map

    def finalize_tengwu_numbers_map(section_key: str) -> dict[str, dict[str, list[str]]]:
        section_map: dict[str, dict[str, list[str]]] = {}
        for product_id, resource_map in grouped_tengwu_numbers[section_key].items():
            section_map[product_id] = {
                resource_id: _normalize_tengwu_requirement_numbers(values)
                for resource_id, values in resource_map.items()
            }
        return section_map

    return {
        'products': products,
        'interception_status_map_by_product': finalize_status_map('interception'),
        'handling_status_map_by_product': finalize_status_map('handling'),
        'observation_status_map_by_product': finalize_status_map('observation'),
        'huatuo_status_map_by_product': finalize_status_map('huatuo'),
        'interception_tengwu_numbers_map_by_product': finalize_tengwu_numbers_map(
            'interception',
        ),
        'handling_tengwu_numbers_map_by_product': finalize_tengwu_numbers_map(
            'handling',
        ),
        'observation_tengwu_numbers_map_by_product': finalize_tengwu_numbers_map(
            'observation',
        ),
        'huatuo_tengwu_numbers_map_by_product': finalize_tengwu_numbers_map(
            'huatuo',
        ),
    }


def _collect_task_landing_product_rows(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = dict(payload or {})
    products = list(payload.get('products') or [])
    rows: list[dict[str, Any]] = []
    for section_key in LANDING_SECTION_KEYS:
        for resource_row in list(payload.get(section_key) or []):
            if not isinstance(resource_row, dict):
                continue
            for product_row in list(resource_row.get('product_rows') or []):
                if not isinstance(product_row, dict):
                    continue
                rows.append(
                    {
                        'resource_id': _normalize_text(resource_row.get('resource_id')),
                        'product_id': _normalize_text(product_row.get('product_id')),
                        'landing_status': failure_mode_services._normalize_landing_status(
                            product_row.get('landing_status')
                            if 'landing_status' in product_row
                            else product_row.get('status'),
                        ),
                        TENGWU_REQUIREMENT_NUMBERS_FIELD: _read_tengwu_requirement_numbers(
                            product_row,
                        ),
                    },
                )
    if not rows:
        for section_key in LANDING_SECTION_KEYS:
            for resource_row in list(payload.get(section_key) or []):
                if not isinstance(resource_row, dict):
                    continue
                resource_id = _normalize_text(resource_row.get('resource_id'))
                legacy_status = failure_mode_services._normalize_landing_status(
                    resource_row.get('landing_status')
                    if 'landing_status' in resource_row
                    else resource_row.get('is_landed'),
                )
                for product_row in products:
                    product_id = _normalize_text(product_row.get('product_id'))
                    if not resource_id or not product_id:
                        continue
                    rows.append(
                        {
                            'resource_id': resource_id,
                            'product_id': product_id,
                            'landing_status': legacy_status,
                            TENGWU_REQUIREMENT_NUMBERS_FIELD: _read_tengwu_requirement_numbers(
                                resource_row,
                            ),
                        },
                    )
    return rows


def _collect_task_landing_missing_tengwu_requirement_rows(
    payload: dict[str, Any] | None,
) -> list[dict[str, str]]:
    missing_rows: list[dict[str, str]] = []
    for item in _collect_task_landing_product_rows(payload):
        if not _normalize_text(item.get('product_id')):
            continue
        if item.get('landing_status') != failure_mode_services.LANDING_STATUS_LANDED:
            continue
        if item.get(TENGWU_REQUIREMENT_NUMBERS_FIELD):
            continue
        missing_rows.append(
            {
                'resource_id': _normalize_text(item.get('resource_id')),
                'product_id': _normalize_text(item.get('product_id')),
            },
        )
    return missing_rows


def _validate_task_landing_tengwu_requirement_numbers(
    payload: dict[str, Any] | None,
):
    if _collect_task_landing_missing_tengwu_requirement_rows(payload):
        raise HttpError(422, '已落地项请填写腾雾需求号。')


def _derive_task_failure_mode_landing_status(payload: dict[str, Any] | None) -> str:
    statuses = [
        item.get('landing_status')
        for item in _collect_task_landing_product_rows(payload)
    ]
    return (
        failure_mode_services._aggregate_landing_status(
            statuses,
            allow_partial=True,
            default=failure_mode_services.LANDING_STATUS_NOT_LANDED,
        )
        or failure_mode_services.LANDING_STATUS_NOT_LANDED
    )


def _derive_task_failure_mode_is_landed(payload: dict[str, Any] | None) -> bool:
    return _derive_task_failure_mode_landing_status(payload) == failure_mode_services.LANDING_STATUS_LANDED


def _normalize_task_landing_payload_for_item(
    item: dict[str, Any],
    *,
    existing_payload: dict[str, Any] | None = None,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(existing_payload or {})
    fallback_payload = dict(fallback_payload or {})
    target_products = _normalize_target_products(
        item,
        existing_payload=payload,
        fallback_payload=fallback_payload,
    )
    if not target_products:
        target_products = [
            {
                'product_id': '',
                'product_name': '公共模板',
                'subsystems': [],
            },
        ]

    normalized_payload = {
        'products': [
            _build_task_landing_product_row(
                product_id=_normalize_text(product_item.get('product_id')),
                product_name=_normalize_text(product_item.get('product_name'))
                or _normalize_text(product_item.get('product_id'))
                or '公共模板',
                landing_status=failure_mode_services._normalize_landing_status(
                    product_item.get('landing_status')
                    if 'landing_status' in product_item
                    else None,
                ),
                subsystems=list(product_item.get('subsystems') or []),
            )
            for product_item in target_products
        ],
        'interception_rows': _normalize_task_landing_rows(
            item.get('interception_strategy_items') or [],
            payload.get('interception_rows'),
            target_products,
            fallback_status_map_by_product=fallback_payload.get(
                'interception_status_map_by_product',
            )
            or {},
            fallback_tengwu_numbers_map_by_product=fallback_payload.get(
                'interception_tengwu_numbers_map_by_product',
            )
            or {},
            default_group_key='interception',
        ),
        'handling_rows': _normalize_task_landing_rows(
            item.get('handling_measure_items') or [],
            payload.get('handling_rows'),
            target_products,
            fallback_status_map_by_product=fallback_payload.get(
                'handling_status_map_by_product',
            )
            or {},
            fallback_tengwu_numbers_map_by_product=fallback_payload.get(
                'handling_tengwu_numbers_map_by_product',
            )
            or {},
            default_group_key='handling',
            use_subtitle_group_key=True,
        ),
        'observation_rows': _normalize_task_landing_rows(
            item.get('observation_method_items') or [],
            payload.get('observation_rows'),
            target_products,
            fallback_status_map_by_product=fallback_payload.get(
                'observation_status_map_by_product',
            )
            or {},
            fallback_tengwu_numbers_map_by_product=fallback_payload.get(
                'observation_tengwu_numbers_map_by_product',
            )
            or {},
            default_group_key='observation',
            use_subtitle_group_key=True,
        ),
        'huatuo_rows': _normalize_task_landing_rows(
            item.get('huatuo_diagnosis_items') or [],
            payload.get('huatuo_rows'),
            target_products,
            fallback_status_map_by_product=fallback_payload.get(
                'huatuo_status_map_by_product',
            )
            or {},
            fallback_tengwu_numbers_map_by_product=fallback_payload.get(
                'huatuo_tengwu_numbers_map_by_product',
            )
            or {},
            default_group_key='huatuo',
        ),
    }

    product_status_map: dict[str, list[str]] = defaultdict(list)
    for section_key in LANDING_SECTION_KEYS:
        for resource_row in normalized_payload.get(section_key) or []:
            for product_row in resource_row.get('product_rows') or []:
                product_id = _normalize_text(product_row.get('product_id'))
                if not product_id:
                    continue
                product_status_map[product_id].append(
                    failure_mode_services._normalize_landing_status(
                        product_row.get('landing_status')
                    )
                )

    for product_row in normalized_payload['products']:
        product_id = _normalize_text(product_row.get('product_id'))
        if not product_id:
            product_row['landing_status'] = failure_mode_services.LANDING_STATUS_NOT_LANDED
            continue
        product_row['landing_status'] = (
            failure_mode_services._aggregate_landing_status(
                product_status_map.get(product_id, []),
                allow_partial=True,
                default=failure_mode_services.LANDING_STATUS_NOT_LANDED,
            )
            or failure_mode_services.LANDING_STATUS_NOT_LANDED
        )

    normalized_payload['failure_mode_landing_status'] = _derive_task_failure_mode_landing_status(
        normalized_payload,
    )
    normalized_payload['failure_mode_is_landed'] = (
        normalized_payload['failure_mode_landing_status']
        == failure_mode_services.LANDING_STATUS_LANDED
    )
    return normalized_payload


def _build_task_landing_payload_for_product(
    payload: dict[str, Any] | None,
    product_id: str,
) -> dict[str, Any]:
    payload = dict(payload or {})
    normalized_product_id = _normalize_text(product_id)
    if not normalized_product_id:
        return {}

    product_rows = [
        dict(item)
        for item in list(payload.get('products') or [])
        if isinstance(item, dict)
        and _normalize_text(item.get('product_id')) == normalized_product_id
    ]
    if not product_rows:
        return {}

    product_row = product_rows[0]
    normalized_payload: dict[str, Any] = {'products': [product_row]}
    product_statuses: list[str] = []

    for section_key in LANDING_SECTION_KEYS:
        section_rows: list[dict[str, Any]] = []
        for resource_row in list(payload.get(section_key) or []):
            if not isinstance(resource_row, dict):
                continue
            resource_product_rows = [
                dict(item)
                for item in list(resource_row.get('product_rows') or [])
                if isinstance(item, dict)
                and _normalize_text(item.get('product_id')) == normalized_product_id
            ]
            if not resource_product_rows:
                continue
            first_product_row = resource_product_rows[0]
            product_statuses.extend(
                failure_mode_services._normalize_landing_status(
                    item.get('landing_status')
                    if 'landing_status' in item
                    else item.get('status'),
                )
                for item in resource_product_rows
            )
            section_rows.append(
                {
                    'resource_id': _normalize_text(resource_row.get('resource_id')),
                    'label': _normalize_text(resource_row.get('label')) or '',
                    'subtitle': _normalize_text(resource_row.get('subtitle')) or None,
                    'group_key': _normalize_text(resource_row.get('group_key')) or '',
                    'landing_status': failure_mode_services._normalize_landing_status(
                        first_product_row.get('landing_status')
                        if 'landing_status' in first_product_row
                        else first_product_row.get('status'),
                    ),
                    'product_rows': resource_product_rows,
                },
            )
        normalized_payload[section_key] = section_rows

    product_row['landing_status'] = (
        failure_mode_services._aggregate_landing_status(
            product_statuses,
            allow_partial=True,
            default=failure_mode_services.LANDING_STATUS_NOT_LANDED,
        )
        or failure_mode_services.LANDING_STATUS_NOT_LANDED
    )
    normalized_payload.update(_summarize_task_landing_payload(normalized_payload))
    return normalized_payload


def _merge_task_landing_payload(
    existing_payload: dict[str, Any] | None,
    incoming_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(existing_payload or {})
    incoming_payload = dict(incoming_payload or {})
    merged.pop('failure_mode_is_landed', None)
    merged.pop('failure_mode_landing_status', None)
    for key in ('products', *LANDING_SECTION_KEYS):
        if key in incoming_payload:
            merged[key] = incoming_payload.get(key) or []
    return merged


def _summarize_task_landing_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(payload or {})
    product_rows = _collect_task_landing_product_rows(payload)
    resource_total = len(product_rows)
    selected_count = sum(1 for item in product_rows if item.get('landing_status') is not None)
    landed_count = sum(
        1
        for item in product_rows
        if item.get('landing_status') == failure_mode_services.LANDING_STATUS_LANDED
    )
    landing_completed = all(
        item.get('landing_status') is not None for item in product_rows
    ) and not _collect_task_landing_missing_tengwu_requirement_rows(payload)
    landing_status = _derive_task_failure_mode_landing_status(payload)
    return {
        'landing_completed': landing_completed,
        'failure_mode_landing_status': landing_status,
        'failure_mode_is_landed': landing_status == failure_mode_services.LANDING_STATUS_LANDED,
        'landing_resource_total': resource_total,
        'landing_resource_selected_count': selected_count,
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
        query = Q(creator=self.user) | Q(assignee=self.user) | Q(current_processor=self.user)
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
        if task.creator_id and str(task.creator_id) == self.user_id:
            return True
        if task.assignee_id and str(task.assignee_id) == self.user_id:
            return True
        if task.current_processor_id and str(task.current_processor_id) == self.user_id:
            return True
        if str(task.product_id) in self.version_product_ids:
            return True
        return (str(task.product_id), task.subsystem or '') in self.scope_pairs

    def _is_task_responsible(self, task: FailureModeTask) -> bool:
        return bool(
            (task.assignee_id and str(task.assignee_id) == self.user_id)
            or (task.current_processor_id and str(task.current_processor_id) == self.user_id)
        )

    def can_accept_task(self, task: FailureModeTask) -> bool:
        return self._is_task_responsible(task)

    def can_process_task(self, task: FailureModeTask) -> bool:
        return self._is_task_responsible(task)

    def can_recall_task(self, task: FailureModeTask) -> bool:
        return self._is_task_responsible(task)

    def can_reject_task(self, task: FailureModeTask) -> bool:
        if _task_scope_is_complete(task):
            return self.is_admin or str(task.product_id) in self.version_product_ids
        return bool(
            self.is_admin
            or (task.creator_id and str(task.creator_id) == self.user_id)
            or (task.current_processor_id and str(task.current_processor_id) == self.user_id)
        )

    def can_close_task(self, task: FailureModeTask) -> bool:
        return self.can_reject_task(task)

    def can_reassign_task(self, task: FailureModeTask) -> bool:
        if self.can_close_task(task):
            return True
        if _task_scope_is_complete(task):
            return False
        return bool(
            (task.creator_id and str(task.creator_id) == self.user_id)
            or self._is_task_responsible(task)
        )

    def can_update_task_scope(self, task: FailureModeTask) -> bool:
        return bool(
            self.is_admin
            or (task.creator_id and str(task.creator_id) == self.user_id)
            or (task.assignee_id and str(task.assignee_id) == self.user_id)
        )

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
        product: FailureModeProduct | None,
        subsystem: str | None,
    ) -> list[str]:
        if not product or not _normalize_text(subsystem):
            return []
        return [
            str(item)
            for item in ProductFailureMode.objects.filter(
                product=product,
                subsystem=_normalize_text(subsystem),
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
        if not _task_scope_is_complete(task):
            return None
        return cls._product_failure_mode_queryset().filter(
            product=task.product,
            subsystem=_normalize_text(task.subsystem),
            failure_mode_id=failure_mode_id,
        ).first()

    @classmethod
    def _get_product_failure_mode_bindings(
        cls,
        failure_mode_id: str,
    ) -> list[ProductFailureMode]:
        return list(
            cls._product_failure_mode_queryset()
            .filter(failure_mode_id=failure_mode_id)
            .order_by('product__project__name', 'subsystem', 'sys_create_datetime', 'id')
        )

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
        product_failure_modes: list[ProductFailureMode] | ProductFailureMode | None = None,
    ) -> dict[str, Any]:
        current_item = item or failure_mode_services._serialize_failure_mode(failure_mode)
        normalized_payload = _normalize_task_landing_payload_for_item(
            current_item,
            existing_payload=existing_payload,
            fallback_payload=_build_product_failure_mode_landing_maps(
                product_failure_modes
            ),
        )
        summary = _summarize_task_landing_payload(normalized_payload)
        return {
            'task_id': str(task.id),
            'failure_mode_id': str(failure_mode.id),
            'failure_mode_brief': current_item.get('brief') or failure_mode.brief,
            'failure_mode_landing_status': summary['failure_mode_landing_status'],
            'failure_mode_is_landed': summary['failure_mode_is_landed'],
            'landing_completed': summary['landing_completed'],
            'landing_resource_total': summary['landing_resource_total'],
            'landing_resource_selected_count': summary['landing_resource_selected_count'],
            'landing_resource_landed_count': summary['landing_resource_landed_count'],
            'products': normalized_payload['products'],
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
        product_failure_modes: list[ProductFailureMode] | ProductFailureMode | None = None,
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
                product_failure_modes,
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
            product_failure_modes = cls._get_product_failure_mode_bindings(
                str(binding.failure_mode_id),
            )
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
                existing_payload=_get_task_landing_payload_for_binding(
                    binding,
                    task=task,
                ),
                fallback_payload=_build_product_failure_mode_landing_maps(
                    product_failure_modes,
                ),
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
                is_landed=(
                    _normalize_resource_row_landing_status(item)
                    == failure_mode_services.LANDING_STATUS_LANDED
                ),
                landing_status=_normalize_resource_row_landing_status(item),
                tengwu_requirement_numbers=(
                    _normalize_resource_row_tengwu_requirement_numbers(item)
                ),
                sys_creator=operator,
                sys_modifier=operator,
            )
            for item in landing_payload.get('interception_rows') or []
        ]
        handling_rows = [
            ProductFailureModeHandlingLanding(
                product_failure_mode=product_failure_mode,
                handling_measure_id=item['resource_id'],
                is_landed=(
                    _normalize_resource_row_landing_status(item)
                    == failure_mode_services.LANDING_STATUS_LANDED
                ),
                landing_status=_normalize_resource_row_landing_status(item),
                tengwu_requirement_numbers=(
                    _normalize_resource_row_tengwu_requirement_numbers(item)
                ),
                sys_creator=operator,
                sys_modifier=operator,
            )
            for item in landing_payload.get('handling_rows') or []
        ]
        observation_rows = [
            ProductFailureModeObservationLanding(
                product_failure_mode=product_failure_mode,
                observation_method_id=item['resource_id'],
                is_landed=(
                    _normalize_resource_row_landing_status(item)
                    == failure_mode_services.LANDING_STATUS_LANDED
                ),
                landing_status=_normalize_resource_row_landing_status(item),
                tengwu_requirement_numbers=(
                    _normalize_resource_row_tengwu_requirement_numbers(item)
                ),
                sys_creator=operator,
                sys_modifier=operator,
            )
            for item in landing_payload.get('observation_rows') or []
        ]
        huatuo_rows = [
            ProductFailureModeHuatuoLanding(
                product_failure_mode=product_failure_mode,
                huatuo_diagnosis_id=item['resource_id'],
                is_landed=(
                    _normalize_resource_row_landing_status(item)
                    == failure_mode_services.LANDING_STATUS_LANDED
                ),
                landing_status=_normalize_resource_row_landing_status(item),
                tengwu_requirement_numbers=(
                    _normalize_resource_row_tengwu_requirement_numbers(item)
                ),
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
    def _sync_task_failure_mode_product_landings(
        cls,
        failure_mode_id: str,
        landing_payload: dict[str, Any] | None,
        operator: User,
    ):
        product_failure_modes = cls._get_product_failure_mode_bindings(failure_mode_id)
        if not product_failure_modes:
            return
        grouped_bindings: dict[str, list[ProductFailureMode]] = defaultdict(list)
        for binding in product_failure_modes:
            if not binding.product_id:
                continue
            grouped_bindings[str(binding.product_id)].append(binding)

        for product_id, bindings in grouped_bindings.items():
            product_payload = _build_task_landing_payload_for_product(
                landing_payload,
                product_id,
            )
            if not product_payload:
                continue
            for binding in bindings:
                cls._sync_product_failure_mode_landings(
                    binding,
                    product_payload,
                    operator,
                )
                cls._sync_product_failure_mode_landing_cache(
                    binding,
                    product_payload,
                    operator,
                )

    @classmethod
    def _persist_binding_landing_payload(
        cls,
        task: FailureModeTask,
        failure_mode_id: str,
        normalized_payload: dict[str, Any],
        operator: User,
        *,
        landing_source: str | None = None,
    ):
        existing_binding = (
            TaskFailureMode.objects.filter(
                task=task,
                failure_mode_id=failure_mode_id,
            )
            .only('landing_payload_json', 'sys_create_datetime', 'sys_update_datetime')
            .first()
        )
        source = landing_source
        if source not in {TASK_LANDING_PAYLOAD_SOURCE_MANUAL, TASK_LANDING_PAYLOAD_SOURCE_SEED}:
            source = (
                TASK_LANDING_PAYLOAD_SOURCE_MANUAL
                if _is_task_landing_payload_manual(existing_binding)
                else TASK_LANDING_PAYLOAD_SOURCE_SEED
            )
        TaskFailureMode.objects.filter(
            task=task,
            failure_mode_id=failure_mode_id,
        ).update(
            landing_payload_json=_annotate_task_landing_payload_source(
                normalized_payload,
                source,
            ),
            sys_modifier_id=operator.id,
            sys_update_datetime=timezone.now(),
        )

    @classmethod
    def _ensure_revise_task_initialized(
        cls,
        task: FailureModeTask,
        operator: User | None = None,
    ) -> FailureModeTask:
        if task.task_type != 'REVISE':
            return task
        if not _task_scope_is_complete(task):
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
                    landing_payload_json=_annotate_task_landing_payload_source(
                        cls._build_task_landing_payload_for_binding(
                            task,
                            product_failure_mode_map[str(failure_mode_id)].failure_mode,
                            product_failure_modes=[
                                product_failure_mode_map[str(failure_mode_id)],
                            ],
                        ),
                        TASK_LANDING_PAYLOAD_SOURCE_SEED,
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
            if not _task_scope_is_complete(task):
                rows: list[dict[str, Any]] = []
                bindings = (
                    TaskFailureMode.objects.filter(task=task)
                    .select_related('failure_mode')
                    .order_by('sys_create_datetime', 'id')
                )
                for binding in bindings:
                    failure_mode = binding.failure_mode
                    product_failure_modes = cls._get_product_failure_mode_bindings(
                        str(binding.failure_mode_id),
                    )
                    item = failure_mode_services._serialize_failure_mode(failure_mode)
                    item['task_change_type'] = 'delete_candidate'
                    item['has_task_draft'] = False
                    cls._attach_task_landing_summary(
                        item,
                        cls._build_task_landing_payload_for_binding(
                            task,
                            failure_mode,
                            existing_payload=_get_task_landing_payload_for_binding(
                                binding,
                                task=task,
                            ),
                            product_failure_modes=product_failure_modes,
                        ),
                    )
                    _attach_task_failure_mode_edit_meta(task, failure_mode, item)
                    rows.append(item)
                return rows
            baseline_relations = (
                cls._product_failure_mode_queryset()
                .filter(product=task.product, subsystem=task.subsystem)
                .order_by('sys_create_datetime', 'id')
            )
            rows: list[dict[str, Any]] = []
            for relation in baseline_relations:
                if not relation.failure_mode_id:
                    continue
                product_failure_modes = cls._get_product_failure_mode_bindings(
                    str(relation.failure_mode_id),
                )
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
                        product_failure_modes=product_failure_modes,
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
            product_failure_modes = cls._get_product_failure_mode_bindings(
                str(binding.failure_mode_id),
            )
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
                existing_payload=_get_task_landing_payload_for_binding(
                    binding,
                    task=task,
                ),
                fallback_payload=_build_product_failure_mode_landing_maps(
                    product_failure_modes,
                ),
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
        task_type = _normalize_text(data.get('task_type'))
        name = _normalize_text(data.get('name'))
        product_id = _normalize_text(data.get('product_id'))
        subsystem = _normalize_text(data.get('subsystem'))
        assignee_id = _normalize_text(data.get('assignee_id'))
        if task_type not in {'CREATE', 'REVISE', 'DELETE'}:
            raise HttpError(422, '任务类型非法。')
        if not name:
            raise HttpError(422, '任务名称不能为空。')
        if bool(product_id) != bool(subsystem):
            raise HttpError(422, '产品和子系统需同时填写或同时留空。')
        if not assignee_id:
            raise HttpError(422, '责任人不能为空。')
        assignee = get_object_or_404(User.objects.all(), id=assignee_id)
        product = None
        if product_id:
            product = get_object_or_404(
                FailureModeProduct.objects.select_related('project', 'owner'),
                id=product_id,
            )
            if not policy.can_create_task(product):
                raise HttpError(403, '只有该产品主版本SE或管理员可以发起任务。')
        task = FailureModeTask.objects.create(
            name=name,
            task_type=task_type,
            status='CREATED',
            product=product,
            subsystem=subsystem or None,
            creator=user,
            assignee=assignee,
            current_processor_id=assignee_id,
            baseline_snapshot_ids=[],
            sys_creator=user,
            sys_modifier=user,
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
                'product_id': str(product.id) if product else None,
                'subsystem': subsystem or None,
            },
        )
        task = cls._get_task_or_404(str(task.id))
        return _serialize_task(task, FailureModeAccessPolicy(user))

    @classmethod
    @transaction.atomic
    def update_task_scope(
        cls,
        user: User,
        task_id: str,
        *,
        product_id: str | None = None,
        subsystem: str | None = None,
    ) -> dict[str, Any]:
        ProductWorkflowService.sync_projects()
        task = cls._get_task_or_404(task_id)
        policy = FailureModeAccessPolicy(user)
        if not policy.can_update_task_scope(task):
            raise HttpError(403, '无权修改当前任务工作范围。')
        if task.status != 'CREATED':
            raise HttpError(422, '只有创建态任务可以修改工作范围。')

        normalized_product_id = _normalize_text(product_id)
        normalized_subsystem = _normalize_text(subsystem)
        if bool(normalized_product_id) != bool(normalized_subsystem):
            raise HttpError(422, '产品和子系统需同时填写或同时清空。')

        if normalized_product_id:
            product = get_object_or_404(
                FailureModeProduct.objects.select_related('project', 'owner'),
                id=normalized_product_id,
            )
            if not policy.can_create_task(product):
                raise HttpError(403, '只有该产品主版本SE或管理员可以设置任务范围。')
            task.product = product
            task.subsystem = normalized_subsystem
            task.baseline_snapshot_ids = cls._load_baseline_failure_mode_ids(
                product,
                normalized_subsystem,
            )
        else:
            task.product = None
            task.subsystem = None
            task.baseline_snapshot_ids = []

        task.sys_modifier = user
        task.save()
        cls._log(
            task=task,
            operator=user,
            action=FailureModeTaskLog.ACTION_UPDATE_SCOPE,
            from_status=task.status,
            to_status=task.status,
            note='补齐任务工作范围',
            extra_data={
                'product_id': str(task.product_id) if task.product_id else None,
                'subsystem': task.subsystem or None,
            },
        )
        return _serialize_task(cls._get_task_or_404(task_id), FailureModeAccessPolicy(user))

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
        product_failure_modes = cls._get_product_failure_mode_bindings(failure_mode_id)
        if task.task_type == 'DELETE':
            failure_mode = get_object_or_404(
                failure_mode_services._failure_mode_queryset(),
                id=failure_mode_id,
            )
            return cls._serialize_task_failure_mode_landing(
                task,
                failure_mode,
                existing_payload=None,
                product_failure_modes=product_failure_modes,
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
            existing_payload=_get_task_landing_payload_for_binding(
                binding,
                task=task,
            ),
            product_failure_modes=product_failure_modes,
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
            product_failure_modes=cls._get_product_failure_mode_bindings(
                failure_mode_id,
            ),
        )
        _validate_task_landing_tengwu_requirement_numbers(normalized_payload)
        cls._persist_binding_landing_payload(
            task,
            failure_mode_id,
            normalized_payload,
            user,
            landing_source=TASK_LANDING_PAYLOAD_SOURCE_MANUAL,
        )
        cls._sync_task_failure_mode_product_landings(
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
            'failure_mode_landing_status': summary['failure_mode_landing_status'],
            'failure_mode_is_landed': summary['failure_mode_is_landed'],
            'landing_completed': summary['landing_completed'],
            'landing_resource_total': summary['landing_resource_total'],
            'landing_resource_selected_count': summary['landing_resource_selected_count'],
            'landing_resource_landed_count': summary['landing_resource_landed_count'],
            'products': normalized_payload['products'],
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
        if task.task_type in {'REVISE', 'DELETE'} and _task_scope_is_complete(task):
            baseline_ids = cls._load_baseline_failure_mode_ids(task.product, task.subsystem)
            if not baseline_ids:
                raise HttpError(422, '当前产品子系统下暂无已生效基线，不能发起修订或删除任务。')
        if task.task_type == 'REVISE':
            cls._ensure_revise_task_initialized(task, user)
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

        if task.task_type == 'DELETE' and _task_scope_is_complete(task):
            baseline_ids = set(cls._load_baseline_failure_mode_ids(task.product, task.subsystem))
            invalid_ids = [item_id for item_id in normalized_ids if item_id not in baseline_ids]
            if invalid_ids:
                raise HttpError(422, '删除任务只能选择当前产品子系统已生效基线中的故障模式。')

        existing_binding_map = {
            str(item.failure_mode_id): _get_manual_task_landing_payload_for_binding(
                item,
            )
            for item in TaskFailureMode.objects.filter(task=task)
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
                            _annotate_task_landing_payload_source(
                                cls._build_task_landing_payload_for_binding(
                                    task,
                                    failure_mode_map[item_id],
                                    existing_payload=existing_binding_map.get(item_id),
                                    product_failure_modes=cls._get_product_failure_mode_bindings(
                                        item_id,
                                    ),
                                ),
                                (
                                    TASK_LANDING_PAYLOAD_SOURCE_MANUAL
                                    if existing_binding_map.get(item_id) is not None
                                    else TASK_LANDING_PAYLOAD_SOURCE_SEED
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

        binding = cls._get_task_failure_mode_binding_or_404(task, failure_mode_id)
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
        product_failure_modes = cls._get_product_failure_mode_bindings(failure_mode_id)
        landing_payload = _normalize_task_landing_payload_for_item(
            item,
            existing_payload=_get_task_landing_payload_snapshot_for_binding(
                binding,
            ),
            fallback_payload=_build_product_failure_mode_landing_maps(
                product_failure_modes,
            ),
        )
        cls._persist_binding_landing_payload(
            task,
            failure_mode_id,
            landing_payload,
            user,
            landing_source=TASK_LANDING_PAYLOAD_SOURCE_MANUAL,
        )
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
        binding = cls._get_task_failure_mode_binding_or_404(task, failure_mode_id)
        product_failure_modes = cls._get_product_failure_mode_bindings(failure_mode_id)
        landing_payload = _normalize_task_landing_payload_for_item(
            item,
            existing_payload=_get_task_landing_payload_snapshot_for_binding(binding),
            fallback_payload=_build_product_failure_mode_landing_maps(
                product_failure_modes,
            ),
        )
        cls._persist_binding_landing_payload(
            task,
            failure_mode_id,
            landing_payload,
            user,
            landing_source=TASK_LANDING_PAYLOAD_SOURCE_MANUAL,
        )
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
                'landing_payload_json': _annotate_task_landing_payload_source(
                    _normalize_task_landing_payload_for_item(
                        created_item,
                    ),
                    TASK_LANDING_PAYLOAD_SOURCE_SEED,
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
                cls._persist_binding_landing_payload(
                    task,
                    failure_mode_id,
                    landing_payload,
                    user,
                    landing_source=TASK_LANDING_PAYLOAD_SOURCE_MANUAL,
                )
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
            raise HttpError(403, '只有当前任务责任人可以撤回任务。')
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
            raise HttpError(403, '无权驳回当前任务。')
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
            raise HttpError(403, '无权关闭当前任务。')
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
        has_scope = _task_scope_is_complete(task)
        baseline_sync_result = {
            'selected_failure_mode_ids': task_failure_modes,
            'added_failure_mode_ids': [],
            'removed_failure_mode_ids': [],
        }
        if task.task_type == 'CREATE':
            if has_scope:
                for failure_mode_id in task_failure_modes:
                    product_failure_mode, created = ProductFailureMode.objects.get_or_create(
                        product=task.product,
                        subsystem=task.subsystem,
                        failure_mode_id=failure_mode_id,
                        defaults={
                            'sys_creator': user,
                            'sys_modifier': user,
                        },
                    )
                    if created:
                        failure_mode_services._sync_product_failure_mode_relations_from_template(
                            product_failure_mode,
                            product_failure_mode.failure_mode,
                            user,
                        )
                        failure_mode_services._seed_product_failure_mode_landings_from_relations(
                            product_failure_mode,
                            user,
                        )
                baseline_sync_result['added_failure_mode_ids'] = task_failure_modes
        elif task.task_type == 'REVISE':
            cls._apply_revise_drafts(task, user)
            if has_scope:
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
                    product_failure_mode, created = ProductFailureMode.objects.get_or_create(
                        product=task.product,
                        subsystem=task.subsystem,
                        failure_mode_id=failure_mode_id,
                        defaults={
                            'sys_creator': user,
                            'sys_modifier': user,
                        },
                    )
                    if created:
                        failure_mode_services._sync_product_failure_mode_relations_from_template(
                            product_failure_mode,
                            failure_mode_map[failure_mode_id],
                            user,
                        )
                        failure_mode_services._seed_product_failure_mode_landings_from_relations(
                            product_failure_mode,
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
            if has_scope:
                ProductFailureMode.objects.filter(
                    product=task.product,
                    subsystem=task.subsystem,
                    failure_mode_id__in=task_failure_modes,
                ).delete()
            else:
                for failure_mode_id in task_failure_modes:
                    failure_mode_services.delete_failure_mode(failure_mode_id)
            baseline_sync_result['removed_failure_mode_ids'] = task_failure_modes

        for failure_mode_id, landing_payload in normalized_landing_payloads.items():
            cls._sync_task_failure_mode_product_landings(
                failure_mode_id,
                landing_payload,
                user,
            )

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
            raise HttpError(403, '无权改派当前任务。')
        if task.status not in ['CREATED', 'PROCESSING']:
            raise HttpError(422, '只有创建态和梳理/修订中的任务可以改派。')

        assignee_id = _normalize_text(assignee_id)
        if not assignee_id:
            raise HttpError(422, '新的责任人不能为空。')
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
