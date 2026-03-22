from __future__ import annotations

from ninja import Router

from . import user_config_services
from .user_config_schemas import (
    AuditSshCredentialSaveSchema,
    AuditSshCredentialSchema,
    AuditUserConfigSchema,
    AuditUserConfigUpdateSchema,
    EmbeddingConfigSchema,
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


@settings_router.put('/me', response=AuditUserConfigSchema, summary='保存我的审计设置')
def update_my_config(request, data: AuditUserConfigUpdateSchema):
    return user_config_services.update_user_config(request.auth, data.dict())


@embedding_router.get('/providers', response=list[EmbeddingProviderSchema], summary='获取 Embedding Provider 列表')
def list_providers(request):
    return user_config_services.list_embedding_providers()


@embedding_router.get('/config', response=EmbeddingConfigSchema, summary='获取 Embedding 配置')
def get_embedding_config(request):
    return user_config_services.get_embedding_config(request.auth)


@embedding_router.put('/config', response=EmbeddingConfigSchema, summary='更新 Embedding 配置')
def update_embedding_config(request, data: EmbeddingConfigSchema):
    return user_config_services.update_embedding_config(request.auth, data.dict())


@embedding_router.post('/test', response=EmbeddingTestResultSchema, summary='测试 Embedding 配置')
def test_embedding(request, data: EmbeddingTestSchema):
    return user_config_services.test_embedding(data.dict())


@ssh_router.get('', response=AuditSshCredentialSchema, summary='获取 SSH 凭据')
def get_ssh_credential(request):
    return user_config_services.get_ssh_credential(request.auth)


@ssh_router.post('', response=AuditSshCredentialSchema, summary='保存 SSH 凭据')
def save_ssh_credential(request, data: AuditSshCredentialSaveSchema):
    return user_config_services.save_ssh_credential(request.auth, data.dict())


@ssh_router.delete('', response=bool, summary='删除 SSH 凭据')
def delete_ssh_credential(request):
    return user_config_services.delete_ssh_credential(request.auth)
