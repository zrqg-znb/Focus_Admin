from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class RagScopeSchema(Schema):
    branch_name: str | None = None
    repository_type: str | None = None
    manifest_xml: str | None = None
    group: str | None = None
    exclude_patterns: list[str] = Field(default_factory=list)
    target_files: list[str] = Field(default_factory=list)


class RagStatusSchema(Schema):
    collection_name: str
    exists: bool = False
    chunk_count: int = 0
    file_count: int = 0
    index_version: str | None = None
    created_at: float | int | None = None
    updated_at: float | int | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_dimension: int | None = None
    project_hash: str | None = None
    needs_rebuild: bool = False
    rebuild_reason: str | None = None
    unavailable_reason: str | None = None


class RagRebuildSchema(RagScopeSchema):
    pass


class RagRebuildResultSchema(Schema):
    collection_name: str
    update_mode: str = ''
    processed_files: int = 0
    total_files: int = 0
    indexed_chunks: int = 0
    added_files: int = 0
    updated_files: int = 0
    deleted_files: int = 0
    embedding_provider: str | None = None
    embedding_model: str | None = None


class RagQuerySchema(RagScopeSchema):
    query: str
    top_k: int = 10
    filter_file_path: str | None = None
    filter_language: str | None = None


class RagQueryResultItemSchema(Schema):
    chunk_id: str
    content: str
    file_path: str
    language: str
    chunk_type: str
    line_start: int = 0
    line_end: int = 0
    score: float = 0.0
    name: str | None = None
    parent_name: str | None = None
    signature: str | None = None
    security_indicators: list[str] = Field(default_factory=list)


class RagQueryResultSchema(Schema):
    collection_name: str
    count: int = 0
    results: list[RagQueryResultItemSchema] = Field(default_factory=list)
    unavailable_reason: str | None = None


class KnowledgeStatusSchema(Schema):
    enabled: bool = False
    chunk_count: int = 0
    document_count: int = 0
    stats: dict[str, Any] = Field(default_factory=dict)


class KnowledgeDocumentSchema(Schema):
    id: str
    title: str
    content: str
    category: str
    tags: list[str] = Field(default_factory=list)
    severity: str | None = None
    cwe_ids: list[str] = Field(default_factory=list)
    owasp_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeListSchema(Schema):
    total: int = 0
    items: list[KnowledgeDocumentSchema] = Field(default_factory=list)


class KnowledgeSearchSchema(Schema):
    query: str
    category: str | None = None
    top_k: int = 5


class KnowledgeSearchItemSchema(Schema):
    id: str
    title: str | None = None
    content: str
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    severity: str | None = None
    cwe_ids: list[str] = Field(default_factory=list)
    owasp_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None
    file_path: str | None = None


class KnowledgeSearchResultSchema(Schema):
    total: int = 0
    items: list[KnowledgeSearchItemSchema] = Field(default_factory=list)


class KnowledgeSaveSchema(Schema):
    id: str | None = None
    title: str
    content: str
    category: str = 'best_practice'
    tags: list[str] = Field(default_factory=list)
    severity: str | None = None
    cwe_ids: list[str] = Field(default_factory=list)
    owasp_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSaveResultSchema(Schema):
    document: KnowledgeDocumentSchema
    rebuilt: bool = False


class KnowledgeDeleteResultSchema(Schema):
    success: bool = False
    rebuilt: bool = False


class KnowledgeValidateSchema(Schema):
    modules: list[str] = Field(default_factory=list)


class KnowledgeValidateResultSchema(Schema):
    valid: list[str] = Field(default_factory=list)
    invalid: list[str] = Field(default_factory=list)
