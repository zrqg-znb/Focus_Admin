"""
Token Estimator - Token 计数器

使用 tiktoken 进行精确计数，不可用时回退到启发式估算。
"""

import hashlib
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# tiktoken 编码器缓存
_encoders: dict = {}
_tiktoken_available: bool | None = None  # None=未检测, True=可用, False=不可用
_logged_method: bool = False  # 是否已输出使用方案日志

_TIKTOKEN_MODE_ENV = "DEEPAUDIT_TIKTOKEN_MODE"
_TIKTOKEN_MODE_OFF = "off"
_TIKTOKEN_MODE_LOCAL = "local"
_TIKTOKEN_MODE_AUTO = "auto"
_TIKTOKEN_ENCODER_URLS = {
    "cl100k_base": "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
    "o200k_base": "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken",
    "p50k_base": "https://openaipublic.blob.core.windows.net/encodings/p50k_base.tiktoken",
    "r50k_base": "https://openaipublic.blob.core.windows.net/encodings/r50k_base.tiktoken",
}


def _get_tiktoken_mode() -> str:
    """
    获取 tiktoken 模式。

    - off: 完全禁用 tiktoken，始终使用启发式估算
    - local: 仅在本地缓存已有编码器文件时使用 tiktoken（默认）
    - auto: 允许 tiktoken 按默认行为下载编码器文件
    """
    raw_value = str(os.getenv(_TIKTOKEN_MODE_ENV, _TIKTOKEN_MODE_LOCAL) or "").strip().lower()

    if raw_value in {"0", "false", "no", "off", "disable", "disabled"}:
        return _TIKTOKEN_MODE_OFF
    if raw_value in {"1", "true", "yes", "auto", "download", "remote"}:
        return _TIKTOKEN_MODE_AUTO
    return _TIKTOKEN_MODE_LOCAL


def _iter_tiktoken_cache_dirs():
    seen: set[str] = set()
    for env_name in ("TIKTOKEN_CACHE_DIR", "DATA_GYM_CACHE_DIR"):
        value = str(os.getenv(env_name, "") or "").strip()
        if value and value not in seen:
            seen.add(value)
            yield Path(value)

    default_dir = str(Path(tempfile.gettempdir()) / "data-gym-cache")
    if default_dir not in seen:
        yield Path(default_dir)


def _has_local_encoder_cache(encoding_name: str) -> bool:
    blob_url = _TIKTOKEN_ENCODER_URLS.get(encoding_name)
    if not blob_url:
        return False

    cache_key = hashlib.sha1(blob_url.encode("utf-8")).hexdigest()
    return any((cache_dir / cache_key).exists() for cache_dir in _iter_tiktoken_cache_dirs())


def _preferred_encoding_for_model(model: str) -> str:
    model_name = str(model or "").strip().lower()
    if any(
        token in model_name
        for token in ("gpt-5", "gpt-4.1", "gpt-4o", "o1", "o3", "o4", "omni")
    ):
        return "o200k_base"
    return "cl100k_base"


def _resolve_local_cached_encoding(model: str) -> str | None:
    candidates = [
        _preferred_encoding_for_model(model),
        "cl100k_base",
        "o200k_base",
        "p50k_base",
        "r50k_base",
    ]
    for encoding_name in candidates:
        if _has_local_encoder_cache(encoding_name):
            return encoding_name
    return None


def _check_tiktoken_availability(log_result: bool = False) -> bool:
    """
    检测 tiktoken 是否可用

    Args:
        log_result: 是否输出日志（首次实际使用时输出）
    """
    global _tiktoken_available, _logged_method

    if _tiktoken_available is not None:
        # 已检测过，只在首次需要时输出日志
        if log_result and not _logged_method:
            _logged_method = True
            if _tiktoken_available:
                logger.info("✅ Token 计数方案: tiktoken 精确计数")
            else:
                logger.warning("⚠️ Token 计数方案: 启发式估算")
        return _tiktoken_available

    mode = _get_tiktoken_mode()
    if mode == _TIKTOKEN_MODE_OFF:
        _tiktoken_available = False
        if log_result:
            _logged_method = True
            logger.info("⚠️ Token 计数方案: 启发式估算 (已通过环境变量禁用 tiktoken)")
        return _tiktoken_available

    try:
        import tiktoken

        if mode == _TIKTOKEN_MODE_LOCAL:
            cached_encoding = _resolve_local_cached_encoding("gpt-4")
            if not cached_encoding:
                _tiktoken_available = False
                if log_result:
                    _logged_method = True
                    logger.info(
                        "⚠️ Token 计数方案: 启发式估算 "
                        "(未找到本地 tiktoken 编码缓存，避免访问公网)"
                    )
                return _tiktoken_available

            tiktoken.get_encoding(cached_encoding)
        else:
            tiktoken.get_encoding("cl100k_base")

        _tiktoken_available = True
        if log_result:
            _logged_method = True
            if mode == _TIKTOKEN_MODE_LOCAL:
                logger.info("✅ Token 计数方案: tiktoken 本地缓存计数")
            else:
                logger.info("✅ Token 计数方案: tiktoken 精确计数")
    except ImportError:
        _tiktoken_available = False
        if log_result:
            _logged_method = True
            logger.warning("⚠️ Token 计数方案: 启发式估算 (tiktoken 未安装)")
    except Exception as e:
        _tiktoken_available = False
        if log_result:
            _logged_method = True
            logger.warning(f"⚠️ Token 计数方案: 启发式估算 (tiktoken 初始化失败: {e})")

    return _tiktoken_available


def _get_tiktoken_encoder(model: str):
    """
    获取 tiktoken 编码器（带缓存）

    Args:
        model: 模型名称

    Returns:
        tiktoken 编码器或 None
    """
    if model in _encoders:
        return _encoders[model]

    try:
        import tiktoken

        mode = _get_tiktoken_mode()
        if mode == _TIKTOKEN_MODE_OFF:
            _encoders[model] = None
            return None

        if mode == _TIKTOKEN_MODE_LOCAL:
            cached_encoding = _resolve_local_cached_encoding(model)
            if not cached_encoding:
                logger.debug(
                    "tiktoken local cache missing for model %s, using heuristic estimation",
                    model,
                )
                _encoders[model] = None
                return None
            encoder = tiktoken.get_encoding(cached_encoding)
            _encoders[model] = encoder
            return encoder

        # 尝试按模型名获取编码器
        try:
            encoder = tiktoken.encoding_for_model(model)
        except KeyError:
            # 未知模型，使用 cl100k_base（GPT-4/3.5 使用的编码）
            encoder = tiktoken.get_encoding("cl100k_base")

        _encoders[model] = encoder
        return encoder
    except ImportError:
        logger.debug("tiktoken not available, using heuristic estimation")
        _encoders[model] = None
        return None
    except Exception as e:
        logger.warning(f"Failed to get tiktoken encoder: {e}")
        _encoders[model] = None
        return None


class TokenEstimator:
    """Token 估算器"""

    @staticmethod
    def count_tokens(text: str, model: str = "gpt-4") -> int:
        """
        计算文本的 token 数量

        优先使用 tiktoken 精确计数，不可用时使用启发式估算。

        Args:
            text: 要计算的文本
            model: 模型名称（用于选择正确的编码器）

        Returns:
            Token 数量
        """
        if not text:
            return 0

        # 首次调用时输出使用方案日志
        _check_tiktoken_availability(log_result=True)

        # 尝试使用 tiktoken
        encoder = _get_tiktoken_encoder(model)
        if encoder is not None:
            try:
                return len(encoder.encode(text))
            except Exception as e:
                logger.debug(f"tiktoken encode failed: {e}, falling back to heuristic")

        # 启发式估算
        return TokenEstimator._heuristic_estimate(text)

    @staticmethod
    def _heuristic_estimate(text: str) -> int:
        """
        启发式 token 估算

        基于字符类型的估算规则：
        - 英文/ASCII: ~4 字符/token
        - 中文/CJK: ~1.5 字符/token（中文分词后每个词约 1-2 token）
        - 其他 Unicode: ~2 字符/token

        Args:
            text: 文本内容

        Returns:
            估算的 token 数量
        """
        if not text:
            return 0

        ascii_chars = 0
        cjk_chars = 0
        other_chars = 0

        for char in text:
            code = ord(char)
            if code < 128:
                ascii_chars += 1
            elif 0x4E00 <= code <= 0x9FFF:  # CJK 统一汉字
                cjk_chars += 1
            elif 0x3400 <= code <= 0x4DBF:  # CJK 扩展 A
                cjk_chars += 1
            elif 0x20000 <= code <= 0x2A6DF:  # CJK 扩展 B
                cjk_chars += 1
            elif 0x3000 <= code <= 0x303F:  # CJK 标点
                cjk_chars += 1
            elif 0xFF00 <= code <= 0xFFEF:  # 全角字符
                cjk_chars += 1
            else:
                other_chars += 1

        # 估算公式
        tokens = (
            ascii_chars / 4.0 +      # 英文约 4 字符/token
            cjk_chars / 1.5 +        # 中文约 1.5 字符/token
            other_chars / 2.0        # 其他约 2 字符/token
        )

        # 至少返回 1
        return max(1, int(tokens + 0.5))

    @staticmethod
    def estimate_messages_tokens(messages: list, model: str = "gpt-4") -> int:
        """
        估算消息列表的 token 数量

        包括消息格式开销（role、分隔符等）

        Args:
            messages: 消息列表，每条消息包含 role 和 content
            model: 模型名称

        Returns:
            总 token 数量
        """
        total = 0

        for msg in messages:
            # 每条消息的格式开销约 4 tokens
            total += 4

            content = msg.get("content", "")
            if isinstance(content, str):
                total += TokenEstimator.count_tokens(content, model)
            elif isinstance(content, list):
                # 多模态消息
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        total += TokenEstimator.count_tokens(part.get("text", ""), model)

        # 消息列表的额外开销
        total += 3

        return total
