from __future__ import annotations

from copy import deepcopy
from typing import Any

from django.conf import settings

from apps.deepaudit.constants import (
    DEFAULT_LLM_CONFIG,
    DEFAULT_OTHER_CONFIG,
    EMBEDDING_PROVIDERS,
)


PROVIDER_API_KEY_FIELDS = {
    "openai": "openaiApiKey",
    "gemini": "geminiApiKey",
    "claude": "claudeApiKey",
    "qwen": "qwenApiKey",
    "deepseek": "deepseekApiKey",
    "zhipu": "zhipuApiKey",
    "moonshot": "moonshotApiKey",
    "baidu": "baiduApiKey",
    "minimax": "minimaxApiKey",
    "doubao": "doubaoApiKey",
}

PROVIDER_API_KEY_SETTINGS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "claude": "CLAUDE_API_KEY",
    "qwen": "QWEN_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "zhipu": "ZHIPU_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "baidu": "BAIDU_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "doubao": "DOUBAO_API_KEY",
}

PROVIDER_BASE_URL_SETTINGS = {
    "openai": "OPENAI_BASE_URL",
    "ollama": "OLLAMA_BASE_URL",
}

SUPPORTED_LLM_PROVIDERS = {
    "openai",
    "qwen",
    "deepseek",
    "zhipu",
    "ollama",
}

DEFAULT_LLM_MODELS = {
    "gemini": "gemini-3-pro",
    "openai": "gpt-5",
    "claude": "claude-sonnet-4.5",
    "qwen": "qwen3-max-instruct",
    "deepseek": "deepseek-chat",
    "zhipu": "glm-4.6",
    "moonshot": "kimi-k2",
    "baidu": "ernie-4.5",
    "minimax": "minimax-m2",
    "doubao": "doubao-1.6-pro",
    "ollama": "llama3.3-70b",
}

DEFAULT_LLM_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "moonshot": "https://api.moonshot.cn/v1",
    "baidu": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1",
    "minimax": "https://api.minimax.chat/v1",
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
    "ollama": "http://localhost:11434/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "claude": "https://api.anthropic.com/v1",
}

EMBEDDING_DEFAULT_MODELS = {
    item["id"]: item["default_model"] for item in EMBEDDING_PROVIDERS
}
EMBEDDING_PROVIDER_IDS = {
    str(item["id"]).strip().lower()
    for item in EMBEDDING_PROVIDERS
    if str(item.get("id") or "").strip()
}

EMBEDDING_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "ollama": "http://127.0.0.1:11434",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}

EMBEDDING_API_KEY_SETTINGS = {
    "openai": ("EMBEDDING_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY"),
    "qwen": ("EMBEDDING_API_KEY", "QWEN_API_KEY", "LLM_API_KEY"),
    "ollama": (),
}

KNOWN_EMBEDDING_DIMENSIONS = {
    ("ollama", "nomic-embed-text"): 768,
    ("ollama", "mxbai-embed-large"): 1024,
    ("ollama", "all-minilm"): 384,
    ("ollama", "snowflake-arctic-embed"): 1024,
    ("ollama", "bge-m3"): 1024,
    ("ollama", "qwen3-embedding"): 1024,
}


def get_setting(name: str, default: Any = None) -> Any:
    return getattr(settings, name, default)


def known_embedding_dimension(provider: str, model: str) -> int | None:
    return KNOWN_EMBEDDING_DIMENSIONS.get((str(provider).lower(), str(model).lower()))


def get_global_embedding_config() -> dict[str, Any]:
    """Load the shared UI-managed embedding configuration without creating rows on reads."""
    try:
        from apps.deepaudit.encryption import decrypt_value
        from apps.deepaudit.user_config.user_config_model import AuditGlobalEmbeddingConfig

        config = AuditGlobalEmbeddingConfig.objects.filter(
            config_key="default", is_deleted=False
        ).first()
    except Exception:
        # The resolver is also used while migrations and lightweight commands start up.
        return {}

    if not config:
        return {}
    return {
        "provider": str(config.provider or "").strip(),
        "model": str(config.model or "").strip(),
        "api_key": decrypt_value(str(config.api_key_encrypted or "")),
        "base_url": str(config.base_url or "").strip(),
        "dimensions": config.dimensions,
        "batch_size": config.batch_size,
    }


def deep_merge(base: dict | None, override: dict | None) -> dict:
    result = deepcopy(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _clean_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in data.items()
        if value is not None
    }


def normalize_embedding_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower() or DEFAULT_OTHER_CONFIG["embedding_config"]["provider"]
    if provider not in EMBEDDING_PROVIDER_IDS:
        return DEFAULT_OTHER_CONFIG["embedding_config"]["provider"]
    return provider


def normalize_embedding_base_url(provider: str, base_url: str | None) -> str:
    normalized_provider = normalize_embedding_provider(provider)
    text = str(base_url or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = f"http://{text}"
    if normalized_provider != "ollama":
        return text.rstrip("/")

    normalized = text.rstrip("/")
    lowered = normalized.lower()
    for suffix in ("/api/embed", "/api/embeddings", "/api", "/v1"):
        if lowered.endswith(suffix):
            normalized = normalized[: -len(suffix)].rstrip("/")
            lowered = normalized.lower()
    return normalized


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return None


def _normalize_timeout_seconds(value: Any) -> int | None:
    timeout = _coerce_int(value)
    if timeout is None:
        return None
    if timeout > 1000:
        return max(1, timeout // 1000)
    return timeout


def _legacy_llm_to_snake(llm_config: dict[str, Any]) -> dict[str, Any]:
    provider_raw = str(
        llm_config.get("provider") or llm_config.get("llmProvider") or ""
    ).strip().lower()
    provider = coerce_llm_provider(provider_raw)
    api_key = str(
        llm_config.get("api_key") or llm_config.get("llmApiKey") or ""
    ).strip()
    if not api_key and provider_raw:
        provider_field = PROVIDER_API_KEY_FIELDS.get(provider_raw)
        api_key = str(llm_config.get(provider_field) or "").strip()
    return _clean_dict(
        {
            "provider": provider or None,
            "model": str(
                llm_config.get("model") or llm_config.get("llmModel") or ""
            ).strip()
            or None,
            "api_key": api_key or None,
            "base_url": str(
                llm_config.get("base_url") or llm_config.get("llmBaseUrl") or ""
            ).strip()
            or None,
            "timeout": _normalize_timeout_seconds(
                llm_config.get("timeout") or llm_config.get("llmTimeout")
            ),
            "temperature": _coerce_float(
                llm_config.get("temperature") or llm_config.get("llmTemperature")
            ),
            "max_tokens": _coerce_int(
                llm_config.get("max_tokens") or llm_config.get("llmMaxTokens")
            ),
            "first_token_timeout": _coerce_int(
                llm_config.get("first_token_timeout")
                or llm_config.get("llmFirstTokenTimeout")
            ),
            "stream_timeout": _coerce_int(
                llm_config.get("stream_timeout") or llm_config.get("llmStreamTimeout")
            ),
            "tool_timeout": _coerce_int(
                llm_config.get("tool_timeout") or llm_config.get("toolTimeout")
            ),
            "sub_agent_timeout": _coerce_int(
                llm_config.get("sub_agent_timeout") or llm_config.get("subAgentTimeout")
            ),
            "agent_timeout": _coerce_int(
                llm_config.get("agent_timeout") or llm_config.get("agentTimeout")
            ),
        }
    )


def _legacy_other_to_snake(other_config: dict[str, Any]) -> dict[str, Any]:
    scan_config = dict(
        other_config.get("scan_config") or other_config.get("scanConfig") or {}
    )
    embedding_config = dict(
        other_config.get("embedding_config") or other_config.get("embeddingConfig") or {}
    )
    codehub_token = str(other_config.get("codehub_token") or other_config.get("codehubToken") or "").strip()
    if not codehub_token:
        for legacy_key in ("github_token", "gitlab_token", "gitea_token", "githubToken", "gitlabToken", "giteaToken"):
            legacy_value = str(other_config.get(legacy_key) or "").strip()
            if legacy_value:
                codehub_token = legacy_value
                break
    return _clean_dict(
        {
            "codehub_token": codehub_token or None,
            "output_language": str(
                other_config.get("output_language")
                or other_config.get("outputLanguage")
                or ""
            ).strip()
            or None,
            "scan_config": _clean_dict(
                {
                    "max_analyze_files": _coerce_int(
                        scan_config.get("max_analyze_files")
                        or scan_config.get("maxAnalyzeFiles")
                    ),
                    "llm_concurrency": _coerce_int(
                        scan_config.get("llm_concurrency")
                        or scan_config.get("llmConcurrency")
                    ),
                    "llm_gap_ms": _coerce_int(
                        scan_config.get("llm_gap_ms") or scan_config.get("llmGapMs")
                    ),
                    "include_tests": _coerce_bool(
                        scan_config.get("include_tests")
                        or scan_config.get("includeTests")
                    ),
                    "include_docs": _coerce_bool(
                        scan_config.get("include_docs") or scan_config.get("includeDocs")
                    ),
                    "max_file_size": _coerce_int(
                        scan_config.get("max_file_size")
                        or scan_config.get("maxFileSize")
                    ),
                    "analysis_depth": str(
                        scan_config.get("analysis_depth")
                        or scan_config.get("analysisDepth")
                        or ""
                    ).strip()
                    or None,
                }
            ),
            "embedding_config": _clean_dict(
                {
                    "provider": str(embedding_config.get("provider") or "").strip()
                    or None,
                    "model": str(embedding_config.get("model") or "").strip() or None,
                    "api_key": str(embedding_config.get("api_key") or "").strip()
                    or None,
                    "base_url": str(embedding_config.get("base_url") or "").strip()
                    or None,
                    "dimensions": _coerce_int(
                        embedding_config.get("dimensions")
                        or embedding_config.get("dimension")
                    ),
                    "batch_size": _coerce_int(embedding_config.get("batch_size")),
                }
            ),
        }
    )


def normalize_runtime_user_config(user_config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(user_config or {})
    llm_source = dict(payload.get("llm_config") or payload.get("llmConfig") or {})
    other_source = dict(payload.get("other_config") or payload.get("otherConfig") or {})

    llm_config = deep_merge(DEFAULT_LLM_CONFIG, _legacy_llm_to_snake(llm_source))
    other_config = deep_merge(DEFAULT_OTHER_CONFIG, _legacy_other_to_snake(other_source))

    return {
        "llm_config": llm_config,
        "other_config": other_config,
        "llmConfig": build_legacy_llm_config(llm_config),
        "otherConfig": build_legacy_other_config(other_config),
    }


def coerce_llm_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower() or DEFAULT_LLM_CONFIG["provider"]
    if provider not in SUPPORTED_LLM_PROVIDERS:
        return DEFAULT_LLM_CONFIG["provider"]
    return provider


def resolve_provider_api_key(
    provider: str,
    llm_config: dict[str, Any] | None = None,
) -> str:
    config = dict(llm_config or {})
    provider = coerce_llm_provider(provider)
    api_key = str(config.get("api_key") or "").strip()
    if api_key:
        return api_key
    legacy_field = PROVIDER_API_KEY_FIELDS.get(provider)
    if legacy_field:
        api_key = str(config.get(legacy_field) or "").strip()
        if api_key:
            return api_key
    return str(
        get_setting("LLM_API_KEY", "")
        or get_setting(PROVIDER_API_KEY_SETTINGS.get(provider, ""), "")
        or ""
    ).strip()


def resolve_provider_base_url(
    provider: str,
    llm_config: dict[str, Any] | None = None,
) -> str | None:
    config = dict(llm_config or {})
    provider = coerce_llm_provider(provider)
    explicit = str(config.get("base_url") or config.get("llmBaseUrl") or "").strip()
    if explicit:
        return explicit
    common = str(get_setting("LLM_BASE_URL", "") or "").strip()
    if common:
        return common
    provider_setting = PROVIDER_BASE_URL_SETTINGS.get(provider)
    specific = str(get_setting(provider_setting, "") or "").strip() if provider_setting else ""
    if specific:
        return specific
    try:
        return DEFAULT_LLM_BASE_URLS[provider]
    except Exception:
        return None


def resolve_provider_model(
    provider: str,
    llm_config: dict[str, Any] | None = None,
) -> str:
    config = dict(llm_config or {})
    provider = coerce_llm_provider(provider)
    explicit = str(config.get("model") or config.get("llmModel") or "").strip()
    if explicit:
        return explicit
    env_model = str(get_setting("LLM_MODEL", "") or "").strip()
    if env_model:
        return env_model
    return DEFAULT_LLM_MODELS.get(provider, DEFAULT_LLM_CONFIG["model"])


def build_legacy_llm_config(llm_config: dict[str, Any]) -> dict[str, Any]:
    provider = coerce_llm_provider(llm_config.get("provider"))
    api_key = str(llm_config.get("api_key") or "").strip()
    payload = _clean_dict(
        {
            "llmProvider": provider,
            "llmApiKey": api_key or None,
            "llmModel": str(llm_config.get("model") or "").strip() or None,
            "llmBaseUrl": str(llm_config.get("base_url") or "").strip() or None,
            "llmTimeout": (
                int(llm_config["timeout"]) * 1000
                if llm_config.get("timeout") not in (None, "")
                else None
            ),
            "llmTemperature": _coerce_float(llm_config.get("temperature")),
            "llmMaxTokens": _coerce_int(llm_config.get("max_tokens")),
            "llmFirstTokenTimeout": _coerce_int(llm_config.get("first_token_timeout")),
            "llmStreamTimeout": _coerce_int(llm_config.get("stream_timeout")),
            "toolTimeout": _coerce_int(llm_config.get("tool_timeout")),
            "subAgentTimeout": _coerce_int(llm_config.get("sub_agent_timeout")),
            "agentTimeout": _coerce_int(llm_config.get("agent_timeout")),
        }
    )
    provider_field = PROVIDER_API_KEY_FIELDS.get(provider)
    if provider_field and api_key:
        payload[provider_field] = api_key
    return payload


def build_legacy_other_config(other_config: dict[str, Any]) -> dict[str, Any]:
    scan_config = dict(other_config.get("scan_config") or {})
    embedding_config = dict(other_config.get("embedding_config") or {})
    return _clean_dict(
        {
            "codehubToken": str(other_config.get("codehub_token") or "").strip() or None,
            "outputLanguage": str(other_config.get("output_language") or "").strip()
            or None,
            "scanConfig": _clean_dict(
                {
                    "maxAnalyzeFiles": _coerce_int(scan_config.get("max_analyze_files")),
                    "llmConcurrency": _coerce_int(scan_config.get("llm_concurrency")),
                    "llmGapMs": _coerce_int(scan_config.get("llm_gap_ms")),
                    "includeTests": _coerce_bool(scan_config.get("include_tests")),
                    "includeDocs": _coerce_bool(scan_config.get("include_docs")),
                    "maxFileSize": _coerce_int(scan_config.get("max_file_size")),
                    "analysisDepth": str(scan_config.get("analysis_depth") or "").strip()
                    or None,
                }
            ),
            "embeddingConfig": _clean_dict(
                {
                    "provider": str(embedding_config.get("provider") or "").strip()
                    or None,
                    "model": str(embedding_config.get("model") or "").strip() or None,
                    "api_key": str(embedding_config.get("api_key") or "").strip()
                    or None,
                    "base_url": str(embedding_config.get("base_url") or "").strip()
                    or None,
                    "dimensions": _coerce_int(embedding_config.get("dimensions")),
                    "batch_size": _coerce_int(embedding_config.get("batch_size")),
                }
            ),
        }
    )


def resolve_embedding_config(
    user_config: dict[str, Any] | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    dimensions: int | None = None,
) -> dict[str, Any]:
    normalized = normalize_runtime_user_config(user_config)
    legacy_embedding_config = dict(normalized["other_config"].get("embedding_config") or {})
    raw_other_config = dict(
        (user_config or {}).get("other_config")
        or (user_config or {}).get("otherConfig")
        or {}
    )
    raw_legacy_embedding_config = dict(
        raw_other_config.get("embedding_config")
        or raw_other_config.get("embeddingConfig")
        or {}
    )
    global_embedding_config = get_global_embedding_config()
    embedding_config = global_embedding_config or legacy_embedding_config
    config_source = (
        "global_ui"
        if global_embedding_config
        else "legacy_user"
        if raw_legacy_embedding_config.get("provider") or raw_legacy_embedding_config.get("model")
        else "default"
    )
    saved_provider = normalize_embedding_provider(embedding_config.get("provider"))
    resolved_provider = normalize_embedding_provider(
        provider or embedding_config.get("provider") or DEFAULT_OTHER_CONFIG["embedding_config"]["provider"]
    )
    same_saved_provider = saved_provider == resolved_provider
    resolved_model = str(
        model
        or (embedding_config.get("model") if same_saved_provider else "")
        or EMBEDDING_DEFAULT_MODELS.get(resolved_provider, DEFAULT_OTHER_CONFIG["embedding_config"]["model"])
    ).strip()
    resolved_api_key = str(
        api_key or (embedding_config.get("api_key") if same_saved_provider else "") or ""
    ).strip()
    resolved_base_url = normalize_embedding_base_url(
        resolved_provider,
        base_url or (embedding_config.get("base_url") if same_saved_provider else ""),
    ) or normalize_embedding_base_url(
        resolved_provider,
        EMBEDDING_DEFAULT_BASE_URLS.get(resolved_provider, ""),
    )
    resolved_dimensions = (
        dimensions
        or (_coerce_int(embedding_config.get("dimensions") or embedding_config.get("dimension")) if same_saved_provider else None)
        or known_embedding_dimension(resolved_provider, resolved_model)
        or _coerce_int(DEFAULT_OTHER_CONFIG["embedding_config"]["dimensions"])
    )
    resolved_batch_size = _coerce_int(embedding_config.get("batch_size")) or _coerce_int(
        DEFAULT_OTHER_CONFIG["embedding_config"]["batch_size"]
    )

    return {
        "provider": resolved_provider,
        "model": resolved_model,
        "api_key": resolved_api_key,
        "base_url": resolved_base_url,
        "dimensions": resolved_dimensions,
        "batch_size": resolved_batch_size,
        "config_source": config_source,
    }
