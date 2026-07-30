from __future__ import annotations

import json
import logging
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import monotonic, perf_counter, sleep
from typing import Callable

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from core.user.user_model import User

from .crypto import credential_cipher
from .models import AgentSkillProvider

logger = logging.getLogger(__name__)

# 仅对通常表示上游暂时不可用的状态码重试，鉴权和请求参数问题必须立即暴露。
RETRYABLE_MODEL_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def _role_codes(user: User | None) -> set[str]:
    """读取角色编码，保持 AI 辅助工具自身的权限边界。"""
    return set(user.core_roles.filter(status=True).values_list('code', flat=True)) if user else set()


def is_agent_tools_admin(user: User | None) -> bool:
    """超级管理员或 ``tools_admin`` 可查看全部模型连接。"""
    return bool(user and (user.is_superuser or 'tools_admin' in _role_codes(user)))


def _display_name(user: User | None) -> str:
    """序列化审计用户名称，避免空关联导致响应失败。"""
    return (user.name or user.username) if user else ''


def _serialize_provider(provider: AgentSkillProvider) -> dict:
    """返回可展示的模型档案，明确排除加密凭证。"""
    return {
        'id': str(provider.id),
        'name': provider.name,
        'base_url': provider.base_url,
        'model': provider.model,
        'has_api_key': bool(provider.api_key_encrypted),
        'is_active': provider.is_active,
        'description': provider.description,
        'owner_name': _display_name(provider.owner),
        'sys_create_datetime': provider.sys_create_datetime,
    }


def list_providers(user: User) -> list[dict]:
    """返回当前用户可使用的模型档案；管理员可见全部记录。"""
    queryset = AgentSkillProvider.objects.filter(is_deleted=False, owner=user)
    if is_agent_tools_admin(user):
        queryset = AgentSkillProvider.objects.filter(is_deleted=False)
    return [_serialize_provider(item) for item in queryset.select_related('owner')]


def get_provider_for_user(user: User, provider_id: str, *, active_only: bool = False) -> AgentSkillProvider:
    """读取用户可用模型档案，供所有子 Agent 统一复用。"""
    queryset = AgentSkillProvider.objects.filter(id=provider_id, is_deleted=False)
    if active_only:
        queryset = queryset.filter(is_active=True)
    provider = get_object_or_404(queryset)
    if not is_agent_tools_admin(user) and provider.owner_id != user.id:
        raise HttpError(403, '不能使用其他用户的模型配置')
    return provider


def save_provider(user: User, payload, provider_id: str | None = None) -> dict:
    """保存模型连接；更新时空 API Key 会保留原有加密凭证。"""
    provider = get_provider_for_user(user, provider_id) if provider_id else AgentSkillProvider(owner=user, sys_creator=user)
    provider.name = payload.name.strip()
    provider.base_url = payload.base_url.rstrip('/')
    provider.model = payload.model.strip()
    provider.is_active = payload.is_active
    provider.description = payload.description.strip()
    provider.sys_modifier = user
    if payload.api_key.strip():
        provider.api_key_encrypted = credential_cipher.encrypt(payload.api_key.strip())
    provider.owner = provider.owner or user
    provider.save()
    return _serialize_provider(provider)


def chat_completion_url(base_url: str) -> str:
    """兼容 API 根地址与完整 Chat Completions 地址两种填写方式。"""
    normalized_url = base_url.rstrip('/')
    return normalized_url if normalized_url.endswith('/chat/completions') else f'{normalized_url}/chat/completions'


def normalize_upstream_text(content: str) -> str:
    """保守修复上游错误按 Latin-1 标注 UTF-8 时产生的典型乱码。"""
    normalized = content
    # 仅命中特征标记时重解码，避免改动本来正确的多语言输出。
    for _ in range(2):
        if not any(marker in normalized for marker in ('Ã', 'Â', 'â\x80', 'ð\x9f')):
            break
        try:
            repaired = normalized.encode('latin-1').decode('utf-8')
        except UnicodeError:
            break
        if repaired == normalized:
            break
        normalized = repaired
    return normalized


def _stream_completion_content(response: requests.Response, on_update: Callable[[str], None]) -> str:
    """读取 OpenAI 兼容 SSE，并把增量文本交给业务模块持久化或渲染。"""
    chunks: list[str] = []
    last_flush_at = perf_counter()
    # 网关可能遗漏 charset，使用原始字节并明确 UTF-8 解码以避免中文乱码。
    for raw_line in response.iter_lines(decode_unicode=False):
        line = raw_line.decode('utf-8', errors='replace') if isinstance(raw_line, bytes) else str(raw_line)
        if not line or not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if data == '[DONE]':
            break
        try:
            chunk = json.loads(data)
            delta = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
        except (AttributeError, IndexError, TypeError, json.JSONDecodeError):
            continue
        if not delta:
            continue
        chunks.append(normalize_upstream_text(str(delta)))
        now = perf_counter()
        if now - last_flush_at >= 0.35:
            on_update(''.join(chunks))
            last_flush_at = now
    content = ''.join(chunks).strip()
    on_update(content)
    return content


def _positive_setting(name: str, default: float, *, minimum: float = 0.1) -> float:
    """读取正数配置，避免异常环境变量让模型调用失去超时边界。"""
    try:
        value = float(getattr(settings, name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _retry_after_seconds(response: requests.Response) -> float | None:
    """解析上游的 Retry-After 秒数或 HTTP 日期，优先遵守服务端恢复建议。"""
    raw_value = response.headers.get('Retry-After', '').strip()
    if not raw_value:
        return None
    try:
        return max(0.0, float(raw_value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(raw_value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError, IndexError):
            return None


def _close_response(response: requests.Response | None) -> None:
    """在每次失败或完成后释放连接，防止多次恢复重试耗尽连接池。"""
    if response is None:
        return
    try:
        response.close()
    except (AttributeError, requests.RequestException):
        logger.debug('关闭模型服务响应失败', exc_info=True)


def _retry_delay_seconds(retry_number: int, retry_after: float | None) -> float:
    """计算带抖动的退避时间，降低服务恢复瞬间的并发重试峰值。"""
    initial_delay = _positive_setting('AGENT_TOOLS_MODEL_RETRY_INITIAL_DELAY_SECONDS', 2)
    max_delay = max(
        initial_delay,
        _positive_setting('AGENT_TOOLS_MODEL_RETRY_MAX_DELAY_SECONDS', 30),
    )
    if retry_after is not None:
        # 即便上游错误返回 Retry-After: 0，也要留出极短缓冲，避免恢复前形成热循环。
        return max(0.5, retry_after)
    capped_delay = min(max_delay, initial_delay * (2 ** min(retry_number - 1, 8)))
    return random.uniform(capped_delay * 0.75, capped_delay * 1.25)


def _recovery_timeout_error(timeout_seconds: float, last_error: str) -> RuntimeError:
    """构造总恢复窗口耗尽后的统一失败信息。"""
    return RuntimeError(
        f'模型服务在 {timeout_seconds:g} 秒内未恢复（最后一次错误：{last_error}）。'
        '已停止重试，请稍后重新执行或检查模型服务。'
    )


def _wait_for_model_recovery(
    *,
    retry_number: int,
    deadline: float,
    timeout_seconds: float,
    last_error: str,
    retry_after: float | None,
    on_retry: Callable[[str], None] | None,
) -> None:
    """在全局五分钟窗口内等待后重试，并把等待状态回传给调用方。"""
    remaining_seconds = deadline - monotonic()
    if remaining_seconds <= 0:
        raise _recovery_timeout_error(timeout_seconds, last_error)

    delay_seconds = min(_retry_delay_seconds(retry_number, retry_after), remaining_seconds)
    next_attempt = retry_number + 1
    wait_message = (
        f'模型服务暂时不可用（{last_error}），将在 {delay_seconds:.0f} 秒后进行第 {next_attempt} 次尝试。'
        f'最长等待 {timeout_seconds:g} 秒。'
    )
    if on_retry:
        try:
            on_retry(wait_message)
        except Exception:
            # 过程展示异常不能中断真正的模型恢复流程。
            logger.exception('写入模型服务重试状态失败')
    sleep(delay_seconds)
    if monotonic() >= deadline:
        raise _recovery_timeout_error(timeout_seconds, last_error)


def _request_timeout(remaining_seconds: float) -> tuple[float, float]:
    """为单次请求分配剩余预算，保证连接和读取合计不会无限越过总窗口。"""
    connect_timeout = min(
        _positive_setting('AGENT_TOOLS_MODEL_CONNECT_TIMEOUT_SECONDS', 10),
        max(0.1, remaining_seconds / 2),
    )
    read_timeout = min(
        _positive_setting('AGENT_TOOLS_MODEL_READ_TIMEOUT_SECONDS', 120),
        max(0.1, remaining_seconds - connect_timeout),
    )
    return connect_timeout, read_timeout


def chat_completion(
    provider: AgentSkillProvider,
    messages: list[dict],
    temperature: float = 0.2,
    *,
    on_stream_update: Callable[[str], None] | None = None,
    on_retry: Callable[[str], None] | None = None,
) -> str:
    """通过平台级模型连接调用模型，并在暂时不可用时最多恢复等待五分钟。"""
    api_key = credential_cipher.decrypt(provider.api_key_encrypted)
    if not api_key:
        raise RuntimeError('模型档案缺少 API Key')
    endpoint = chat_completion_url(provider.base_url)
    use_stream = on_stream_update is not None
    recovery_timeout_seconds = _positive_setting('AGENT_TOOLS_MODEL_RECOVERY_TIMEOUT_SECONDS', 300, minimum=1)
    deadline = monotonic() + recovery_timeout_seconds
    retry_number = 0

    while True:
        response: requests.Response | None = None
        try:
            remaining_seconds = deadline - monotonic()
            if remaining_seconds <= 0:
                raise _recovery_timeout_error(recovery_timeout_seconds, '等待模型服务响应超时')
            response = requests.post(
                endpoint,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={'model': provider.model, 'messages': messages, 'temperature': temperature, 'stream': use_stream},
                stream=use_stream,
                timeout=_request_timeout(remaining_seconds),
            )
            if response.status_code in RETRYABLE_MODEL_STATUS_CODES:
                retry_number += 1
                status_error = f'HTTP {response.status_code}'
                retry_after = _retry_after_seconds(response)
                _close_response(response)
                response = None
                _wait_for_model_recovery(
                    retry_number=retry_number,
                    deadline=deadline,
                    timeout_seconds=recovery_timeout_seconds,
                    last_error=status_error,
                    retry_after=retry_after,
                    on_retry=on_retry,
                )
                continue
            if not response.ok:
                raise RuntimeError(f'模型服务请求失败（HTTP {response.status_code}）：{response.text[:300]}')
            if use_stream and 'text/event-stream' in response.headers.get('Content-Type', '').lower():
                content = _stream_completion_content(response, on_stream_update)
                if not content:
                    raise RuntimeError('模型服务流式响应未包含可用文本')
                return content
            try:
                payload = response.json()
            except ValueError as exc:
                content_type = response.headers.get('Content-Type', '未提供')
                preview = ' '.join(response.text.split())[:160] or '空响应'
                raise RuntimeError(
                    f'模型服务返回了非 JSON 响应（Content-Type: {content_type}，地址：{endpoint}，内容：{preview}）。'
                    '请确认 Base URL 是 OpenAI 兼容接口根地址；部分服务需要以 /v1 结尾。'
                ) from exc
            try:
                return normalize_upstream_text(str(payload['choices'][0]['message']['content']).strip())
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError('模型服务响应不包含 choices[0].message.content') from exc
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as exc:
            retry_number += 1
            _close_response(response)
            response = None
            _wait_for_model_recovery(
                retry_number=retry_number,
                deadline=deadline,
                timeout_seconds=recovery_timeout_seconds,
                last_error=f'连接异常：{exc}',
                retry_after=None,
                on_retry=on_retry,
            )
        finally:
            _close_response(response)


def test_provider(user: User, provider_id: str) -> dict:
    """发起最小模型请求，验证当前用户有权使用的模型连接。"""
    provider = get_provider_for_user(user, provider_id)
    try:
        chat_completion(provider, [{'role': 'user', 'content': 'Reply with OK only.'}], temperature=0)
        return {'ok': True, 'message': '模型服务连接成功'}
    except Exception as exc:
        return {'ok': False, 'message': str(exc)}
