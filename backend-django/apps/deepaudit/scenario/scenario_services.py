from __future__ import annotations

import copy
import re
import uuid
from typing import Any, Iterable

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from apps.deepaudit.agent_engine.knowledge.loader import knowledge_loader
from apps.deepaudit.audit_rule.audit_rule_model import AuditRuleSet
from apps.deepaudit.permissions import get_user_id, is_superadmin
from apps.deepaudit.prompt_template.prompt_template_model import PromptTemplate
from apps.deepaudit.scenario.scenario_model import AuditScenarioProfile, ScenarioObjectiveType
from apps.deepaudit.scenario.scenario_schemas import (
    ScenarioProfileCopySchema,
    ScenarioProfileListSchema,
    ScenarioProfileSaveSchema,
    ScenarioProfileSchema,
    ScenarioProfileUpdateSchema,
)
from apps.deepaudit.scenario_profile import (
    API_CHAIN_SCENARIO_KEY,
    CONCURRENCY_SCENARIO_KEY,
    GENERAL_SCENARIO_KEY,
    SCENARIO_DEFINITIONS,
    SYSTEM_SCENARIO_KEYS,
    _build_tool_policy,
    _normalize_key,
    _unique_list,
)
from apps.deepaudit.serialization import format_datetime_text, normalize_json_payload


SCENARIO_KEY_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_-]*$')
RESERVED_SCENARIO_KEYS = set(SYSTEM_SCENARIO_KEYS) | {
    'auto',
    'default',
    'legacy',
    'legacy_c_family',
    'c_family',
    'c-family',
    'critical_section',
    'scenario_a',
    'scenario_b',
    'scenario_c',
    'scenario_d',
    'a',
    'b',
    'c',
    'd',
}


def _visible_queryset(user):
    queryset = AuditScenarioProfile.objects.filter(is_deleted=False)
    if is_superadmin(user):
        return queryset.distinct()
    user_id = get_user_id(user)
    if not user_id:
        return queryset.filter(is_system=True).distinct()
    return (queryset.filter(is_system=True) | queryset.filter(created_by_id=user_id)).distinct()


def _visible_prompt_queryset(user):
    queryset = PromptTemplate.objects.filter(is_deleted=False, is_active=True)
    if is_superadmin(user):
        return queryset.distinct()
    user_id = get_user_id(user)
    if not user_id:
        return queryset.filter(is_system=True).distinct()
    return (queryset.filter(is_system=True) | queryset.filter(created_by_id=user_id)).distinct()


def _visible_rule_queryset(user):
    queryset = AuditRuleSet.objects.filter(is_deleted=False, is_active=True)
    if is_superadmin(user):
        return queryset.distinct()
    user_id = get_user_id(user)
    if not user_id:
        return queryset.filter(is_system=True).distinct()
    return (queryset.filter(is_system=True) | queryset.filter(created_by_id=user_id)).distinct()


def _normalize_objective_type(value: str | None) -> str:
    objective_type = str(value or ScenarioObjectiveType.AUDIT).strip().lower()
    if objective_type not in {ScenarioObjectiveType.AUDIT, ScenarioObjectiveType.INVENTORY}:
        raise HttpError(422, f'不支持的场景输出目标: {value}')
    return objective_type


def _normalize_tool_policy(
    payload: dict[str, Any] | None,
    *,
    target_vulnerabilities: Iterable[str],
    search_keywords: Iterable[str],
    objective_type: str = ScenarioObjectiveType.AUDIT,
) -> dict[str, Any]:
    policy = normalize_json_payload(payload or {})
    if policy:
        if objective_type == ScenarioObjectiveType.INVENTORY:
            inventory_defaults = _build_tool_policy(
                focus_vulnerabilities=target_vulnerabilities,
                search_keywords=search_keywords,
                quick_mode=True,
                objective_type=objective_type,
            )
            policy = {**inventory_defaults, **policy}
            policy['result_mode'] = 'inventory'
            default_allowed = _unique_list(inventory_defaults.get('allowed_tools') or [])
            default_blocked = _unique_list(inventory_defaults.get('blocked_tools') or [])
            custom_allowed = _unique_list((payload or {}).get('allowed_tools') or [])
            custom_blocked = _unique_list((payload or {}).get('blocked_tools') or [])
            allowed_set = set(default_allowed)
            policy['allowed_tools'] = [
                tool
                for tool in (custom_allowed or default_allowed)
                if tool in allowed_set
            ] or default_allowed
            policy['blocked_tools'] = _unique_list([*default_blocked, *custom_blocked])
        else:
            policy['result_mode'] = 'audit'

        smart_scan = dict(policy.get('smart_scan') or {})
        smart_scan.setdefault('quick_mode', objective_type == ScenarioObjectiveType.INVENTORY)
        smart_scan.setdefault('scan_types', ['pattern'])
        smart_scan.setdefault('focus_vulnerabilities', _unique_list(target_vulnerabilities))
        policy['smart_scan'] = smart_scan

        pattern_match = dict(policy.get('pattern_match') or {})
        pattern_match.setdefault('pattern_types', _unique_list(target_vulnerabilities))
        policy['pattern_match'] = pattern_match

        search_code = dict(policy.get('search_code') or {})
        search_code.setdefault('keywords', _unique_list(search_keywords))
        policy['search_code'] = search_code
        policy.setdefault(
            'first_pass_order',
            (
                ['search_code', 'rag_query', 'read_file', 'function_context', 'pattern_match', 'smart_scan']
                if objective_type == ScenarioObjectiveType.INVENTORY
                else ['semgrep_scan', 'smart_scan', 'pattern_match']
            ),
        )
        if objective_type == ScenarioObjectiveType.INVENTORY:
            blocked = {str(item).strip() for item in policy.get('blocked_tools') or [] if str(item).strip()}
            allowed = {str(item).strip() for item in policy.get('allowed_tools') or [] if str(item).strip()}
            policy['first_pass_order'] = [
                tool
                for tool in _unique_list(policy.get('first_pass_order') or [])
                if tool not in blocked and (not allowed or tool in allowed)
            ]
        return policy

    return _build_tool_policy(
        focus_vulnerabilities=target_vulnerabilities,
        search_keywords=search_keywords,
        quick_mode=False,
        objective_type=objective_type,
    )


def _default_rule_set_for_user(user):
    return _visible_rule_queryset(user).order_by('-is_default', 'name').prefetch_related('rules').first()


def _default_prompt_template_for_user(user):
    return _visible_prompt_queryset(user).order_by('-is_default', 'name').first()


def _resolve_prompt_template(user, template_id: str | None) -> PromptTemplate | None:
    if not template_id:
        return None
    template = get_object_or_404(PromptTemplate, id=template_id, is_deleted=False)
    if not template.is_system and str(template.created_by_id or '') != str(get_user_id(user)) and not is_superadmin(user):
        raise HttpError(403, '无权访问该提示词模板')
    return template


def _resolve_rule_set(user, rule_set_id: str | None) -> AuditRuleSet | None:
    if not rule_set_id:
        return None
    rule_set = get_object_or_404(AuditRuleSet, id=rule_set_id, is_deleted=False)
    if not rule_set.is_system and str(rule_set.created_by_id or '') != str(get_user_id(user)) and not is_superadmin(user):
        raise HttpError(403, '无权访问该规则集')
    return rule_set


def _normalize_scenario_key(value: str | None, *, fallback_name: str = '') -> str:
    normalized = _normalize_key(value)
    if normalized and normalized not in RESERVED_SCENARIO_KEYS and SCENARIO_KEY_PATTERN.fullmatch(normalized):
        return normalized

    base = re.sub(r'[^a-z0-9_-]+', '_', str(value or fallback_name or '').strip().lower())
    base = base.strip('_-')
    if not base or not SCENARIO_KEY_PATTERN.fullmatch(base):
        base = f'scenario_{uuid.uuid4().hex[:8]}'
    if base in RESERVED_SCENARIO_KEYS:
        base = f'{base}_{uuid.uuid4().hex[:4]}'
    return base


def _generate_copy_key(base_key: str) -> str:
    candidate = f'{base_key}_copy'
    if candidate not in RESERVED_SCENARIO_KEYS and not AuditScenarioProfile.objects.filter(scenario_key=candidate, is_deleted=False).exists():
        return candidate
    suffix = 2
    while True:
        next_key = f'{base_key}_copy_{suffix}'
        if next_key not in RESERVED_SCENARIO_KEYS and not AuditScenarioProfile.objects.filter(scenario_key=next_key, is_deleted=False).exists():
            return next_key
        suffix += 1


def _collect_rule_categories(rule_set: AuditRuleSet | None) -> list[str]:
    if not rule_set:
        return []
    return _unique_list(
        rule.category
        for rule in rule_set.rules.filter(is_deleted=False, enabled=True).order_by('sort', 'rule_code')
        if str(rule.category or '').strip()
    )


def _default_search_keywords(objective_type: str, rule_set: AuditRuleSet | None, scenario_key: str) -> list[str]:
    definition = SCENARIO_DEFINITIONS.get(scenario_key, {})
    keywords = list(definition.get('focus_keywords') or [])
    if keywords:
        return _unique_list(keywords)

    if objective_type == ScenarioObjectiveType.INVENTORY:
        categories = _collect_rule_categories(rule_set)
        return categories[:12]
    return []


def _build_default_tool_policy_for_scenario(
    *,
    objective_type: str,
    rule_set: AuditRuleSet | None,
    scenario_key: str,
    knowledge_modules: Iterable[str],
) -> dict[str, Any]:
    target_vulnerabilities = _collect_rule_categories(rule_set)
    search_keywords = _default_search_keywords(objective_type, rule_set, scenario_key)
    if not target_vulnerabilities:
        definition = SCENARIO_DEFINITIONS.get(scenario_key, {})
        target_vulnerabilities = _unique_list(definition.get('target_vulnerabilities') or [])
    if not search_keywords:
        search_keywords = _unique_list(definition.get('focus_keywords') or [] ) if (definition := SCENARIO_DEFINITIONS.get(scenario_key, {})) else []
    return _normalize_tool_policy(
        None,
        target_vulnerabilities=target_vulnerabilities,
        search_keywords=search_keywords or knowledge_modules,
        objective_type=objective_type,
    )


def serialize_scenario(instance: AuditScenarioProfile) -> dict[str, Any]:
    tool_policy = normalize_json_payload(instance.tool_policy or {})
    if not tool_policy:
        tool_policy = _build_default_tool_policy_for_scenario(
            objective_type=instance.objective_type,
            rule_set=instance.rule_set,
            scenario_key=str(instance.scenario_key or ''),
            knowledge_modules=instance.knowledge_modules or [],
        )
    smart_scan = dict(tool_policy.get('smart_scan') or {})
    pattern_match = dict(tool_policy.get('pattern_match') or {})
    search_code = dict(tool_policy.get('search_code') or {})
    target_vulnerabilities = _unique_list(
        smart_scan.get('focus_vulnerabilities')
        or pattern_match.get('pattern_types')
        or _collect_rule_categories(instance.rule_set)
    )
    focus_keywords = _unique_list(
        search_code.get('keywords')
        or _default_search_keywords(instance.objective_type, instance.rule_set, str(instance.scenario_key or ''))
    )
    return {
        'id': str(instance.id),
        'scenario_key': instance.scenario_key,
        'name': instance.name,
        'description': instance.description or '',
        'objective_type': instance.objective_type,
        'prompt_template_id': str(instance.prompt_template_id) if instance.prompt_template_id else None,
        'prompt_template_name': instance.prompt_template.name if instance.prompt_template else None,
        'rule_set_id': str(instance.rule_set_id) if instance.rule_set_id else None,
        'rule_set_name': instance.rule_set.name if instance.rule_set else None,
        'knowledge_modules': list(instance.knowledge_modules or []),
        'knowledge_modules_count': len(list(instance.knowledge_modules or [])),
        'target_vulnerabilities': target_vulnerabilities,
        'focus_keywords': focus_keywords,
        'tool_policy': tool_policy,
        'is_default': instance.is_default,
        'is_system': instance.is_system,
        'is_active': instance.is_active,
        'created_by': str(instance.created_by_id) if instance.created_by_id else None,
        'sys_create_datetime': format_datetime_text(instance.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(instance.sys_update_datetime),
    }


def list_scenarios(user, *, keyword: str = '', objective_type: str = '', is_active: bool | None = None, page: int = 1, page_size: int = 20) -> dict:
    queryset = _visible_queryset(user).select_related('prompt_template', 'rule_set', 'created_by').prefetch_related('rule_set__rules')
    queryset = queryset.order_by('-is_default', 'is_system', 'name')
    if keyword:
        queryset = queryset.filter(
            Q(name__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(scenario_key__icontains=keyword)
        )
    if objective_type:
        queryset = queryset.filter(objective_type=_normalize_objective_type(objective_type))
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    items = [serialize_scenario(item) for item in queryset[start:start + page_size]]
    return {'items': items, 'total': total}


def get_scenario(user, scenario_id: str) -> AuditScenarioProfile:
    scenario = get_object_or_404(AuditScenarioProfile, id=scenario_id, is_deleted=False)
    if not scenario.is_system and str(scenario.created_by_id or '') != str(get_user_id(user)) and not is_superadmin(user):
        raise HttpError(403, '无权访问该场景')
    return scenario


def create_scenario(user, payload: dict) -> AuditScenarioProfile:
    name = str(payload.get('name') or '').strip()
    if not name:
        raise HttpError(422, '场景名称不能为空')

    objective_type = _normalize_objective_type(payload.get('objective_type'))
    prompt_template = _resolve_prompt_template(user, payload.get('prompt_template_id')) if payload.get('prompt_template_id') else None
    rule_set = _resolve_rule_set(user, payload.get('rule_set_id')) if payload.get('rule_set_id') else None
    scenario_key = _normalize_scenario_key(payload.get('scenario_key'), fallback_name=name)
    if scenario_key in RESERVED_SCENARIO_KEYS:
        raise HttpError(422, f'场景键 `{scenario_key}` 属于系统保留键，请更换一个自定义场景键')
    if AuditScenarioProfile.objects.filter(scenario_key=scenario_key, is_deleted=False).exists():
        raise HttpError(422, f'场景键 `{scenario_key}` 已存在')

    knowledge_modules = _unique_list(payload.get('knowledge_modules') or [])
    validation = knowledge_loader.validate_modules(knowledge_modules) if knowledge_modules else {'valid': [], 'invalid': []}
    if validation.get('invalid'):
        raise HttpError(422, f"无效的知识模块: {', '.join(validation['invalid'])}")

    if payload.get('tool_policy'):
        tool_policy = _normalize_tool_policy(
            payload.get('tool_policy') or {},
            target_vulnerabilities=_collect_rule_categories(rule_set),
            search_keywords=_default_search_keywords(objective_type, rule_set, scenario_key),
            objective_type=objective_type,
        )
    else:
        tool_policy = _build_default_tool_policy_for_scenario(
            objective_type=objective_type,
            rule_set=rule_set,
            scenario_key=scenario_key,
            knowledge_modules=knowledge_modules,
        )
    instance = AuditScenarioProfile.objects.create(
        scenario_key=scenario_key,
        name=name,
        description=str(payload.get('description') or '').strip() or None,
        objective_type=objective_type,
        prompt_template=prompt_template,
        rule_set=rule_set,
        knowledge_modules=knowledge_modules,
        tool_policy=tool_policy,
        is_active=bool(payload.get('is_active', True)),
        is_default=bool(payload.get('is_default', False)),
        is_system=False,
        created_by=user,
        sys_creator=user,
        sys_modifier=user,
    )
    if instance.is_default:
        AuditScenarioProfile.objects.filter(
            created_by_id=get_user_id(user),
            is_deleted=False,
            is_system=False,
        ).exclude(id=instance.id).update(is_default=False)
    return instance


def update_scenario(user, scenario_id: str, payload: dict) -> AuditScenarioProfile:
    scenario = get_scenario(user, scenario_id)
    if scenario.is_system and not is_superadmin(user):
        raise HttpError(403, '系统场景仅允许超级管理员修改')

    if 'name' in payload:
        name = str(payload.get('name') or '').strip()
        if not name:
            raise HttpError(422, '场景名称不能为空')
        scenario.name = name
    if 'description' in payload:
        scenario.description = str(payload.get('description') or '').strip() or None
    if 'objective_type' in payload:
        scenario.objective_type = _normalize_objective_type(payload.get('objective_type'))
    if 'prompt_template_id' in payload:
        scenario.prompt_template = _resolve_prompt_template(user, payload.get('prompt_template_id')) if payload.get('prompt_template_id') else None
    if 'rule_set_id' in payload:
        scenario.rule_set = _resolve_rule_set(user, payload.get('rule_set_id')) if payload.get('rule_set_id') else None
    if 'knowledge_modules' in payload:
        knowledge_modules = _unique_list(payload.get('knowledge_modules') or [])
        validation = knowledge_loader.validate_modules(knowledge_modules) if knowledge_modules else {'valid': [], 'invalid': []}
        if validation.get('invalid'):
            raise HttpError(422, f"无效的知识模块: {', '.join(validation['invalid'])}")
        scenario.knowledge_modules = knowledge_modules
    if 'tool_policy' in payload:
        scenario.tool_policy = _normalize_tool_policy(
            payload.get('tool_policy') or {},
            target_vulnerabilities=_collect_rule_categories(scenario.rule_set),
            search_keywords=_default_search_keywords(scenario.objective_type, scenario.rule_set, scenario.scenario_key),
            objective_type=scenario.objective_type,
        )
    elif 'objective_type' in payload or 'rule_set_id' in payload:
        scenario.tool_policy = _build_default_tool_policy_for_scenario(
            objective_type=scenario.objective_type,
            rule_set=scenario.rule_set,
            scenario_key=scenario.scenario_key,
            knowledge_modules=scenario.knowledge_modules or [],
        )
    if 'is_active' in payload:
        scenario.is_active = bool(payload.get('is_active'))
    if 'is_default' in payload:
        scenario.is_default = bool(payload.get('is_default'))
        if scenario.is_default:
            AuditScenarioProfile.objects.filter(
                created_by_id=get_user_id(user),
                is_deleted=False,
                is_system=False,
            ).exclude(id=scenario.id).update(is_default=False)
    scenario.sys_modifier = user
    scenario.save()
    return scenario


def delete_scenario(user, scenario_id: str) -> bool:
    scenario = get_scenario(user, scenario_id)
    if scenario.is_system:
        raise HttpError(403, '系统场景不允许删除')
    scenario.is_deleted = True
    scenario.sys_modifier = user
    scenario.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return True


def copy_scenario(user, scenario_id: str, payload: dict | None = None) -> AuditScenarioProfile:
    source = get_scenario(user, scenario_id)
    payload = dict(payload or {})
    name = str(payload.get('name') or f'{source.name}（副本）').strip()
    description = str(payload.get('description') or source.description or '').strip() or None
    scenario_key = _normalize_scenario_key(payload.get('scenario_key') or _generate_copy_key(source.scenario_key), fallback_name=name)
    if scenario_key in RESERVED_SCENARIO_KEYS:
        scenario_key = _generate_copy_key(source.scenario_key)
    if AuditScenarioProfile.objects.filter(scenario_key=scenario_key, is_deleted=False).exists():
        scenario_key = _generate_copy_key(scenario_key)

    clone = AuditScenarioProfile.objects.create(
        scenario_key=scenario_key,
        name=name,
        description=description,
        objective_type=_normalize_objective_type(payload.get('objective_type') or source.objective_type),
        prompt_template=source.prompt_template,
        rule_set=source.rule_set,
        knowledge_modules=list(source.knowledge_modules or []),
        tool_policy=normalize_json_payload(payload.get('tool_policy') or source.tool_policy or {}),
        is_active=bool(payload.get('is_active', source.is_active)),
        is_default=bool(payload.get('is_default', False)),
        is_system=False,
        created_by=user,
        sys_creator=user,
        sys_modifier=user,
    )
    if not clone.tool_policy:
        clone.tool_policy = _build_default_tool_policy_for_scenario(
            objective_type=clone.objective_type,
            rule_set=clone.rule_set,
            scenario_key=clone.scenario_key,
            knowledge_modules=clone.knowledge_modules or [],
        )
        clone.save(update_fields=['tool_policy', 'sys_modifier', 'sys_update_datetime'])
    return clone


def set_default_scenario(user, scenario_id: str) -> bool:
    scenario = get_scenario(user, scenario_id)
    if scenario.is_system and not is_superadmin(user):
        raise HttpError(403, '系统场景仅允许超级管理员修改')
    AuditScenarioProfile.objects.filter(
        created_by_id=get_user_id(user),
        is_deleted=False,
        is_system=False,
    ).update(is_default=False)
    scenario.is_default = True
    scenario.sys_modifier = user
    scenario.save(update_fields=['is_default', 'sys_modifier', 'sys_update_datetime'])
    return True


def ensure_default_scenarios() -> int:
    created = 0
    from apps.deepaudit.prompt_template.prompt_template_services import ensure_default_templates
    from apps.deepaudit.audit_rule.audit_rule_services import ensure_default_rule_sets

    ensure_default_templates()
    ensure_default_rule_sets()

    seed_keys = [GENERAL_SCENARIO_KEY, CONCURRENCY_SCENARIO_KEY, API_CHAIN_SCENARIO_KEY]
    for key in seed_keys:
        if AuditScenarioProfile.objects.filter(scenario_key=key, is_deleted=False).exists():
            continue
        definition = dict(SCENARIO_DEFINITIONS[key])
        prompt_template = _default_prompt_template_for_user(None)
        rule_set = _default_rule_set_for_user(None)
        if definition.get('prompt_template_name'):
            prompt_template = (
                PromptTemplate.objects.filter(name=definition['prompt_template_name'], is_deleted=False)
                .order_by('-is_system', '-is_default', 'name')
                .first()
            )
        if definition.get('rule_set_name'):
            rule_set = (
                AuditRuleSet.objects.filter(name=definition['rule_set_name'], is_deleted=False)
                .prefetch_related('rules')
                .order_by('-is_system', '-is_default', 'name')
                .first()
            )
        scenario = AuditScenarioProfile.objects.create(
            scenario_key=key,
            name=definition.get('scenario_name') or key,
            description=definition.get('description') or None,
            objective_type=str(definition.get('objective_type') or ScenarioObjectiveType.AUDIT),
            prompt_template=prompt_template,
            rule_set=rule_set,
            knowledge_modules=list(definition.get('knowledge_modules') or []),
            tool_policy=_build_tool_policy(
                focus_vulnerabilities=definition.get('target_vulnerabilities') or [],
                search_keywords=definition.get('focus_keywords') or [],
                quick_mode=False,
                objective_type=str(definition.get('objective_type') or ScenarioObjectiveType.AUDIT),
            ),
            is_default=bool(definition.get('scenario_code') == 'D'),
            is_system=True,
            is_active=True,
            sys_creator=None,
            sys_modifier=None,
        )
        if scenario:
            created += 1
    return created
