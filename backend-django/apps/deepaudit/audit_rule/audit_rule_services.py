from __future__ import annotations

import copy

from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from apps.deepaudit.audit_rule.audit_rule_model import AuditRule, AuditRuleSet
from apps.deepaudit.c_family import C_FAMILY_SYSTEM_RULE_SET_NAME
from apps.deepaudit.heuristics import DEFAULT_RULE_PATTERNS
from apps.deepaudit.permissions import get_user_id
from apps.deepaudit.runtime import load_rule_export
from apps.deepaudit.scenario_profile import SCENARIO_RULE_SET_SEEDS
from apps.deepaudit.serialization import format_datetime_text


DEFAULT_RULE_SETS = [
    {
        'name': '内置安全规则集',
        'description': '基于 DeepAudit 迁移的默认安全启发式规则',
        'language': 'all',
        'rule_type': 'builtin',
        'severity_weights': {'critical': 10, 'high': 5, 'medium': 2, 'low': 1},
        'is_default': True,
        'is_system': True,
        'is_active': True,
        'rules': [
            {
                'rule_code': item.code,
                'name': item.title,
                'description': item.description,
                'category': item.issue_type,
                'severity': item.severity,
                'fix_suggestion': item.suggestion,
                'enabled': True,
            }
            for item in DEFAULT_RULE_PATTERNS
        ],
    },
    {
        'name': C_FAMILY_SYSTEM_RULE_SET_NAME,
        'description': '面向嵌入式 C/C++ 项目的 CERT/CWE 语义规则集',
        'language': 'cpp',
        'rule_type': 'builtin',
        'severity_weights': {'critical': 18, 'high': 10, 'medium': 5, 'low': 2},
        'is_default': False,
        'is_system': True,
        'is_active': True,
        'rules': [
            {
                'rule_code': item.code,
                'name': item.title,
                'description': item.description,
                'category': item.issue_type,
                'severity': item.severity,
                'fix_suggestion': item.suggestion,
                'custom_prompt': (
                    '请结合上下文确认根因、触发条件、影响场景、边界/生命周期约束，'
                    '并给出 CERT/CWE 对应的修复建议。'
                ),
                'enabled': True,
            }
            for item in DEFAULT_RULE_PATTERNS
            if item.issue_type in {
                'buffer_overflow',
                'out_of_bounds',
                'integer_overflow',
                'null_dereference',
                'use_after_free',
                'double_free',
                'uninitialized_memory',
                'resource_leak',
                'race_condition',
                'deadlock',
                'format_string',
                'api_contract_violation',
            }
        ],
    },
    *[copy.deepcopy(item) for item in SCENARIO_RULE_SET_SEEDS],
]


def serialize_rule(rule: AuditRule) -> dict:
    return {
        'id': str(rule.id),
        'rule_set_id': str(rule.rule_set_id),
        'rule_code': rule.rule_code,
        'name': rule.name,
        'description': rule.description,
        'category': rule.category,
        'severity': rule.severity,
        'custom_prompt': rule.custom_prompt,
        'fix_suggestion': rule.fix_suggestion,
        'reference_url': rule.reference_url,
        'enabled': rule.enabled,
        'sys_create_datetime': format_datetime_text(rule.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(rule.sys_update_datetime),
    }


def serialize_rule_set(instance: AuditRuleSet, include_rules: bool = True) -> dict:
    rules_qs = instance.rules.filter(is_deleted=False).order_by('sort', 'rule_code')
    rules = [serialize_rule(rule) for rule in rules_qs] if include_rules else []
    return {
        'id': str(instance.id),
        'name': instance.name,
        'description': instance.description,
        'language': instance.language,
        'rule_type': instance.rule_type,
        'severity_weights': instance.severity_weights or {},
        'is_default': instance.is_default,
        'is_system': instance.is_system,
        'is_active': instance.is_active,
        'created_by': str(instance.created_by_id) if instance.created_by_id else None,
        'rules_count': rules_qs.count(),
        'enabled_rules_count': rules_qs.filter(enabled=True).count(),
        'rules': rules,
        'sys_create_datetime': format_datetime_text(instance.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(instance.sys_update_datetime),
    }


def _visible_queryset(user):
    user_id = get_user_id(user)
    queryset = AuditRuleSet.objects.filter(is_deleted=False)
    return (queryset.filter(is_system=True) | queryset.filter(created_by_id=user_id)).distinct()


def list_rule_sets(user, *, keyword: str = '', language: str = '', rule_type: str = '', is_active: bool | None = None, page: int = 1, page_size: int = 20) -> dict:
    queryset = _visible_queryset(user).order_by('-is_default', '-is_system', 'name')
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)
    if language:
        queryset = queryset.filter(language=language)
    if rule_type:
        queryset = queryset.filter(rule_type=rule_type)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    items = [serialize_rule_set(item) for item in queryset[start:start + page_size]]
    return {'items': items, 'total': total}


def get_rule_set(user, rule_set_id: str) -> AuditRuleSet:
    instance = get_object_or_404(AuditRuleSet, id=rule_set_id, is_deleted=False)
    if not instance.is_system and str(instance.created_by_id or '') != str(getattr(user, 'id', '')):
        raise HttpError(403, '无权访问该规则集')
    return instance


def create_rule_set(user, payload: dict) -> AuditRuleSet:
    rules = payload.pop('rules', [])
    instance = AuditRuleSet.objects.create(
        name=str(payload.get('name') or '').strip(),
        description=str(payload.get('description') or '').strip() or None,
        language=str(payload.get('language') or 'all').strip() or 'all',
        rule_type=str(payload.get('rule_type') or 'custom').strip() or 'custom',
        severity_weights=payload.get('severity_weights') or {},
        is_active=bool(payload.get('is_active', True)),
        is_default=False,
        is_system=False,
        created_by=user,
        sys_creator=user,
        sys_modifier=user,
    )
    for rule in rules:
        AuditRule.objects.create(
            rule_set=instance,
            rule_code=str(rule.get('rule_code') or '').strip(),
            name=str(rule.get('name') or '').strip(),
            description=rule.get('description') or None,
            category=str(rule.get('category') or 'security').strip() or 'security',
            severity=str(rule.get('severity') or 'medium').strip() or 'medium',
            custom_prompt=rule.get('custom_prompt') or None,
            fix_suggestion=rule.get('fix_suggestion') or None,
            reference_url=rule.get('reference_url') or None,
            enabled=bool(rule.get('enabled', True)),
            sys_creator=user,
            sys_modifier=user,
        )
    return instance


def update_rule_set(user, rule_set_id: str, payload: dict) -> AuditRuleSet:
    instance = get_rule_set(user, rule_set_id)
    if instance.is_system and not getattr(user, 'is_superuser', False):
        raise HttpError(403, '系统规则集仅允许超级管理员修改')
    for field in ('name', 'description', 'language', 'rule_type', 'is_active'):
        if field in payload:
            setattr(instance, field, payload[field])
    if payload.get('severity_weights') is not None:
        instance.severity_weights = payload.get('severity_weights') or {}
    instance.sys_modifier = user
    instance.save()
    return instance


def delete_rule_set(user, rule_set_id: str) -> bool:
    instance = get_rule_set(user, rule_set_id)
    if instance.is_system:
        raise HttpError(403, '系统规则集不允许删除')
    instance.is_deleted = True
    instance.sys_modifier = user
    instance.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return True


def set_default_rule_set(user, rule_set_id: str) -> bool:
    instance = get_rule_set(user, rule_set_id)
    AuditRuleSet.objects.filter(created_by_id=get_user_id(user), is_deleted=False).update(is_default=False)
    instance.is_default = True
    instance.sys_modifier = user
    instance.save(update_fields=['is_default', 'sys_modifier', 'sys_update_datetime'])
    return True


def add_rule(user, rule_set_id: str, payload: dict) -> AuditRule:
    rule_set = get_rule_set(user, rule_set_id)
    if rule_set.is_system and not getattr(user, 'is_superuser', False):
        raise HttpError(403, '系统规则集仅允许超级管理员修改')
    return AuditRule.objects.create(
        rule_set=rule_set,
        rule_code=str(payload.get('rule_code') or '').strip(),
        name=str(payload.get('name') or '').strip(),
        description=payload.get('description') or None,
        category=str(payload.get('category') or 'security').strip() or 'security',
        severity=str(payload.get('severity') or 'medium').strip() or 'medium',
        custom_prompt=payload.get('custom_prompt') or None,
        fix_suggestion=payload.get('fix_suggestion') or None,
        reference_url=payload.get('reference_url') or None,
        enabled=bool(payload.get('enabled', True)),
        sys_creator=user,
        sys_modifier=user,
    )


def update_rule(user, rule_set_id: str, rule_id: str, payload: dict) -> AuditRule:
    rule_set = get_rule_set(user, rule_set_id)
    rule = get_object_or_404(AuditRule, id=rule_id, rule_set=rule_set, is_deleted=False)
    if rule_set.is_system and not getattr(user, 'is_superuser', False):
        raise HttpError(403, '系统规则集仅允许超级管理员修改')
    for field in ('rule_code', 'name', 'description', 'category', 'severity', 'custom_prompt', 'fix_suggestion', 'reference_url', 'enabled'):
        if field in payload:
            setattr(rule, field, payload[field])
    rule.sys_modifier = user
    rule.save()
    return rule


def delete_rule(user, rule_set_id: str, rule_id: str) -> bool:
    rule_set = get_rule_set(user, rule_set_id)
    rule = get_object_or_404(AuditRule, id=rule_id, rule_set=rule_set, is_deleted=False)
    if rule_set.is_system and not getattr(user, 'is_superuser', False):
        raise HttpError(403, '系统规则集仅允许超级管理员修改')
    rule.is_deleted = True
    rule.sys_modifier = user
    rule.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return True


def toggle_rule(user, rule_set_id: str, rule_id: str) -> dict:
    rule = update_rule(user, rule_set_id, rule_id, {'enabled': not get_object_or_404(AuditRule, id=rule_id, is_deleted=False).enabled})
    return {'enabled': rule.enabled, 'message': '规则状态已更新'}


def import_rule_set(user, payload: dict) -> AuditRuleSet:
    return create_rule_set(user, payload)


def export_rule_set(user, rule_set_id: str) -> dict:
    return load_rule_export(get_rule_set(user, rule_set_id))


def ensure_default_rule_sets() -> int:
    created = 0
    for raw_item in DEFAULT_RULE_SETS:
        item = {**raw_item}
        if AuditRuleSet.objects.filter(name=item['name'], is_system=True, is_deleted=False).exists():
            continue
        rules = [dict(rule) for rule in item.pop('rules', [])]
        rule_set = AuditRuleSet.objects.create(**item)
        for rule in rules:
            AuditRule.objects.create(rule_set=rule_set, **rule)
        created += 1
    return created
