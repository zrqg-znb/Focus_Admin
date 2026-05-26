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


class AuditUserConfigDefaultsSchema(Schema):
    llm_config: dict[str, Any] = Field(default_factory=dict)
    other_config: dict[str, Any] = Field(default_factory=dict)


class LLMTestSchema(Schema):
    provider: str = 'openai'
    api_key: str = ''
    model: str = ''
    base_url: str = ''


class LLMTestResultSchema(Schema):
    success: bool = True
    message: str = ''
    model: str | None = None
    response: str | None = None
    debug: dict[str, Any] | None = None


class LLMProviderSchema(Schema):
    id: str
    name: str
    default_model: str | None = None
    models: list[str] = Field(default_factory=list)
    default_base_url: str | None = None


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
    config_locked: bool = False
    api_key_configured: bool = False


class EmbeddingConfigUpdateSchema(Schema):
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
    dimensions: int | None = None
    dimension: int | None = None
    test_text: str = 'Focus DeepAudit embedding health check'


class EmbeddingTestResultSchema(Schema):
    success: bool = True
    message: str = ''
    preview_vector_length: int = 0
    dimensions: int | None = None
    sample_embedding: list[float] = Field(default_factory=list)
    latency_ms: int | None = None


class EmbeddingModelListSchema(Schema):
    provider: str
    models: list[str] = Field(default_factory=list)
    default_model: str | None = None
    requires_api_key: bool = False


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


class AuditSshGenerateSchema(Schema):
    key_type: str = 'rsa'
    key_size: int = 4096


class AuditSshGenerateResultSchema(Schema):
    public_key: str
    fingerprint: str | None = None
    message: str = ''


class AuditSshTestSchema(Schema):
    repo_url: str


class AuditSshTestResultSchema(Schema):
    success: bool = True
    message: str = ''
    output: str | None = None
