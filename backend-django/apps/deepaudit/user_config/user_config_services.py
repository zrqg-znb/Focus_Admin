from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
from base64 import b64decode, b64encode
from copy import deepcopy
from urllib.parse import urlencode

import requests
from asgiref.sync import async_to_sync
from django.conf import settings
from ninja.errors import HttpError

from apps.deepaudit.llm.factory import LLMFactory
from apps.deepaudit.llm.types import DEFAULT_BASE_URLS, LLMProvider
from apps.deepaudit.rag import EmbeddingService

from apps.deepaudit.constants import DEFAULT_LLM_CONFIG, DEFAULT_OTHER_CONFIG, EMBEDDING_PROVIDERS
from apps.deepaudit.config_resolver import (
    coerce_llm_provider,
    embedding_config_locked,
    normalize_embedding_base_url,
    normalize_embedding_provider,
    resolve_embedding_config,
)
from apps.deepaudit.encryption import decrypt_value, encrypt_value
from apps.deepaudit.permissions import get_user_id
from apps.deepaudit.serialization import format_datetime_text
from apps.deepaudit.user_config.user_config_model import AuditSshCredential, AuditUserConfig

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
except ImportError:  # pragma: no cover - runtime dependency expected in app env
    default_backend = None
    serialization = None
    ed25519 = None
    rsa = None


SENSITIVE_LLM_FIELDS = {'api_key'}
SENSITIVE_TOKEN_FIELDS = {'codehub_token', 'github_token', 'gitlab_token', 'gitea_token'}
SENSITIVE_EMBEDDING_FIELDS = {'api_key'}
LLM_TEST_MODELS = {
    'openai': 'gpt-5',
    'claude': 'claude-sonnet-4.5',
    'gemini': 'gemini-2.0-flash',
    'qwen': 'qwen3-max-instruct',
    'deepseek': 'deepseek-chat',
    'zhipu': 'glm-4.6',
    'moonshot': 'kimi-k2',
    'baidu': 'ERNIE-4.0',
    'minimax': 'abab6.5-chat',
    'doubao': 'doubao-pro-32k',
    'ollama': 'llama3.3',
}
LLM_TEST_BASE_URLS = {
    'openai': 'https://api.openai.com/v1',
    'claude': 'https://api.anthropic.com/v1',
    'gemini': 'https://generativelanguage.googleapis.com/v1beta',
    'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'deepseek': 'https://api.deepseek.com',
    'zhipu': 'https://open.bigmodel.cn/api/paas/v4',
    'moonshot': 'https://api.moonshot.cn/v1',
    'baidu': 'https://aip.baidubce.com',
    'minimax': 'https://api.minimax.chat/v1',
    'doubao': 'https://ark.cn-beijing.volces.com/api/v3',
    'ollama': 'http://127.0.0.1:11434/v1',
}
OPENAI_COMPATIBLE_PROVIDERS = {
    'openai',
    'qwen',
    'deepseek',
    'zhipu',
    'moonshot',
    'doubao',
    'ollama',
}
API_KEY_OPTIONAL_PROVIDERS = {'ollama'}
BAIDU_MODEL_ENDPOINTS = {
    'ERNIE-4.0': 'completions_pro',
    'ERNIE-3.5-8K': 'completions',
    'ERNIE-3.5-128K': 'ernie-3.5-128k',
    'ERNIE-Speed': 'ernie_speed',
    'ERNIE-Lite': 'ernie-lite-8k',
}
LLM_TEST_PROMPT = "Reply with the single word: hello"


def _deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _build_system_default_llm_config() -> dict:
    payload = deepcopy(DEFAULT_LLM_CONFIG)
    payload.update(
        {
            'provider': str(getattr(settings, 'LLM_PROVIDER', '') or payload['provider']).strip() or payload['provider'],
            'model': str(getattr(settings, 'LLM_MODEL', '') or payload['model']).strip(),
            'base_url': str(getattr(settings, 'LLM_BASE_URL', '') or payload['base_url']).strip(),
            'timeout': int(getattr(settings, 'LLM_TIMEOUT', payload['timeout']) or payload['timeout']),
            'temperature': float(getattr(settings, 'LLM_TEMPERATURE', payload['temperature']) or payload['temperature']),
            'max_tokens': int(getattr(settings, 'LLM_MAX_TOKENS', payload['max_tokens']) or payload['max_tokens']),
            'first_token_timeout': int(getattr(settings, 'LLM_FIRST_TOKEN_TIMEOUT', payload['first_token_timeout']) or payload['first_token_timeout']),
            'stream_timeout': int(getattr(settings, 'LLM_STREAM_TIMEOUT', payload['stream_timeout']) or payload['stream_timeout']),
            'tool_timeout': int(getattr(settings, 'TOOL_TIMEOUT_SECONDS', payload['tool_timeout']) or payload['tool_timeout']),
            'sub_agent_timeout': int(getattr(settings, 'SUB_AGENT_TIMEOUT_SECONDS', payload['sub_agent_timeout']) or payload['sub_agent_timeout']),
            'agent_timeout': int(getattr(settings, 'AGENT_TIMEOUT_SECONDS', payload['agent_timeout']) or payload['agent_timeout']),
        }
    )
    return payload


def _build_system_default_other_config() -> dict:
    payload = deepcopy(DEFAULT_OTHER_CONFIG)
    codehub_token = str(
        getattr(settings, 'CODEHUB_TOKEN', '')
        or getattr(settings, 'GITHUB_TOKEN', '')
        or getattr(settings, 'GITLAB_TOKEN', '')
        or getattr(settings, 'GITEA_TOKEN', '')
        or ''
    ).strip()
    payload.update(
        {
            'codehub_token': codehub_token,
            'output_language': str(getattr(settings, 'OUTPUT_LANGUAGE', payload['output_language']) or payload['output_language']).strip() or payload['output_language'],
        }
    )
    payload['scan_config'] = _deep_merge(
        payload.get('scan_config') or {},
        {
            'max_analyze_files': int(getattr(settings, 'MAX_ANALYZE_FILES', payload['scan_config']['max_analyze_files']) or 0),
            'llm_concurrency': int(getattr(settings, 'LLM_CONCURRENCY', payload['scan_config']['llm_concurrency']) or payload['scan_config']['llm_concurrency']),
            'llm_gap_ms': int(getattr(settings, 'LLM_GAP_MS', payload['scan_config']['llm_gap_ms']) or payload['scan_config']['llm_gap_ms']),
        },
    )
    payload['embedding_config'] = _deep_merge(
        payload.get('embedding_config') or {},
        {
            'provider': str(getattr(settings, 'EMBEDDING_PROVIDER', '') or payload['embedding_config']['provider']).strip() or payload['embedding_config']['provider'],
            'model': str(getattr(settings, 'EMBEDDING_MODEL', '') or payload['embedding_config']['model']).strip() or payload['embedding_config']['model'],
            'api_key': str(getattr(settings, 'EMBEDDING_API_KEY', '') or '').strip(),
            'base_url': str(getattr(settings, 'EMBEDDING_BASE_URL', '') or '').strip(),
            'dimensions': int(getattr(settings, 'EMBEDDING_DIMENSIONS', payload['embedding_config']['dimensions']) or payload['embedding_config']['dimensions']),
            'batch_size': int(getattr(settings, 'EMBEDDING_BATCH_SIZE', payload['embedding_config']['batch_size']) or payload['embedding_config']['batch_size']),
        },
    )
    return payload


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


def _normalize_codehub_token(payload: dict) -> dict:
    result = dict(payload or {})
    codehub_token = str(result.get('codehub_token') or '').strip()
    if not codehub_token:
        for legacy_key in ('github_token', 'gitlab_token', 'gitea_token'):
            legacy_value = str(result.get(legacy_key) or '').strip()
            if legacy_value:
                codehub_token = legacy_value
                break
    result['codehub_token'] = codehub_token
    for legacy_key in ('github_token', 'gitlab_token', 'gitea_token'):
        result.pop(legacy_key, None)
    return result


def _mask_api_key(api_key: str) -> str:
    if not api_key:
        return '(empty)'
    if len(api_key) <= 8:
        return api_key
    return f'{api_key[:8]}...'


def _contains_only_ascii(value: str) -> bool:
    try:
        value.encode('ascii')
    except UnicodeEncodeError:
        return False
    return True


def _invalid_api_key_message() -> str:
    return 'API Key 只能包含 ASCII 字符，请勿输入中文或其它非 ASCII 占位内容'


def _validate_embedding_api_key(api_key: str) -> None:
    if api_key and not _contains_only_ascii(api_key):
        raise HttpError(422, _invalid_api_key_message())


def _normalize_embedding_update_payload(payload: dict) -> dict:
    provider = normalize_embedding_provider(payload.get('provider'))
    api_key = str(payload.get('api_key') or '').strip()
    _validate_embedding_api_key(api_key)
    normalized = {
        'provider': provider,
        'model': str(payload.get('model') or '').strip(),
        'api_key': '' if provider == 'ollama' else api_key,
        'base_url': normalize_embedding_base_url(provider, payload.get('base_url')),
        'dimensions': payload.get('dimensions'),
        'batch_size': payload.get('batch_size'),
    }
    return normalized


def _default_model_for_provider(provider: str) -> str:
    return LLM_TEST_MODELS.get(provider, LLM_TEST_MODELS['openai'])


def _default_base_url_for_provider(provider: str) -> str:
    if provider == 'openai':
        for setting_name in ('LLM_BASE_URL', 'INTERNAL_LLM_BASE_URL', 'OPENAI_BASE_URL'):
            value = str(getattr(settings, setting_name, '') or '').strip()
            if value:
                return value
    return LLM_TEST_BASE_URLS.get(provider, '')


def _build_url(base_url: str, suffix: str) -> str:
    if not base_url:
        return suffix
    if base_url.endswith(suffix):
        return base_url
    return f"{base_url.rstrip('/')}{suffix}"


def _safe_json(response: requests.Response) -> dict:
    try:
        payload = response.json()
        return payload if isinstance(payload, dict) else {'data': payload}
    except Exception:
        return {}


def _stringify_payload(value) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _extract_openai_content(payload: dict) -> str:
    choices = payload.get('choices') or []
    if not choices:
        return ''
    message = (choices[0] or {}).get('message') or {}
    content = message.get('content')
    if isinstance(content, list):
        return ''.join(
            str(item.get('text') or '')
            for item in content
            if isinstance(item, dict)
        )
    return str(content or '')


def _extract_claude_content(payload: dict) -> str:
    items = payload.get('content') or []
    texts: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get('type') == 'text':
            texts.append(str(item.get('text') or ''))
    return ''.join(texts)


def _extract_gemini_content(payload: dict) -> str:
    candidates = payload.get('candidates') or []
    if not candidates:
        return ''
    content = (candidates[0] or {}).get('content') or {}
    parts = content.get('parts') or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get('text'):
            texts.append(str(part.get('text')))
    return ''.join(texts)


def _extract_error_message(payload: dict, fallback: str) -> str:
    if not payload:
        return fallback
    error = payload.get('error')
    if isinstance(error, dict):
        return str(error.get('message') or error.get('msg') or fallback)
    base_resp = payload.get('base_resp')
    if isinstance(base_resp, dict):
        return str(base_resp.get('status_msg') or fallback)
    for key in ('message', 'msg', 'error_msg'):
        if payload.get(key):
            return str(payload.get(key))
    return fallback


def _build_saved_debug(user) -> dict:
    config = get_user_config(user)
    llm_config = config.get('llm_config') or {}
    other_config = config.get('other_config') or {}
    scan_config = other_config.get('scan_config') or {}
    timeout_seconds = int(llm_config.get('timeout') or DEFAULT_LLM_CONFIG['timeout'])
    return {
        'timeout_ms': timeout_seconds * 1000,
        'temperature': llm_config.get('temperature', DEFAULT_LLM_CONFIG['temperature']),
        'max_tokens': llm_config.get('max_tokens', DEFAULT_LLM_CONFIG['max_tokens']),
        'concurrency': scan_config.get(
            'llm_concurrency',
            DEFAULT_OTHER_CONFIG['scan_config']['llm_concurrency'],
        ),
        'gap_ms': scan_config.get(
            'llm_gap_ms',
            DEFAULT_OTHER_CONFIG['scan_config']['llm_gap_ms'],
        ),
        'max_analyze_files': scan_config.get(
            'max_analyze_files',
            DEFAULT_OTHER_CONFIG['scan_config']['max_analyze_files'],
        ),
        'output_language': other_config.get(
            'output_language',
            DEFAULT_OTHER_CONFIG['output_language'],
        ),
    }


def _send_openai_compatible_request(
    provider: str,
    api_key: str,
    model: str,
    base_url: str,
    *,
    timeout: int,
    temperature: float,
    max_tokens: int,
) -> tuple[dict, dict]:
    url = _build_url(base_url, '/chat/completions')
    headers = {'Content-Type': 'application/json'}
    if provider not in API_KEY_OPTIONAL_PROVIDERS:
        headers['Authorization'] = f'Bearer {api_key}'
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': LLM_TEST_PROMPT}],
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    data = _safe_json(response)
    return data, {
        'request_url': url,
        'status_code': response.status_code,
        'api_response': _stringify_payload(data or response.text),
    }


def _send_claude_request(
    api_key: str,
    model: str,
    base_url: str,
    *,
    timeout: int,
    temperature: float,
    max_tokens: int,
) -> tuple[dict, dict]:
    url = _build_url(base_url, '/messages')
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
    }
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': LLM_TEST_PROMPT}],
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    data = _safe_json(response)
    return data, {
        'request_url': url,
        'status_code': response.status_code,
        'api_response': _stringify_payload(data or response.text),
    }


def _send_gemini_request(
    api_key: str,
    model: str,
    base_url: str,
    *,
    timeout: int,
    temperature: float,
    max_tokens: int,
) -> tuple[dict, dict]:
    url = _build_url(base_url, f'/models/{model}:generateContent')
    query = urlencode({'key': api_key})
    request_url = f'{url}?{query}'
    payload = {
        'contents': [{'parts': [{'text': LLM_TEST_PROMPT}]}],
        'generationConfig': {
            'temperature': temperature,
            'maxOutputTokens': max_tokens,
        },
    }
    response = requests.post(request_url, json=payload, timeout=timeout)
    data = _safe_json(response)
    return data, {
        'request_url': url,
        'status_code': response.status_code,
        'api_response': _stringify_payload(data or response.text),
    }


def _send_baidu_request(
    api_key: str,
    model: str,
    base_url: str,
    *,
    timeout: int,
    temperature: float,
    max_tokens: int,
) -> tuple[dict, dict]:
    if ':' not in api_key:
        raise ValueError('百度文心测试需要同时提供 API Key 和 Secret Key，格式为 api_key:secret_key')
    client_id, client_secret = api_key.split(':', 1)
    token_url = _build_url(base_url, '/oauth/2.0/token')
    token_response = requests.post(
        token_url,
        params={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
        },
        timeout=min(timeout, 30),
    )
    token_payload = _safe_json(token_response)
    access_token = token_payload.get('access_token')
    if token_response.status_code != 200 or not access_token:
        raise ValueError(_extract_error_message(token_payload, '获取百度 access_token 失败'))

    endpoint = BAIDU_MODEL_ENDPOINTS.get(model, 'completions')
    url = _build_url(base_url, f'/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{endpoint}')
    response = requests.post(
        f'{url}?{urlencode({"access_token": access_token})}',
        json={
            'messages': [{'role': 'user', 'content': LLM_TEST_PROMPT}],
            'temperature': temperature,
            'max_output_tokens': max_tokens,
        },
        timeout=timeout,
    )
    data = _safe_json(response)
    return data, {
        'request_url': url,
        'status_code': response.status_code,
        'api_response': _stringify_payload(data or response.text),
    }


def _send_minimax_request(
    api_key: str,
    model: str,
    base_url: str,
    *,
    timeout: int,
    temperature: float,
    max_tokens: int,
) -> tuple[dict, dict]:
    url = _build_url(base_url, '/text/chatcompletion_v2')
    response = requests.post(
        url,
        headers={'Authorization': f'Bearer {api_key}'},
        json={
            'model': model,
            'messages': [{'role': 'user', 'content': LLM_TEST_PROMPT}],
            'temperature': temperature,
            'max_tokens': max_tokens,
        },
        timeout=timeout,
    )
    data = _safe_json(response)
    return data, {
        'request_url': url,
        'status_code': response.status_code,
        'api_response': _stringify_payload(data or response.text),
    }


def get_or_create_config(user) -> AuditUserConfig:
    config, _ = AuditUserConfig.objects.get_or_create(
        user=user,
        defaults={
            'llm_config': _encrypt_llm_config(_build_system_default_llm_config()),
            'other_config': _encrypt_other_config(_build_system_default_other_config()),
            'sys_creator': user,
            'sys_modifier': user,
        },
    )
    return config


def get_default_user_config() -> dict:
    return {
        'llm_config': _build_system_default_llm_config(),
        'other_config': _build_system_default_other_config(),
    }


def serialize_user_config(instance: AuditUserConfig) -> dict:
    llm_config = _deep_merge(_build_system_default_llm_config(), _decrypt_llm_config(instance.llm_config or {}))
    other_config = _normalize_codehub_token(
        _deep_merge(_build_system_default_other_config(), _decrypt_other_config(instance.other_config or {}))
    )
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
    merged_other = _normalize_codehub_token(_deep_merge(current['other_config'], payload.get('other_config') or {}))
    instance.llm_config = _encrypt_llm_config(merged_llm)
    instance.other_config = _encrypt_other_config(merged_other)
    instance.sys_modifier = user
    instance.save()
    return serialize_user_config(instance)


def delete_user_config(user) -> bool:
    AuditUserConfig.objects.filter(user_id=get_user_id(user)).delete()
    return True


def list_llm_providers() -> list[dict]:
    providers: list[dict] = []
    for provider in LLMProvider:
        models = LLMFactory.get_available_models(provider)
        providers.append(
            {
                'id': provider.value,
                'name': provider.value.upper(),
                'default_model': LLMFactory.get_default_model(provider),
                'models': models,
                'default_base_url': DEFAULT_BASE_URLS.get(provider),
            }
        )
    return providers


def list_embedding_providers() -> list[dict]:
    return EMBEDDING_PROVIDERS


def get_embedding_provider_models(provider: str) -> dict:
    provider_id = str(provider or '').strip().lower()
    provider_meta = next((item for item in EMBEDDING_PROVIDERS if item['id'] == provider_id), None)
    if not provider_meta:
        raise HttpError(404, f'Embedding provider 不存在: {provider}')
    return {
        'provider': provider_id,
        'models': list(provider_meta.get('models') or []),
        'default_model': provider_meta.get('default_model'),
        'requires_api_key': bool(provider_meta.get('requires_api_key')),
    }


def get_embedding_config(user) -> dict:
    config = get_user_config(user)
    resolved = resolve_embedding_config(config)
    saved_embedding_config = dict(config.get('other_config', {}).get('embedding_config') or {})
    locked = embedding_config_locked()
    return {
        'provider': resolved.get('provider') or 'openai',
        'model': resolved.get('model') or '',
        'api_key': '' if locked else str(saved_embedding_config.get('api_key') or resolved.get('api_key') or ''),
        'base_url': resolved.get('base_url') or '',
        'dimensions': resolved.get('dimensions'),
        'batch_size': resolved.get('batch_size'),
        'config_locked': locked,
        'api_key_configured': bool(str(resolved.get('api_key') or '').strip()),
    }


def update_embedding_config(user, payload: dict) -> dict:
    if embedding_config_locked():
        raise HttpError(403, '当前 embedding 配置由生产环境统一管理，不能在页面保存覆盖')
    normalized_payload = _normalize_embedding_update_payload(payload)
    update_user_config(user, {'other_config': {'embedding_config': normalized_payload}})
    return get_embedding_config(user)


def test_embedding(user, payload: dict) -> dict:
    provider = normalize_embedding_provider(payload.get('provider'))
    model = str(payload.get('model') or '').strip()
    test_text = str(payload.get('test_text') or 'Focus DeepAudit embedding health check')
    dimension = payload.get('dimensions') or payload.get('dimension')
    api_key = str(payload.get('api_key') or '').strip()
    if api_key and not _contains_only_ascii(api_key):
        return {
            'success': False,
            'message': _invalid_api_key_message(),
            'preview_vector_length': 0,
            'dimensions': None,
            'sample_embedding': [],
            'latency_ms': None,
        }
    user_config = get_user_config(user) if user is not None else None
    resolved = resolve_embedding_config(
        user_config,
        provider=provider or None,
        model=model or None,
        api_key=api_key or None,
        base_url=str(payload.get('base_url') or '').strip() or None,
        dimensions=dimension,
    )
    requires_key = any(item['id'] == resolved['provider'] and item['requires_api_key'] for item in EMBEDDING_PROVIDERS)
    if requires_key and not str(resolved.get('api_key') or '').strip():
        return {
            'success': False,
            'message': '当前 embedding provider 需要 API Key',
            'preview_vector_length': 0,
            'dimensions': None,
            'sample_embedding': [],
            'latency_ms': None,
        }
    started = time.perf_counter()
    try:
        service = EmbeddingService(
            provider=resolved.get('provider'),
            model=resolved.get('model'),
            api_key=str(resolved.get('api_key') or '').strip() or None,
            base_url=str(resolved.get('base_url') or '').strip() or None,
            dimension=resolved.get('dimensions'),
        )
        embedding = async_to_sync(service.embed)(test_text)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            'success': True,
            'message': f'嵌入成功! 维度: {len(embedding)}',
            'preview_vector_length': min(16, len(embedding)),
            'dimensions': len(embedding),
            'sample_embedding': [float(item) for item in embedding[:5]],
            'latency_ms': latency_ms,
        }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        if resolved.get('provider') == 'ollama':
            message = (
                '嵌入失败: 无法连接或调用 Ollama embedding 服务。'
                f' 请确认当前 DeepAudit 后端机器可以访问 {resolved.get("base_url") or "Ollama 地址"}'
                f'，当前测试地址: {resolved.get("base_url") or "-"}。原始错误: {exc}'
            )
        else:
            message = f'嵌入失败: {exc}'
        return {
            'success': False,
            'message': message,
            'preview_vector_length': 0,
            'dimensions': None,
            'sample_embedding': [],
            'latency_ms': latency_ms,
        }


def test_llm_connection(user, payload: dict) -> dict:
    provider_requested = coerce_llm_provider(str(payload.get('provider') or '').strip().lower() or 'openai')
    saved_debug = _build_saved_debug(user)
    saved_config = get_user_config(user).get('llm_config') or {}
    api_key = str(
        payload.get('api_key')
        or payload.get('apiKey')
        or saved_config.get('api_key')
        or ''
    ).strip()
    explicit_model = str(payload.get('model') or '').strip()
    explicit_base_url = str(payload.get('base_url') or payload.get('baseUrl') or '').strip()
    saved_model = str(saved_config.get('model') or '').strip()
    saved_base_url = str(saved_config.get('base_url') or '').strip()
    provider = provider_requested
    model = explicit_model or saved_model or _default_model_for_provider(provider)
    base_url = explicit_base_url or saved_base_url or _default_base_url_for_provider(provider)

    timeout_seconds = max(5, int(saved_config.get('timeout') or DEFAULT_LLM_CONFIG['timeout']))
    temperature = float(saved_config.get('temperature', DEFAULT_LLM_CONFIG['temperature']))
    max_tokens = int(saved_config.get('max_tokens', DEFAULT_LLM_CONFIG['max_tokens']))

    debug = {
        'provider_requested': provider_requested,
        'provider_used': provider,
        'model_requested': explicit_model,
        'model_used': model,
        'base_url_requested': explicit_base_url,
        'base_url_used': base_url,
        'api_key_length': len(api_key),
        'api_key_prefix': _mask_api_key(api_key),
        'saved_config': saved_debug,
        'test_params': {
            'timeout': timeout_seconds,
            'temperature': temperature,
            'max_tokens': max_tokens,
        },
    }

    if provider not in LLM_TEST_MODELS:
        debug['error_category'] = 'unsupported_provider'
        return {
            'success': False,
            'message': f'暂不支持的 LLM Provider: {provider_requested}',
            'model': model,
            'debug': debug,
        }

    if provider not in API_KEY_OPTIONAL_PROVIDERS and not api_key:
        debug['error_category'] = 'missing_api_key'
        return {
            'success': False,
            'message': '请先填写 API Key',
            'model': model,
            'debug': debug,
        }

    def _attempt_connection(attempt_provider: str, attempt_model: str, attempt_base_url: str, attempt_api_key: str, *, is_fallback: bool = False):
        start = time.perf_counter()
        attempt_debug = dict(debug)
        attempt_debug['provider_used'] = attempt_provider
        attempt_debug['model_used'] = attempt_model
        attempt_debug['base_url_used'] = attempt_base_url
        if is_fallback:
            attempt_debug['fallback_provider'] = attempt_provider

        try:
            if attempt_provider in OPENAI_COMPATIBLE_PROVIDERS:
                attempt_debug['adapter_type'] = 'openai-compatible'
                response_payload, transport_debug = _send_openai_compatible_request(
                    attempt_provider,
                    attempt_api_key,
                    attempt_model,
                    attempt_base_url,
                    timeout=timeout_seconds,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = _extract_openai_content(response_payload)
            elif attempt_provider == 'claude':
                attempt_debug['adapter_type'] = 'anthropic-native'
                response_payload, transport_debug = _send_claude_request(
                    attempt_api_key,
                    attempt_model,
                    attempt_base_url,
                    timeout=timeout_seconds,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = _extract_claude_content(response_payload)
            elif attempt_provider == 'gemini':
                attempt_debug['adapter_type'] = 'gemini-native'
                response_payload, transport_debug = _send_gemini_request(
                    attempt_api_key,
                    attempt_model,
                    attempt_base_url,
                    timeout=timeout_seconds,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = _extract_gemini_content(response_payload)
            elif attempt_provider == 'baidu':
                attempt_debug['adapter_type'] = 'baidu-native'
                response_payload, transport_debug = _send_baidu_request(
                    attempt_api_key,
                    attempt_model,
                    attempt_base_url,
                    timeout=timeout_seconds,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = str(response_payload.get('result') or '')
            elif attempt_provider == 'minimax':
                attempt_debug['adapter_type'] = 'minimax-native'
                response_payload, transport_debug = _send_minimax_request(
                    attempt_api_key,
                    attempt_model,
                    attempt_base_url,
                    timeout=timeout_seconds,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = _extract_openai_content(response_payload)
            else:
                attempt_debug['error_category'] = 'unsupported_provider'
                return {
                    'success': False,
                    'message': f'当前 Provider 暂未接入在线测试: {attempt_provider}',
                    'model': attempt_model,
                    'debug': attempt_debug,
                }

            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            attempt_debug['elapsed_time_ms'] = elapsed_ms
            attempt_debug.update(transport_debug)

            status_code = int(transport_debug.get('status_code') or 0)
            if status_code and status_code >= 400:
                attempt_debug['error_category'] = 'http_error'
                attempt_debug['error_message'] = _extract_error_message(
                    response_payload,
                    f'LLM 服务返回 HTTP {status_code}',
                )
                return {
                    'success': False,
                    'message': attempt_debug['error_message'],
                    'model': attempt_model,
                    'debug': attempt_debug,
                }

            if not content:
                attempt_debug['error_category'] = 'empty_response'
                attempt_debug['error_message'] = 'LLM 返回空响应，请检查模型名、端点和 API Key'
                return {
                    'success': False,
                    'message': attempt_debug['error_message'],
                    'model': attempt_model,
                    'debug': attempt_debug,
                }

            usage = response_payload.get('usage')
            if usage is not None:
                attempt_debug['usage'] = usage

            return {
                'success': True,
                'message': f'连接成功 ({elapsed_ms} ms)',
                'model': attempt_model,
                'response': content[:100],
                'debug': attempt_debug,
            }
        except requests.Timeout:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            attempt_debug['elapsed_time_ms'] = elapsed_ms
            attempt_debug['error_category'] = 'timeout'
            attempt_debug['error_type'] = 'Timeout'
            attempt_debug['error_message'] = f'请求超时，请检查网络连通性或适当增大超时时间（当前 {timeout_seconds}s）'
            return {
                'success': False,
                'message': attempt_debug['error_message'],
                'model': attempt_model,
                'debug': attempt_debug,
            }
        except requests.RequestException as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            attempt_debug['elapsed_time_ms'] = elapsed_ms
            attempt_debug['error_category'] = 'network'
            attempt_debug['error_type'] = type(exc).__name__
            attempt_debug['error_message'] = str(exc)
            return {
                'success': False,
                'message': f'网络请求失败: {exc}',
                'model': attempt_model,
                'debug': attempt_debug,
            }
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            attempt_debug['elapsed_time_ms'] = elapsed_ms
            attempt_debug['error_category'] = 'unexpected'
            attempt_debug['error_type'] = type(exc).__name__
            attempt_debug['error_message'] = str(exc)
            return {
                'success': False,
                'message': str(exc) or 'LLM 测试失败',
                'model': attempt_model,
                'debug': attempt_debug,
            }

    # 手动“测试连接”只验证当前填写/已保存的入口，避免主请求失败后被本地兜底掩盖。
    return _attempt_connection(provider, model, base_url, api_key)


def _fingerprint(public_key: str) -> str:
    if not public_key:
        return ''
    try:
        parts = public_key.strip().split()
        if len(parts) >= 2:
            key_bytes = b64decode(parts[1].encode('utf-8'))
            digest = b64encode(hashlib.sha256(key_bytes).digest()).decode('utf-8').rstrip('=')
            return f'SHA256:{digest}'
    except Exception:
        pass
    digest = hashlib.sha256(public_key.encode('utf-8')).hexdigest()
    return ':'.join(digest[index:index + 2] for index in range(0, 32, 2))


def _ensure_ssh_runtime_support() -> None:
    if not serialization or not default_backend:
        raise HttpError(500, '当前环境缺少 cryptography 依赖，无法生成 SSH 密钥')


def _generate_rsa_key(key_size: int = 4096) -> tuple[str, str]:
    _ensure_ssh_runtime_support()
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=max(2048, int(key_size or 4096)),
        backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode('utf-8')
    return private_pem, public_key


def _generate_ed25519_key() -> tuple[str, str]:
    _ensure_ssh_runtime_support()
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode('utf-8')
    return private_pem, public_key


def _verify_key_pair(private_key: str, public_key: str) -> bool:
    _ensure_ssh_runtime_support()
    if not private_key or not public_key:
        return False
    private_key_bytes = private_key.encode('utf-8')
    key_obj = None
    try:
        key_obj = serialization.load_ssh_private_key(private_key_bytes, password=None, backend=default_backend())
    except Exception:
        try:
            key_obj = serialization.load_pem_private_key(private_key_bytes, password=None, backend=default_backend())
        except Exception:
            return False
    derived_public = key_obj.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode('utf-8').strip()
    expected_parts = public_key.strip().split()
    actual_parts = derived_public.strip().split()
    return len(expected_parts) >= 2 and len(actual_parts) >= 2 and expected_parts[:2] == actual_parts[:2]


def _extract_ssh_host(repo_url: str) -> str:
    value = str(repo_url or '').strip()
    if not value:
        raise HttpError(422, 'repo_url 不能为空')
    if value.startswith('ssh://'):
        host = value.split('ssh://', 1)[1].split('/', 1)[0].split('@')[-1].split(':', 1)[0]
    elif '@' in value and ':' in value.split('@', 1)[1]:
        host = value.split('@', 1)[1].split(':', 1)[0]
    else:
        raise HttpError(422, '仅支持 SSH 仓库地址进行测试')
    if not re.match(r'^[A-Za-z0-9.-]+$', host):
        raise HttpError(422, '仓库地址中的主机名不合法')
    return host


def _write_temp_private_key(temp_dir: str, private_key: str) -> str:
    key_path = os.path.join(temp_dir, 'id_key')
    with open(key_path, 'w', encoding='utf-8') as handle:
        handle.write(private_key)
    os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    return key_path


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


def generate_ssh_credential(user, payload: dict) -> dict:
    key_type = str(payload.get('key_type') or 'rsa').strip().lower()
    if key_type == 'ed25519':
        private_key, public_key = _generate_ed25519_key()
    else:
        private_key, public_key = _generate_rsa_key(payload.get('key_size') or 4096)
    save_ssh_credential(
        user,
        {
            'private_key': private_key,
            'public_key': public_key,
        },
    )
    return {
        'public_key': public_key,
        'fingerprint': _fingerprint(public_key),
        'message': 'SSH 密钥生成成功，请将公钥添加到 CodeHub 或内网 Git 服务账号 / Deploy Key',
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


def test_ssh_credential(user, payload: dict) -> dict:
    credential = AuditSshCredential.objects.filter(user_id=get_user_id(user), is_deleted=False).first()
    if not credential or not credential.private_key_encrypted:
        raise HttpError(404, '未找到 SSH 私钥，请先生成或上传 SSH 密钥')
    private_key = decrypt_value(credential.private_key_encrypted)
    public_key = str(credential.public_key or '').strip()
    if public_key and not _verify_key_pair(private_key, public_key):
        return {
            'success': False,
            'message': '密钥对验证失败：私钥和公钥不匹配',
            'output': '',
        }

    host = _extract_ssh_host(payload.get('repo_url'))
    temp_dir = tempfile.mkdtemp(prefix='deepaudit-ssh-test-')
    try:
        key_path = _write_temp_private_key(temp_dir, private_key)
        known_hosts_file = os.path.join(temp_dir, 'known_hosts')
        known_hosts_payload = str(credential.known_hosts or '').strip()
        with open(known_hosts_file, 'w', encoding='utf-8') as handle:
            handle.write(known_hosts_payload)
        os.chmod(known_hosts_file, stat.S_IRUSR | stat.S_IWUSR)

        cmd = [
            'ssh',
            '-i',
            key_path,
            '-o',
            'StrictHostKeyChecking=accept-new',
            '-o',
            f'UserKnownHostsFile={known_hosts_file}',
            '-o',
            f'ConnectTimeout={int(getattr(settings, "SSH_CONNECT_TIMEOUT", 15))}',
            '-o',
            'PreferredAuthentications=publickey',
            '-o',
            'IdentitiesOnly=yes',
            '-T',
            f'git@{host}',
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=int(getattr(settings, 'SSH_TEST_TIMEOUT', 20)),
        )
        output = f'{result.stdout or ""}{result.stderr or ""}'.strip()
        credential.known_hosts = open(known_hosts_file, 'r', encoding='utf-8').read() or None
        credential.sys_modifier = user
        credential.save(update_fields=['known_hosts', 'sys_modifier', 'sys_update_datetime'])

        lowered = output.lower()
        success_markers = (
            'successfully authenticated',
            'welcome to gitlab',
            'welcome to codeup',
            'hi ',
        )
        if any(marker in lowered for marker in success_markers):
            return {'success': True, 'message': 'SSH 密钥验证成功', 'output': output}
        if 'anonymous' in lowered:
            return {
                'success': True,
                'message': 'SSH 连接成功，但公钥尚未关联到具体账号',
                'output': output,
            }
        if 'permission denied' in lowered:
            return {
                'success': False,
                'message': 'SSH 密钥验证失败：权限被拒绝，请确认公钥已添加到 CodeHub 或内网 Git 服务',
                'output': output,
            }
        if 'connection refused' in lowered or 'no route to host' in lowered:
            return {
                'success': False,
                'message': 'SSH 连接失败，请检查网络或 Git 服务可用性',
                'output': output,
            }
        return {
            'success': result.returncode == 0,
            'message': 'SSH 测试完成' if result.returncode == 0 else 'SSH 密钥验证失败',
            'output': output,
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'message': f'SSH 连接超时（{int(getattr(settings, "SSH_TEST_TIMEOUT", 20))}秒）',
            'output': '',
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def clear_ssh_known_hosts(user) -> bool:
    credential = AuditSshCredential.objects.filter(user_id=get_user_id(user), is_deleted=False).first()
    if not credential:
        return True
    credential.known_hosts = ''
    credential.sys_modifier = user
    credential.save(update_fields=['known_hosts', 'sys_modifier', 'sys_update_datetime'])
    return True


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
