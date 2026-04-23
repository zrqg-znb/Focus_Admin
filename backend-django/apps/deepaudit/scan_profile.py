from __future__ import annotations

from typing import Any

from django.db.models import Q
from ninja.errors import HttpError

from apps.deepaudit.audit_rule.audit_rule_model import AuditRule, AuditRuleSet
from apps.deepaudit.c_family import (
    C_FAMILY_SYSTEM_PROMPT_TEMPLATE_NAME,
    C_FAMILY_SYSTEM_RULE_SET_NAME,
    build_c_family_analysis_profile,
    normalize_analysis_depth,
)
from apps.deepaudit.heuristics import DEFAULT_RULE_PATTERNS, RulePattern, normalize_severity_weights
from apps.deepaudit.permissions import get_user_id
from apps.deepaudit.prompt_template.prompt_template_model import PromptTemplate


DEFAULT_ANALYSIS_DEPTH = 'standard'
DEFAULT_RULE_BY_CODE = {item.code: item for item in DEFAULT_RULE_PATTERNS}
DEFAULT_RULE_BY_ISSUE = {item.issue_type: item for item in DEFAULT_RULE_PATTERNS}
RULE_KEYWORD_MAP = {
    'command_injection': ('cmd', 'command', 'os.system', 'shell'),
    'hardcoded_secret': ('credential', 'password', 'secret', 'token'),
    'insecure_deserialization': ('deserialize', 'deserialization', 'pickle', 'yaml.load'),
    'path_traversal': ('directory traversal', 'file path', 'path traversal', 'read file'),
    'sql_injection': ('sql', 'sqli', 'injection', 'query'),
    'ssrf': ('http client', 'request forgery', 'ssrf', 'url fetch'),
    'unsafe_eval': ('dynamic execution', 'eval', 'exec'),
    'weak_crypto': ('crypto', 'encryption', 'hash', 'md5', 'sha1'),
    'xss': ('dom', 'html', 'innerhtml', 'script', 'xss'),
    'xxe': ('entity', 'xml', 'xxe'),
}
DEPTH_HINTS = {
    'basic': '基础模式：优先审计高价值代码单元。',
    'quick': '快速模式：优先输出高价值结果。',
    'standard': '标准模式：平衡覆盖率和审计成本。',
    'deep': '深入模式：补充更多上下文与修复说明。',
}


def _visible_rule_set_queryset(user):
    user_id = get_user_id(user)
    return (
        AuditRuleSet.objects.filter(is_deleted=False, is_active=True)
        .filter(Q(is_system=True) | Q(created_by_id=user_id))
        .distinct()
    )


def _visible_prompt_template_queryset(user):
    user_id = get_user_id(user)
    return (
        PromptTemplate.objects.filter(is_deleted=False, is_active=True)
        .filter(Q(is_system=True) | Q(created_by_id=user_id))
        .distinct()
    )


def resolve_rule_set(user, rule_set_id: str | None, *, strict: bool = False) -> AuditRuleSet | None:
    queryset = _visible_rule_set_queryset(user)
    user_id = get_user_id(user)
    if rule_set_id:
        instance = queryset.filter(id=rule_set_id).first()
        if strict and not instance:
            raise HttpError(404, '规则集不存在、未启用或无权访问')
        return instance
    return (
        queryset.filter(created_by_id=user_id, is_default=True).first()
        or queryset.filter(is_system=True, is_default=True).first()
        or queryset.order_by('-is_system', 'name').first()
    )


def resolve_named_system_rule_set(user, name: str) -> AuditRuleSet | None:
    return _visible_rule_set_queryset(user).filter(is_system=True, name=name).first()


def resolve_prompt_template(user, template_id: str | None, *, strict: bool = False) -> PromptTemplate | None:
    queryset = _visible_prompt_template_queryset(user)
    user_id = get_user_id(user)
    if template_id:
        instance = queryset.filter(id=template_id).first()
        if strict and not instance:
            raise HttpError(404, '提示词模板不存在、未启用或无权访问')
        return instance
    return (
        queryset.filter(created_by_id=user_id, is_default=True).first()
        or queryset.filter(is_system=True, is_default=True).first()
        or queryset.order_by('-is_system', 'name').first()
    )


def resolve_named_system_prompt_template(user, name: str) -> PromptTemplate | None:
    return _visible_prompt_template_queryset(user).filter(is_system=True, name=name).first()


def _guess_default_rule(text: str) -> RulePattern | None:
    normalized = str(text or '').strip().lower()
    if not normalized:
        return None
    for issue_type, keywords in RULE_KEYWORD_MAP.items():
        if any(keyword in normalized for keyword in keywords):
            return DEFAULT_RULE_BY_ISSUE.get(issue_type)
    return None


def _match_default_rule(rule: AuditRule) -> RulePattern | None:
    if rule.rule_code and rule.rule_code in DEFAULT_RULE_BY_CODE:
        return DEFAULT_RULE_BY_CODE[rule.rule_code]
    if rule.category and rule.category in DEFAULT_RULE_BY_ISSUE:
        return DEFAULT_RULE_BY_ISSUE[rule.category]
    candidate_text = ' '.join(
        filter(
            None,
            [
                str(rule.rule_code or ''),
                str(rule.category or ''),
                str(rule.name or ''),
                str(rule.description or ''),
                str(rule.custom_prompt or ''),
            ],
        )
    )
    return _guess_default_rule(candidate_text)


def build_runtime_rule_profile(rule_set: AuditRuleSet | None) -> dict[str, Any]:
    if not rule_set:
        return {
            'patterns': DEFAULT_RULE_PATTERNS,
            'enabled_rule_count': len(DEFAULT_RULE_PATTERNS),
            'rule_codes': [item.code for item in DEFAULT_RULE_PATTERNS],
            'unresolved_rules': [],
        }

    enabled_rules = list(
        rule_set.rules.filter(is_deleted=False, enabled=True).order_by('sort', 'rule_code')
    )
    patterns: list[RulePattern] = []
    unresolved_rules: list[str] = []
    for rule in enabled_rules:
        base = _match_default_rule(rule)
        if not base:
            unresolved_rules.append(rule.rule_code or rule.name or str(rule.id))
            continue
        patterns.append(
            RulePattern(
                code=str(rule.rule_code or base.code).strip() or base.code,
                issue_type=str(rule.category or base.issue_type).strip() or base.issue_type,
                title=str(rule.name or base.title).strip() or base.title,
                severity=str(rule.severity or base.severity).strip() or base.severity,
                patterns=base.patterns,
                suggestion=str(rule.fix_suggestion or base.suggestion).strip() or base.suggestion,
                description=str(rule.description or base.description).strip() or base.description,
            )
        )
    return {
        'patterns': tuple(patterns),
        'enabled_rule_count': len(enabled_rules),
        'rule_codes': [rule.rule_code for rule in enabled_rules if rule.rule_code],
        'unresolved_rules': unresolved_rules,
    }


def _infer_prompt_focus(*texts: str) -> list[str]:
    raw_text = ' '.join(filter(None, texts)).strip().lower()
    if not raw_text:
        return []
    focus: list[str] = []
    for issue_type, keywords in RULE_KEYWORD_MAP.items():
        if any(keyword in raw_text for keyword in keywords):
            focus.append(issue_type)
    return focus


def build_prompt_context(template: PromptTemplate | None, analysis_depth: str) -> dict[str, Any]:
    if not template:
        return {}
    content = str(template.content_zh or template.content_en or '').strip()
    return {
        'id': str(template.id),
        'name': template.name,
        'description': template.description or '',
        'template_type': template.template_type,
        'content_excerpt': content[:240],
        'focus': _infer_prompt_focus(template.name or '', template.description or '', content),
        'hint': DEPTH_HINTS.get(analysis_depth, DEPTH_HINTS[DEFAULT_ANALYSIS_DEPTH]),
    }


def resolve_scan_profile(user, scan_config: dict[str, Any] | None = None, *, strict: bool = False) -> dict[str, Any]:
    config = dict(scan_config or {})
    analysis_depth = normalize_analysis_depth(config.get('analysis_depth'))
    language_profile = dict(config.get('language_profile') or {})
    explicit_rule_set_id = config.get('rule_set_id')
    explicit_prompt_template_id = config.get('prompt_template_id')
    rule_set = resolve_rule_set(user, explicit_rule_set_id, strict=strict)
    prompt_template = resolve_prompt_template(user, explicit_prompt_template_id, strict=strict)
    if language_profile.get('is_c_family_dominant'):
        if not explicit_rule_set_id:
            rule_set = resolve_named_system_rule_set(user, C_FAMILY_SYSTEM_RULE_SET_NAME) or rule_set
        if not explicit_prompt_template_id:
            prompt_template = resolve_named_system_prompt_template(user, C_FAMILY_SYSTEM_PROMPT_TEMPLATE_NAME) or prompt_template
    rule_profile = build_runtime_rule_profile(rule_set)
    analysis_profile = (
        build_c_family_analysis_profile(
            analysis_depth=analysis_depth,
            language_profile=language_profile,
            context_sources=[],
            prompt_template_id=str(prompt_template.id) if prompt_template else None,
            rule_set_id=str(rule_set.id) if rule_set else None,
            engine='profile_resolver',
        )
        if language_profile.get('is_c_family_dominant')
        else {
            'analysis_depth': analysis_depth,
            'profile_mode': 'default',
            'language_profile': language_profile,
        }
    )
    return {
        'analysis_depth': analysis_depth,
        'language_profile': language_profile,
        'rule_set': rule_set,
        'prompt_template': prompt_template,
        'rule_patterns': rule_profile['patterns'],
        'severity_weights': normalize_severity_weights(rule_set.severity_weights if rule_set else None),
        'prompt_context': build_prompt_context(prompt_template, analysis_depth),
        'enabled_rule_count': rule_profile['enabled_rule_count'],
        'rule_codes': rule_profile['rule_codes'],
        'unresolved_rules': rule_profile['unresolved_rules'],
        'analysis_profile': analysis_profile,
    }


def serialize_scan_profile(profile: dict[str, Any]) -> dict[str, Any]:
    rule_set = profile.get('rule_set')
    prompt_template = profile.get('prompt_template')
    prompt_context = profile.get('prompt_context') or {}
    return {
        'analysis_depth': profile.get('analysis_depth') or DEFAULT_ANALYSIS_DEPTH,
        'rule_set_id': str(rule_set.id) if rule_set else None,
        'rule_set_name': rule_set.name if rule_set else None,
        'prompt_template_id': str(prompt_template.id) if prompt_template else None,
        'prompt_template_name': prompt_template.name if prompt_template else None,
        'enabled_rule_count': int(profile.get('enabled_rule_count') or 0),
        'rule_codes': list(profile.get('rule_codes') or []),
        'unresolved_rules': list(profile.get('unresolved_rules') or []),
        'prompt_focus': list(prompt_context.get('focus') or []),
        'prompt_hint': prompt_context.get('hint'),
        'language_profile': dict(profile.get('language_profile') or {}),
        'profile_mode': str((profile.get('analysis_profile') or {}).get('profile_mode') or 'default'),
    }
