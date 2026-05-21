from __future__ import annotations

from collections import defaultdict
import json
from types import SimpleNamespace
from typing import Any, Iterable, Type

from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from core.dict_item.dict_item_model import DictItem
from core.user.user_model import User

from .failure_mode_model import (
    FailureMode,
    FailureModeHandlingMeasureRel,
    FailureModeHuatuoDiagnosisRel,
    FailureModeInterceptionStrategyRel,
    FailureModeProduct,
    FailureModeObservationMethodRel,
    FailureModeSubsystemConfig,
    HandlingMeasure,
    HandlingMeasureTestCaseRel,
    HuatuoDiagnosis,
    InterceptionStrategy,
    ObservationMethod,
    ProductFailureMode,
    ProductFailureModeHandlingLanding,
    ProductFailureModeHuatuoLanding,
    ProductFailureModeInterceptionLanding,
    ProductFailureModeInterceptionStrategyRel,
    ProductFailureModeHandlingMeasureRel,
    ProductFailureModeObservationLanding,
    ProductFailureModeObservationMethodRel,
    ProductFailureModeHuatuoDiagnosisRel,
    TestCase,
)

DICT_CODE_MAP = {
    'subsystem': 'failure_mode_subsystem',
    'module': 'failure_mode_module',
    'chip': 'failure_mode_chip',
    'fault_category': 'failure_mode_fault_category',
    'symptom': 'failure_mode_symptom',
    'functional_safety_level': 'failure_mode_functional_safety_level',
    'occurrence_frequency': 'failure_mode_occurrence_frequency',
    'detectability': 'failure_mode_detectability',
    'severity': 'failure_mode_severity',
    'status': 'failure_mode_status',
    'measure_category': 'failure_mode_measure_category',
    'monitor_type': 'failure_mode_monitor_type',
}

FIXED_HANDLING_MEASURE_CATEGORIES = ['检测', '预防', '自愈']
FIXED_OBSERVATION_METHOD_TYPES = ['流水日志', 'DMD 点位', 'FMP 点位']
STATISTICS_STATUS_ORDER = ['已配置', '待补充', '无需配置']
PRODUCT_STATISTICS_STATUS_ORDER = ['已落地', '待开展', '不涉及']
FAILURE_MODE_LANDING_STATUS_ORDER = ['已落地', '未落地']
EMPTY_SUBSYSTEM_LABEL = '未配置子系统'
PLATFORM_PROJECT_TYPE = '平台项目'


def _normalize_text_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        text = values.strip()
        if text.startswith('[') and text.endswith(']'):
            try:
                decoded = json.loads(text)
            except (TypeError, ValueError):
                decoded = None
            if isinstance(decoded, list):
                values = decoded
    raw_values = values if isinstance(values, list) else [values]
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        if isinstance(item, str):
            nested = item.strip()
            if nested.startswith('[') and nested.endswith(']'):
                try:
                    decoded = json.loads(nested)
                except (TypeError, ValueError):
                    decoded = None
                if isinstance(decoded, list):
                    for nested_item in _normalize_text_list(decoded):
                        if nested_item in seen:
                            continue
                        seen.add(nested_item)
                        result.append(nested_item)
                    continue
        text = str(item or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_html_text(value: Any) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {'1', 'true', 'yes', 'on'}:
        return True
    if text in {'0', 'false', 'no', 'off'}:
        return False
    return default


def _normalize_enum_list(values: Any, allowed_values: list[str]) -> list[str]:
    normalized = _normalize_text_list(values)
    normalized_set = set(normalized)
    return [item for item in allowed_values if item in normalized_set]


def _normalize_failure_mode_source_type(value: Any) -> str:
    normalized = _normalize_optional_text(value) or FailureMode.SOURCE_TYPE_MANUAL
    allowed_values = {
        FailureMode.SOURCE_TYPE_MANUAL,
        FailureMode.SOURCE_TYPE_TASK_QUICK_CREATE,
    }
    if normalized not in allowed_values:
        raise HttpError(422, 'source_type 非法')
    return normalized


def _append_unique_text(target: list[str], seen: set[str], value: Any):
    text = _normalize_optional_text(value)
    if not text or text in seen:
        return
    seen.add(text)
    target.append(text)


def _normalize_scope_bindings(values: Any) -> list[dict[str, str]]:
    if values is None:
        return []
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        values = [values]

    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in values:
        product_id: str | None = None
        subsystem: str | None = None
        if isinstance(item, dict):
            product_id = _normalize_optional_text(item.get('product_id'))
            subsystem = _normalize_optional_text(item.get('subsystem'))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            product_id = _normalize_optional_text(item[0])
            subsystem = _normalize_optional_text(item[1])
        else:
            text = _normalize_optional_text(item)
            if text and '|' in text:
                parts = [part.strip() for part in text.split('|', 1)]
                if len(parts) == 2:
                    product_id = _normalize_optional_text(parts[0])
                    subsystem = _normalize_optional_text(parts[1])
        if not product_id or not subsystem:
            continue
        key = (product_id, subsystem)
        if key in seen:
            continue
        seen.add(key)
        result.append({'product_id': product_id, 'subsystem': subsystem})
    return result


FAILURE_MODE_SIMPLE_FIELD_NORMALIZERS = {
    'brief': _normalize_optional_text,
    'subsystem': _normalize_optional_text,
    'module': _normalize_optional_text,
    'chips': _normalize_text_list,
    'fault_categories': _normalize_text_list,
    'symptoms': _normalize_text_list,
    'effect_html': _normalize_html_text,
    'root_cause_html': _normalize_html_text,
    'functional_safety_level': _normalize_optional_text,
    'occurrence_frequency': _normalize_optional_text,
    'detectability': _normalize_optional_text,
    'severity': _normalize_optional_text,
    'related_dts_nos': _normalize_text_list,
    'scope_bindings': _normalize_scope_bindings,
    'status': _normalize_optional_text,
    'interception_required': _normalize_bool,
    'huatuo_required': _normalize_bool,
    'required_handling_measure_categories': (
        lambda value: _normalize_enum_list(value, FIXED_HANDLING_MEASURE_CATEGORIES)
    ),
    'required_observation_method_types': (
        lambda value: _normalize_enum_list(value, FIXED_OBSERVATION_METHOD_TYPES)
    ),
}

FAILURE_MODE_MODEL_FIELD_MAP = {
    'brief': 'brief',
    'subsystem': 'subsystem',
    'module': 'module_name',
    'chips': 'chips',
    'fault_categories': 'fault_categories',
    'symptoms': 'symptoms',
    'effect_html': 'effect_html',
    'root_cause_html': 'root_cause_html',
    'functional_safety_level': 'functional_safety_level',
    'occurrence_frequency': 'occurrence_frequency',
    'detectability': 'detectability',
    'severity': 'severity',
    'related_dts_nos': 'related_dts_nos',
    'scope_bindings': 'scope_bindings',
    'status': 'status',
    'interception_required': 'interception_required',
    'huatuo_required': 'huatuo_required',
    'required_handling_measure_categories': 'required_handling_measure_categories',
    'required_observation_method_types': 'required_observation_method_types',
}

FAILURE_MODE_RELATION_TRIGGER_FIELDS = {
    'interception': ('interception_required', 'interception_strategy_ids'),
    'handling': ('required_handling_measure_categories', 'handling_measure_ids'),
    'observation': ('required_observation_method_types', 'observation_method_ids'),
    'huatuo': ('huatuo_required', 'huatuo_diagnosis_ids'),
}

FAILURE_MODE_TASK_DRAFT_ALLOWED_FIELDS = {
    'brief',
    'subsystem',
    'module',
    'chips',
    'fault_categories',
    'symptoms',
    'effect_html',
    'root_cause_html',
    'functional_safety_level',
    'occurrence_frequency',
    'detectability',
    'severity',
    'author_ids',
    'related_dts_nos',
    'scope_bindings',
    'interception_required',
    'huatuo_required',
    'required_handling_measure_categories',
    'required_observation_method_types',
    'interception_strategy_ids',
    'handling_measure_ids',
    'observation_method_ids',
    'huatuo_diagnosis_ids',
}


def _build_option_list(values: Iterable[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in values:
        text = _normalize_optional_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        items.append({'label': text, 'value': text})
    return items


def _format_datetime(value) -> str | None:
    if not value:
        return None
    return value.isoformat()


def _user_brief(user: User | None) -> dict[str, str | None] | None:
    if not user:
        return None
    return {
        'id': str(user.id),
        'username': user.username,
        'name': user.name,
    }


def _users_brief(users: Iterable[User]) -> list[dict[str, str | None]]:
    items: list[dict[str, str | None]] = []
    for user in users:
        brief = _user_brief(user)
        if brief is not None:
            items.append(brief)
    return items


def _filter_users_by_keyword(queryset, relation_name: str, keyword: str):
    text = _normalize_optional_text(keyword)
    if not text:
        return queryset
    return queryset.filter(
        Q(**{f'{relation_name}__username__icontains': text})
        | Q(**{f'{relation_name}__name__icontains': text})
    ).distinct()


def _filter_by_exact_values(queryset, field_name: str, values: Any):
    normalized_values = _normalize_text_list(values)
    if not normalized_values:
        return queryset
    return queryset.filter(**{f'{field_name}__in': normalized_values})


def _fetch_ordered_objects(model: Type[Any], ids: list[str], label: str):
    normalized_ids = _normalize_text_list(ids)
    if not normalized_ids:
        return []

    queryset = model.objects.filter(id__in=normalized_ids, is_deleted=False)
    objects = list(queryset)
    mapping = {str(item.id): item for item in objects}
    missing = [item_id for item_id in normalized_ids if item_id not in mapping]
    if missing:
        raise HttpError(422, f'{label}不存在: {missing[0]}')
    return [mapping[item_id] for item_id in normalized_ids]


def _resolve_users(user_ids: list[str] | None, current_user: User) -> list[User]:
    normalized_ids = _normalize_text_list(user_ids)
    if not normalized_ids:
        normalized_ids = [str(current_user.id)]
    return _fetch_ordered_objects(User, normalized_ids, '用户')


def _relation_item(label: str, item_id: str, subtitle: str | None = None):
    return {'id': item_id, 'label': label, 'subtitle': subtitle}


def _serialize_test_case(test_case: TestCase) -> dict[str, Any]:
    owners = list(test_case.owners.all())
    return {
        'id': str(test_case.id),
        'brief': test_case.brief,
        'detail_html': test_case.detail_html or '',
        'cida_link': test_case.cida_link,
        'owner_ids': [str(item.id) for item in owners],
        'owner_info': _users_brief(owners),
        'display_name': test_case.brief,
        'sys_create_datetime': _format_datetime(test_case.sys_create_datetime),
        'sys_update_datetime': _format_datetime(test_case.sys_update_datetime),
    }


def _serialize_interception_strategy(strategy: InterceptionStrategy) -> dict[str, Any]:
    owners = list(strategy.owners.all())
    return {
        'id': str(strategy.id),
        'interception_item': strategy.interception_item,
        'version_detection_html': strategy.version_detection_html or '',
        'station': strategy.station,
        'owner_ids': [str(item.id) for item in owners],
        'owner_info': _users_brief(owners),
        'display_name': strategy.interception_item,
        'sys_create_datetime': _format_datetime(strategy.sys_create_datetime),
        'sys_update_datetime': _format_datetime(strategy.sys_update_datetime),
    }


def _serialize_observation_method(method: ObservationMethod) -> dict[str, Any]:
    owners = list(method.owners.all())
    label = method.log_keyword or method.log_id or method.monitor_type or method.log_path or '未命名维测项'
    return {
        'id': str(method.id),
        'monitor_type': method.monitor_type,
        'log_id': method.log_id,
        'log_keyword': method.log_keyword,
        'log_path': method.log_path,
        'owner_ids': [str(item.id) for item in owners],
        'owner_info': _users_brief(owners),
        'display_name': label,
        'sys_create_datetime': _format_datetime(method.sys_create_datetime),
        'sys_update_datetime': _format_datetime(method.sys_update_datetime),
    }


def _serialize_huatuo_diagnosis(diagnosis: HuatuoDiagnosis) -> dict[str, Any]:
    owners = list(diagnosis.owners.all())
    description = diagnosis.description or ''
    label = description if len(description) <= 60 else f'{description[:60]}...'
    return {
        'id': str(diagnosis.id),
        'description': description,
        'owner_ids': [str(item.id) for item in owners],
        'owner_info': _users_brief(owners),
        'display_name': label,
        'sys_create_datetime': _format_datetime(diagnosis.sys_create_datetime),
        'sys_update_datetime': _format_datetime(diagnosis.sys_update_datetime),
    }


def _serialize_handling_measure(measure: HandlingMeasure) -> dict[str, Any]:
    owners = list(measure.owners.all())
    ordered_relations = sorted(
        measure.test_case_relations.all(),
        key=lambda item: (item.order_index, item.sys_create_datetime),
    )
    test_case_items = [
        _relation_item(
            relation.test_case.brief,
            str(relation.test_case_id),
            relation.test_case.cida_link,
        )
        for relation in ordered_relations
    ]
    return {
        'id': str(measure.id),
        'measure_category': measure.measure_category,
        'measure': measure.measure,
        'measure_detail_html': measure.measure_detail_html or '',
        'measure_effect': measure.measure_effect or '',
        'owner_ids': [str(item.id) for item in owners],
        'owner_info': _users_brief(owners),
        'test_case_ids': [str(relation.test_case_id) for relation in ordered_relations],
        'test_case_items': test_case_items,
        'display_name': measure.measure,
        'sys_create_datetime': _format_datetime(measure.sys_create_datetime),
        'sys_update_datetime': _format_datetime(measure.sys_update_datetime),
    }


def _build_failure_mode_scope_binding_items(failure_mode: FailureMode) -> list[dict[str, str | None]]:
    bindings = list(
        ProductFailureMode.objects.filter(
            is_deleted=False,
            failure_mode_id=failure_mode.id,
            product__is_deleted=False,
        )
        .select_related('product__project')
        .order_by('product__project__name', 'subsystem', 'sys_create_datetime')
    )
    result: list[dict[str, str | None]] = []
    seen: set[tuple[str, str]] = set()
    for binding in bindings:
        product_id = str(binding.product_id)
        subsystem = _normalize_optional_text(binding.subsystem)
        if not product_id or not subsystem:
            continue
        key = (product_id, subsystem)
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                'product_id': product_id,
                'product_name': binding.product.project.name if binding.product and binding.product.project else '',
                'subsystem': subsystem,
            },
        )
    return result


def _serialize_failure_mode(failure_mode: FailureMode) -> dict[str, Any]:
    authors = list(failure_mode.authors.all())
    interception_relations = sorted(
        failure_mode.interception_relations.all(),
        key=lambda item: (item.order_index, item.sys_create_datetime),
    )
    handling_measure_relations = sorted(
        failure_mode.handling_measure_relations.all(),
        key=lambda item: (item.order_index, item.sys_create_datetime),
    )
    observation_relations = sorted(
        failure_mode.observation_method_relations.all(),
        key=lambda item: (item.order_index, item.sys_create_datetime),
    )
    huatuo_relations = sorted(
        failure_mode.huatuo_diagnosis_relations.all(),
        key=lambda item: (item.order_index, item.sys_create_datetime),
    )

    return {
        'id': str(failure_mode.id),
        'brief': failure_mode.brief,
        'subsystem': failure_mode.subsystem,
        'module': failure_mode.module_name,
        'chips': _normalize_text_list(failure_mode.chips),
        'fault_categories': _normalize_text_list(failure_mode.fault_categories),
        'symptoms': _normalize_text_list(failure_mode.symptoms),
        'effect_html': failure_mode.effect_html or '',
        'root_cause_html': failure_mode.root_cause_html or '',
        'functional_safety_level': failure_mode.functional_safety_level,
        'occurrence_frequency': failure_mode.occurrence_frequency,
        'detectability': failure_mode.detectability,
        'severity': failure_mode.severity,
        'author_ids': [str(item.id) for item in authors],
        'author_info': _users_brief(authors),
        'related_dts_nos': _normalize_text_list(failure_mode.related_dts_nos),
        'status': failure_mode.status,
        'scope_bindings': _build_failure_mode_scope_binding_items(failure_mode),
        'source_type': failure_mode.source_type,
        'source_task_id': str(failure_mode.source_task_id) if failure_mode.source_task_id else None,
        'source_task_no': getattr(getattr(failure_mode, 'source_task', None), 'task_no', None),
        'interception_required': bool(failure_mode.interception_required),
        'huatuo_required': bool(failure_mode.huatuo_required),
        'required_handling_measure_categories': _normalize_enum_list(
            failure_mode.required_handling_measure_categories,
            FIXED_HANDLING_MEASURE_CATEGORIES,
        ),
        'required_observation_method_types': _normalize_enum_list(
            failure_mode.required_observation_method_types,
            FIXED_OBSERVATION_METHOD_TYPES,
        ),
        'interception_strategy_ids': [str(item.interception_strategy_id) for item in interception_relations],
        'interception_strategy_items': [
            _relation_item(
                item.interception_strategy.interception_item,
                str(item.interception_strategy_id),
                item.interception_strategy.station,
            )
            for item in interception_relations
        ],
        'handling_measure_ids': [str(item.handling_measure_id) for item in handling_measure_relations],
        'handling_measure_items': [
            _relation_item(
                item.handling_measure.measure,
                str(item.handling_measure_id),
                item.handling_measure.measure_category,
            )
            for item in handling_measure_relations
        ],
        'observation_method_ids': [str(item.observation_method_id) for item in observation_relations],
        'observation_method_items': [
            _relation_item(
                item.observation_method.log_keyword
                or item.observation_method.log_id
                or item.observation_method.monitor_type
                or item.observation_method.log_path
                or '未命名维测项',
                str(item.observation_method_id),
                item.observation_method.monitor_type,
            )
            for item in observation_relations
        ],
        'huatuo_diagnosis_ids': [str(item.huatuo_diagnosis_id) for item in huatuo_relations],
        'huatuo_diagnosis_items': [
            _relation_item(
                item.huatuo_diagnosis.description[:60]
                + ('...' if len(item.huatuo_diagnosis.description) > 60 else ''),
                str(item.huatuo_diagnosis_id),
                None,
            )
            for item in huatuo_relations
        ],
        'sys_create_datetime': _format_datetime(failure_mode.sys_create_datetime),
        'sys_update_datetime': _format_datetime(failure_mode.sys_update_datetime),
    }


def _serialize_subsystem_config(config: FailureModeSubsystemConfig) -> dict[str, Any]:
    return {
        'id': str(config.id),
        'subsystem': config.subsystem,
        'module_options': _normalize_text_list(config.module_options),
        'chip_options': _normalize_text_list(config.chip_options),
        'sys_create_datetime': _format_datetime(config.sys_create_datetime),
        'sys_update_datetime': _format_datetime(config.sys_update_datetime),
    }


def _failure_mode_queryset():
    return FailureMode.objects.filter(is_deleted=False).select_related('source_task').prefetch_related(
        'authors',
        Prefetch(
            'interception_relations',
            queryset=FailureModeInterceptionStrategyRel.objects.select_related('interception_strategy').order_by('order_index', 'sys_create_datetime'),
        ),
        Prefetch(
            'handling_measure_relations',
            queryset=FailureModeHandlingMeasureRel.objects.select_related('handling_measure').order_by('order_index', 'sys_create_datetime'),
        ),
        Prefetch(
            'observation_method_relations',
            queryset=FailureModeObservationMethodRel.objects.select_related('observation_method').order_by('order_index', 'sys_create_datetime'),
        ),
        Prefetch(
            'huatuo_diagnosis_relations',
            queryset=FailureModeHuatuoDiagnosisRel.objects.select_related('huatuo_diagnosis').order_by('order_index', 'sys_create_datetime'),
        ),
    )


def _interception_strategy_queryset():
    return InterceptionStrategy.objects.filter(is_deleted=False).prefetch_related('owners')


def _handling_measure_queryset():
    return HandlingMeasure.objects.filter(is_deleted=False).prefetch_related(
        'owners',
        Prefetch(
            'test_case_relations',
            queryset=HandlingMeasureTestCaseRel.objects.select_related('test_case').order_by('order_index', 'sys_create_datetime'),
        ),
    )


def _observation_method_queryset():
    return ObservationMethod.objects.filter(is_deleted=False).prefetch_related('owners')


def _huatuo_diagnosis_queryset():
    return HuatuoDiagnosis.objects.filter(is_deleted=False).prefetch_related('owners')


def _test_case_queryset():
    return TestCase.objects.filter(is_deleted=False).prefetch_related('owners')


def _subsystem_config_queryset():
    return FailureModeSubsystemConfig.objects.filter(is_deleted=False).order_by('subsystem', '-sort', 'sys_create_datetime')


def _sync_owner_relation(instance, relation_name: str, owner_ids: list[str] | None, current_user: User):
    owners = _resolve_users(owner_ids, current_user)
    getattr(instance, relation_name).set(owners)


def _sync_ordered_relations(
    *,
    parent,
    ids: list[str] | None,
    relation_model,
    target_model,
    relation_field_name: str,
    parent_field_name: str,
    label: str,
    current_user: User,
):
    relation_model.objects.filter(**{parent_field_name: parent}).delete()
    targets = _fetch_ordered_objects(target_model, ids or [], label)
    for index, target in enumerate(targets):
        relation_model.objects.create(
            **{
                parent_field_name: parent,
                relation_field_name: target,
                'order_index': index,
                'sys_creator': current_user,
                'sys_modifier': current_user,
            }
        )


PRODUCT_FAILURE_MODE_RELATION_SPECS = [
    (
        'interception_relations',
        ProductFailureModeInterceptionStrategyRel,
        InterceptionStrategy,
        'interception_strategy',
        'failure_mode',
        '产线拦截策略',
    ),
    (
        'handling_measure_relations',
        ProductFailureModeHandlingMeasureRel,
        HandlingMeasure,
        'handling_measure',
        'failure_mode',
        '故障处理措施',
    ),
    (
        'observation_method_relations',
        ProductFailureModeObservationMethodRel,
        ObservationMethod,
        'observation_method',
        'failure_mode',
        '维测手段',
    ),
    (
        'huatuo_diagnosis_relations',
        ProductFailureModeHuatuoDiagnosisRel,
        HuatuoDiagnosis,
        'huatuo_diagnosis',
        'failure_mode',
        '华佗诊断方案',
    ),
]


def _sync_product_failure_mode_relations_from_template(
    product_failure_mode: ProductFailureMode,
    failure_mode: FailureMode,
    current_user: User,
):
    for global_relation_name, relation_model, target_model, relation_field_name, parent_field_name, label in PRODUCT_FAILURE_MODE_RELATION_SPECS:
        relation_ids = _extract_current_relation_ids(
            failure_mode,
            global_relation_name,
            relation_field_name,
        )
        _sync_ordered_relations(
            parent=product_failure_mode,
            ids=relation_ids,
            relation_model=relation_model,
            target_model=target_model,
            relation_field_name=relation_field_name,
            parent_field_name=parent_field_name,
            label=label,
            current_user=current_user,
        )


def _seed_product_failure_mode_landings_from_relations(
    product_failure_mode: ProductFailureMode,
    current_user: User,
):
    interception_rows = [
        ProductFailureModeInterceptionLanding(
            product_failure_mode=product_failure_mode,
            interception_strategy_id=item.interception_strategy_id,
            is_landed=False,
            sys_creator=current_user,
            sys_modifier=current_user,
        )
        for item in product_failure_mode.interception_relations.all()
    ]
    handling_rows = [
        ProductFailureModeHandlingLanding(
            product_failure_mode=product_failure_mode,
            handling_measure_id=item.handling_measure_id,
            is_landed=False,
            sys_creator=current_user,
            sys_modifier=current_user,
        )
        for item in product_failure_mode.handling_measure_relations.all()
    ]
    observation_rows = [
        ProductFailureModeObservationLanding(
            product_failure_mode=product_failure_mode,
            observation_method_id=item.observation_method_id,
            is_landed=False,
            sys_creator=current_user,
            sys_modifier=current_user,
        )
        for item in product_failure_mode.observation_method_relations.all()
    ]
    huatuo_rows = [
        ProductFailureModeHuatuoLanding(
            product_failure_mode=product_failure_mode,
            huatuo_diagnosis_id=item.huatuo_diagnosis_id,
            is_landed=False,
            sys_creator=current_user,
            sys_modifier=current_user,
        )
        for item in product_failure_mode.huatuo_diagnosis_relations.all()
    ]
    if interception_rows:
        ProductFailureModeInterceptionLanding.objects.bulk_create(interception_rows)
    if handling_rows:
        ProductFailureModeHandlingLanding.objects.bulk_create(handling_rows)
    if observation_rows:
        ProductFailureModeObservationLanding.objects.bulk_create(observation_rows)
    if huatuo_rows:
        ProductFailureModeHuatuoLanding.objects.bulk_create(huatuo_rows)


@transaction.atomic
def _sync_failure_mode_scope_bindings(
    instance: FailureMode,
    scope_bindings: Any,
    current_user: User,
):
    normalized_bindings = _normalize_scope_bindings(scope_bindings)
    normalized_product_ids = _normalize_text_list(
        [item['product_id'] for item in normalized_bindings],
    )
    products = _fetch_ordered_objects(FailureModeProduct, normalized_product_ids, '产品')
    product_map = {str(item.id): item for item in products}

    existing_bindings = {
        (str(item.product_id), _normalize_optional_text(item.subsystem) or '')
        for item in ProductFailureMode.objects.filter(
            failure_mode=instance,
            is_deleted=False,
        ).only('product_id', 'subsystem')
    }
    target_bindings = {
        (
            binding['product_id'],
            binding['subsystem'],
        )
        for binding in normalized_bindings
    }

    for product_id, subsystem in target_bindings - existing_bindings:
        product = product_map.get(product_id)
        if not product:
            raise HttpError(422, f'产品不存在: {product_id}')
        product_failure_mode = ProductFailureMode.objects.create(
            product=product,
            subsystem=subsystem,
            failure_mode=instance,
            sys_creator=current_user,
            sys_modifier=current_user,
        )
        _sync_product_failure_mode_relations_from_template(
            product_failure_mode,
            instance,
            current_user,
        )
        _seed_product_failure_mode_landings_from_relations(
            product_failure_mode,
            current_user,
        )

    for product_id, subsystem in existing_bindings - target_bindings:
        ProductFailureMode.objects.filter(
            failure_mode=instance,
            product_id=product_id,
            subsystem=subsystem,
        ).delete()

    instance.scope_bindings = normalized_bindings
    instance.sys_modifier = current_user
    instance.save(update_fields=['scope_bindings', 'sys_modifier', 'sys_update_datetime'])


def _serialize_paginated_queryset(queryset, serializer, pagination=None):
    if pagination is None:
        return [serializer(item) for item in queryset]

    page = max(getattr(pagination, 'page', 1), 1)
    page_size = max(getattr(pagination, 'pageSize', 10), 1)
    offset = page_size * (page - 1)
    page_queryset = queryset[offset: offset + page_size]
    return {
        'items': [serializer(item) for item in page_queryset],
        'total': queryset.count(),
    }


def _resolve_insight_landing_status(flags: list[bool]) -> str:
    if not flags:
        return '未落地'
    if all(flags):
        return '已落地'
    if any(flags):
        return '部分落地'
    return '未落地'


def _derive_product_failure_mode_is_landed(binding: ProductFailureMode) -> bool:
    landing_flags: list[bool] = []
    for relation_name in (
        'interception_landings',
        'handling_landings',
        'observation_landings',
        'huatuo_landings',
    ):
        relation_manager = getattr(binding, relation_name, None)
        if not hasattr(relation_manager, 'all'):
            continue
        landing_flags.extend(
            bool(item.is_landed)
            for item in relation_manager.all()
            if not getattr(item, 'is_deleted', False)
        )
    return bool(landing_flags) and all(landing_flags)


def _build_failure_mode_insight_landing_row(
    *,
    item_id: str,
    label: str,
    flags: list[bool],
    subtitle: str | None = None,
) -> dict[str, Any]:
    return {
        'id': item_id,
        'label': label,
        'subtitle': subtitle,
        'status': _resolve_insight_landing_status(flags),
    }


def _build_failure_mode_insight_product_payload(
    failure_mode_id: str,
) -> dict[str, Any]:
    relations = list(
        ProductFailureMode.objects.filter(
            is_deleted=False,
            failure_mode_id=failure_mode_id,
            product__is_deleted=False,
        )
        .select_related('product__owner', 'product__project')
        .prefetch_related(
            Prefetch(
                'interception_landings',
                queryset=ProductFailureModeInterceptionLanding.objects.filter(
                    is_deleted=False,
                ).select_related('interception_strategy'),
            ),
            Prefetch(
                'handling_landings',
                queryset=ProductFailureModeHandlingLanding.objects.filter(
                    is_deleted=False,
                ).select_related('handling_measure'),
            ),
            Prefetch(
                'observation_landings',
                queryset=ProductFailureModeObservationLanding.objects.filter(
                    is_deleted=False,
                ).select_related('observation_method'),
            ),
            Prefetch(
                'huatuo_landings',
                queryset=ProductFailureModeHuatuoLanding.objects.filter(
                    is_deleted=False,
                ).select_related('huatuo_diagnosis'),
            ),
        )
        .order_by('product__project__name', 'subsystem', '-sys_update_datetime')
    )
    grouped: dict[str, dict[str, Any]] = {}
    for relation in relations:
        product = relation.product
        product_id = str(product.id)
        row = grouped.get(product_id)
        if row is None:
            row = {
                'product_id': product_id,
                'product_name': product.project.name if product.project else '',
                'owner_info': _user_brief(product.owner),
                'subsystems': [],
                'failure_mode_status': '未落地',
                'interception_rows': [],
                'handling_rows': [],
                'observation_rows': [],
                'huatuo_rows': [],
                'landed_at': None,
                '_landed_at_raw': None,
                '_subsystem_seen': set(),
                '_failure_mode_flags': [],
                '_interception_items': {},
                '_handling_items': {},
                '_observation_items': {},
                '_huatuo_items': {},
            }
            grouped[product_id] = row

        subsystem_seen = row['_subsystem_seen']
        subsystem = _normalize_optional_text(relation.subsystem)
        if subsystem and subsystem not in subsystem_seen:
            subsystem_seen.add(subsystem)
            row['subsystems'].append(subsystem)

        derived_failure_mode_landed = _derive_product_failure_mode_is_landed(relation)
        row['_failure_mode_flags'].append(derived_failure_mode_landed)
        current_landed_at = row['_landed_at_raw']
        if derived_failure_mode_landed and (
            current_landed_at is None
            or (
                relation.sys_update_datetime
                and relation.sys_update_datetime > current_landed_at
            )
        ):
            row['_landed_at_raw'] = relation.sys_update_datetime
            row['landed_at'] = _format_datetime(relation.sys_update_datetime)

        for landing in relation.interception_landings.all():
            if not landing.interception_strategy:
                continue
            cache = row['_interception_items'].setdefault(
                str(landing.interception_strategy_id),
                {
                    'id': str(landing.interception_strategy_id),
                    'label': landing.interception_strategy.interception_item,
                    'subtitle': None,
                    'flags': [],
                },
            )
            cache['flags'].append(bool(landing.is_landed))

        for landing in relation.handling_landings.all():
            if not landing.handling_measure:
                continue
            cache = row['_handling_items'].setdefault(
                str(landing.handling_measure_id),
                {
                    'id': str(landing.handling_measure_id),
                    'label': landing.handling_measure.measure,
                    'subtitle': _normalize_optional_text(
                        landing.handling_measure.measure_category,
                    ),
                    'flags': [],
                },
            )
            cache['flags'].append(bool(landing.is_landed))

        for landing in relation.observation_landings.all():
            if not landing.observation_method:
                continue
            cache = row['_observation_items'].setdefault(
                str(landing.observation_method_id),
                {
                    'id': str(landing.observation_method_id),
                    'label': (
                        landing.observation_method.log_keyword
                        or landing.observation_method.log_id
                        or landing.observation_method.monitor_type
                        or landing.observation_method.log_path
                        or '未命名维测项'
                    ),
                    'subtitle': _normalize_optional_text(
                        landing.observation_method.monitor_type,
                    ),
                    'flags': [],
                },
            )
            cache['flags'].append(bool(landing.is_landed))

        for landing in relation.huatuo_landings.all():
            if not landing.huatuo_diagnosis:
                continue
            cache = row['_huatuo_items'].setdefault(
                str(landing.huatuo_diagnosis_id),
                {
                    'id': str(landing.huatuo_diagnosis_id),
                    'label': landing.huatuo_diagnosis.description,
                    'subtitle': None,
                    'flags': [],
                },
            )
            cache['flags'].append(bool(landing.is_landed))

    rows: list[dict[str, Any]] = []
    landed_product_count = 0
    for row in sorted(
        grouped.values(),
        key=lambda item: (item['product_name'], item['product_id']),
    ):
        row['failure_mode_status'] = _resolve_insight_landing_status(
            row['_failure_mode_flags'],
        )
        if row['failure_mode_status'] == '已落地':
            landed_product_count += 1
        row['interception_rows'] = [
            _build_failure_mode_insight_landing_row(
                item_id=item['id'],
                label=item['label'],
                subtitle=item['subtitle'],
                flags=item['flags'],
            )
            for item in sorted(
                row['_interception_items'].values(),
                key=lambda item: (item['label'], item['id']),
            )
        ]
        row['handling_rows'] = [
            _build_failure_mode_insight_landing_row(
                item_id=item['id'],
                label=item['label'],
                subtitle=item['subtitle'],
                flags=item['flags'],
            )
            for item in sorted(
                row['_handling_items'].values(),
                key=lambda item: (item['subtitle'] or '', item['label'], item['id']),
            )
        ]
        row['observation_rows'] = [
            _build_failure_mode_insight_landing_row(
                item_id=item['id'],
                label=item['label'],
                subtitle=item['subtitle'],
                flags=item['flags'],
            )
            for item in sorted(
                row['_observation_items'].values(),
                key=lambda item: (item['subtitle'] or '', item['label'], item['id']),
            )
        ]
        row['huatuo_rows'] = [
            _build_failure_mode_insight_landing_row(
                item_id=item['id'],
                label=item['label'],
                subtitle=item['subtitle'],
                flags=item['flags'],
            )
            for item in sorted(
                row['_huatuo_items'].values(),
                key=lambda item: (item['label'], item['id']),
            )
        ]
        rows.append(
            {
                key: value
                for key, value in row.items()
                if not key.startswith('_')
            },
        )

    return {
        'landed_product_count': landed_product_count,
        'product_rows': rows,
        'related_product_count': len(rows),
    }


def _dedupe_failure_modes(failure_modes: Iterable[FailureMode]) -> list[FailureMode]:
    rows: list[FailureMode] = []
    seen: set[str] = set()
    for item in failure_modes:
        item_id = str(item.id)
        if item_id in seen:
            continue
        seen.add(item_id)
        rows.append(item)
    return rows


def _build_resource_insight_rows(
    failure_modes: Iterable[FailureMode],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_failure_modes = _dedupe_failure_modes(failure_modes)
    failure_mode_ids = [str(item.id) for item in normalized_failure_modes]
    if not failure_mode_ids:
        return [], []

    bindings = list(
        ProductFailureMode.objects.filter(
            is_deleted=False,
            failure_mode_id__in=failure_mode_ids,
            product__is_deleted=False,
        )
        .select_related('product__owner', 'product__project', 'failure_mode')
        .order_by('product__project__name', 'subsystem', '-sys_create_datetime')
    )
    product_binding_map: dict[str, list[ProductFailureMode]] = defaultdict(list)
    for binding in bindings:
        product_binding_map[str(binding.failure_mode_id)].append(binding)

    failure_mode_rows: list[dict[str, Any]] = []
    product_rows_map: dict[str, dict[str, Any]] = {}

    for failure_mode in normalized_failure_modes:
        failure_mode_binding_rows = product_binding_map.get(str(failure_mode.id), [])
        product_names: list[str] = []
        product_id_seen: set[str] = set()

        for binding in failure_mode_binding_rows:
            product = binding.product
            product_id = str(product.id)
            product_name = product.project.name if product.project else ''
            if product_id not in product_id_seen:
                product_id_seen.add(product_id)
                product_names.append(product_name)

            product_row = product_rows_map.get(product_id)
            if product_row is None:
                product_row = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'owner_info': _user_brief(product.owner),
                    'failure_mode_briefs': [],
                    '_failure_mode_seen': set(),
                }
                product_rows_map[product_id] = product_row

            failure_mode_seen = product_row['_failure_mode_seen']
            if failure_mode.brief not in failure_mode_seen:
                failure_mode_seen.add(failure_mode.brief)
                product_row['failure_mode_briefs'].append(failure_mode.brief)

        failure_mode_rows.append(
            {
                'failure_mode_id': str(failure_mode.id),
                'failure_mode_brief': failure_mode.brief,
                'subsystem': failure_mode.subsystem,
                'status': failure_mode.status,
                'product_names': product_names,
                'landed_product_count': len(product_names),
            }
        )

    product_rows = [
        {
            key: value
            for key, value in row.items()
            if not key.startswith('_')
        }
        for row in sorted(
            product_rows_map.values(),
            key=lambda item: (item['product_name'], item['product_id']),
        )
    ]
    return failure_mode_rows, product_rows


def _total_failure_mode_product_count() -> int:
    return FailureModeProduct.objects.filter(is_deleted=False).count()


def _build_resource_insight_rows_by_product_landings(
    failure_modes: Iterable[FailureMode],
    *,
    landing_model,
    resource_field_name: str,
    resource_ids: Iterable[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_failure_modes = _dedupe_failure_modes(failure_modes)
    failure_mode_ids = [str(item.id) for item in normalized_failure_modes]
    normalized_resource_ids = _normalize_text_list(list(resource_ids))
    failure_mode_rows: list[dict[str, Any]] = [
        {
            'failure_mode_id': str(item.id),
            'failure_mode_brief': item.brief,
            'subsystem': item.subsystem,
            'status': item.status,
            'product_names': [],
            'landed_product_count': 0,
        }
        for item in normalized_failure_modes
    ]
    if not failure_mode_ids or not normalized_resource_ids:
        return failure_mode_rows, []

    landed_rows = list(
        landing_model.objects.filter(
            is_deleted=False,
            is_landed=True,
            product_failure_mode__is_deleted=False,
            product_failure_mode__product__is_deleted=False,
            product_failure_mode__failure_mode_id__in=failure_mode_ids,
            **{f'{resource_field_name}__in': normalized_resource_ids},
        )
        .select_related(
            'product_failure_mode__product__owner',
            'product_failure_mode__product__project',
            'product_failure_mode__failure_mode',
        )
        .order_by(
            'product_failure_mode__product__project__name',
            'product_failure_mode__subsystem',
            '-product_failure_mode__sys_update_datetime',
        )
    )

    failure_mode_product_names: dict[str, list[str]] = defaultdict(list)
    failure_mode_product_seen: dict[str, set[str]] = defaultdict(set)
    product_rows_map: dict[str, dict[str, Any]] = {}

    for landed_row in landed_rows:
        product_failure_mode = landed_row.product_failure_mode
        product = product_failure_mode.product
        if not product:
            continue
        product_id = str(product.id)
        product_name = product.project.name if product.project else ''
        failure_mode_id = str(product_failure_mode.failure_mode_id)
        if product_id not in failure_mode_product_seen[failure_mode_id]:
            failure_mode_product_seen[failure_mode_id].add(product_id)
            failure_mode_product_names[failure_mode_id].append(product_name)

        product_row = product_rows_map.get(product_id)
        if product_row is None:
            product_row = {
                'product_id': product_id,
                'product_name': product_name,
                'owner_info': _user_brief(product.owner),
                'failure_mode_briefs': [],
                '_failure_mode_seen': set(),
            }
            product_rows_map[product_id] = product_row
        if (
            product_failure_mode.failure_mode
            and product_failure_mode.failure_mode.brief
            and product_failure_mode.failure_mode.brief not in product_row['_failure_mode_seen']
        ):
            product_row['_failure_mode_seen'].add(
                product_failure_mode.failure_mode.brief,
            )
            product_row['failure_mode_briefs'].append(
                product_failure_mode.failure_mode.brief,
            )

    for row in failure_mode_rows:
        product_names = failure_mode_product_names.get(row['failure_mode_id'], [])
        row['product_names'] = product_names
        row['landed_product_count'] = len(product_names)

    product_rows = [
        {
            key: value
            for key, value in row.items()
            if not key.startswith('_')
        }
        for row in sorted(
            product_rows_map.values(),
            key=lambda item: (item['product_name'], item['product_id']),
        )
    ]
    return failure_mode_rows, product_rows


def _build_interception_insight_data(item_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    relations = list(
        FailureModeInterceptionStrategyRel.objects.filter(
            is_deleted=False,
            interception_strategy_id=item_id,
            failure_mode__is_deleted=False,
        )
        .select_related('failure_mode')
        .order_by('order_index', 'sys_create_datetime')
    )
    return _build_resource_insight_rows_by_product_landings(
        [item.failure_mode for item in relations],
        landing_model=ProductFailureModeInterceptionLanding,
        resource_field_name='interception_strategy_id',
        resource_ids=[item_id],
    )


def _load_dict_grouped(field_names: Iterable[str] | None = None) -> dict[str, list[str]]:
    target_fields = list(field_names or DICT_CODE_MAP.keys())
    target_codes = [DICT_CODE_MAP[field] for field in target_fields if field in DICT_CODE_MAP]
    rows = (
        DictItem.objects.select_related('dict')
        .filter(
            dict__code__in=target_codes,
            dict__status=True,
            dict__is_deleted=False,
            status=True,
            is_deleted=False,
        )
        .order_by('dict__code', '-sort', 'sys_create_datetime')
    )

    reverse_map = {DICT_CODE_MAP[field]: field for field in target_fields if field in DICT_CODE_MAP}
    grouped: dict[str, list[str]] = {field: [] for field in target_fields}
    seen: dict[str, set[str]] = {field: set() for field in target_fields}

    for item in rows:
        dict_obj = getattr(item, 'dict', None)
        dict_code = _normalize_optional_text(getattr(dict_obj, 'code', ''))
        if not dict_code or dict_code not in reverse_map:
            continue
        field = reverse_map[dict_code]
        label = _normalize_optional_text(getattr(item, 'label', '') or getattr(item, 'value', ''))
        if not label or label in seen[field]:
            continue
        seen[field].add(label)
        grouped[field].append(label)

    return grouped


def _build_subsystem_config_options() -> dict[str, Any]:
    dict_grouped = _load_dict_grouped(['subsystem', 'module', 'chip'])
    configs = list(_subsystem_config_queryset())
    failure_modes = list(FailureMode.objects.filter(is_deleted=False).only('subsystem', 'module_name', 'chips'))

    item_map: dict[str, dict[str, Any]] = {}

    def ensure_item(subsystem: str):
        item = item_map.get(subsystem)
        if item is None:
            item = {
                'subsystem': subsystem,
                'module_options': [],
                'chip_options': [],
                '_module_seen': set(),
                '_chip_seen': set(),
            }
            item_map[subsystem] = item
        return item

    global_module_options: list[str] = []
    global_module_seen: set[str] = set()
    global_chip_options: list[str] = []
    global_chip_seen: set[str] = set()

    for config in configs:
        item = ensure_item(config.subsystem)
        for value in _normalize_text_list(config.module_options):
            _append_unique_text(item['module_options'], item['_module_seen'], value)
            _append_unique_text(global_module_options, global_module_seen, value)
        for value in _normalize_text_list(config.chip_options):
            _append_unique_text(item['chip_options'], item['_chip_seen'], value)
            _append_unique_text(global_chip_options, global_chip_seen, value)

    for failure_mode in failure_modes:
        subsystem = _normalize_optional_text(failure_mode.subsystem)
        module_name = _normalize_optional_text(failure_mode.module_name)
        chips = _normalize_text_list(failure_mode.chips)
        if subsystem:
            item = ensure_item(subsystem)
            _append_unique_text(item['module_options'], item['_module_seen'], module_name)
            for chip in chips:
                _append_unique_text(item['chip_options'], item['_chip_seen'], chip)
        _append_unique_text(global_module_options, global_module_seen, module_name)
        for chip in chips:
            _append_unique_text(global_chip_options, global_chip_seen, chip)

    for subsystem in dict_grouped.get('subsystem', []):
        ensure_item(subsystem)
    for value in dict_grouped.get('module', []):
        _append_unique_text(global_module_options, global_module_seen, value)
    for value in dict_grouped.get('chip', []):
        _append_unique_text(global_chip_options, global_chip_seen, value)

    dict_subsystems = set(dict_grouped.get('subsystem', []))
    for subsystem, item in item_map.items():
        if subsystem in dict_subsystems and not item['module_options']:
            item['module_options'] = list(global_module_options)
            item['_module_seen'] = set(global_module_options)
        if subsystem in dict_subsystems and not item['chip_options']:
            item['chip_options'] = list(global_chip_options)
            item['_chip_seen'] = set(global_chip_options)

    items = sorted(
        [
            {
                'subsystem': subsystem,
                'module_options': item['module_options'],
                'chip_options': item['chip_options'],
            }
            for subsystem, item in item_map.items()
        ],
        key=lambda item: item['subsystem'],
    )

    subsystem_options = _build_option_list(item['subsystem'] for item in items)
    module_options = _build_option_list(global_module_options + dict_grouped.get('module', []))
    chip_options = _build_option_list(global_chip_options + dict_grouped.get('chip', []))

    return {
        'subsystem_options': subsystem_options,
        'module_options': module_options,
        'chip_options': chip_options,
        'items': items,
    }


def _build_subsystem_option_lookup() -> dict[str, dict[str, list[str]]]:
    options = _build_subsystem_config_options()
    return {
        item['subsystem']: {
            'module_options': _normalize_text_list(item.get('module_options')),
            'chip_options': _normalize_text_list(item.get('chip_options')),
        }
        for item in options['items']
    }


def _sanitize_subsystem_fields(payload: dict[str, Any]) -> dict[str, Any]:
    subsystem = _normalize_optional_text(payload.get('subsystem'))
    module_name = _normalize_optional_text(payload.get('module'))
    chips = _normalize_text_list(payload.get('chips'))
    if not subsystem:
        payload['subsystem'] = subsystem
        payload['module'] = module_name
        payload['chips'] = chips
        return payload

    option_lookup = _build_subsystem_option_lookup()
    config = option_lookup.get(subsystem)
    if config is None:
        payload['subsystem'] = subsystem
        payload['module'] = module_name
        payload['chips'] = chips
        return payload

    allowed_modules = set(_normalize_text_list(config.get('module_options')))
    allowed_chips = set(_normalize_text_list(config.get('chip_options')))
    if module_name and allowed_modules and module_name not in allowed_modules:
        module_name = None
    if allowed_chips:
        chips = [chip for chip in chips if chip in allowed_chips]

    payload['subsystem'] = subsystem
    payload['module'] = module_name
    payload['chips'] = chips
    return payload


def _failure_mode_attrs(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _sanitize_subsystem_fields(dict(payload))
    attrs = {
        'brief': _normalize_optional_text(payload.get('brief')),
        'subsystem': _normalize_optional_text(payload.get('subsystem')),
        'module_name': _normalize_optional_text(payload.get('module')),
        'chips': _normalize_text_list(payload.get('chips')),
        'fault_categories': _normalize_text_list(payload.get('fault_categories')),
        'symptoms': _normalize_text_list(payload.get('symptoms')),
        'effect_html': _normalize_html_text(payload.get('effect_html')),
        'root_cause_html': _normalize_html_text(payload.get('root_cause_html')),
        'functional_safety_level': _normalize_optional_text(payload.get('functional_safety_level')),
        'occurrence_frequency': _normalize_optional_text(payload.get('occurrence_frequency')),
        'detectability': _normalize_optional_text(payload.get('detectability')),
        'severity': _normalize_optional_text(payload.get('severity')),
        'related_dts_nos': _normalize_text_list(payload.get('related_dts_nos')),
        'scope_bindings': _normalize_scope_bindings(payload.get('scope_bindings')),
        'status': _normalize_optional_text(payload.get('status')),
        'source_type': _normalize_failure_mode_source_type(payload.get('source_type')),
        'source_task_id': _normalize_optional_text(payload.get('source_task_id')),
        'interception_required': _normalize_bool(payload.get('interception_required')),
        'huatuo_required': _normalize_bool(payload.get('huatuo_required')),
        'required_handling_measure_categories': _normalize_enum_list(
            payload.get('required_handling_measure_categories'),
            FIXED_HANDLING_MEASURE_CATEGORIES,
        ),
        'required_observation_method_types': _normalize_enum_list(
            payload.get('required_observation_method_types'),
            FIXED_OBSERVATION_METHOD_TYPES,
        ),
    }
    if attrs['source_type'] == FailureMode.SOURCE_TYPE_MANUAL:
        attrs['source_task_id'] = None
    if not attrs['brief']:
        raise HttpError(422, 'brief 不能为空')
    return attrs


def _update_failure_mode_attrs(instance: FailureMode, payload: dict[str, Any]):
    payload = _sanitize_subsystem_fields(dict(payload))
    mapping = {
        'brief': ('brief', _normalize_optional_text),
        'subsystem': ('subsystem', _normalize_optional_text),
        'module': ('module_name', _normalize_optional_text),
        'chips': ('chips', _normalize_text_list),
        'fault_categories': ('fault_categories', _normalize_text_list),
        'symptoms': ('symptoms', _normalize_text_list),
        'effect_html': ('effect_html', _normalize_html_text),
        'root_cause_html': ('root_cause_html', _normalize_html_text),
        'functional_safety_level': ('functional_safety_level', _normalize_optional_text),
        'occurrence_frequency': ('occurrence_frequency', _normalize_optional_text),
        'detectability': ('detectability', _normalize_optional_text),
        'severity': ('severity', _normalize_optional_text),
        'related_dts_nos': ('related_dts_nos', _normalize_text_list),
        'scope_bindings': ('scope_bindings', _normalize_scope_bindings),
        'status': ('status', _normalize_optional_text),
        'interception_required': ('interception_required', _normalize_bool),
        'huatuo_required': ('huatuo_required', _normalize_bool),
        'required_handling_measure_categories': (
            'required_handling_measure_categories',
            lambda value: _normalize_enum_list(value, FIXED_HANDLING_MEASURE_CATEGORIES),
        ),
        'required_observation_method_types': (
            'required_observation_method_types',
            lambda value: _normalize_enum_list(value, FIXED_OBSERVATION_METHOD_TYPES),
        ),
    }
    for payload_key, (field_name, normalizer) in mapping.items():
        if payload_key not in payload:
            continue
        value = normalizer(payload.get(payload_key))
        if field_name == 'brief' and not value:
            raise HttpError(422, 'brief 不能为空')
        setattr(instance, field_name, value)


def _extract_current_relation_ids(instance: FailureMode, relation_name: str, field_name: str) -> list[str]:
    relations = sorted(
        getattr(instance, relation_name).all(),
        key=lambda item: (item.order_index, item.sys_create_datetime),
    )
    return [str(getattr(item, field_name)) for item in relations]


def _validate_categorized_relations(
    *,
    ids: list[str],
    label: str,
    model,
    category_attr: str,
    allowed_categories: list[str],
    explicit: bool,
) -> list[str]:
    normalized_ids = _normalize_text_list(ids)
    if not normalized_ids:
        return []
    if not allowed_categories:
        return []

    objects = _fetch_ordered_objects(model, normalized_ids, label)
    allowed_set = set(allowed_categories)
    valid_ids: list[str] = []
    invalid_names: list[str] = []

    for obj in objects:
        category = _normalize_optional_text(getattr(obj, category_attr, None))
        if category in allowed_set:
            valid_ids.append(str(obj.id))
            continue
        if explicit:
            name = (
                _normalize_optional_text(getattr(obj, 'measure', None))
                or _normalize_optional_text(getattr(obj, 'log_keyword', None))
                or _normalize_optional_text(getattr(obj, 'log_id', None))
                or _normalize_optional_text(getattr(obj, 'log_path', None))
                or _normalize_optional_text(getattr(obj, 'description', None))
                or str(obj.id)
            )
            invalid_names.append(name)

    if invalid_names:
        raise HttpError(422, f'{label}存在未勾选类别的数据: {invalid_names[0]}')

    return valid_ids


def _resolve_failure_mode_relation_plan(
    payload: dict[str, Any],
    instance: FailureMode | None = None,
) -> dict[str, Any]:
    explicit_interception = 'interception_strategy_ids' in payload
    explicit_handling = 'handling_measure_ids' in payload
    explicit_observation = 'observation_method_ids' in payload
    explicit_huatuo = 'huatuo_diagnosis_ids' in payload

    interception_required = _normalize_bool(
        payload.get('interception_required'),
        instance.interception_required if instance else False,
    )
    huatuo_required = _normalize_bool(
        payload.get('huatuo_required'),
        instance.huatuo_required if instance else False,
    )
    required_handling_categories = (
        _normalize_enum_list(
            payload.get('required_handling_measure_categories'),
            FIXED_HANDLING_MEASURE_CATEGORIES,
        )
        if 'required_handling_measure_categories' in payload or instance is None
        else _normalize_enum_list(
            instance.required_handling_measure_categories,
            FIXED_HANDLING_MEASURE_CATEGORIES,
        )
    )
    required_observation_types = (
        _normalize_enum_list(
            payload.get('required_observation_method_types'),
            FIXED_OBSERVATION_METHOD_TYPES,
        )
        if 'required_observation_method_types' in payload or instance is None
        else _normalize_enum_list(
            instance.required_observation_method_types,
            FIXED_OBSERVATION_METHOD_TYPES,
        )
    )

    interception_ids = (
        _normalize_text_list(payload.get('interception_strategy_ids'))
        if explicit_interception or instance is None
        else _extract_current_relation_ids(instance, 'interception_relations', 'interception_strategy_id')
    )
    handling_ids = (
        _normalize_text_list(payload.get('handling_measure_ids'))
        if explicit_handling or instance is None
        else _extract_current_relation_ids(instance, 'handling_measure_relations', 'handling_measure_id')
    )
    observation_ids = (
        _normalize_text_list(payload.get('observation_method_ids'))
        if explicit_observation or instance is None
        else _extract_current_relation_ids(instance, 'observation_method_relations', 'observation_method_id')
    )
    huatuo_ids = (
        _normalize_text_list(payload.get('huatuo_diagnosis_ids'))
        if explicit_huatuo or instance is None
        else _extract_current_relation_ids(instance, 'huatuo_diagnosis_relations', 'huatuo_diagnosis_id')
    )

    if not interception_required:
        interception_ids = []
    if not huatuo_required:
        huatuo_ids = []

    handling_ids = _validate_categorized_relations(
        ids=handling_ids,
        label='故障处理措施',
        model=HandlingMeasure,
        category_attr='measure_category',
        allowed_categories=required_handling_categories,
        explicit=explicit_handling,
    )
    observation_ids = _validate_categorized_relations(
        ids=observation_ids,
        label='维测手段',
        model=ObservationMethod,
        category_attr='monitor_type',
        allowed_categories=required_observation_types,
        explicit=explicit_observation,
    )

    return {
        'interception_required': interception_required,
        'huatuo_required': huatuo_required,
        'required_handling_measure_categories': required_handling_categories,
        'required_observation_method_types': required_observation_types,
        'interception_strategy_ids': interception_ids,
        'handling_measure_ids': handling_ids,
        'observation_method_ids': observation_ids,
        'huatuo_diagnosis_ids': huatuo_ids,
    }


def _normalize_failure_mode_update_fields(
    payload: dict[str, Any],
    *,
    allowed_fields: set[str] | None = None,
) -> dict[str, Any]:
    normalized_payload: dict[str, Any] = {}
    payload = _sanitize_subsystem_fields(dict(payload))
    for payload_key, normalizer in FAILURE_MODE_SIMPLE_FIELD_NORMALIZERS.items():
        if allowed_fields is not None and payload_key not in allowed_fields:
            continue
        if payload_key not in payload:
            continue
        value = normalizer(payload.get(payload_key))
        if payload_key == 'brief' and not value:
            raise HttpError(422, 'brief 不能为空')
        normalized_payload[payload_key] = value
    return normalized_payload


def _relation_triggered(payload: dict[str, Any], relation_key: str) -> bool:
    return any(field in payload for field in FAILURE_MODE_RELATION_TRIGGER_FIELDS[relation_key])


def _prepare_failure_mode_update_plan(
    instance: FailureMode,
    payload: dict[str, Any],
    current_user: User,
    *,
    allowed_fields: set[str] | None = None,
) -> dict[str, Any]:
    filtered_payload = dict(payload)
    if allowed_fields is not None:
        filtered_payload = {
            key: value for key, value in filtered_payload.items() if key in allowed_fields
        }

    relation_plan = _resolve_failure_mode_relation_plan(filtered_payload, instance)
    normalized_payload = _normalize_failure_mode_update_fields(
        filtered_payload,
        allowed_fields=allowed_fields,
    )

    if 'author_ids' in filtered_payload:
        authors = _resolve_users(filtered_payload.get('author_ids'), current_user)
        normalized_payload['author_ids'] = [str(item.id) for item in authors]

    sync_interception = _relation_triggered(filtered_payload, 'interception')
    sync_handling = _relation_triggered(filtered_payload, 'handling')
    sync_observation = _relation_triggered(filtered_payload, 'observation')
    sync_huatuo = _relation_triggered(filtered_payload, 'huatuo')

    if sync_interception:
        normalized_payload['interception_required'] = relation_plan['interception_required']
        normalized_payload['interception_strategy_ids'] = relation_plan['interception_strategy_ids']
    if sync_handling:
        normalized_payload['required_handling_measure_categories'] = relation_plan[
            'required_handling_measure_categories'
        ]
        normalized_payload['handling_measure_ids'] = relation_plan['handling_measure_ids']
    if sync_observation:
        normalized_payload['required_observation_method_types'] = relation_plan[
            'required_observation_method_types'
        ]
        normalized_payload['observation_method_ids'] = relation_plan['observation_method_ids']
    if sync_huatuo:
        normalized_payload['huatuo_required'] = relation_plan['huatuo_required']
        normalized_payload['huatuo_diagnosis_ids'] = relation_plan['huatuo_diagnosis_ids']

    return {
        'payload': normalized_payload,
        'sync_interception': sync_interception,
        'sync_handling': sync_handling,
        'sync_observation': sync_observation,
        'sync_huatuo': sync_huatuo,
    }


def _build_interception_relation_items(ids: list[str]) -> list[dict[str, str | None]]:
    items = _fetch_ordered_objects(InterceptionStrategy, ids, '产线拦截策略')
    return [
        _relation_item(item.interception_item, str(item.id), item.station)
        for item in items
    ]


def _build_handling_measure_relation_items(ids: list[str]) -> list[dict[str, str | None]]:
    items = _fetch_ordered_objects(HandlingMeasure, ids, '故障处理措施')
    return [
        _relation_item(item.measure, str(item.id), item.measure_category)
        for item in items
    ]


def _build_observation_method_relation_items(ids: list[str]) -> list[dict[str, str | None]]:
    items = _fetch_ordered_objects(ObservationMethod, ids, '维测手段')
    return [
        _relation_item(
            item.log_keyword or item.log_id or item.monitor_type or item.log_path or '未命名维测项',
            str(item.id),
            item.monitor_type,
        )
        for item in items
    ]


def _build_huatuo_relation_items(ids: list[str]) -> list[dict[str, str | None]]:
    items = _fetch_ordered_objects(HuatuoDiagnosis, ids, '华佗诊断方案')
    return [
        _relation_item(
            item.description[:60] + ('...' if len(item.description or '') > 60 else ''),
            str(item.id),
            None,
        )
        for item in items
    ]


def merge_failure_mode_snapshot(
    instance: FailureMode,
    snapshot_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    detail = _serialize_failure_mode(instance)
    payload = dict(snapshot_payload or {})
    for field_name in FAILURE_MODE_SIMPLE_FIELD_NORMALIZERS:
        if field_name in payload:
            detail[field_name] = payload[field_name]

    if 'author_ids' in payload:
        authors = _fetch_ordered_objects(User, payload.get('author_ids') or [], '用户')
        detail['author_ids'] = [str(item.id) for item in authors]
        detail['author_info'] = _users_brief(authors)

    if 'interception_strategy_ids' in payload:
        detail['interception_strategy_ids'] = _normalize_text_list(payload.get('interception_strategy_ids'))
        detail['interception_strategy_items'] = _build_interception_relation_items(
            detail['interception_strategy_ids']
        )
    if 'handling_measure_ids' in payload:
        detail['handling_measure_ids'] = _normalize_text_list(payload.get('handling_measure_ids'))
        detail['handling_measure_items'] = _build_handling_measure_relation_items(
            detail['handling_measure_ids']
        )
    if 'observation_method_ids' in payload:
        detail['observation_method_ids'] = _normalize_text_list(payload.get('observation_method_ids'))
        detail['observation_method_items'] = _build_observation_method_relation_items(
            detail['observation_method_ids']
        )
    if 'huatuo_diagnosis_ids' in payload:
        detail['huatuo_diagnosis_ids'] = _normalize_text_list(payload.get('huatuo_diagnosis_ids'))
        detail['huatuo_diagnosis_items'] = _build_huatuo_relation_items(
            detail['huatuo_diagnosis_ids']
        )
    if 'scope_bindings' in payload:
        detail['scope_bindings'] = _normalize_scope_bindings(payload.get('scope_bindings'))
    return detail


@transaction.atomic
def apply_failure_mode_snapshot(
    instance: FailureMode,
    snapshot_payload: dict[str, Any],
    current_user: User,
) -> dict[str, Any]:
    plan = _prepare_failure_mode_update_plan(instance, snapshot_payload, current_user)
    normalized_payload = plan['payload']
    for payload_key, value in normalized_payload.items():
        field_name = FAILURE_MODE_MODEL_FIELD_MAP.get(payload_key)
        if field_name:
            setattr(instance, field_name, value)

    instance.sys_modifier = current_user
    instance.save()

    if 'author_ids' in normalized_payload:
        _sync_owner_relation(instance, 'authors', normalized_payload.get('author_ids'), current_user)

    if plan['sync_interception']:
        _sync_ordered_relations(
            parent=instance,
            ids=normalized_payload.get('interception_strategy_ids'),
            relation_model=FailureModeInterceptionStrategyRel,
            target_model=InterceptionStrategy,
            relation_field_name='interception_strategy',
            parent_field_name='failure_mode',
            label='产线拦截策略',
            current_user=current_user,
        )
    if plan['sync_handling']:
        _sync_ordered_relations(
            parent=instance,
            ids=normalized_payload.get('handling_measure_ids'),
            relation_model=FailureModeHandlingMeasureRel,
            target_model=HandlingMeasure,
            relation_field_name='handling_measure',
            parent_field_name='failure_mode',
            label='故障处理措施',
            current_user=current_user,
        )
    if plan['sync_observation']:
        _sync_ordered_relations(
            parent=instance,
            ids=normalized_payload.get('observation_method_ids'),
            relation_model=FailureModeObservationMethodRel,
            target_model=ObservationMethod,
            relation_field_name='observation_method',
            parent_field_name='failure_mode',
            label='维测手段',
            current_user=current_user,
        )
    if plan['sync_huatuo']:
        _sync_ordered_relations(
            parent=instance,
            ids=normalized_payload.get('huatuo_diagnosis_ids'),
            relation_model=FailureModeHuatuoDiagnosisRel,
            target_model=HuatuoDiagnosis,
            relation_field_name='huatuo_diagnosis',
            parent_field_name='failure_mode',
            label='华佗诊断方案',
            current_user=current_user,
        )

    if 'scope_bindings' in payload:
        _sync_failure_mode_scope_bindings(
            instance,
            normalized_payload.get('scope_bindings'),
            current_user,
        )

    instance = _failure_mode_queryset().get(id=instance.id)
    return _serialize_failure_mode(instance)


def prepare_failure_mode_task_draft_payload(
    instance: FailureMode,
    payload: dict[str, Any],
    current_user: User,
) -> dict[str, Any]:
    plan = _prepare_failure_mode_update_plan(
        instance,
        payload,
        current_user,
        allowed_fields=FAILURE_MODE_TASK_DRAFT_ALLOWED_FIELDS,
    )
    return plan['payload']


def list_failure_modes(filters) -> Any:
    queryset = _failure_mode_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(brief__icontains=filters.keyword)
            | Q(subsystem__icontains=filters.keyword)
            | Q(module_name__icontains=filters.keyword)
            | Q(status__icontains=filters.keyword)
            | Q(related_dts_nos__icontains=filters.keyword)
        )
    if getattr(filters, 'author_keyword', None):
        queryset = _filter_users_by_keyword(queryset, 'authors', filters.author_keyword)
    queryset = _filter_by_exact_values(queryset, 'subsystem', filters.subsystem)
    queryset = _filter_by_exact_values(queryset, 'module_name', filters.module)
    queryset = _filter_by_exact_values(queryset, 'status', filters.status)
    if filters.author_id:
        queryset = queryset.filter(authors__id=filters.author_id)
    queryset = queryset.distinct().order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_failure_mode, filters)


@transaction.atomic
def create_failure_mode(request, data) -> dict[str, Any]:
    payload = data.dict()
    relation_plan = _resolve_failure_mode_relation_plan(payload)
    payload.update(relation_plan)
    attrs = _failure_mode_attrs(payload)
    instance = FailureMode.objects.create(
        **attrs,
        sys_creator=request.auth,
        sys_modifier=request.auth,
    )
    _sync_owner_relation(instance, 'authors', payload.get('author_ids'), request.auth)
    _sync_ordered_relations(
        parent=instance,
        ids=relation_plan['interception_strategy_ids'],
        relation_model=FailureModeInterceptionStrategyRel,
        target_model=InterceptionStrategy,
        relation_field_name='interception_strategy',
        parent_field_name='failure_mode',
        label='产线拦截策略',
        current_user=request.auth,
    )
    _sync_ordered_relations(
        parent=instance,
        ids=relation_plan['handling_measure_ids'],
        relation_model=FailureModeHandlingMeasureRel,
        target_model=HandlingMeasure,
        relation_field_name='handling_measure',
        parent_field_name='failure_mode',
        label='故障处理措施',
        current_user=request.auth,
    )
    _sync_ordered_relations(
        parent=instance,
        ids=relation_plan['observation_method_ids'],
        relation_model=FailureModeObservationMethodRel,
        target_model=ObservationMethod,
        relation_field_name='observation_method',
        parent_field_name='failure_mode',
        label='维测手段',
        current_user=request.auth,
    )
    _sync_ordered_relations(
        parent=instance,
        ids=relation_plan['huatuo_diagnosis_ids'],
        relation_model=FailureModeHuatuoDiagnosisRel,
        target_model=HuatuoDiagnosis,
        relation_field_name='huatuo_diagnosis',
        parent_field_name='failure_mode',
        label='华佗诊断方案',
        current_user=request.auth,
    )
    if payload.get('scope_bindings') is not None:
        _sync_failure_mode_scope_bindings(
            instance,
            payload.get('scope_bindings'),
            request.auth,
        )
    instance = _failure_mode_queryset().get(id=instance.id)
    return _serialize_failure_mode(instance)


@transaction.atomic
def update_failure_mode(request, failure_mode_id: str, data) -> dict[str, Any]:
    payload = data.dict(exclude_unset=True)
    instance = get_object_or_404(_failure_mode_queryset(), id=failure_mode_id)
    return apply_failure_mode_snapshot(instance, payload, request.auth)


def get_failure_mode_detail(failure_mode_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_failure_mode_queryset(), id=failure_mode_id)
    return _serialize_failure_mode(instance)


def get_failure_mode_insight(failure_mode_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_failure_mode_queryset(), id=failure_mode_id)
    product_payload = _build_failure_mode_insight_product_payload(failure_mode_id)
    return {
        'id': str(instance.id),
        'brief': instance.brief,
        'subsystem': instance.subsystem,
        'status': instance.status,
        'landed_product_count': product_payload['landed_product_count'],
        'related_product_count': product_payload['related_product_count'],
        'total_product_count': _total_failure_mode_product_count(),
        'product_rows': product_payload['product_rows'],
    }


@transaction.atomic
def delete_failure_mode(failure_mode_id: str) -> dict[str, bool]:
    if ProductFailureMode.objects.filter(
        failure_mode_id=failure_mode_id,
        is_deleted=False,
    ).exists():
        raise HttpError(409, '该故障模式已关联产品基线，无法删除')
    instance = get_object_or_404(FailureMode.objects.filter(is_deleted=False), id=failure_mode_id)
    instance.delete()
    return {'success': True}


def list_interception_strategies(filters) -> Any:
    queryset = _interception_strategy_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(interception_item__icontains=filters.keyword)
            | Q(station__icontains=filters.keyword)
        )
    if getattr(filters, 'owner_keyword', None):
        queryset = _filter_users_by_keyword(queryset, 'owners', filters.owner_keyword)
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(
        queryset,
        _serialize_interception_strategy,
        filters,
    )


@transaction.atomic
def create_interception_strategy(request, data) -> dict[str, Any]:
    payload = data.dict()
    item = _normalize_optional_text(payload.get('interception_item'))
    if not item:
        raise HttpError(422, 'interception_item 不能为空')
    instance = InterceptionStrategy.objects.create(
        interception_item=item,
        version_detection_html=_normalize_html_text(payload.get('version_detection_html')),
        station=_normalize_optional_text(payload.get('station')),
        sys_creator=request.auth,
        sys_modifier=request.auth,
    )
    _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    instance = _interception_strategy_queryset().get(id=instance.id)
    return _serialize_interception_strategy(instance)


@transaction.atomic
def update_interception_strategy(request, item_id: str, data) -> dict[str, Any]:
    payload = data.dict(exclude_unset=True)
    instance = get_object_or_404(_interception_strategy_queryset(), id=item_id)
    if 'interception_item' in payload:
        value = _normalize_optional_text(payload.get('interception_item'))
        if not value:
            raise HttpError(422, 'interception_item 不能为空')
        instance.interception_item = value
    if 'version_detection_html' in payload:
        instance.version_detection_html = _normalize_html_text(payload.get('version_detection_html'))
    if 'station' in payload:
        instance.station = _normalize_optional_text(payload.get('station'))
    instance.sys_modifier = request.auth
    instance.save()
    if 'owner_ids' in payload:
        _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    instance = _interception_strategy_queryset().get(id=instance.id)
    return _serialize_interception_strategy(instance)


def get_interception_strategy_detail(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_interception_strategy_queryset(), id=item_id)
    return _serialize_interception_strategy(instance)


def get_interception_strategy_insight(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_interception_strategy_queryset(), id=item_id)
    failure_mode_rows, product_rows = _build_interception_insight_data(item_id)
    return {
        'id': str(instance.id),
        'interception_item': instance.interception_item,
        'station': instance.station,
        'related_failure_mode_count': len(failure_mode_rows),
        'landed_product_count': len(product_rows),
        'total_product_count': _total_failure_mode_product_count(),
        'failure_mode_rows': failure_mode_rows,
        'product_rows': product_rows,
    }


@transaction.atomic
def delete_interception_strategy(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(InterceptionStrategy.objects.filter(is_deleted=False), id=item_id)
    if instance.failure_mode_relations.exists():
        raise HttpError(409, '该产线拦截策略已被故障模式引用，无法删除')
    instance.delete()
    return {'success': True}


def list_handling_measures(filters) -> Any:
    queryset = _handling_measure_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(measure__icontains=filters.keyword)
            | Q(measure_category__icontains=filters.keyword)
            | Q(measure_effect__icontains=filters.keyword)
        )
    queryset = _filter_by_exact_values(queryset, 'measure_category', filters.measure_category)
    if getattr(filters, 'owner_keyword', None):
        queryset = _filter_users_by_keyword(queryset, 'owners', filters.owner_keyword)
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_handling_measure, filters)


@transaction.atomic
def create_handling_measure(request, data) -> dict[str, Any]:
    payload = data.dict()
    measure = _normalize_optional_text(payload.get('measure'))
    if not measure:
        raise HttpError(422, 'measure 不能为空')
    instance = HandlingMeasure.objects.create(
        measure_category=_normalize_optional_text(payload.get('measure_category')),
        measure=measure,
        measure_detail_html=_normalize_html_text(payload.get('measure_detail_html')),
        measure_effect=_normalize_optional_text(payload.get('measure_effect')) or '',
        sys_creator=request.auth,
        sys_modifier=request.auth,
    )
    _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    _sync_ordered_relations(
        parent=instance,
        ids=payload.get('test_case_ids'),
        relation_model=HandlingMeasureTestCaseRel,
        target_model=TestCase,
        relation_field_name='test_case',
        parent_field_name='handling_measure',
        label='测试用例',
        current_user=request.auth,
    )
    instance = _handling_measure_queryset().get(id=instance.id)
    return _serialize_handling_measure(instance)


@transaction.atomic
def update_handling_measure(request, item_id: str, data) -> dict[str, Any]:
    payload = data.dict(exclude_unset=True)
    instance = get_object_or_404(_handling_measure_queryset(), id=item_id)
    if 'measure_category' in payload:
        instance.measure_category = _normalize_optional_text(payload.get('measure_category'))
    if 'measure' in payload:
        value = _normalize_optional_text(payload.get('measure'))
        if not value:
            raise HttpError(422, 'measure 不能为空')
        instance.measure = value
    if 'measure_detail_html' in payload:
        instance.measure_detail_html = _normalize_html_text(payload.get('measure_detail_html'))
    if 'measure_effect' in payload:
        instance.measure_effect = _normalize_optional_text(payload.get('measure_effect')) or ''
    instance.sys_modifier = request.auth
    instance.save()
    if 'owner_ids' in payload:
        _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    if 'test_case_ids' in payload:
        _sync_ordered_relations(
            parent=instance,
            ids=payload.get('test_case_ids'),
            relation_model=HandlingMeasureTestCaseRel,
            target_model=TestCase,
            relation_field_name='test_case',
            parent_field_name='handling_measure',
            label='测试用例',
            current_user=request.auth,
        )
    instance = _handling_measure_queryset().get(id=instance.id)
    return _serialize_handling_measure(instance)


def get_handling_measure_detail(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_handling_measure_queryset(), id=item_id)
    return _serialize_handling_measure(instance)


def get_handling_measure_insight(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_handling_measure_queryset(), id=item_id)
    failure_mode_relations = list(
        FailureModeHandlingMeasureRel.objects.filter(
            is_deleted=False,
            handling_measure_id=item_id,
            failure_mode__is_deleted=False,
        )
        .select_related('failure_mode')
        .order_by('order_index', 'sys_create_datetime')
    )
    failure_mode_rows, product_rows = _build_resource_insight_rows_by_product_landings(
        [item.failure_mode for item in failure_mode_relations],
        landing_model=ProductFailureModeHandlingLanding,
        resource_field_name='handling_measure_id',
        resource_ids=[item_id],
    )
    return {
        'id': str(instance.id),
        'measure': instance.measure,
        'measure_category': instance.measure_category,
        'related_test_case_count': instance.test_case_relations.count(),
        'related_failure_mode_count': len(failure_mode_rows),
        'landed_product_count': len(product_rows),
        'total_product_count': _total_failure_mode_product_count(),
        'failure_mode_rows': failure_mode_rows,
        'product_rows': product_rows,
    }


@transaction.atomic
def delete_handling_measure(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(HandlingMeasure.objects.filter(is_deleted=False), id=item_id)
    if instance.failure_mode_relations.exists():
        raise HttpError(409, '该故障处理措施已被故障模式引用，无法删除')
    instance.delete()
    return {'success': True}


def list_observation_methods(filters) -> Any:
    queryset = _observation_method_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(monitor_type__icontains=filters.keyword)
            | Q(log_id__icontains=filters.keyword)
            | Q(log_keyword__icontains=filters.keyword)
            | Q(log_path__icontains=filters.keyword)
        )
    queryset = _filter_by_exact_values(queryset, 'monitor_type', filters.monitor_type)
    if getattr(filters, 'owner_keyword', None):
        queryset = _filter_users_by_keyword(queryset, 'owners', filters.owner_keyword)
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_observation_method, filters)


@transaction.atomic
def create_observation_method(request, data) -> dict[str, Any]:
    payload = data.dict()
    instance = ObservationMethod.objects.create(
        monitor_type=_normalize_optional_text(payload.get('monitor_type')),
        log_id=_normalize_optional_text(payload.get('log_id')),
        log_keyword=_normalize_optional_text(payload.get('log_keyword')),
        log_path=_normalize_optional_text(payload.get('log_path')),
        sys_creator=request.auth,
        sys_modifier=request.auth,
    )
    _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    instance = _observation_method_queryset().get(id=instance.id)
    return _serialize_observation_method(instance)


@transaction.atomic
def update_observation_method(request, item_id: str, data) -> dict[str, Any]:
    payload = data.dict(exclude_unset=True)
    instance = get_object_or_404(_observation_method_queryset(), id=item_id)
    for field in ['monitor_type', 'log_id', 'log_keyword', 'log_path']:
        if field in payload:
            setattr(instance, field, _normalize_optional_text(payload.get(field)))
    instance.sys_modifier = request.auth
    instance.save()
    if 'owner_ids' in payload:
        _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    instance = _observation_method_queryset().get(id=instance.id)
    return _serialize_observation_method(instance)


def get_observation_method_detail(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_observation_method_queryset(), id=item_id)
    return _serialize_observation_method(instance)


def get_observation_method_insight(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_observation_method_queryset(), id=item_id)
    failure_mode_relations = list(
        FailureModeObservationMethodRel.objects.filter(
            is_deleted=False,
            observation_method_id=item_id,
            failure_mode__is_deleted=False,
        )
        .select_related('failure_mode')
        .order_by('order_index', 'sys_create_datetime')
    )
    failure_mode_rows, product_rows = _build_resource_insight_rows_by_product_landings(
        [item.failure_mode for item in failure_mode_relations],
        landing_model=ProductFailureModeObservationLanding,
        resource_field_name='observation_method_id',
        resource_ids=[item_id],
    )
    return {
        'id': str(instance.id),
        'display_name': instance.log_keyword
        or instance.log_id
        or instance.monitor_type
        or instance.log_path
        or '未命名维测项',
        'monitor_type': instance.monitor_type,
        'log_id': instance.log_id,
        'log_keyword': instance.log_keyword,
        'log_path': instance.log_path,
        'related_failure_mode_count': len(failure_mode_rows),
        'landed_product_count': len(product_rows),
        'total_product_count': _total_failure_mode_product_count(),
        'failure_mode_rows': failure_mode_rows,
        'product_rows': product_rows,
    }


@transaction.atomic
def delete_observation_method(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(ObservationMethod.objects.filter(is_deleted=False), id=item_id)
    if instance.failure_mode_relations.exists():
        raise HttpError(409, '该维测手段已被故障模式引用，无法删除')
    instance.delete()
    return {'success': True}


def list_huatuo_diagnoses(filters) -> Any:
    queryset = _huatuo_diagnosis_queryset()
    if filters.keyword:
        queryset = queryset.filter(description__icontains=filters.keyword)
    if getattr(filters, 'owner_keyword', None):
        queryset = _filter_users_by_keyword(queryset, 'owners', filters.owner_keyword)
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_huatuo_diagnosis, filters)


@transaction.atomic
def create_huatuo_diagnosis(request, data) -> dict[str, Any]:
    payload = data.dict()
    description = _normalize_optional_text(payload.get('description'))
    if not description:
        raise HttpError(422, 'description 不能为空')
    instance = HuatuoDiagnosis.objects.create(
        description=description,
        sys_creator=request.auth,
        sys_modifier=request.auth,
    )
    _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    instance = _huatuo_diagnosis_queryset().get(id=instance.id)
    return _serialize_huatuo_diagnosis(instance)


@transaction.atomic
def update_huatuo_diagnosis(request, item_id: str, data) -> dict[str, Any]:
    payload = data.dict(exclude_unset=True)
    instance = get_object_or_404(_huatuo_diagnosis_queryset(), id=item_id)
    if 'description' in payload:
        description = _normalize_optional_text(payload.get('description'))
        if not description:
            raise HttpError(422, 'description 不能为空')
        instance.description = description
    instance.sys_modifier = request.auth
    instance.save()
    if 'owner_ids' in payload:
        _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    instance = _huatuo_diagnosis_queryset().get(id=instance.id)
    return _serialize_huatuo_diagnosis(instance)


def get_huatuo_diagnosis_detail(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_huatuo_diagnosis_queryset(), id=item_id)
    return _serialize_huatuo_diagnosis(instance)


def get_huatuo_diagnosis_insight(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_huatuo_diagnosis_queryset(), id=item_id)
    failure_mode_relations = list(
        FailureModeHuatuoDiagnosisRel.objects.filter(
            is_deleted=False,
            huatuo_diagnosis_id=item_id,
            failure_mode__is_deleted=False,
        )
        .select_related('failure_mode')
        .order_by('order_index', 'sys_create_datetime')
    )
    failure_mode_rows, product_rows = _build_resource_insight_rows_by_product_landings(
        [item.failure_mode for item in failure_mode_relations],
        landing_model=ProductFailureModeHuatuoLanding,
        resource_field_name='huatuo_diagnosis_id',
        resource_ids=[item_id],
    )
    return {
        'id': str(instance.id),
        'description': instance.description,
        'related_failure_mode_count': len(failure_mode_rows),
        'landed_product_count': len(product_rows),
        'total_product_count': _total_failure_mode_product_count(),
        'failure_mode_rows': failure_mode_rows,
        'product_rows': product_rows,
    }


@transaction.atomic
def delete_huatuo_diagnosis(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(HuatuoDiagnosis.objects.filter(is_deleted=False), id=item_id)
    if instance.failure_mode_relations.exists():
        raise HttpError(409, '该华佗诊断方案已被故障模式引用，无法删除')
    instance.delete()
    return {'success': True}


def list_test_cases(filters) -> Any:
    queryset = _test_case_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(brief__icontains=filters.keyword)
            | Q(cida_link__icontains=filters.keyword)
        )
    if getattr(filters, 'owner_keyword', None):
        queryset = _filter_users_by_keyword(queryset, 'owners', filters.owner_keyword)
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_test_case, filters)


@transaction.atomic
def create_test_case(request, data) -> dict[str, Any]:
    payload = data.dict()
    brief = _normalize_optional_text(payload.get('brief'))
    if not brief:
        raise HttpError(422, 'brief 不能为空')
    instance = TestCase.objects.create(
        brief=brief,
        detail_html=_normalize_html_text(payload.get('detail_html')),
        cida_link=_normalize_optional_text(payload.get('cida_link')),
        sys_creator=request.auth,
        sys_modifier=request.auth,
    )
    _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    instance = _test_case_queryset().get(id=instance.id)
    return _serialize_test_case(instance)


@transaction.atomic
def update_test_case(request, item_id: str, data) -> dict[str, Any]:
    payload = data.dict(exclude_unset=True)
    instance = get_object_or_404(_test_case_queryset(), id=item_id)
    if 'brief' in payload:
        brief = _normalize_optional_text(payload.get('brief'))
        if not brief:
            raise HttpError(422, 'brief 不能为空')
        instance.brief = brief
    if 'detail_html' in payload:
        instance.detail_html = _normalize_html_text(payload.get('detail_html'))
    if 'cida_link' in payload:
        instance.cida_link = _normalize_optional_text(payload.get('cida_link'))
    instance.sys_modifier = request.auth
    instance.save()
    if 'owner_ids' in payload:
        _sync_owner_relation(instance, 'owners', payload.get('owner_ids'), request.auth)
    instance = _test_case_queryset().get(id=instance.id)
    return _serialize_test_case(instance)


def get_test_case_detail(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_test_case_queryset(), id=item_id)
    return _serialize_test_case(instance)


def get_test_case_insight(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_test_case_queryset(), id=item_id)
    handling_measure_relations = list(
        HandlingMeasureTestCaseRel.objects.filter(
            is_deleted=False,
            test_case_id=item_id,
            handling_measure__is_deleted=False,
        )
        .select_related('handling_measure')
        .order_by('order_index', 'sys_create_datetime')
    )
    handling_measure_ids = [str(item.handling_measure_id) for item in handling_measure_relations]
    failure_mode_relations = list(
        FailureModeHandlingMeasureRel.objects.filter(
            is_deleted=False,
            handling_measure_id__in=handling_measure_ids,
            failure_mode__is_deleted=False,
        )
        .select_related('failure_mode')
        .order_by('handling_measure_id', 'order_index', 'sys_create_datetime')
    )
    failure_mode_rows, product_rows = _build_resource_insight_rows_by_product_landings(
        [item.failure_mode for item in failure_mode_relations],
        landing_model=ProductFailureModeHandlingLanding,
        resource_field_name='handling_measure_id',
        resource_ids=handling_measure_ids,
    )
    return {
        'id': str(instance.id),
        'brief': instance.brief,
        'cida_link': instance.cida_link,
        'related_handling_measure_count': len({str(item.handling_measure_id) for item in handling_measure_relations}),
        'related_failure_mode_count': len(failure_mode_rows),
        'landed_product_count': len(product_rows),
        'total_product_count': _total_failure_mode_product_count(),
        'failure_mode_rows': failure_mode_rows,
        'product_rows': product_rows,
    }


@transaction.atomic
def delete_test_case(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(TestCase.objects.filter(is_deleted=False), id=item_id)
    if instance.handling_measure_relations.exists():
        raise HttpError(409, '该测试用例已被故障处理措施引用，无法删除')
    instance.delete()
    return {'success': True}


def list_failure_mode_subsystem_configs(filters) -> dict[str, Any]:
    queryset = _subsystem_config_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(subsystem__icontains=filters.keyword)
            | Q(module_options__icontains=filters.keyword)
            | Q(chip_options__icontains=filters.keyword)
        )
    queryset = queryset.order_by('subsystem', '-sort', 'sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_subsystem_config, filters)


@transaction.atomic
def create_failure_mode_subsystem_config(request, data) -> dict[str, Any]:
    payload = data.dict()
    subsystem = _normalize_optional_text(payload.get('subsystem'))
    if not subsystem:
        raise HttpError(422, 'subsystem 不能为空')

    existing = FailureModeSubsystemConfig.objects.filter(subsystem=subsystem).first()
    if existing and not existing.is_deleted:
        raise HttpError(409, '该子系统配置已存在')

    module_options = _normalize_text_list(payload.get('module_options'))
    chip_options = _normalize_text_list(payload.get('chip_options'))
    if existing and existing.is_deleted:
        existing.is_deleted = False
        existing.module_options = module_options
        existing.chip_options = chip_options
        existing.sys_modifier = request.auth
        existing.save(update_fields=['is_deleted', 'module_options', 'chip_options', 'sys_modifier', 'sys_update_datetime'])
        instance = existing
    else:
        instance = FailureModeSubsystemConfig.objects.create(
            subsystem=subsystem,
            module_options=module_options,
            chip_options=chip_options,
            sys_creator=request.auth,
            sys_modifier=request.auth,
        )
    return _serialize_subsystem_config(instance)


@transaction.atomic
def update_failure_mode_subsystem_config(request, item_id: str, data) -> dict[str, Any]:
    payload = data.dict(exclude_unset=True)
    instance = get_object_or_404(_subsystem_config_queryset(), id=item_id)

    if 'subsystem' in payload:
        subsystem = _normalize_optional_text(payload.get('subsystem'))
        if not subsystem:
            raise HttpError(422, 'subsystem 不能为空')
        duplicate = FailureModeSubsystemConfig.objects.filter(subsystem=subsystem).exclude(id=item_id).first()
        if duplicate and not duplicate.is_deleted:
            raise HttpError(409, '该子系统配置已存在')
        if duplicate and duplicate.is_deleted:
            raise HttpError(409, '存在已删除的同名子系统配置，请先更换名称')
        instance.subsystem = subsystem

    if 'module_options' in payload:
        instance.module_options = _normalize_text_list(payload.get('module_options'))
    if 'chip_options' in payload:
        instance.chip_options = _normalize_text_list(payload.get('chip_options'))

    instance.sys_modifier = request.auth
    instance.save()
    return _serialize_subsystem_config(instance)


def get_failure_mode_subsystem_config_detail(item_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_subsystem_config_queryset(), id=item_id)
    return _serialize_subsystem_config(instance)


@transaction.atomic
def delete_failure_mode_subsystem_config(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(_subsystem_config_queryset(), id=item_id)
    instance.delete()
    return {'success': True}


def get_failure_mode_subsystem_config_options() -> dict[str, Any]:
    return _build_subsystem_config_options()


def _resolve_statistics_status(required: bool, configured: bool) -> str:
    if not required:
        return '无需配置'
    return '已配置' if configured else '待补充'


def _build_statistics_status_dataset(
    counter: dict[str, int],
    status_order: list[str] | None = None,
) -> list[dict[str, int | str]]:
    return [
        {'name': status, 'value': int(counter.get(status, 0))}
        for status in (status_order or STATISTICS_STATUS_ORDER)
    ]


def _resolve_statistics_light(pending_rate: float) -> str:
    if pending_rate > 60:
        return 'red'
    if pending_rate > 20:
        return 'yellow'
    return 'green'


def _make_statistics_source_rows_from_failure_modes(
    failure_modes: Iterable[FailureMode],
) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(subsystem=item.subsystem, failure_mode=item)
        for item in failure_modes
    ]


def _make_statistics_source_rows_from_product_bindings(
    bindings: Iterable[ProductFailureMode],
) -> list[SimpleNamespace]:
    rows: list[SimpleNamespace] = []
    for item in bindings:
        if not getattr(item, 'failure_mode', None):
            continue
        rows.append(
            SimpleNamespace(subsystem=item.subsystem, failure_mode=item.failure_mode),
        )
    return rows


def _build_statistics_payload_from_sources(
    source_rows: Iterable[SimpleNamespace],
    seed_subsystems: Iterable[str] | None = None,
    selected_subsystems: Iterable[str] | None = None,
) -> dict[str, Any]:
    subsystem_keys: list[str] = []
    subsystem_seen: set[str] = set()
    selected_subsystem_set = {
        (_normalize_optional_text(item) or EMPTY_SUBSYSTEM_LABEL)
        for item in _normalize_text_list(selected_subsystems)
    }
    source_row_list: list[SimpleNamespace] = []
    for source in source_rows:
        subsystem = _normalize_optional_text(source.subsystem) or EMPTY_SUBSYSTEM_LABEL
        if selected_subsystem_set and subsystem not in selected_subsystem_set:
            continue
        source_row_list.append(
            SimpleNamespace(
                subsystem=subsystem,
                failure_mode=source.failure_mode,
            ),
        )

    def ensure_subsystem_key(subsystem: str):
        if subsystem in subsystem_seen:
            return
        subsystem_seen.add(subsystem)
        subsystem_keys.append(subsystem)

    def ensure_row(
        rows: dict[str, dict[str, Any]],
        subsystem: str,
    ) -> dict[str, Any]:
        row = rows.get(subsystem)
        if row is not None:
            return row
        row = {
            'subsystem': subsystem,
            'failure_mode_count': 0,
            'interception_relation_count': 0,
            'handling_detection_relation_count': 0,
            'handling_prevention_relation_count': 0,
            'handling_self_heal_relation_count': 0,
            'observation_pipeline_log_relation_count': 0,
            'observation_dmd_relation_count': 0,
            'observation_fmp_relation_count': 0,
            'huatuo_relation_count': 0,
            'pending_failure_mode_count': 0,
            'pending_rate': 0.0,
            'status_light': 'green',
        }
        rows[subsystem] = row
        return row

    for subsystem in seed_subsystems or []:
        text = _normalize_optional_text(subsystem) or EMPTY_SUBSYSTEM_LABEL
        if selected_subsystem_set and text not in selected_subsystem_set:
            continue
        if text:
            ensure_subsystem_key(text)

    for source in source_row_list:
        ensure_subsystem_key(source.subsystem)

    rows: dict[str, dict[str, Any]] = {}
    for subsystem in subsystem_keys:
        ensure_row(rows, subsystem)

    interception_counter = defaultdict(int)
    huatuo_counter = defaultdict(int)
    handling_counters = {
        category: defaultdict(int)
        for category in FIXED_HANDLING_MEASURE_CATEGORIES
    }
    observation_counters = {
        monitor_type: defaultdict(int)
        for monitor_type in FIXED_OBSERVATION_METHOD_TYPES
    }

    for source in source_row_list:
        failure_mode = source.failure_mode
        row = ensure_row(rows, source.subsystem)
        row['failure_mode_count'] += 1

        interception_relations = list(failure_mode.interception_relations.all())
        handling_relations = list(failure_mode.handling_measure_relations.all())
        observation_relations = list(failure_mode.observation_method_relations.all())
        huatuo_relations = list(failure_mode.huatuo_diagnosis_relations.all())

        row['interception_relation_count'] += len(interception_relations)
        row['huatuo_relation_count'] += len(huatuo_relations)

        handling_counts = defaultdict(int)
        for relation in handling_relations:
            category = _normalize_optional_text(
                relation.handling_measure.measure_category,
            )
            if category:
                handling_counts[category] += 1
        row['handling_detection_relation_count'] += handling_counts['检测']
        row['handling_prevention_relation_count'] += handling_counts['预防']
        row['handling_self_heal_relation_count'] += handling_counts['自愈']

        observation_counts = defaultdict(int)
        for relation in observation_relations:
            monitor_type = _normalize_optional_text(
                relation.observation_method.monitor_type,
            )
            if monitor_type:
                observation_counts[monitor_type] += 1
        row['observation_pipeline_log_relation_count'] += observation_counts['流水日志']
        row['observation_dmd_relation_count'] += observation_counts['DMD 点位']
        row['observation_fmp_relation_count'] += observation_counts['FMP 点位']

        required_handling_categories = set(
            _normalize_enum_list(
                failure_mode.required_handling_measure_categories,
                FIXED_HANDLING_MEASURE_CATEGORIES,
            ),
        )
        required_observation_types = set(
            _normalize_enum_list(
                failure_mode.required_observation_method_types,
                FIXED_OBSERVATION_METHOD_TYPES,
            ),
        )

        interception_status = _resolve_statistics_status(
            bool(failure_mode.interception_required),
            len(interception_relations) > 0,
        )
        interception_counter[interception_status] += 1

        huatuo_status = _resolve_statistics_status(
            bool(failure_mode.huatuo_required),
            len(huatuo_relations) > 0,
        )
        huatuo_counter[huatuo_status] += 1

        handling_available = {
            _normalize_optional_text(relation.handling_measure.measure_category)
            for relation in handling_relations
        }
        for category in FIXED_HANDLING_MEASURE_CATEGORIES:
            status = _resolve_statistics_status(
                category in required_handling_categories,
                category in handling_available,
            )
            handling_counters[category][status] += 1

        observation_available = {
            _normalize_optional_text(relation.observation_method.monitor_type)
            for relation in observation_relations
        }
        for monitor_type in FIXED_OBSERVATION_METHOD_TYPES:
            status = _resolve_statistics_status(
                monitor_type in required_observation_types,
                monitor_type in observation_available,
            )
            observation_counters[monitor_type][status] += 1

        pending = False
        if failure_mode.interception_required and not interception_relations:
            pending = True
        if failure_mode.huatuo_required and not huatuo_relations:
            pending = True
        for category in required_handling_categories:
            if handling_counts[category] <= 0:
                pending = True
                break
        if not pending:
            for monitor_type in required_observation_types:
                if observation_counts[monitor_type] <= 0:
                    pending = True
                    break
        if pending:
            row['pending_failure_mode_count'] += 1

    subsystem_rows: list[dict[str, Any]] = []
    for subsystem in subsystem_keys:
        row = ensure_row(rows, subsystem)
        total = row['failure_mode_count']
        pending_count = row['pending_failure_mode_count']
        pending_rate = round((pending_count / total) * 100, 2) if total > 0 else 0.0
        row['pending_rate'] = pending_rate
        row['status_light'] = _resolve_statistics_light(pending_rate)
        subsystem_rows.append(row)

    subsystem_rows.sort(key=lambda item: (-item['failure_mode_count'], item['subsystem']))

    summary = {
        'subsystem_counts': [
            {
                'name': item['subsystem'],
                'value': item['failure_mode_count'],
            }
            for item in subsystem_rows
        ],
        'interception_status': _build_statistics_status_dataset(interception_counter),
        'huatuo_status': _build_statistics_status_dataset(huatuo_counter),
        'handling_detection_status': _build_statistics_status_dataset(
            handling_counters['检测'],
        ),
        'handling_prevention_status': _build_statistics_status_dataset(
            handling_counters['预防'],
        ),
        'handling_self_heal_status': _build_statistics_status_dataset(
            handling_counters['自愈'],
        ),
        'observation_pipeline_log_status': _build_statistics_status_dataset(
            observation_counters['流水日志'],
        ),
        'observation_dmd_status': _build_statistics_status_dataset(
            observation_counters['DMD 点位'],
        ),
        'observation_fmp_status': _build_statistics_status_dataset(
            observation_counters['FMP 点位'],
        ),
    }
    return {
        'rows': subsystem_rows,
        'summary': summary,
    }


def _build_global_failure_mode_statistics_payload(
    selected_subsystems: Iterable[str] | None = None,
) -> dict[str, Any]:
    failure_modes = list(_failure_mode_queryset().order_by('-sort', '-sys_create_datetime'))
    config_subsystems = [
        item.subsystem
        for item in _subsystem_config_queryset().only('subsystem')
    ]
    return _build_statistics_payload_from_sources(
        _make_statistics_source_rows_from_failure_modes(failure_modes),
        config_subsystems,
        selected_subsystems=selected_subsystems,
    )


def get_failure_mode_statistics_subsystem_options() -> list[str]:
    payload = _build_global_failure_mode_statistics_payload()
    return [str(item['subsystem']) for item in payload['rows']]


def get_failure_mode_statistics_summary(filters=None) -> dict[str, Any]:
    payload = _build_global_failure_mode_statistics_payload(
        getattr(filters, 'subsystems', None),
    )
    return payload['summary']


def list_failure_mode_statistics_subsystems(filters) -> dict[str, Any]:
    rows = _build_global_failure_mode_statistics_payload(
        getattr(filters, 'subsystems', None),
    )['rows']
    keyword = _normalize_optional_text(getattr(filters, 'keyword', None))
    if keyword:
        rows = [
            item for item in rows
            if keyword in item['subsystem']
        ]

    page = max(getattr(filters, 'page', 1), 1)
    page_size = max(getattr(filters, 'pageSize', 10), 1)
    offset = page_size * (page - 1)
    return {
        'items': rows[offset: offset + page_size],
        'total': len(rows),
    }


def _get_product_statistics_policy():
    from apps.failure_mode.failure_mode_workflow_services import (
        FailureModeAccessPolicy,
        ProductWorkflowService,
    )

    return FailureModeAccessPolicy, ProductWorkflowService


def _get_visible_product_statistics_queryset(user: User):
    FailureModeAccessPolicy, ProductWorkflowService = _get_product_statistics_policy()
    ProductWorkflowService.sync_projects()
    policy = FailureModeAccessPolicy(user)
    queryset = FailureModeProduct.objects.filter(is_deleted=False).select_related(
        'project',
        'owner',
    )
    queryset = policy.filter_products(queryset)
    queryset = queryset.filter(project__type=PLATFORM_PROJECT_TYPE)
    return policy, queryset.order_by('project__name', '-sys_create_datetime')


def _product_failure_mode_statistics_queryset():
    return ProductFailureMode.objects.filter(
        is_deleted=False,
        product__is_deleted=False,
        product__project__type=PLATFORM_PROJECT_TYPE,
        failure_mode__is_deleted=False,
    ).select_related('product', 'product__project', 'product__owner', 'failure_mode').prefetch_related(
        Prefetch(
            'interception_landings',
            queryset=ProductFailureModeInterceptionLanding.objects.select_related(
                'interception_strategy',
            ),
        ),
        Prefetch(
            'handling_landings',
            queryset=ProductFailureModeHandlingLanding.objects.select_related(
                'handling_measure',
            ),
        ),
        Prefetch(
            'observation_landings',
            queryset=ProductFailureModeObservationLanding.objects.select_related(
                'observation_method',
            ),
        ),
        Prefetch(
            'huatuo_landings',
            queryset=ProductFailureModeHuatuoLanding.objects.select_related(
                'huatuo_diagnosis',
            ),
        ),
        Prefetch(
            'failure_mode__interception_relations',
            queryset=FailureModeInterceptionStrategyRel.objects.select_related(
                'interception_strategy',
            ).order_by('order_index', 'sys_create_datetime'),
        ),
        Prefetch(
            'failure_mode__handling_measure_relations',
            queryset=FailureModeHandlingMeasureRel.objects.select_related(
                'handling_measure',
            ).order_by('order_index', 'sys_create_datetime'),
        ),
        Prefetch(
            'failure_mode__observation_method_relations',
            queryset=FailureModeObservationMethodRel.objects.select_related(
                'observation_method',
            ).order_by('order_index', 'sys_create_datetime'),
        ),
        Prefetch(
            'failure_mode__huatuo_diagnosis_relations',
            queryset=FailureModeHuatuoDiagnosisRel.objects.select_related(
                'huatuo_diagnosis',
            ).order_by('order_index', 'sys_create_datetime'),
        ),
    )


def _resolve_visible_product_statistics_products(
    user: User,
    product_ids: Iterable[str] | None = None,
):
    policy, queryset = _get_visible_product_statistics_queryset(user)
    selected_product_ids = _normalize_text_list(product_ids)
    if selected_product_ids:
        queryset = queryset.filter(id__in=selected_product_ids)
    products = list(queryset)
    return policy, products


def _get_visible_product_statistics_bindings(
    policy,
    product_ids: Iterable[str] | None = None,
    subsystems: Iterable[str] | None = None,
) -> list[ProductFailureMode]:
    queryset = _product_failure_mode_statistics_queryset()
    queryset = policy.filter_product_failure_modes(queryset)
    normalized_product_ids = _normalize_text_list(product_ids)
    if normalized_product_ids:
        queryset = queryset.filter(product_id__in=normalized_product_ids)
    normalized_subsystems = _normalize_text_list(subsystems)
    if normalized_subsystems:
        queryset = queryset.filter(subsystem__in=normalized_subsystems)
    return list(queryset.order_by('subsystem', '-sys_create_datetime'))


def _resolve_product_landing_status(required: bool, landed_flags: list[bool]) -> str:
    if not required:
        return '不涉及'
    if not landed_flags:
        return '待开展'
    return '已落地' if all(landed_flags) else '待开展'


def _build_product_statistics_payload_from_bindings(
    bindings: Iterable[ProductFailureMode],
) -> dict[str, Any]:
    grouped_rows: dict[str, dict[str, Any]] = {}
    subsystem_keys: list[str] = []
    subsystem_seen: set[str] = set()

    def ensure_row(subsystem: str) -> dict[str, Any]:
        row = grouped_rows.get(subsystem)
        if row is not None:
            return row
        if subsystem not in subsystem_seen:
            subsystem_seen.add(subsystem)
            subsystem_keys.append(subsystem)
        row = {
            'subsystem': subsystem,
            'baseline_failure_mode_count': 0,
            'landed_failure_mode_count': 0,
            'pending_failure_mode_count': 0,
            'pending_rate': 0.0,
            'status_light': 'green',
        }
        grouped_rows[subsystem] = row
        return row

    failure_mode_landing_counter = defaultdict(int)
    interception_counter = defaultdict(int)
    huatuo_counter = defaultdict(int)
    handling_counters = {
        category: defaultdict(int)
        for category in FIXED_HANDLING_MEASURE_CATEGORIES
    }
    observation_counters = {
        monitor_type: defaultdict(int)
        for monitor_type in FIXED_OBSERVATION_METHOD_TYPES
    }

    binding_list = list(bindings)
    for binding in binding_list:
        failure_mode = binding.failure_mode
        if not failure_mode:
            continue
        subsystem = _normalize_optional_text(binding.subsystem) or EMPTY_SUBSYSTEM_LABEL
        row = ensure_row(subsystem)
        row['baseline_failure_mode_count'] += 1

        failure_mode_is_landed = _derive_product_failure_mode_is_landed(binding)
        if failure_mode_is_landed:
            row['landed_failure_mode_count'] += 1
            failure_mode_landing_counter['已落地'] += 1
        else:
            failure_mode_landing_counter['未落地'] += 1

        interception_flags = [
            bool(item.is_landed)
            for item in binding.interception_landings.all()
            if not item.is_deleted
        ]
        interception_status = _resolve_product_landing_status(
            bool(failure_mode.interception_required),
            interception_flags,
        )
        interception_counter[interception_status] += 1

        huatuo_flags = [
            bool(item.is_landed)
            for item in binding.huatuo_landings.all()
            if not item.is_deleted
        ]
        huatuo_status = _resolve_product_landing_status(
            bool(failure_mode.huatuo_required),
            huatuo_flags,
        )
        huatuo_counter[huatuo_status] += 1

        required_handling_categories = set(
            _normalize_enum_list(
                failure_mode.required_handling_measure_categories,
                FIXED_HANDLING_MEASURE_CATEGORIES,
            ),
        )
        handling_flags_map: dict[str, list[bool]] = defaultdict(list)
        for landing in binding.handling_landings.all():
            if landing.is_deleted or not landing.handling_measure:
                continue
            category = _normalize_optional_text(landing.handling_measure.measure_category)
            if category:
                handling_flags_map[category].append(bool(landing.is_landed))
        for category in FIXED_HANDLING_MEASURE_CATEGORIES:
            status = _resolve_product_landing_status(
                category in required_handling_categories,
                handling_flags_map.get(category, []),
            )
            handling_counters[category][status] += 1

        required_observation_types = set(
            _normalize_enum_list(
                failure_mode.required_observation_method_types,
                FIXED_OBSERVATION_METHOD_TYPES,
            ),
        )
        observation_flags_map: dict[str, list[bool]] = defaultdict(list)
        for landing in binding.observation_landings.all():
            if landing.is_deleted or not landing.observation_method:
                continue
            monitor_type = _normalize_optional_text(landing.observation_method.monitor_type)
            if monitor_type:
                observation_flags_map[monitor_type].append(bool(landing.is_landed))
        for monitor_type in FIXED_OBSERVATION_METHOD_TYPES:
            status = _resolve_product_landing_status(
                monitor_type in required_observation_types,
                observation_flags_map.get(monitor_type, []),
            )
            observation_counters[monitor_type][status] += 1

        pending = not failure_mode_is_landed
        if not pending and interception_status == '待开展':
            pending = True
        if not pending and huatuo_status == '待开展':
            pending = True
        if not pending:
            pending = any(
                handling_counters[category] is not None
                and _resolve_product_landing_status(
                    category in required_handling_categories,
                    handling_flags_map.get(category, []),
                )
                == '待开展'
                for category in FIXED_HANDLING_MEASURE_CATEGORIES
            )
        if not pending:
            pending = any(
                _resolve_product_landing_status(
                    monitor_type in required_observation_types,
                    observation_flags_map.get(monitor_type, []),
                )
                == '待开展'
                for monitor_type in FIXED_OBSERVATION_METHOD_TYPES
            )
        if pending:
            row['pending_failure_mode_count'] += 1

    rows: list[dict[str, Any]] = []
    for subsystem in subsystem_keys:
        row = ensure_row(subsystem)
        total = row['baseline_failure_mode_count']
        pending_count = row['pending_failure_mode_count']
        row['pending_rate'] = round((pending_count / total) * 100, 2) if total > 0 else 0.0
        row['status_light'] = _resolve_statistics_light(row['pending_rate'])
        rows.append(row)

    rows.sort(key=lambda item: (-item['baseline_failure_mode_count'], item['subsystem']))
    summary = {
        'subsystem_counts': [
            {'name': item['subsystem'], 'value': item['baseline_failure_mode_count']}
            for item in rows
        ],
        'failure_mode_landing_status': _build_statistics_status_dataset(
            failure_mode_landing_counter,
            FAILURE_MODE_LANDING_STATUS_ORDER,
        ),
        'interception_status': _build_statistics_status_dataset(
            interception_counter,
            PRODUCT_STATISTICS_STATUS_ORDER,
        ),
        'huatuo_status': _build_statistics_status_dataset(
            huatuo_counter,
            PRODUCT_STATISTICS_STATUS_ORDER,
        ),
        'handling_detection_status': _build_statistics_status_dataset(
            handling_counters['检测'],
            PRODUCT_STATISTICS_STATUS_ORDER,
        ),
        'handling_prevention_status': _build_statistics_status_dataset(
            handling_counters['预防'],
            PRODUCT_STATISTICS_STATUS_ORDER,
        ),
        'handling_self_heal_status': _build_statistics_status_dataset(
            handling_counters['自愈'],
            PRODUCT_STATISTICS_STATUS_ORDER,
        ),
        'observation_pipeline_log_status': _build_statistics_status_dataset(
            observation_counters['流水日志'],
            PRODUCT_STATISTICS_STATUS_ORDER,
        ),
        'observation_dmd_status': _build_statistics_status_dataset(
            observation_counters['DMD 点位'],
            PRODUCT_STATISTICS_STATUS_ORDER,
        ),
        'observation_fmp_status': _build_statistics_status_dataset(
            observation_counters['FMP 点位'],
            PRODUCT_STATISTICS_STATUS_ORDER,
        ),
    }
    return {'rows': rows, 'summary': summary}


def list_failure_mode_product_statistics_overview(user: User) -> list[dict[str, Any]]:
    policy, products = _get_visible_product_statistics_queryset(user)
    product_list = list(products)
    product_ids = [str(item.id) for item in product_list]
    bindings = list(
        _get_visible_product_statistics_bindings(policy, product_ids),
    )
    grouped_bindings: dict[str, list[ProductFailureMode]] = defaultdict(list)
    for item in bindings:
        grouped_bindings[str(item.product_id)].append(item)

    rows: list[dict[str, Any]] = []
    for product in product_list:
        product_id = str(product.id)
        product_bindings = grouped_bindings.get(product_id, [])
        payload = _build_product_statistics_payload_from_bindings(product_bindings)
        subsystem_rows = payload['rows']
        baseline_count = len(product_bindings)
        landed_count = sum(
            1 for item in product_bindings if _derive_product_failure_mode_is_landed(item)
        )
        pending_count = sum(
            int(item['pending_failure_mode_count'])
            for item in subsystem_rows
        )
        pending_rate = round((pending_count / baseline_count) * 100, 2) if baseline_count > 0 else 0.0
        rows.append(
            {
                'product_id': product_id,
                'product_name': product.project.name if product.project else '',
                'owner_info': _user_brief(product.owner),
                'baseline_failure_mode_count': baseline_count,
                'landed_failure_mode_count': landed_count,
                'pending_failure_mode_count': pending_count,
                'pending_rate': pending_rate,
                'status_light': _resolve_statistics_light(pending_rate),
            },
        )

    rows.sort(
        key=lambda item: (
            -item['pending_failure_mode_count'],
            -item['pending_rate'],
            item['product_name'],
        ),
    )
    return rows


def get_failure_mode_product_statistics_summary(user: User, filters) -> dict[str, Any]:
    policy, products = _resolve_visible_product_statistics_products(
        user,
        getattr(filters, 'product_ids', None),
    )
    product_ids = [str(item.id) for item in products]
    bindings = _get_visible_product_statistics_bindings(
        policy,
        product_ids,
        getattr(filters, 'subsystems', None),
    )
    payload = _build_product_statistics_payload_from_bindings(bindings)
    return payload['summary']


def list_failure_mode_product_statistics_subsystem_options(user: User, filters) -> list[str]:
    policy, products = _resolve_visible_product_statistics_products(
        user,
        getattr(filters, 'product_ids', None),
    )
    product_ids = [str(item.id) for item in products]
    bindings = _get_visible_product_statistics_bindings(policy, product_ids)
    seen: set[str] = set()
    options: list[str] = []
    for item in bindings:
        subsystem = _normalize_optional_text(item.subsystem) or EMPTY_SUBSYSTEM_LABEL
        if subsystem in seen:
            continue
        seen.add(subsystem)
        options.append(subsystem)
    return sorted(options)


def list_failure_mode_product_statistics_subsystems(user: User, filters) -> dict[str, Any]:
    policy, products = _resolve_visible_product_statistics_products(
        user,
        getattr(filters, 'product_ids', None),
    )
    product_ids = [str(item.id) for item in products]
    bindings = _get_visible_product_statistics_bindings(
        policy,
        product_ids,
        getattr(filters, 'subsystems', None),
    )
    rows = _build_product_statistics_payload_from_bindings(bindings)['rows']
    keyword = _normalize_optional_text(getattr(filters, 'keyword', None))
    if keyword:
        rows = [
            item for item in rows
            if keyword in item['subsystem']
        ]

    page = max(getattr(filters, 'page', 1), 1)
    page_size = max(getattr(filters, 'pageSize', 10), 1)
    offset = page_size * (page - 1)
    return {
        'items': rows[offset: offset + page_size],
        'total': len(rows),
    }


def get_failure_mode_dict_options() -> dict[str, Any]:
    grouped = _load_dict_grouped()
    subsystem_options = _build_subsystem_config_options()
    grouped['subsystem'] = [item['value'] for item in subsystem_options['subsystem_options']]
    grouped['module'] = [item['value'] for item in subsystem_options['module_options']]
    grouped['chip'] = [item['value'] for item in subsystem_options['chip_options']]

    grouped['measure_category'] = [
        *_normalize_enum_list(FIXED_HANDLING_MEASURE_CATEGORIES, FIXED_HANDLING_MEASURE_CATEGORIES),
        *[item for item in grouped.get('measure_category', []) if item not in FIXED_HANDLING_MEASURE_CATEGORIES],
    ]
    grouped['monitor_type'] = [
        *_normalize_enum_list(FIXED_OBSERVATION_METHOD_TYPES, FIXED_OBSERVATION_METHOD_TYPES),
        *[item for item in grouped.get('monitor_type', []) if item not in FIXED_OBSERVATION_METHOD_TYPES],
    ]

    return {
        field: _build_option_list(values)
        for field, values in grouped.items()
    }
