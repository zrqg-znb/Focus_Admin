from __future__ import annotations

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
    FailureModeObservationMethodRel,
    HandlingMeasure,
    HandlingMeasureTestCaseRel,
    HuatuoDiagnosis,
    InterceptionStrategy,
    ObservationMethod,
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


def _normalize_text_list(values: Any) -> list[str]:
    if values is None:
        return []
    raw_values = values if isinstance(values, list) else [values]
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
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
        'chips': failure_mode.chips or [],
        'fault_categories': failure_mode.fault_categories or [],
        'symptoms': failure_mode.symptoms or [],
        'effect_html': failure_mode.effect_html or '',
        'root_cause_html': failure_mode.root_cause_html or '',
        'functional_safety_level': failure_mode.functional_safety_level,
        'occurrence_frequency': failure_mode.occurrence_frequency,
        'detectability': failure_mode.detectability,
        'severity': failure_mode.severity,
        'author_ids': [str(item.id) for item in authors],
        'author_info': _users_brief(authors),
        'related_dts_nos': failure_mode.related_dts_nos or [],
        'status': failure_mode.status,
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
                item.huatuo_diagnosis.description[:60] + ('...' if len(item.huatuo_diagnosis.description) > 60 else ''),
                str(item.huatuo_diagnosis_id),
                None,
            )
            for item in huatuo_relations
        ],
        'sys_create_datetime': _format_datetime(failure_mode.sys_create_datetime),
        'sys_update_datetime': _format_datetime(failure_mode.sys_update_datetime),
    }


def _failure_mode_queryset():
    return FailureMode.objects.filter(is_deleted=False).prefetch_related(
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


def _failure_mode_attrs(payload: dict[str, Any]) -> dict[str, Any]:
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
        'status': _normalize_optional_text(payload.get('status')),
    }
    if not attrs['brief']:
        raise HttpError(422, 'brief 不能为空')
    return attrs


def _update_failure_mode_attrs(instance: FailureMode, payload: dict[str, Any]):
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
        'status': ('status', _normalize_optional_text),
    }
    for payload_key, (field_name, normalizer) in mapping.items():
        if payload_key not in payload:
            continue
        value = normalizer(payload.get(payload_key))
        if field_name == 'brief' and not value:
            raise HttpError(422, 'brief 不能为空')
        setattr(instance, field_name, value)


def list_failure_modes(filters, pagination=None) -> Any:
    queryset = _failure_mode_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(brief__icontains=filters.keyword)
            | Q(subsystem__icontains=filters.keyword)
            | Q(module_name__icontains=filters.keyword)
            | Q(status__icontains=filters.keyword)
            | Q(related_dts_nos__icontains=filters.keyword)
        )
    if filters.subsystem:
        queryset = queryset.filter(subsystem=filters.subsystem)
    if filters.module:
        queryset = queryset.filter(module_name=filters.module)
    if filters.status:
        queryset = queryset.filter(status=filters.status)
    if filters.author_id:
        queryset = queryset.filter(authors__id=filters.author_id)
    queryset = queryset.distinct().order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_failure_mode, pagination)


@transaction.atomic
def create_failure_mode(request, data) -> dict[str, Any]:
    payload = data.dict()
    attrs = _failure_mode_attrs(payload)
    instance = FailureMode.objects.create(
        **attrs,
        sys_creator=request.auth,
        sys_modifier=request.auth,
    )
    _sync_owner_relation(instance, 'authors', payload.get('author_ids'), request.auth)
    _sync_ordered_relations(
        parent=instance,
        ids=payload.get('interception_strategy_ids'),
        relation_model=FailureModeInterceptionStrategyRel,
        target_model=InterceptionStrategy,
        relation_field_name='interception_strategy',
        parent_field_name='failure_mode',
        label='产线拦截策略',
        current_user=request.auth,
    )
    _sync_ordered_relations(
        parent=instance,
        ids=payload.get('handling_measure_ids'),
        relation_model=FailureModeHandlingMeasureRel,
        target_model=HandlingMeasure,
        relation_field_name='handling_measure',
        parent_field_name='failure_mode',
        label='故障处理措施',
        current_user=request.auth,
    )
    _sync_ordered_relations(
        parent=instance,
        ids=payload.get('observation_method_ids'),
        relation_model=FailureModeObservationMethodRel,
        target_model=ObservationMethod,
        relation_field_name='observation_method',
        parent_field_name='failure_mode',
        label='维测手段',
        current_user=request.auth,
    )
    _sync_ordered_relations(
        parent=instance,
        ids=payload.get('huatuo_diagnosis_ids'),
        relation_model=FailureModeHuatuoDiagnosisRel,
        target_model=HuatuoDiagnosis,
        relation_field_name='huatuo_diagnosis',
        parent_field_name='failure_mode',
        label='华佗诊断方案',
        current_user=request.auth,
    )
    instance = _failure_mode_queryset().get(id=instance.id)
    return _serialize_failure_mode(instance)


@transaction.atomic
def update_failure_mode(request, failure_mode_id: str, data) -> dict[str, Any]:
    payload = data.dict(exclude_unset=True)
    instance = get_object_or_404(_failure_mode_queryset(), id=failure_mode_id)
    _update_failure_mode_attrs(instance, payload)
    instance.sys_modifier = request.auth
    instance.save()
    if 'author_ids' in payload:
        _sync_owner_relation(instance, 'authors', payload.get('author_ids'), request.auth)
    if 'interception_strategy_ids' in payload:
        _sync_ordered_relations(
            parent=instance,
            ids=payload.get('interception_strategy_ids'),
            relation_model=FailureModeInterceptionStrategyRel,
            target_model=InterceptionStrategy,
            relation_field_name='interception_strategy',
            parent_field_name='failure_mode',
            label='产线拦截策略',
            current_user=request.auth,
        )
    if 'handling_measure_ids' in payload:
        _sync_ordered_relations(
            parent=instance,
            ids=payload.get('handling_measure_ids'),
            relation_model=FailureModeHandlingMeasureRel,
            target_model=HandlingMeasure,
            relation_field_name='handling_measure',
            parent_field_name='failure_mode',
            label='故障处理措施',
            current_user=request.auth,
        )
    if 'observation_method_ids' in payload:
        _sync_ordered_relations(
            parent=instance,
            ids=payload.get('observation_method_ids'),
            relation_model=FailureModeObservationMethodRel,
            target_model=ObservationMethod,
            relation_field_name='observation_method',
            parent_field_name='failure_mode',
            label='维测手段',
            current_user=request.auth,
        )
    if 'huatuo_diagnosis_ids' in payload:
        _sync_ordered_relations(
            parent=instance,
            ids=payload.get('huatuo_diagnosis_ids'),
            relation_model=FailureModeHuatuoDiagnosisRel,
            target_model=HuatuoDiagnosis,
            relation_field_name='huatuo_diagnosis',
            parent_field_name='failure_mode',
            label='华佗诊断方案',
            current_user=request.auth,
        )
    instance = _failure_mode_queryset().get(id=instance.id)
    return _serialize_failure_mode(instance)


def get_failure_mode_detail(failure_mode_id: str) -> dict[str, Any]:
    instance = get_object_or_404(_failure_mode_queryset(), id=failure_mode_id)
    return _serialize_failure_mode(instance)


@transaction.atomic
def delete_failure_mode(failure_mode_id: str) -> dict[str, bool]:
    instance = get_object_or_404(FailureMode.objects.filter(is_deleted=False), id=failure_mode_id)
    instance.delete()
    return {'success': True}


def list_interception_strategies(filters, pagination=None) -> Any:
    queryset = _interception_strategy_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(interception_item__icontains=filters.keyword)
            | Q(station__icontains=filters.keyword)
        )
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(
        queryset,
        _serialize_interception_strategy,
        pagination,
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


@transaction.atomic
def delete_interception_strategy(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(InterceptionStrategy.objects.filter(is_deleted=False), id=item_id)
    if instance.failure_mode_relations.exists():
        raise HttpError(409, '该产线拦截策略已被故障模式引用，无法删除')
    instance.delete()
    return {'success': True}


def list_handling_measures(filters, pagination=None) -> Any:
    queryset = _handling_measure_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(measure__icontains=filters.keyword)
            | Q(measure_category__icontains=filters.keyword)
            | Q(measure_effect__icontains=filters.keyword)
        )
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_handling_measure, pagination)


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


@transaction.atomic
def delete_handling_measure(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(HandlingMeasure.objects.filter(is_deleted=False), id=item_id)
    if instance.failure_mode_relations.exists():
        raise HttpError(409, '该故障处理措施已被故障模式引用，无法删除')
    instance.delete()
    return {'success': True}


def list_observation_methods(filters, pagination=None) -> Any:
    queryset = _observation_method_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(monitor_type__icontains=filters.keyword)
            | Q(log_id__icontains=filters.keyword)
            | Q(log_keyword__icontains=filters.keyword)
            | Q(log_path__icontains=filters.keyword)
        )
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_observation_method, pagination)


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


@transaction.atomic
def delete_observation_method(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(ObservationMethod.objects.filter(is_deleted=False), id=item_id)
    if instance.failure_mode_relations.exists():
        raise HttpError(409, '该维测手段已被故障模式引用，无法删除')
    instance.delete()
    return {'success': True}


def list_huatuo_diagnoses(filters, pagination=None) -> Any:
    queryset = _huatuo_diagnosis_queryset()
    if filters.keyword:
        queryset = queryset.filter(description__icontains=filters.keyword)
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_huatuo_diagnosis, pagination)


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


@transaction.atomic
def delete_huatuo_diagnosis(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(HuatuoDiagnosis.objects.filter(is_deleted=False), id=item_id)
    if instance.failure_mode_relations.exists():
        raise HttpError(409, '该华佗诊断方案已被故障模式引用，无法删除')
    instance.delete()
    return {'success': True}


def list_test_cases(filters, pagination=None) -> Any:
    queryset = _test_case_queryset()
    if filters.keyword:
        queryset = queryset.filter(
            Q(brief__icontains=filters.keyword)
            | Q(cida_link__icontains=filters.keyword)
        )
    queryset = queryset.order_by('-sort', '-sys_create_datetime')
    return _serialize_paginated_queryset(queryset, _serialize_test_case, pagination)


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


@transaction.atomic
def delete_test_case(item_id: str) -> dict[str, bool]:
    instance = get_object_or_404(TestCase.objects.filter(is_deleted=False), id=item_id)
    if instance.handling_measure_relations.exists():
        raise HttpError(409, '该测试用例已被故障处理措施引用，无法删除')
    instance.delete()
    return {'success': True}


def get_failure_mode_dict_options() -> dict[str, Any]:
    rows = (
        DictItem.objects.select_related('dict')
        .filter(
            dict__code__in=set(DICT_CODE_MAP.values()),
            dict__status=True,
            dict__is_deleted=False,
            status=True,
            is_deleted=False,
        )
        .order_by('dict__code', '-sort', 'sys_create_datetime')
    )

    grouped: dict[str, list[dict[str, str]]] = {field: [] for field in DICT_CODE_MAP.keys()}
    seen: dict[str, set[str]] = {field: set() for field in DICT_CODE_MAP.keys()}
    reverse_map = {dict_code: field for field, dict_code in DICT_CODE_MAP.items()}

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
        grouped[field].append({'label': label, 'value': label})

    return grouped
