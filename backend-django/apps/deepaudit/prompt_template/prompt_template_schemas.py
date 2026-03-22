from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class PromptTemplateSaveSchema(Schema):
    name: str
    description: str | None = None
    template_type: str = 'system'
    content_zh: str | None = None
    content_en: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class PromptTemplateUpdateSchema(Schema):
    name: str | None = None
    description: str | None = None
    template_type: str | None = None
    content_zh: str | None = None
    content_en: str | None = None
    variables: dict[str, Any] | None = None
    is_active: bool | None = None


class PromptTemplateSchema(Schema):
    id: str
    name: str
    description: str | None = None
    template_type: str
    content_zh: str | None = None
    content_en: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    is_system: bool = False
    is_active: bool = True
    created_by: str | None = None
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class PromptTemplateListSchema(Schema):
    items: list[PromptTemplateSchema]
    total: int


class PromptTemplateTestSchema(Schema):
    content: str
    language: str = 'python'
    code: str
    output_language: str = 'zh'


class PromptTemplateTestResultSchema(Schema):
    success: bool = True
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    execution_time: float = 0.0
