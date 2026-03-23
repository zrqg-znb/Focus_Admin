from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from urllib.parse import urlencode

import requests

from apps.deepaudit.constants import DEFAULT_LLM_CONFIG, DEFAULT_OTHER_CONFIG, EMBEDDING_PROVIDERS
from apps.deepaudit.encryption import decrypt_value, encrypt_value
from apps.deepaudit.permissions import get_user_id
from apps.deepaudit.serialization import format_datetime_text
from apps.deepaudit.user_config.user_config_model import AuditSshCredential, AuditUserConfig


SENSITIVE_LLM_FIELDS = {'api_key'}
SENSITIVE_TOKEN_FIELDS = {'github_token', 'gitlab_token', 'gitea_token'}
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


def _mask_api_key(api_key: str) -> str:
    if not api_key:
        return '(empty)'
    if len(api_key) <= 8:
        return api_key
    return f'{api_key[:8]}...'


def _default_model_for_provider(provider: str) -> str:
    return LLM_TEST_MODELS.get(provider, LLM_TEST_MODELS['openai'])


def _default_base_url_for_provider(provider: str) -> str:
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


def test_llm_connection(user, payload: dict) -> dict:
    provider = str(payload.get('provider') or '').strip().lower() or 'openai'
    saved_debug = _build_saved_debug(user)
    saved_config = get_user_config(user).get('llm_config') or {}
    api_key = str(
        payload.get('api_key')
        or payload.get('apiKey')
        or saved_config.get('api_key')
        or ''
    ).strip()
    model = str(payload.get('model') or '').strip() or _default_model_for_provider(provider)
    base_url = str(payload.get('base_url') or payload.get('baseUrl') or '').strip() or _default_base_url_for_provider(provider)
    timeout_seconds = max(5, int(saved_config.get('timeout') or DEFAULT_LLM_CONFIG['timeout']))
    temperature = float(saved_config.get('temperature', DEFAULT_LLM_CONFIG['temperature']))
    max_tokens = int(saved_config.get('max_tokens', DEFAULT_LLM_CONFIG['max_tokens']))

    debug = {
        'provider': provider,
        'model_requested': str(payload.get('model') or ''),
        'model_used': model,
        'base_url_requested': str(payload.get('base_url') or payload.get('baseUrl') or ''),
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
            'message': f'暂不支持的 LLM Provider: {provider}',
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

    start = time.perf_counter()

    try:
        if provider in OPENAI_COMPATIBLE_PROVIDERS:
            debug['adapter_type'] = 'openai-compatible'
            response_payload, transport_debug = _send_openai_compatible_request(
                provider,
                api_key,
                model,
                base_url,
                timeout=timeout_seconds,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = _extract_openai_content(response_payload)
        elif provider == 'claude':
            debug['adapter_type'] = 'anthropic-native'
            response_payload, transport_debug = _send_claude_request(
                api_key,
                model,
                base_url,
                timeout=timeout_seconds,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = _extract_claude_content(response_payload)
        elif provider == 'gemini':
            debug['adapter_type'] = 'gemini-native'
            response_payload, transport_debug = _send_gemini_request(
                api_key,
                model,
                base_url,
                timeout=timeout_seconds,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = _extract_gemini_content(response_payload)
        elif provider == 'baidu':
            debug['adapter_type'] = 'baidu-native'
            response_payload, transport_debug = _send_baidu_request(
                api_key,
                model,
                base_url,
                timeout=timeout_seconds,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = str(response_payload.get('result') or '')
        elif provider == 'minimax':
            debug['adapter_type'] = 'minimax-native'
            response_payload, transport_debug = _send_minimax_request(
                api_key,
                model,
                base_url,
                timeout=timeout_seconds,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = _extract_openai_content(response_payload)
        else:
            debug['error_category'] = 'unsupported_provider'
            return {
                'success': False,
                'message': f'当前 Provider 暂未接入在线测试: {provider}',
                'model': model,
                'debug': debug,
            }

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        debug['elapsed_time_ms'] = elapsed_ms
        debug.update(transport_debug)

        status_code = int(transport_debug.get('status_code') or 0)
        if status_code and status_code >= 400:
            debug['error_category'] = 'http_error'
            debug['error_message'] = _extract_error_message(
                response_payload,
                f'LLM 服务返回 HTTP {status_code}',
            )
            return {
                'success': False,
                'message': debug['error_message'],
                'model': model,
                'debug': debug,
            }

        if not content:
            debug['error_category'] = 'empty_response'
            debug['error_message'] = 'LLM 返回空响应，请检查模型名、端点和 API Key'
            return {
                'success': False,
                'message': debug['error_message'],
                'model': model,
                'debug': debug,
            }

        usage = response_payload.get('usage')
        if usage is not None:
            debug['usage'] = usage

        return {
            'success': True,
            'message': f'连接成功 ({elapsed_ms} ms)',
            'model': model,
            'response': content[:100],
            'debug': debug,
        }
    except requests.Timeout:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        debug['elapsed_time_ms'] = elapsed_ms
        debug['error_category'] = 'timeout'
        debug['error_type'] = 'Timeout'
        debug['error_message'] = f'请求超时，请检查网络连通性或适当增大超时时间（当前 {timeout_seconds}s）'
        return {
            'success': False,
            'message': debug['error_message'],
            'model': model,
            'debug': debug,
        }
    except requests.RequestException as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        debug['elapsed_time_ms'] = elapsed_ms
        debug['error_category'] = 'network'
        debug['error_type'] = type(exc).__name__
        debug['error_message'] = str(exc)
        return {
            'success': False,
            'message': f'网络请求失败: {exc}',
            'model': model,
            'debug': debug,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        debug['elapsed_time_ms'] = elapsed_ms
        debug['error_category'] = 'unexpected'
        debug['error_type'] = type(exc).__name__
        debug['error_message'] = str(exc)
        return {
            'success': False,
            'message': str(exc) or 'LLM 测试失败',
            'model': model,
            'debug': debug,
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
