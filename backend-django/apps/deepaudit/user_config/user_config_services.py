from __future__ import annotations

import hashlib
from copy import deepcopy

from apps.deepaudit.constants import DEFAULT_LLM_CONFIG, DEFAULT_OTHER_CONFIG, EMBEDDING_PROVIDERS
from apps.deepaudit.encryption import decrypt_value, encrypt_value
from apps.deepaudit.permissions import get_user_id
from apps.deepaudit.serialization import format_datetime_text
from apps.deepaudit.user_config.user_config_model import AuditSshCredential, AuditUserConfig


SENSITIVE_LLM_FIELDS = {'api_key'}
SENSITIVE_TOKEN_FIELDS = {'github_token', 'gitlab_token', 'gitea_token'}
SENSITIVE_EMBEDDING_FIELDS = {'api_key'}


def _deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _decrypt_llm_config(payload: dict) -> dict:
    result = dict(payload or {})
    for key in SENSITIVE_LLM_FIELDS:
        if result.get(key):
            result[key] = decrypt_value(result[key])
    return result


def _encrypt_llm_config(payload: dict) -> dict:
    result = dict(payload or {})
    for key in SENSITIVE_LLM_FIELDS:
        if result.get(key):
            result[key] = encrypt_value(str(result[key]))
    return result


def _decrypt_other_config(payload: dict) -> dict:
    result = dict(payload or {})
    for key in SENSITIVE_TOKEN_FIELDS:
        if result.get(key):
            result[key] = decrypt_value(result[key])
    embedding = dict(result.get('embedding_config') or {})
    for key in SENSITIVE_EMBEDDING_FIELDS:
        if embedding.get(key):
            embedding[key] = decrypt_value(embedding[key])
    result['embedding_config'] = embedding
    return result


def _encrypt_other_config(payload: dict) -> dict:
    result = dict(payload or {})
    for key in SENSITIVE_TOKEN_FIELDS:
        if result.get(key):
            result[key] = encrypt_value(str(result[key]))
    embedding = dict(result.get('embedding_config') or {})
    for key in SENSITIVE_EMBEDDING_FIELDS:
        if embedding.get(key):
            embedding[key] = encrypt_value(str(embedding[key]))
    result['embedding_config'] = embedding
    return result


def get_or_create_config(user) -> AuditUserConfig:
    config, _ = AuditUserConfig.objects.get_or_create(
        user=user,
        defaults={
            'llm_config': _encrypt_llm_config(DEFAULT_LLM_CONFIG),
            'other_config': _encrypt_other_config(DEFAULT_OTHER_CONFIG),
            'sys_creator': user,
            'sys_modifier': user,
        },
    )
    return config


def serialize_user_config(instance: AuditUserConfig) -> dict:
    llm_config = _deep_merge(DEFAULT_LLM_CONFIG, _decrypt_llm_config(instance.llm_config or {}))
    other_config = _deep_merge(DEFAULT_OTHER_CONFIG, _decrypt_other_config(instance.other_config or {}))
    return {
        'user_id': str(instance.user_id),
        'llm_config': llm_config,
        'other_config': other_config,
        'sys_create_datetime': format_datetime_text(instance.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(instance.sys_update_datetime),
    }


def get_user_config(user) -> dict:
    return serialize_user_config(get_or_create_config(user))


def update_user_config(user, payload: dict) -> dict:
    instance = get_or_create_config(user)
    current = serialize_user_config(instance)
    merged_llm = _deep_merge(current['llm_config'], payload.get('llm_config') or {})
    merged_other = _deep_merge(current['other_config'], payload.get('other_config') or {})
    instance.llm_config = _encrypt_llm_config(merged_llm)
    instance.other_config = _encrypt_other_config(merged_other)
    instance.sys_modifier = user
    instance.save()
    return serialize_user_config(instance)


def list_embedding_providers() -> list[dict]:
    return EMBEDDING_PROVIDERS


def get_embedding_config(user) -> dict:
    config = get_user_config(user)
    return config['other_config'].get('embedding_config') or {}


def update_embedding_config(user, payload: dict) -> dict:
    return update_user_config(user, {'other_config': {'embedding_config': payload}})['other_config']['embedding_config']


def test_embedding(payload: dict) -> dict:
    provider = str(payload.get('provider') or '').strip() or 'openai'
    model = str(payload.get('model') or '').strip()
    requires_key = any(item['id'] == provider and item['requires_api_key'] for item in EMBEDDING_PROVIDERS)
    if requires_key and not str(payload.get('api_key') or '').strip():
        return {'success': False, 'message': '当前 embedding provider 需要 API Key', 'preview_vector_length': 0}
    checksum = hashlib.sha256(f"{provider}:{model}:{payload.get('test_text') or ''}".encode('utf-8')).hexdigest()
    preview_length = min(16, len(checksum))
    return {
        'success': True,
        'message': f'Embedding 配置校验通过（provider={provider}, model={model or "default"}）',
        'preview_vector_length': preview_length,
    }


def _fingerprint(public_key: str) -> str:
    if not public_key:
        return ''
    digest = hashlib.sha256(public_key.encode('utf-8')).hexdigest()
    return ':'.join(digest[index:index + 2] for index in range(0, 32, 2))


def get_ssh_credential(user) -> dict:
    credential = AuditSshCredential.objects.filter(user_id=get_user_id(user), is_deleted=False).first()
    if not credential:
        return {
            'has_private_key': False,
            'public_key': None,
            'fingerprint': None,
            'known_hosts': None,
            'updated_at': None,
        }
    return {
        'has_private_key': bool(credential.private_key_encrypted),
        'public_key': credential.public_key,
        'fingerprint': credential.fingerprint,
        'known_hosts': credential.known_hosts,
        'updated_at': format_datetime_text(credential.sys_update_datetime),
    }


def save_ssh_credential(user, payload: dict) -> dict:
    credential, _ = AuditSshCredential.objects.get_or_create(
        user=user,
        defaults={'sys_creator': user, 'sys_modifier': user},
    )
    private_key = str(payload.get('private_key') or '').strip()
    if private_key:
        credential.private_key_encrypted = encrypt_value(private_key)
    public_key = payload.get('public_key')
    if public_key is not None:
        credential.public_key = str(public_key or '').strip() or None
    if payload.get('known_hosts') is not None:
        credential.known_hosts = str(payload.get('known_hosts') or '').strip() or None
    credential.fingerprint = _fingerprint(credential.public_key or '') or credential.fingerprint
    credential.is_deleted = False
    credential.sys_modifier = user
    credential.save()
    return get_ssh_credential(user)


def delete_ssh_credential(user) -> bool:
    credential = AuditSshCredential.objects.filter(user_id=get_user_id(user), is_deleted=False).first()
    if not credential:
        return True
    credential.private_key_encrypted = ''
    credential.public_key = ''
    credential.fingerprint = ''
    credential.known_hosts = ''
    credential.is_deleted = True
    credential.sys_modifier = user
    credential.save()
    return True
