from __future__ import annotations

from ninja import Router

from . import user_config_services
from .user_config_schemas import (
    AuditSshGenerateResultSchema,
    AuditSshGenerateSchema,
    AuditSshCredentialSaveSchema,
    AuditSshCredentialSchema,
    AuditSshTestResultSchema,
    AuditSshTestSchema,
    AuditUserConfigSchema,
    AuditUserConfigDefaultsSchema,
    AuditUserConfigUpdateSchema,
    EmbeddingModelListSchema,
    LLMTestResultSchema,
    LLMTestSchema,
    LLMProviderSchema,
    EmbeddingConfigSchema,
    EmbeddingConfigUpdateSchema,
    EmbeddingProviderSchema,
    EmbeddingTestResultSchema,
    EmbeddingTestSchema,
)

settings_router = Router(tags=['DeepAudit-Settings'])
embedding_router = Router(tags=['DeepAudit-Embedding'])
ssh_router = Router(tags=['DeepAudit-SSH'])


@settings_router.get('/me', response=AuditUserConfigSchema, summary='获取我的审计设置')
def get_my_config(request):
    return user_config_services.get_user_config(request.auth)


@settings_router.get('/defaults', response=AuditUserConfigDefaultsSchema, summary='获取系统默认审计设置')
def get_default_config(request):
    return user_config_services.get_default_user_config()


@settings_router.put('/me', response=AuditUserConfigSchema, summary='保存我的审计设置')
def update_my_config(request, data: AuditUserConfigUpdateSchema):
    return user_config_services.update_user_config(request.auth, data.dict())


@settings_router.delete('/me', response=bool, summary='重置我的审计设置')
def delete_my_config(request):
    return user_config_services.delete_user_config(request.auth)


@settings_router.post('/test-llm', response=LLMTestResultSchema, summary='测试 LLM 连接')
def test_llm_connection(request, data: LLMTestSchema):
    return user_config_services.test_llm_connection(request.auth, data.dict())


@settings_router.get('/llm-providers', response=list[LLMProviderSchema], summary='获取 LLM Provider 列表')
def list_llm_providers(request):
    return user_config_services.list_llm_providers()


@embedding_router.get('/providers', response=list[EmbeddingProviderSchema], summary='获取 Embedding Provider 列表')
def list_providers(request):
    return user_config_services.list_embedding_providers()


@embedding_router.get('/models/{provider}', response=EmbeddingModelListSchema, summary='获取 Embedding Provider 模型列表')
def list_provider_models(request, provider: str):
    return user_config_services.get_embedding_provider_models(provider)


@embedding_router.get('/config', response=EmbeddingConfigSchema, summary='获取 Embedding 配置')
def get_embedding_config(request):
    return user_config_services.get_embedding_config(request.auth)


@embedding_router.put('/config', response=EmbeddingConfigSchema, summary='更新 Embedding 配置')
def update_embedding_config(request, data: EmbeddingConfigUpdateSchema):
    return user_config_services.update_embedding_config(request.auth, data.dict())


@embedding_router.post('/test', response=EmbeddingTestResultSchema, summary='测试 Embedding 配置')
def test_embedding(request, data: EmbeddingTestSchema):
    return user_config_services.test_embedding(request.auth, data.dict())


@ssh_router.get('', response=AuditSshCredentialSchema, summary='获取 SSH 凭据')
def get_ssh_credential(request):
    return user_config_services.get_ssh_credential(request.auth)


@ssh_router.post('', response=AuditSshCredentialSchema, summary='保存 SSH 凭据')
def save_ssh_credential(request, data: AuditSshCredentialSaveSchema):
    return user_config_services.save_ssh_credential(request.auth, data.dict())


@ssh_router.post('/generate', response=AuditSshGenerateResultSchema, summary='生成 SSH 密钥')
def generate_ssh_credential(request, data: AuditSshGenerateSchema):
    return user_config_services.generate_ssh_credential(request.auth, data.dict())


@ssh_router.post('/test', response=AuditSshTestResultSchema, summary='测试 SSH 连接')
def test_ssh_credential(request, data: AuditSshTestSchema):
    return user_config_services.test_ssh_credential(request.auth, data.dict())


@ssh_router.delete('/known-hosts', response=bool, summary='清空 known_hosts')
def clear_known_hosts(request):
    return user_config_services.clear_ssh_known_hosts(request.auth)


@ssh_router.delete('', response=bool, summary='删除 SSH 凭据')
def delete_ssh_credential(request):
    return user_config_services.delete_ssh_credential(request.auth)
