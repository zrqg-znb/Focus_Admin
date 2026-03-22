from __future__ import annotations

import json

from django.http import HttpResponse
from ninja import Router

from . import audit_rule_services
from ..serialization import normalize_json_payload
from .audit_rule_schemas import (
    AuditRuleImportSchema,
    AuditRuleSaveSchema,
    AuditRuleSchema,
    AuditRuleSetListSchema,
    AuditRuleSetSaveSchema,
    AuditRuleSetSchema,
    AuditRuleSetUpdateSchema,
    AuditRuleUpdateSchema,
)

router = Router(tags=['DeepAudit-Rules'])


@router.get('', response=AuditRuleSetListSchema, summary='获取规则集列表')
def list_rule_sets(request, keyword: str = '', language: str = '', rule_type: str = '', is_active: bool | None = None, page: int = 1, pageSize: int = 20):
    return audit_rule_services.list_rule_sets(
        request.auth,
        keyword=keyword,
        language=language,
        rule_type=rule_type,
        is_active=is_active,
        page=page,
        page_size=pageSize,
    )


@router.get('/{rule_set_id}', response=AuditRuleSetSchema, summary='获取规则集详情')
def get_rule_set(request, rule_set_id: str):
    return audit_rule_services.serialize_rule_set(audit_rule_services.get_rule_set(request.auth, rule_set_id))


@router.post('', response=AuditRuleSetSchema, summary='创建规则集')
def create_rule_set(request, data: AuditRuleSetSaveSchema):
    return audit_rule_services.serialize_rule_set(audit_rule_services.create_rule_set(request.auth, data.dict()))


@router.put('/{rule_set_id}', response=AuditRuleSetSchema, summary='更新规则集')
def update_rule_set(request, rule_set_id: str, data: AuditRuleSetUpdateSchema):
    return audit_rule_services.serialize_rule_set(audit_rule_services.update_rule_set(request.auth, rule_set_id, data.dict(exclude_unset=True)))


@router.delete('/{rule_set_id}', response=bool, summary='删除规则集')
def delete_rule_set(request, rule_set_id: str):
    return audit_rule_services.delete_rule_set(request.auth, rule_set_id)


@router.post('/{rule_set_id}/set-default', response=bool, summary='设置默认规则集')
def set_default_rule_set(request, rule_set_id: str):
    return audit_rule_services.set_default_rule_set(request.auth, rule_set_id)


@router.get('/{rule_set_id}/export', summary='导出规则集')
def export_rule_set(request, rule_set_id: str):
    payload = normalize_json_payload(audit_rule_services.export_rule_set(request.auth, rule_set_id))
    response = HttpResponse(json.dumps(payload, ensure_ascii=False, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="rule-set-{rule_set_id}.json"'
    return response


@router.post('/import', response=AuditRuleSetSchema, summary='导入规则集')
def import_rule_set(request, data: AuditRuleImportSchema):
    return audit_rule_services.serialize_rule_set(audit_rule_services.import_rule_set(request.auth, data.dict()))


@router.post('/{rule_set_id}/rules', response=AuditRuleSchema, summary='新增规则')
def add_rule(request, rule_set_id: str, data: AuditRuleSaveSchema):
    return audit_rule_services.serialize_rule(audit_rule_services.add_rule(request.auth, rule_set_id, data.dict()))


@router.put('/{rule_set_id}/rules/{rule_id}', response=AuditRuleSchema, summary='更新规则')
def update_rule(request, rule_set_id: str, rule_id: str, data: AuditRuleUpdateSchema):
    return audit_rule_services.serialize_rule(audit_rule_services.update_rule(request.auth, rule_set_id, rule_id, data.dict(exclude_unset=True)))


@router.delete('/{rule_set_id}/rules/{rule_id}', response=bool, summary='删除规则')
def delete_rule(request, rule_set_id: str, rule_id: str):
    return audit_rule_services.delete_rule(request.auth, rule_set_id, rule_id)


@router.put('/{rule_set_id}/rules/{rule_id}/toggle', response=dict, summary='切换规则状态')
def toggle_rule(request, rule_set_id: str, rule_id: str):
    return audit_rule_services.toggle_rule(request.auth, rule_set_id, rule_id)
