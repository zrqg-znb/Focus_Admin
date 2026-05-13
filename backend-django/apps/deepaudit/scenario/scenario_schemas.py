from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class ScenarioProfileSaveSchema(Schema):
    scenario_key: str
    name: str
    description: str | None = None
    objective_type: str = 'audit'
    prompt_template_id: str | None = None
    rule_set_id: str | None = None
    knowledge_modules: list[str] = Field(default_factory=list)
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ScenarioProfileUpdateSchema(Schema):
    name: str | None = None
    description: str | None = None
    objective_type: str | None = None
    prompt_template_id: str | None = None
    rule_set_id: str | None = None
    knowledge_modules: list[str] | None = None
    tool_policy: dict[str, Any] | None = None
    is_active: bool | None = None
    is_default: bool | None = None


class ScenarioProfileCopySchema(Schema):
    scenario_key: str | None = None
    name: str | None = None
    description: str | None = None


class ScenarioProfileSchema(Schema):
    id: str
    scenario_key: str
    name: str
    description: str | None = None
    objective_type: str = 'audit'
    prompt_template_id: str | None = None
    prompt_template_name: str | None = None
    rule_set_id: str | None = None
    rule_set_name: str | None = None
    knowledge_modules: list[str] = Field(default_factory=list)
    knowledge_modules_count: int = 0
    target_vulnerabilities: list[str] = Field(default_factory=list)
    focus_keywords: list[str] = Field(default_factory=list)
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    is_system: bool = False
    is_active: bool = True
    created_by: str | None = None
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class ScenarioProfileListSchema(Schema):
    items: list[ScenarioProfileSchema]
    total: int
