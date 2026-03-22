from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class AuditUserConfigSchema(Schema):
    user_id: str
    llm_config: dict[str, Any] = Field(default_factory=dict)
    other_config: dict[str, Any] = Field(default_factory=dict)
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class AuditUserConfigUpdateSchema(Schema):
    llm_config: dict[str, Any] = Field(default_factory=dict)
    other_config: dict[str, Any] = Field(default_factory=dict)


class EmbeddingProviderSchema(Schema):
    id: str
    name: str
    description: str
    models: list[str] = Field(default_factory=list)
    requires_api_key: bool = False
    default_model: str | None = None


class EmbeddingConfigSchema(Schema):
    provider: str = 'openai'
    model: str = ''
    api_key: str = ''
    base_url: str = ''
    dimensions: int | None = None
    batch_size: int | None = None


class EmbeddingTestSchema(Schema):
    provider: str = 'openai'
    model: str = ''
    api_key: str = ''
    base_url: str = ''
    test_text: str = 'Focus DeepAudit embedding health check'


class EmbeddingTestResultSchema(Schema):
    success: bool = True
    message: str = ''
    preview_vector_length: int = 0


class AuditSshCredentialSchema(Schema):
    has_private_key: bool = False
    public_key: str | None = None
    fingerprint: str | None = None
    known_hosts: str | None = None
    updated_at: str | None = None


class AuditSshCredentialSaveSchema(Schema):
    private_key: str | None = None
    public_key: str | None = None
    known_hosts: str | None = None
