from __future__ import annotations

import copy
import time

from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from apps.deepaudit.c_family import C_FAMILY_SYSTEM_PROMPT_TEMPLATE_NAME, get_c_family_prompt_text
from apps.deepaudit.llm.service import LLMService
from apps.deepaudit.permissions import get_user_id
from apps.deepaudit.prompt_template.prompt_template_model import PromptTemplate
from apps.deepaudit.scenario_profile import SCENARIO_PROMPT_TEMPLATE_SEEDS
from apps.deepaudit.serialization import format_datetime_text
from apps.deepaudit.user_config import user_config_services


DEFAULT_PROMPT_TEMPLATES = [
    {
        'name': '默认代码审计',
        'description': '全量安全与质量扫描提示词模板',
        'template_type': 'system',
        'content_zh': '你是 Focus DeepAudit 的安全审计助手，请关注高危漏洞、代码质量、可维护性和修复建议。',
        'content_en': 'You are the Focus DeepAudit auditing assistant. Focus on security issues, quality risks, maintainability and remediation.',
        'variables': {'language': '编程语言', 'code': '代码内容'},
        'is_default': True,
        'is_system': True,
        'is_active': True,
    },
    {
        'name': '安全专项审计',
        'description': '偏重漏洞类型分析与利用链说明',
        'template_type': 'analysis',
        'content_zh': '请重点识别 SQL 注入、XSS、命令注入、路径遍历、SSRF、硬编码密钥等问题，并给出风险评级。',
        'content_en': 'Focus on SQLi, XSS, command injection, path traversal, SSRF and hardcoded secrets, and assign risk ratings.',
        'variables': {'language': '编程语言', 'code': '代码内容'},
        'is_default': False,
        'is_system': True,
        'is_active': True,
    },
    {
        'name': C_FAMILY_SYSTEM_PROMPT_TEMPLATE_NAME,
        'description': '面向汽车级 MCU 嵌入式 C/C++ 项目的语义级深度审计模板',
        'template_type': 'system',
        'content_zh': get_c_family_prompt_text(),
        'content_en': (
            'Audit the current C/C++ code unit as an embedded automotive MCU security reviewer. '
            'Focus on buffer overflows, out-of-bounds access, integer overflow or truncation, null dereference, '
            'use-after-free, double free, uninitialized memory, resource leaks, deadlocks, race conditions, '
            'ISR or task-context shared state, unsafe standard-library APIs, unchecked return values, and API contract violations.'
        ),
        'variables': {'language': '编程语言', 'code': '代码内容'},
        'is_default': False,
        'is_system': True,
        'is_active': True,
    },
    *[copy.deepcopy(item) for item in SCENARIO_PROMPT_TEMPLATE_SEEDS],
]


def serialize_template(instance: PromptTemplate) -> dict:
    return {
        'id': str(instance.id),
        'name': instance.name,
        'description': instance.description,
        'template_type': instance.template_type,
        'content_zh': instance.content_zh,
        'content_en': instance.content_en,
        'variables': instance.variables or {},
        'is_default': instance.is_default,
        'is_system': instance.is_system,
        'is_active': instance.is_active,
        'created_by': str(instance.created_by_id) if instance.created_by_id else None,
        'sys_create_datetime': format_datetime_text(instance.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(instance.sys_update_datetime),
    }


def list_templates(user, *, keyword: str = '', template_type: str = '', is_active: bool | None = None, page: int = 1, page_size: int = 20) -> dict:
    user_id = get_user_id(user)
    queryset = PromptTemplate.objects.filter(is_deleted=False)
    queryset = queryset.filter(is_system=True) | queryset.filter(created_by_id=user_id)
    queryset = queryset.distinct().order_by('-is_default', '-is_system', 'name')
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)
    if template_type:
        queryset = queryset.filter(template_type=template_type)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    items = [serialize_template(item) for item in queryset[start:start + page_size]]
    return {'items': items, 'total': total}


def get_template(user, template_id: str) -> PromptTemplate:
    template = get_object_or_404(PromptTemplate, id=template_id, is_deleted=False)
    if not template.is_system and str(template.created_by_id or '') != str(getattr(user, 'id', '')):
        raise HttpError(403, '无权访问该提示词模板')
    return template


def create_template(user, payload: dict) -> PromptTemplate:
    return PromptTemplate.objects.create(
        name=str(payload.get('name') or '').strip(),
        description=str(payload.get('description') or '').strip() or None,
        template_type=str(payload.get('template_type') or 'system').strip() or 'system',
        content_zh=payload.get('content_zh') or None,
        content_en=payload.get('content_en') or None,
        variables=payload.get('variables') or {},
        is_active=bool(payload.get('is_active', True)),
        created_by=user,
        sys_creator=user,
        sys_modifier=user,
    )


def update_template(user, template_id: str, payload: dict) -> PromptTemplate:
    template = get_template(user, template_id)
    if template.is_system and not getattr(user, 'is_superuser', False):
        raise HttpError(403, '系统模板仅允许超级管理员修改')
    for field in ('name', 'description', 'template_type', 'content_zh', 'content_en', 'is_active'):
        if field in payload:
            setattr(template, field, payload[field])
    if payload.get('variables') is not None:
        template.variables = payload.get('variables') or {}
    template.sys_modifier = user
    template.save()
    return template


def delete_template(user, template_id: str) -> bool:
    template = get_template(user, template_id)
    if template.is_system:
        raise HttpError(403, '系统模板不允许删除')
    template.is_deleted = True
    template.sys_modifier = user
    template.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return True


def set_default_template(user, template_id: str) -> bool:
    template = get_template(user, template_id)
    PromptTemplate.objects.filter(created_by_id=get_user_id(user), is_deleted=False).update(is_default=False)
    template.is_default = True
    template.sys_modifier = user
    template.save(update_fields=['is_default', 'sys_modifier', 'sys_update_datetime'])
    return True


def test_template(user, payload: dict) -> dict:
    started = time.perf_counter()
    content = str(payload.get('content') or '').strip()
    code = str(payload.get('code') or '')
    language = str(payload.get('language') or 'text').strip() or 'text'
    output_language = str(payload.get('output_language') or 'zh').strip() or 'zh'
    if not content:
        return {
            'success': False,
            'result': {},
            'error': '提示词内容不能为空',
            'execution_time': round(time.perf_counter() - started, 3),
        }

    config = user_config_services.get_user_config(user)
    service = LLMService(user_config=config)
    try:
        result = async_to_sync(service.analyze_code_with_custom_prompt)(
            code,
            language,
            content,
            output_language=output_language,
        )
        return {
            'success': True,
            'result': result,
            'execution_time': round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            'success': False,
            'result': {},
            'error': str(exc) or '提示词测试失败',
            'execution_time': round(time.perf_counter() - started, 3),
        }


def ensure_default_templates() -> int:
    created = 0
    for item in DEFAULT_PROMPT_TEMPLATES:
        if PromptTemplate.objects.filter(name=item['name'], is_system=True, is_deleted=False).exists():
            continue
        PromptTemplate.objects.create(**item)
        created += 1
    return created
