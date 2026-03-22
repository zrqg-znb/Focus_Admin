from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class AuditRuleSaveSchema(Schema):
    rule_code: str
    name: str
    description: str | None = None
    category: str = 'security'
    severity: str = 'medium'
    custom_prompt: str | None = None
    fix_suggestion: str | None = None
    reference_url: str | None = None
    enabled: bool = True


class AuditRuleUpdateSchema(Schema):
    rule_code: str | None = None
    name: str | None = None
    description: str | None = None
    category: str | None = None
    severity: str | None = None
    custom_prompt: str | None = None
    fix_suggestion: str | None = None
    reference_url: str | None = None
    enabled: bool | None = None


class AuditRuleSetSaveSchema(Schema):
    name: str
    description: str | None = None
    language: str = 'all'
    rule_type: str = 'custom'
    severity_weights: dict[str, int] = Field(default_factory=dict)
    is_active: bool = True
    rules: list[AuditRuleSaveSchema] = Field(default_factory=list)


class AuditRuleSetUpdateSchema(Schema):
    name: str | None = None
    description: str | None = None
    language: str | None = None
    rule_type: str | None = None
    severity_weights: dict[str, int] | None = None
    is_active: bool | None = None


class AuditRuleSchema(Schema):
    id: str
    rule_set_id: str
    rule_code: str
    name: str
    description: str | None = None
    category: str
    severity: str
    custom_prompt: str | None = None
    fix_suggestion: str | None = None
    reference_url: str | None = None
    enabled: bool = True
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class AuditRuleSetSchema(Schema):
    id: str
    name: str
    description: str | None = None
    language: str
    rule_type: str
    severity_weights: dict[str, int] = Field(default_factory=dict)
    is_default: bool = False
    is_system: bool = False
    is_active: bool = True
    created_by: str | None = None
    rules_count: int = 0
    enabled_rules_count: int = 0
    rules: list[AuditRuleSchema] = Field(default_factory=list)
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class AuditRuleSetListSchema(Schema):
    items: list[AuditRuleSetSchema]
    total: int


class AuditRuleImportSchema(Schema):
    name: str
    description: str | None = None
    language: str = 'all'
    rule_type: str = 'custom'
    severity_weights: dict[str, int] = Field(default_factory=dict)
    rules: list[AuditRuleSaveSchema] = Field(default_factory=list)
