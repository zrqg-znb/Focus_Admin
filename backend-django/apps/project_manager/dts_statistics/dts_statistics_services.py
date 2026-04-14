from __future__ import annotations

import calendar
import datetime
import hashlib
import json
import logging
import math
import os
import random
import tempfile
import threading
import time
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable, Iterable

import openpyxl
import requests
from django.conf import settings
from django.core.cache import cache
from django.db import close_old_connections, connection, transaction
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from ninja.errors import HttpError

from common.fu_cache import CacheManager
from core.dict_item.dict_item_model import DictItem
from core.dept.dept_model import Dept
from core.pl.pl_model import PlGroup
from core.user.user_model import User
from scheduler.module.executor import scheduler_task

from .dts_statistics_model import (
    DtsExtension,
    DtsStatisticsExportTask,
    DtsStatisticsQueryTask,
)
from .dts_statistics_schemas import (
    DtsExtensionSaveSchema,
    DtsFieldSetRequestSchema,
    DtsStatisticsExportSchema,
    DtsStatisticsQuerySchema,
)

logger = logging.getLogger(__name__)

_SOURCE_CACHE_KEY_PREFIX = "cache:dts_statistics:source:v2:"
_PREPARED_CACHE_KEY_PREFIX = "cache:dts_statistics:prepared:v1:"
_LOCK_KEY_PREFIX = "cache:dts_statistics:lock:v2:"
_SNAPSHOT_META_KEY_PREFIX = "cache:dts_statistics:snapshot:meta:v1:"
_SNAPSHOT_CHUNK_KEY_PREFIX = "cache:dts_statistics:snapshot:chunk:v1:"
_SNAPSHOT_FIELD_SET_KEY_PREFIX = "cache:dts_statistics:snapshot:field-set:v1:"
_SNAPSHOT_LOCK_KEY_PREFIX = "cache:dts_statistics:snapshot:lock:v1:"
_FILTERED_RESULT_CACHE_KEY_PREFIX = "cache:dts_statistics:filtered:v1:"

_DEFAULT_SOURCE_CACHE_TTL_SECONDS = 180
_DEFAULT_LOCK_TTL_SECONDS = 30
_DEFAULT_PREPARED_CACHE_TTL_SECONDS = 10 * 60
_DEFAULT_EXPORT_FILE_TTL_SECONDS = 24 * 60 * 60
_DEFAULT_SNAPSHOT_CACHE_TTL_SECONDS = 72 * 60 * 60
_DEFAULT_FILTERED_RESULT_CACHE_TTL_SECONDS = 10 * 60
_DEFAULT_SNAPSHOT_CHUNK_SIZE = 1000
_DEFAULT_SNAPSHOT_STALE_AFTER_SECONDS = 4 * 60 * 60
_SNAPSHOT_WINDOW_MONTHS = 2

_DATA_LAKE_PAGE_SIZE = 500
_MAX_TIME_SPAN_MS_PER_CHUNK = 3 * 24 * 60 * 60 * 1000
_MAX_SCAN_PAGES_PER_CHUNK = 2000

_QUERY_TASK_ACTIVE_STATUSES = {
    DtsStatisticsQueryTask.STATUS_PENDING,
    DtsStatisticsQueryTask.STATUS_RUNNING,
}
_EXPORT_TASK_ACTIVE_STATUSES = {
    DtsStatisticsExportTask.STATUS_PENDING,
    DtsStatisticsExportTask.STATUS_RUNNING,
}

_PRODUCT_ID_TO_NAME = {
    "250539396": "座舱",
    "250539397": "车控",
}
_SUPPORTED_PRODUCT_IDS = tuple(_PRODUCT_ID_TO_NAME.keys())

_DEFAULT_FIELDS = [
    "dtsBizNo",
    "briefDesc",
    "dtsStatusName",
    "serverityNoName",
    "updateAt",
    "parentNo",
    "createAt",
    "dCloseTime",
    "uQbiCloseTypeName",
    "sDeptOneNoName",
    "currentHandler",
    "creator",
    "sSubmitUserName",
    "sSubsystemNoName",
    "sConfigFlowType",
    "sProdFamilyNoName",
    "sProdXtdNoName",
    "iTestBackCount",
    "sSuggestByReviewer",
    "sTestReport",
    "sTestSuggest",
    "sModifyDocument",
    "sTestorTestReport",
    "last_dts009_handler",
    "last_dts010_handler",
    "last_dts013_handler",
    "iNumOfCloseDays",
    "iNumOfFirmDays",
    "iNumOfLocateDays",
    "iNumofModifyDays",
    "iNumofTestDays",
    "dts009ReasonAnalysis",
]

_FIELD_SET_SUPPORTED_FIELDS = {
    "sDeptOneNoName",
    "sSubsystemNoName",
    "sConfigFlowType",
    "auto_pl_group_name",
    "uQbiCloseTypeName",
}

_SEVERITY_NAME_TO_CODE = {
    "提示": "Suggestion",
    "一般": "Minor",
    "严重": "Major",
    "关键": "Critical",
}

_FLOW_STATE_CODE_TO_NAME = {
    "DTS001": "问题提交人填写",
    "DTS002": "测试(项目)经理审核",
    "DTS003": "项目经理审核",
    "DTS004": "开发人员定位",
    "DTS005": "项目经理审核定位",
    "DTS006": "开发人员方案审计",
    "DTS007": "CCB方案审核",
    "DTS008": "评审专家在线评审",
    "DTS009": "开发人员审核修改",
    "DTS010": "审核人员审核修改",
    "DTS011": "CMO归档",
    "DTS012": "测试经理组织测试",
    "DTS013": "测试人员回归测试",
    "DTS014": "确认问题单",
    "DTS015": "制定修补计划",
    "FS99": "关闭",
    "FS01": "撤销",
}

_FLOW_STATE_NAME_TO_CODES: dict[str, set[str]] = {}
for _code, _name in _FLOW_STATE_CODE_TO_NAME.items():
    if not _name:
        continue
    _FLOW_STATE_NAME_TO_CODES.setdefault(_name, set()).add(_code)

_BRIEF_DESC_EXCLUDED_KEYWORDS = (
    "【自动提单】",
    "【漏洞】",
    "【三方件】",
)
_BASE_SOFT_DEPT_NAME = "底软开发部"
_BASE_SOFT_TEST_KEYWORD = "【底软测试】"
_AUTO_SOURCE_EXTERNAL = "外领域自提单"
_AUTO_SOURCE_TEST = "测试自提单"
_AUTO_SOURCE_DEV = "底软开发自提单"
_AUTO_PL_GROUP_UNKNOWN = "未识别"
_ALLOWED_CONFIG_FLOW_TYPES = {"简易", "标准"}

_EXPORT_SHEET_TITLE = "DTS统计"


def _get_setting(name: str, default: Any = None) -> Any:
    return getattr(settings, name, os.environ.get(name, default))


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text:
        return default
    return text in {"1", "true", "yes", "y", "on"}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_list(values: Any) -> list[str]:
    if values is None:
        return []
    raw_values = values if isinstance(values, list) else [values]
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        text = _clean_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_runtime_datetime(
    dt: datetime.datetime | None,
) -> datetime.datetime | None:
    if dt is None:
        return None
    current_tz = timezone.get_current_timezone()
    if settings.USE_TZ:
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, current_tz)
        return timezone.localtime(dt, current_tz)
    if timezone.is_aware(dt):
        return timezone.make_naive(dt, current_tz)
    return dt


def _runtime_min_datetime() -> datetime.datetime:
    return _normalize_runtime_datetime(datetime.datetime.min) or datetime.datetime.min


def _parse_datetime(value: Any) -> datetime.datetime | None:
    text = _clean_text(value)
    if not text:
        return None

    normalized_text = text.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(normalized_text)
        return _normalize_runtime_datetime(dt)
    except Exception:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ):
        try:
            dt = datetime.datetime.strptime(text, fmt)
            return _normalize_runtime_datetime(dt)
        except Exception:
            continue
    return None


def _cache_key(prefix: str, payload: dict[str, Any]) -> tuple[str, str]:
    digest = hashlib.md5(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"{prefix}{digest}", digest


def _fingerprint_payload(payload: dict[str, Any]) -> str:
    return hashlib.md5(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def _get_user_cache_scope(user: Any) -> str:
    user_id = getattr(user, "id", None)
    return str(user_id) if user_id else "anonymous"


def _get_prepared_cache_key(fingerprint: str, *, user: Any = None) -> str:
    return f"{_PREPARED_CACHE_KEY_PREFIX}{_get_user_cache_scope(user)}:{fingerprint}"


def _resolve_prepared_cache_ttl_seconds() -> int:
    return _resolve_cache_ttl(
        "DTS_STATISTICS_PREPARED_CACHE_TTL_SECONDS",
        _DEFAULT_PREPARED_CACHE_TTL_SECONDS,
    )


def _resolve_export_file_ttl_seconds() -> int:
    return _resolve_cache_ttl(
        "DTS_STATISTICS_EXPORT_FILE_TTL_SECONDS",
        _DEFAULT_EXPORT_FILE_TTL_SECONDS,
    )


def _resolve_export_temp_dir() -> Path:
    configured = _clean_text(_get_setting("DTS_STATISTICS_EXPORT_TEMP_DIR", ""))
    if configured:
        path = Path(configured)
    else:
        path = Path(tempfile.gettempdir()) / "focus-admin" / "dts-statistics-export"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _snapshot_meta_key(product_id: str) -> str:
    return f"{_SNAPSHOT_META_KEY_PREFIX}{_clean_text(product_id)}"


def _snapshot_chunk_key(product_id: str, version: str, chunk_index: int) -> str:
    return (
        f"{_SNAPSHOT_CHUNK_KEY_PREFIX}{_clean_text(product_id)}:"
        f"{_clean_text(version)}:{max(int(chunk_index or 0), 0)}"
    )


def _snapshot_field_set_key(product_id: str, version: str) -> str:
    return f"{_SNAPSHOT_FIELD_SET_KEY_PREFIX}{_clean_text(product_id)}:{_clean_text(version)}"


def _snapshot_lock_key(product_id: str) -> str:
    return f"{_SNAPSHOT_LOCK_KEY_PREFIX}{_clean_text(product_id)}"


def _serialize_snapshot_meta(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(meta, dict):
        return None
    product_id = _clean_text(meta.get("productId"))
    generated_at = _clean_text(meta.get("generatedAt"))
    is_stale = bool(meta.get("isStale"))
    generated_dt = _parse_datetime(generated_at)
    if generated_dt is not None:
        is_stale = is_stale or (
            timezone.now() - generated_dt
            > datetime.timedelta(seconds=_resolve_snapshot_stale_after_seconds())
        )
    return {
        "productId": product_id,
        "productName": _clean_text(meta.get("productName"))
        or (_PRODUCT_ID_TO_NAME.get(product_id) or product_id),
        "version": _clean_text(meta.get("version")),
        "generatedAt": generated_at or None,
        "windowBegin": max(int(meta.get("windowBegin") or 0), 0),
        "windowEnd": max(int(meta.get("windowEnd") or 0), 0),
        "rowCount": max(int(meta.get("rowCount") or 0), 0),
        "isStale": is_stale,
    }


def _serialize_query_task(
    task: DtsStatisticsQueryTask | None,
) -> dict[str, Any] | None:
    if task is None:
        return None
    return {
        "id": str(task.id),
        "fingerprint": _clean_text(task.fingerprint),
        "status": _clean_text(task.status),
        "message": _clean_text(task.message),
        "error_message": _clean_text(task.error_message),
        "progress": max(int(task.progress or 0), 0),
        "scanned_pages": max(int(task.scanned_pages or 0), 0),
        "total_pages": max(int(task.total_pages or 0), 0),
        "matched_count": max(int(task.matched_count or 0), 0),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


def _serialize_export_task(
    task: DtsStatisticsExportTask | None,
) -> dict[str, Any] | None:
    if task is None:
        return None
    return {
        "id": str(task.id),
        "fingerprint": _clean_text(task.fingerprint),
        "status": _clean_text(task.status),
        "message": _clean_text(task.message),
        "error_message": _clean_text(task.error_message),
        "progress": max(int(task.progress or 0), 0),
        "file_name": _clean_text(task.file_name) or None,
        "file_size": max(int(task.file_size or 0), 0),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


def _resolve_cache_ttl(setting_name: str, default: int) -> int:
    raw_value = _get_setting(setting_name, default)
    try:
        value = int(raw_value)
    except Exception:
        value = default
    return max(value, 1)


def _resolve_max_scan_pages() -> int:
    raw_value = _get_setting(
        "DTS_STATISTICS_SCAN_MAX_PAGES_PER_CHUNK",
        _MAX_SCAN_PAGES_PER_CHUNK,
    )
    try:
        value = int(raw_value)
    except Exception:
        value = _MAX_SCAN_PAGES_PER_CHUNK
    return max(value, 1)


def _resolve_snapshot_cache_ttl_seconds() -> int:
    return _resolve_cache_ttl(
        "DTS_STATISTICS_SNAPSHOT_CACHE_TTL_SECONDS",
        _DEFAULT_SNAPSHOT_CACHE_TTL_SECONDS,
    )


def _resolve_filtered_result_cache_ttl_seconds() -> int:
    return _resolve_cache_ttl(
        "DTS_STATISTICS_FILTERED_RESULT_CACHE_TTL_SECONDS",
        _DEFAULT_FILTERED_RESULT_CACHE_TTL_SECONDS,
    )


def _resolve_snapshot_chunk_size() -> int:
    raw_value = _get_setting(
        "DTS_STATISTICS_SNAPSHOT_CHUNK_SIZE",
        _DEFAULT_SNAPSHOT_CHUNK_SIZE,
    )
    try:
        value = int(raw_value)
    except Exception:
        value = _DEFAULT_SNAPSHOT_CHUNK_SIZE
    return max(value, 100)


def _resolve_snapshot_stale_after_seconds() -> int:
    return _resolve_cache_ttl(
        "DTS_STATISTICS_SNAPSHOT_STALE_AFTER_SECONDS",
        _DEFAULT_SNAPSHOT_STALE_AFTER_SECONDS,
    )


def _subtract_months(dt: datetime.datetime, months: int) -> datetime.datetime:
    safe_months = max(int(months or 0), 0)
    if safe_months <= 0:
        return dt
    month_index = (dt.month - 1) - safe_months
    year = dt.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _resolve_snapshot_window(
    reference_dt: datetime.datetime | None = None,
) -> tuple[int, int]:
    end_dt = reference_dt or timezone.now()
    begin_dt = _subtract_months(end_dt, _SNAPSHOT_WINDOW_MONTHS)
    return int(begin_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)


def _resolve_time_window_ms(
    update_time_begin: int,
    update_time_end: int,
) -> tuple[int, int]:
    now = timezone.now()
    default_end = int(now.timestamp() * 1000)
    default_begin = int((now - datetime.timedelta(days=30)).timestamp() * 1000)

    begin = int(update_time_begin or 0)
    end = int(update_time_end or 0)
    if begin <= 0:
        begin = default_begin
    if end <= 0:
        end = default_end

    if begin > end:
        begin, end = end, begin
    return begin, end


def _iter_time_chunks(
    begin_ms: int,
    end_ms: int,
    chunk_span_ms: int = _MAX_TIME_SPAN_MS_PER_CHUNK,
):
    if begin_ms > end_ms:
        return
    current_begin = begin_ms
    while current_begin <= end_ms:
        current_end = min(current_begin + chunk_span_ms - 1, end_ms)
        yield current_begin, current_end
        current_begin = current_end + 1


def _build_request_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    token = _clean_text(_get_setting("DTS_STATISTICS_API_TOKEN", ""))
    if token:
        headers["Authorization"] = (
            token if token.lower().startswith("bearer ") else f"Bearer {token}"
        )

    raw_extra = _clean_text(_get_setting("DTS_STATISTICS_API_HEADERS_JSON", ""))
    if raw_extra:
        try:
            parsed = json.loads(raw_extra)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            for key, value in parsed.items():
                text = _clean_text(value)
                if key and text:
                    headers[str(key)] = text
    return headers


def _build_data_lake_payload(
    *,
    page_index: int,
    page_size: int,
    product_id: str,
    update_time_begin: int,
    update_time_end: int,
    flow_states: list[str] | None = None,
    severity_nos: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pageIndex": max(int(page_index or 1), 1),
        "pageSize": max(min(int(page_size or _DATA_LAKE_PAGE_SIZE), _DATA_LAKE_PAGE_SIZE), 1),
        "productId": _clean_text(product_id),
        "updateTimeBegin": int(update_time_begin or 0),
        "updateTimeEnd": int(update_time_end or 0),
        "fields": list(_DEFAULT_FIELDS),
    }
    safe_flow_states = _normalize_text_list(flow_states)
    if safe_flow_states:
        payload["flowStates"] = safe_flow_states
    safe_severity_nos = _normalize_text_list(severity_nos)
    if safe_severity_nos:
        payload["severityNos"] = safe_severity_nos
    return payload


def _mock_fetch_page(payload: dict[str, Any]) -> dict[str, Any]:
    seed_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    rng = random.Random(hashlib.md5(seed_text.encode("utf-8")).hexdigest())

    page_index = max(int(payload.get("pageIndex") or 1), 1)
    page_size = max(min(int(payload.get("pageSize") or _DATA_LAKE_PAGE_SIZE), _DATA_LAKE_PAGE_SIZE), 1)
    total = max(int(_get_setting("DTS_STATISTICS_MOCK_TOTAL", 1200) or 0), 0)
    start = (page_index - 1) * page_size
    end = min(start + page_size, total)

    severity_codes = ["Suggestion", "Minor", "Major", "Critical"]
    severity_names = ["提示", "一般", "严重", "关键"]
    flow_codes = ["DTS010", "FS99", "DTS004", "DTS012"]
    flow_names = {
        "DTS010": "审核人员审核修改",
        "FS99": "关闭",
        "DTS004": "开发人员定位",
        "DTS012": "测试经理组织测试",
    }
    product_id = _clean_text(payload.get("productId")) or "250539396"

    base_dt = timezone.now()
    rows: list[dict[str, Any]] = []
    for index in range(start, end):
        flow_state = rng.choice(flow_codes)
        severity_pos = rng.randint(0, len(severity_codes) - 1)
        create_dt = base_dt - datetime.timedelta(hours=index % (24 * 30))
        update_dt = create_dt + datetime.timedelta(hours=rng.randint(1, 96))
        close_dt = (
            create_dt + datetime.timedelta(hours=rng.randint(4, 72))
            if flow_state == "FS99"
            else None
        )
        rows.append(
            {
                "data": {
                    "dtsBizNo": f"DTS{product_id[-4:]}{index + 1000000}",
                    "briefDesc": f"Mock defect {index + 1}",
                    "dtsStatusName": flow_names.get(flow_state) or flow_state,
                    "serverityNoName": severity_names[severity_pos],
                    "updateAt": update_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "parentNo": f"DTSP{index % 2000:04d}",
                    "createAt": create_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "dCloseTime": close_dt.strftime("%Y-%m-%d %H:%M:%S")
                    if close_dt
                    else None,
                    "uQbiCloseTypeName": (
                        rng.choice(["修复关闭", "重复关闭", "无效关闭", "延期关闭"])
                        if close_dt
                        else None
                    ),
                    "sDeptOneNoName": f"研发{(index % 5) + 1}部",
                    "currentHandler": f"user{(index % 15) + 1}",
                    "creator": f"creator{(index % 10) + 1}",
                    "sSubmitUserName": f"提交人{(index % 10) + 1}",
                    "sSubsystemNoName": f"子系统{(index % 6) + 1}",
                    "sConfigFlowType": rng.choice(["简易", "标准", "复杂"]),
                    "sProdFamilyNoName": f"产品族{(index % 4) + 1}",
                    "sProdXtdNoName": f"产品{(index % 8) + 1}",
                    "iTestBackCount": str(index % 6),
                    "sSuggestByReviewer": f"<p>审核意见 {index + 1}</p>",
                    "sTestReport": f"<p>开发测试报告 {index + 1}</p>",
                    "sTestSuggest": f"<p>测试建议 {index + 1}</p>",
                    "sModifyDocument": f"<ul><li>doc-{index + 1}.md</li></ul>",
                    "sTestorTestReport": f"<p>mock report {index + 1}</p>",
                    "last_dts009_handler": f"dev_user{(index % 10) + 1}",
                    "last_dts010_handler": f"review_user{(index % 10) + 1}",
                    "last_dts013_handler": f"test_user{(index % 10) + 1}",
                    "iNumOfCloseDays": f"{(index % 20) + 1}",
                    "iNumOfFirmDays": f"{(index % 8) + 1}",
                    "iNumOfLocateDays": f"{(index % 6) + 1}",
                    "iNumofModifyDays": f"{(index % 10) + 1}",
                    "iNumofTestDays": f"{(index % 7) + 1}",
                    "dts009ReasonAnalysis": f"<p>原因分析 {index + 1}</p>",
                }
            }
        )

    return {
        "result": {
            "total": total,
            "dataList": rows,
        }
    }


def _fetch_data_lake_page(payload: dict[str, Any]) -> dict[str, Any]:
    if _to_bool(_get_setting("DTS_STATISTICS_FORCE_MOCK", False), False):
        logger.info("DtsStatistics upstream mock forced payload=%s", payload)
        return _mock_fetch_page(payload)

    url = _clean_text(_get_setting("DTS_STATISTICS_API_URL", ""))
    if not url:
        logger.info("DtsStatistics upstream mock request payload=%s", payload)
        return _mock_fetch_page(payload)

    headers = _build_request_headers()
    timeout = float(_get_setting("DTS_STATISTICS_API_TIMEOUT", 15))
    verify = _to_bool(_get_setting("DTS_STATISTICS_API_VERIFY_SSL", True), True)

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout,
            verify=verify,
        )
    except requests.RequestException as exc:
        raise HttpError(502, f"请求数据湖失败: {exc}") from exc

    if response.status_code >= 400:
        raise HttpError(502, f"数据湖响应异常: HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise HttpError(502, "数据湖响应不是合法 JSON") from exc

    if not isinstance(data, dict):
        raise HttpError(502, "数据湖响应格式异常")
    return data


def _extract_page_result(raw: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    result = raw.get("result") or {}
    if not isinstance(result, dict):
        result = {}

    raw_total = result.get("total")
    try:
        total = int(raw_total)
    except Exception:
        total = 0

    data_list = result.get("dataList") or []
    if not isinstance(data_list, list):
        data_list = []

    rows: list[dict[str, Any]] = []
    for item in data_list:
        if not isinstance(item, dict):
            continue
        node = item.get("data") if isinstance(item.get("data"), dict) else item
        if isinstance(node, dict):
            rows.append(node)
    if total <= 0:
        total = len(rows)
    return total, rows


def _wait_for_cache(key: str, *, max_wait_seconds: float = 3.0) -> Any:
    if max_wait_seconds <= 0:
        return None
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        time.sleep(0.3)
        cached = CacheManager.get(key)
        if cached is not None:
            return cached
    return None


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def _parse_dept_path_ids(path: Any) -> list[str]:
    text = _clean_text(path)
    if not text:
        return []
    return [segment.strip() for segment in text.split("/") if segment.strip()]


def _contains_any_keyword(text: Any, keywords: tuple[str, ...]) -> bool:
    content = _clean_text(text)
    if not content:
        return False
    return any(keyword in content for keyword in keywords)


def _merge_duplicate_row_into(
    merged: dict[str, dict[str, Any]],
    row: dict[str, Any],
) -> None:
    if not isinstance(row, dict):
        return
    defect_no = _clean_text(row.get("dtsBizNo"))
    if not defect_no:
        return
    existing = merged.get(defect_no)
    if existing is None:
        current = dict(row)
        current["dtsBizNo"] = defect_no
        merged[defect_no] = current
        return

    existing_update_dt = _parse_datetime(existing.get("updateAt"))
    incoming_update_dt = _parse_datetime(row.get("updateAt"))
    existing_create_dt = _parse_datetime(existing.get("createAt"))
    incoming_create_dt = _parse_datetime(row.get("createAt"))
    should_overlay_primary_fields = False
    if incoming_update_dt and (
        not existing_update_dt or incoming_update_dt > existing_update_dt
    ):
        should_overlay_primary_fields = True
    elif (
        incoming_update_dt == existing_update_dt
        and incoming_create_dt
        and (not existing_create_dt or incoming_create_dt > existing_create_dt)
    ):
        should_overlay_primary_fields = True

    if should_overlay_primary_fields:
        for key, value in row.items():
            if not _is_empty_value(value):
                existing[key] = value

    for key, value in row.items():
        if key not in existing or (
            _is_empty_value(existing.get(key)) and not _is_empty_value(value)
        ):
            existing[key] = value


def _merge_duplicate_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        _merge_duplicate_row_into(merged, row)
    return list(merged.values())


def _fetch_rows_for_time_chunk(
    *,
    product_id: str,
    update_time_begin: int,
    update_time_end: int,
    page_observer: Callable[[int, int, int], None] | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    rows: list[dict[str, Any]] = []
    fetched = 0
    scanned_pages = 0
    total_pages = 0
    max_pages = _resolve_max_scan_pages()

    for page_index in range(1, max_pages + 1):
        payload = _build_data_lake_payload(
            page_index=page_index,
            page_size=_DATA_LAKE_PAGE_SIZE,
            product_id=product_id,
            update_time_begin=update_time_begin,
            update_time_end=update_time_end,
            flow_states=[],
            severity_nos=[],
        )
        raw = _fetch_data_lake_page(payload)
        total, page_rows = _extract_page_result(raw)
        rows.extend(page_rows)
        fetched += len(page_rows)
        scanned_pages = page_index
        if total > 0:
            total_pages = max(total_pages, math.ceil(total / _DATA_LAKE_PAGE_SIZE))
        else:
            total_pages = max(total_pages, page_index)
        if page_observer:
            page_observer(scanned_pages, total_pages, fetched)

        if not page_rows:
            break
        if len(page_rows) < _DATA_LAKE_PAGE_SIZE:
            break
        if total > 0 and fetched >= total:
            break
    else:
        raise HttpError(422, "DTS 扫描页数过多，请缩小筛选范围")

    return rows, scanned_pages, total_pages


def _load_source_rows_cached(
    *,
    product_id: str,
    update_time_begin: int,
    update_time_end: int,
    progress_callback: Callable[[str, int, int, int], None] | None = None,
) -> list[dict[str, Any]]:
    cache_payload = {
        "productId": _clean_text(product_id),
        "updateTimeBegin": int(update_time_begin),
        "updateTimeEnd": int(update_time_end),
        "fields": list(_DEFAULT_FIELDS),
    }
    cache_key, digest = _cache_key(_SOURCE_CACHE_KEY_PREFIX, cache_payload)
    cached = CacheManager.get(cache_key)
    if isinstance(cached, list):
        if progress_callback:
            progress_callback("命中源数据缓存", 70, 0, 0)
        return [item for item in cached if isinstance(item, dict)]

    lock_key = f"{_LOCK_KEY_PREFIX}{digest}"
    lock_ttl = _resolve_cache_ttl(
        "DTS_STATISTICS_SOURCE_LOCK_TTL_SECONDS",
        _DEFAULT_LOCK_TTL_SECONDS,
    )
    lock_acquired = cache.add(lock_key, "1", lock_ttl)
    if not lock_acquired:
        waiting = _wait_for_cache(cache_key)
        if isinstance(waiting, list):
            if progress_callback:
                progress_callback("命中源数据缓存", 70, 0, 0)
            return [item for item in waiting if isinstance(item, dict)]

    ttl = _resolve_cache_ttl(
        "DTS_STATISTICS_SOURCE_CACHE_TTL_SECONDS",
        _DEFAULT_SOURCE_CACHE_TTL_SECONDS,
    )
    try:
        scanned: list[dict[str, Any]] = []
        chunks = list(
            _iter_time_chunks(
                update_time_begin,
                update_time_end,
                _MAX_TIME_SPAN_MS_PER_CHUNK,
            )
        )
        total_chunks = max(len(chunks), 1)
        total_scanned_pages = 0
        total_pages = total_chunks

        for chunk_index, (chunk_begin, chunk_end) in enumerate(chunks, start=1):

            def _observe_chunk_page(
                chunk_scanned_pages: int,
                chunk_total_pages: int,
                _chunk_fetched: int,
            ) -> None:
                if not progress_callback:
                    return
                scanned_pages = total_scanned_pages + max(chunk_scanned_pages, 0)
                known_total_pages = total_scanned_pages + max(
                    chunk_total_pages,
                    chunk_scanned_pages,
                )
                remaining_chunks = max(total_chunks - chunk_index, 0)
                estimated_total_pages = max(
                    known_total_pages + remaining_chunks,
                    scanned_pages,
                )
                phase_ratio = (
                    ((chunk_index - 1) / total_chunks)
                    + (
                        min(
                            chunk_scanned_pages / max(chunk_total_pages, 1),
                            1.0,
                        )
                        / total_chunks
                    )
                )
                progress = min(70, 5 + int(phase_ratio * 65))
                progress_callback(
                    "正在从数据湖拉取数据",
                    progress,
                    scanned_pages,
                    estimated_total_pages,
                )

            chunk_rows, chunk_scanned_pages, chunk_total_pages = _fetch_rows_for_time_chunk(
                product_id=product_id,
                update_time_begin=chunk_begin,
                update_time_end=chunk_end,
                page_observer=_observe_chunk_page,
            )
            scanned.extend(chunk_rows)
            total_scanned_pages += max(chunk_scanned_pages, 0)
            total_pages = max(
                total_pages,
                total_scanned_pages + max(total_chunks - chunk_index, 0),
                total_scanned_pages + max(chunk_total_pages - chunk_scanned_pages, 0),
            )

        merged = _merge_duplicate_rows(scanned)
        if progress_callback:
            progress_callback(
                "数据湖数据拉取完成",
                75,
                total_scanned_pages,
                max(total_pages, total_scanned_pages),
            )
        CacheManager.set(cache_key, merged, ttl)
        return merged
    finally:
        if lock_acquired:
            cache.delete(lock_key)


def _resolve_severity_code(row: dict[str, Any]) -> str:
    code = _clean_text(
        row.get("serverityNo")
        or row.get("severityNo")
    )
    if code:
        return code

    name = _clean_text(
        row.get("serverityNoName")
    )
    if not name:
        return ""
    return _SEVERITY_NAME_TO_CODE.get(name, name)


def _compute_process_days(create_at: Any, close_time: Any) -> str | None:
    create_dt = _parse_datetime(create_at)
    close_dt = _parse_datetime(close_time)
    if not create_dt or not close_dt:
        return None
    delta = close_dt - create_dt
    if delta.total_seconds() < 0:
        return None
    return f"{delta.total_seconds() / 86400:.2f}"


def _normalize_source_row(
    row: dict[str, Any],
    *,
    product_id: str,
) -> dict[str, Any] | None:
    defect_no = _clean_text(row.get("dtsBizNo"))
    if not defect_no:
        return None

    product_name = _PRODUCT_ID_TO_NAME.get(product_id) or product_id
    brief_desc = _clean_text(row.get("briefDesc"))
    status_name = _clean_text(row.get("dtsStatusName"))
    severity_name = _clean_text(row.get("serverityNoName"))
    update_time = _clean_text(row.get("updateAt"))
    create_at = _clean_text(row.get("createAt"))
    close_time = _clean_text(row.get("dCloseTime"))
    close_type_name = _clean_text(row.get("uQbiCloseTypeName"))
    team_name = _clean_text(row.get("sDeptOneNoName"))
    subsystem_name = _clean_text(row.get("sSubsystemNoName"))
    config_flow_type = _clean_text(row.get("sConfigFlowType"))
    close_days = _clean_text(row.get("iNumOfCloseDays"))
    if not close_days:
        close_days = _clean_text(_compute_process_days(create_at, close_time))

    normalized = {
        "dtsBizNo": defect_no,
        "briefDesc": brief_desc or None,
        "dtsStatusName": status_name or None,
        "serverityNoName": severity_name or None,
        "updateAt": update_time or None,
        "parentNo": _clean_text(row.get("parentNo")) or None,
        "createAt": create_at or None,
        "dCloseTime": close_time or None,
        "uQbiCloseTypeName": close_type_name or None,
        "sDeptOneNoName": team_name or None,
        "currentHandler": _clean_text(row.get("currentHandler")) or None,
        "creator": _clean_text(row.get("creator")) or None,
        "sSubmitUserName": _clean_text(row.get("sSubmitUserName")) or None,
        "sSubsystemNoName": subsystem_name or None,
        "sConfigFlowType": config_flow_type or None,
        "sProdFamilyNoName": _clean_text(row.get("sProdFamilyNoName")) or None,
        "sProdXtdNoName": _clean_text(row.get("sProdXtdNoName")) or None,
        "iTestBackCount": _clean_text(row.get("iTestBackCount")) or None,
        "sSuggestByReviewer": _clean_text(row.get("sSuggestByReviewer")) or None,
        "sTestReport": _clean_text(row.get("sTestReport")) or None,
        "sTestSuggest": _clean_text(row.get("sTestSuggest")) or None,
        "sModifyDocument": _clean_text(row.get("sModifyDocument")) or None,
        "sTestorTestReport": _clean_text(row.get("sTestorTestReport")) or None,
        "last_dts009_handler": _clean_text(row.get("last_dts009_handler")) or None,
        "last_dts010_handler": _clean_text(row.get("last_dts010_handler")) or None,
        "last_dts013_handler": _clean_text(row.get("last_dts013_handler")) or None,
        "iNumOfCloseDays": close_days or None,
        "iNumOfFirmDays": _clean_text(row.get("iNumOfFirmDays")) or None,
        "iNumOfLocateDays": _clean_text(
            row.get("iNumOfLocateDays") or row.get("iNumofLocateDays")
        )
        or None,
        "iNumofModifyDays": _clean_text(row.get("iNumofModifyDays")) or None,
        "iNumofTestDays": _clean_text(row.get("iNumofTestDays")) or None,
        "dts009ReasonAnalysis": _clean_text(row.get("dts009ReasonAnalysis"))
        or None,
        # helper fields
        "serverityNo": _resolve_severity_code(row) or None,
        "productId": product_id,
        "productName": product_name,
        "auto_source_type": None,
        "auto_pl_group_id": None,
        "auto_pl_group_name": None,
    }
    return normalized


def _load_users_by_username(usernames: Iterable[str]) -> dict[str, User]:
    unique_usernames = _normalize_text_list(list(usernames))
    if not unique_usernames:
        return {}
    users = (
        User.objects.filter(username__in=unique_usernames)
        .select_related("dept")
        .only(
            "id",
            "username",
            "name",
            "dept_id",
            "dept__id",
            "dept__name",
            "dept__path",
            "dept__parent_id",
        )
        .all()
    )
    return {_clean_text(item.username): item for item in users if _clean_text(item.username)}


def _load_dept_map_for_users(users: Iterable[User]) -> dict[str, Dept]:
    pending_ids = {
        str(item.dept_id)
        for item in users
        if getattr(item, "dept_id", None)
    }
    dept_map: dict[str, Dept] = {}
    while pending_ids:
        batch_ids = {dept_id for dept_id in pending_ids if dept_id not in dept_map}
        if not batch_ids:
            break
        current_items = list(
            Dept.objects.filter(id__in=batch_ids)
            .only("id", "name", "path", "parent_id")
            .all()
        )
        pending_ids = set()
        for item in current_items:
            dept_map[str(item.id)] = item
        for item in current_items:
            if item.parent_id and str(item.parent_id) not in dept_map:
                pending_ids.add(str(item.parent_id))
            for ancestor_id in _parse_dept_path_ids(item.path):
                if ancestor_id not in dept_map:
                    pending_ids.add(ancestor_id)
    return dept_map


def _build_dept_base_soft_flag_map(
    users_by_username: dict[str, User],
) -> dict[str, bool]:
    dept_map = _load_dept_map_for_users(users_by_username.values())
    memo: dict[str, bool] = {}

    def _match_dept(dept_id: str | None) -> bool:
        safe_dept_id = _clean_text(dept_id)
        if not safe_dept_id:
            return False
        cached = memo.get(safe_dept_id)
        if cached is not None:
            return cached
        dept = dept_map.get(safe_dept_id)
        if dept is None:
            memo[safe_dept_id] = False
            return False
        if _clean_text(dept.name) == _BASE_SOFT_DEPT_NAME:
            memo[safe_dept_id] = True
            return True

        related_ids = []
        if dept.parent_id:
            related_ids.append(str(dept.parent_id))
        related_ids.extend(_parse_dept_path_ids(dept.path))
        for related_id in related_ids:
            if related_id == safe_dept_id:
                continue
            if _match_dept(related_id):
                memo[safe_dept_id] = True
                return True
        memo[safe_dept_id] = False
        return False

    return {
        username: _match_dept(str(user.dept_id) if user.dept_id else "")
        for username, user in users_by_username.items()
    }


def _load_auto_pl_group_by_username(
    usernames: Iterable[str],
) -> dict[str, tuple[str | None, str]]:
    unique_usernames = _normalize_text_list(list(usernames))
    if not unique_usernames:
        return {}

    rows = (
        PlGroup.objects.filter(status=True, members__username__in=unique_usernames)
        .values("id", "name", "sort", "members__username")
        .order_by("-sort", "name", "id")
    )

    mapping: dict[str, tuple[str | None, str]] = {}
    for row in rows:
        username = _clean_text(row.get("members__username"))
        if not username or username in mapping:
            continue
        mapping[username] = (
            str(row.get("id")) if row.get("id") is not None else None,
            _clean_text(row.get("name")) or _AUTO_PL_GROUP_UNKNOWN,
        )
    return mapping


def _resolve_auto_source_type(row: dict[str, Any]) -> str:
    team_name = _clean_text(row.get("sDeptOneNoName"))
    brief_desc = _clean_text(row.get("briefDesc"))
    if team_name != _BASE_SOFT_DEPT_NAME:
        return _AUTO_SOURCE_EXTERNAL
    if _BASE_SOFT_TEST_KEYWORD in brief_desc:
        return _AUTO_SOURCE_TEST
    return _AUTO_SOURCE_DEV


def _filter_and_enrich_snapshot_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    usernames = [
        _clean_text(item.get("last_dts009_handler"))
        for item in rows
        if _clean_text(item.get("last_dts009_handler"))
    ]
    users_by_username = _load_users_by_username(usernames)
    dept_flag_by_username = _build_dept_base_soft_flag_map(users_by_username)
    auto_pl_group_by_username = _load_auto_pl_group_by_username(usernames)

    counters = {
        "merged_total": len(rows),
        "brief_filtered": 0,
        "dept_filtered": 0,
        "final_total": 0,
    }
    result: list[dict[str, Any]] = []

    for row in rows:
        if _contains_any_keyword(row.get("briefDesc"), _BRIEF_DESC_EXCLUDED_KEYWORDS):
            counters["brief_filtered"] += 1
            continue

        handler_username = _clean_text(row.get("last_dts009_handler"))
        matched_user = users_by_username.get(handler_username)
        if matched_user is not None and not dept_flag_by_username.get(handler_username, False):
            counters["dept_filtered"] += 1
            continue

        auto_pl_group_id = None
        auto_pl_group_name = _AUTO_PL_GROUP_UNKNOWN
        if handler_username:
            auto_pl_group_id, auto_pl_group_name = auto_pl_group_by_username.get(
                handler_username,
                (None, _AUTO_PL_GROUP_UNKNOWN),
            )

        enriched = dict(row)
        enriched["auto_source_type"] = _resolve_auto_source_type(row)
        enriched["auto_pl_group_id"] = auto_pl_group_id
        enriched["auto_pl_group_name"] = auto_pl_group_name
        result.append(enriched)

    counters["final_total"] = len(result)
    return result, counters


def _apply_source_filters(
    rows: list[dict[str, Any]],
    *,
    flow_states: list[str],
    severity_nos: list[str],
) -> list[dict[str, Any]]:
    flow_set = {item.upper() for item in _normalize_text_list(flow_states)}
    severity_set = {item.lower() for item in _normalize_text_list(severity_nos)}
    if not flow_set and not severity_set:
        return rows

    result: list[dict[str, Any]] = []
    for row in rows:
        flow_codes: set[str] = set()
        status_name = _clean_text(row.get("dtsStatusName"))
        if status_name in _FLOW_STATE_NAME_TO_CODES:
            flow_codes.update(_FLOW_STATE_NAME_TO_CODES[status_name])
        upper_status = status_name.upper()
        if upper_status:
            flow_codes.add(upper_status)

        if flow_set and not flow_codes.intersection(flow_set):
            continue

        row_severity_code = _clean_text(_resolve_severity_code(row)).lower()
        if severity_set and row_severity_code not in severity_set:
            continue
        result.append(row)
    return result


def _sort_defects(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]):
        dt = _parse_datetime(item.get("createAt"))
        safe_dt = dt or _runtime_min_datetime()
        defect_no = _clean_text(item.get("dtsBizNo"))
        return safe_dt, defect_no

    return sorted(items, key=sort_key, reverse=True)


def _paginate(items: list[dict[str, Any]], page_index: int, page_size: int) -> tuple[int, list[dict[str, Any]]]:
    safe_page_index = max(int(page_index or 1), 1)
    safe_page_size = max(int(page_size or 20), 1)
    safe_page_size = min(safe_page_size, 500)
    total = len(items)
    start = max(safe_page_index - 1, 0) * safe_page_size
    end = start + safe_page_size
    return total, items[start:end]


def _load_extensions(defect_nos: list[str]) -> dict[str, DtsExtension]:
    if not defect_nos:
        return {}
    qs = (
        DtsExtension.objects.filter(defect_no__in=defect_nos)
        .select_related("pl_group", "dev_owner", "test_owner")
        .all()
    )
    return {item.defect_no: item for item in qs}


def _merge_defect_with_extension(
    defect: dict[str, Any],
    *,
    extension: DtsExtension | None,
) -> dict[str, Any]:
    merged = dict(defect)
    defect_no = _clean_text(merged.get("dtsBizNo"))
    merged["dtsBizNo"] = defect_no

    if extension is None:
        merged.update(
            {
                "qa_category": None,
                "pl_group_id": None,
                "pl_group_name": None,
                "is_downstream": None,
                "process_quality_type": None,
                "need_dev_analyze": None,
                "need_test_analyze": None,
                "dev_owner_id": None,
                "dev_owner_name": None,
                "test_owner_id": None,
                "test_owner_name": None,
                "is_dev_analyzed": None,
                "is_test_analyzed": None,
                "qa_remark": None,
                "dev_sub_category": [],
                "dev_reason": None,
                "dev_intro_reason": None,
                "dev_improvements": [],
                "dev_non_base_desc": [],
                "dev_asset_link": None,
                "dev_status": None,
                "test_feature": None,
                "test_miss_reason": [],
                "test_standard_desc": None,
                "test_improvements": [],
                "test_non_test_desc": None,
                "test_asset_link": None,
                "test_status": None,
            }
        )
        return merged

    merged["qa_category"] = extension.qa_category
    merged["pl_group_id"] = extension.pl_group_id
    merged["pl_group_name"] = extension.pl_group.name if extension.pl_group else None
    merged["is_downstream"] = extension.is_downstream
    merged["process_quality_type"] = extension.process_quality_type
    merged["need_dev_analyze"] = extension.need_dev_analyze
    merged["need_test_analyze"] = extension.need_test_analyze
    merged["dev_owner_id"] = extension.dev_owner_id
    merged["dev_owner_name"] = (
        extension.dev_owner.name or extension.dev_owner.username
        if extension.dev_owner
        else None
    )
    merged["test_owner_id"] = extension.test_owner_id
    merged["test_owner_name"] = (
        extension.test_owner.name or extension.test_owner.username
        if extension.test_owner
        else None
    )
    merged["is_dev_analyzed"] = extension.is_dev_analyzed
    merged["is_test_analyzed"] = extension.is_test_analyzed
    merged["qa_remark"] = extension.qa_remark

    merged["dev_sub_category"] = extension.dev_sub_category or []
    merged["dev_reason"] = extension.dev_reason
    merged["dev_intro_reason"] = extension.dev_intro_reason
    merged["dev_improvements"] = extension.dev_improvements or []
    merged["dev_non_base_desc"] = extension.dev_non_base_desc or []
    merged["dev_asset_link"] = extension.dev_asset_link
    merged["dev_status"] = extension.dev_status

    merged["test_feature"] = extension.test_feature
    merged["test_miss_reason"] = extension.test_miss_reason or []
    merged["test_standard_desc"] = extension.test_standard_desc
    merged["test_improvements"] = extension.test_improvements or []
    merged["test_non_test_desc"] = extension.test_non_test_desc
    merged["test_asset_link"] = extension.test_asset_link
    merged["test_status"] = extension.test_status
    return merged


def _normalize_optional_time_range(begin: int, end: int) -> tuple[int, int]:
    safe_begin = max(int(begin or 0), 0)
    safe_end = max(int(end or 0), 0)
    if safe_begin and safe_end and safe_begin > safe_end:
        return safe_end, safe_begin
    return safe_begin, safe_end


def _resolve_base_runtime_filters(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
) -> tuple[str, list[str], list[str], int, int]:
    product_id = _clean_text(getattr(query, "productId", "")) or "250539396"
    flow_states = _normalize_text_list(getattr(query, "flowStates", []))
    severity_nos = _normalize_text_list(getattr(query, "severityNos", []))
    update_time_begin, update_time_end = _resolve_time_window_ms(
        int(getattr(query, "updateTimeBegin", 0) or 0),
        int(getattr(query, "updateTimeEnd", 0) or 0),
    )
    return product_id, flow_states, severity_nos, update_time_begin, update_time_end


def _resolve_local_runtime_filters(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
) -> dict[str, Any]:
    create_at_begin, create_at_end = _normalize_optional_time_range(
        int(getattr(query, "createAtBegin", 0) or 0),
        int(getattr(query, "createAtEnd", 0) or 0),
    )
    close_time_begin, close_time_end = _normalize_optional_time_range(
        int(getattr(query, "dCloseTimeBegin", 0) or 0),
        int(getattr(query, "dCloseTimeEnd", 0) or 0),
    )
    return {
        "dtsBizNoKeyword": _clean_text(getattr(query, "dtsBizNoKeyword", "")),
        "last_dts009_handlerKeywords": _normalize_text_list(
            getattr(query, "last_dts009_handlerKeywords", [])
        ),
        "createAtBegin": create_at_begin,
        "createAtEnd": create_at_end,
        "dCloseTimeBegin": close_time_begin,
        "dCloseTimeEnd": close_time_end,
        "sDeptOneNoNames": _normalize_text_list(getattr(query, "sDeptOneNoNames", [])),
        "sSubsystemNoNames": _normalize_text_list(
            getattr(query, "sSubsystemNoNames", [])
        ),
        "sConfigFlowTypes": _normalize_text_list(
            getattr(query, "sConfigFlowTypes", [])
        ),
        "auto_pl_group_names": _normalize_text_list(
            getattr(query, "auto_pl_group_names", [])
        ),
        "uQbiCloseTypeNames": _normalize_text_list(
            getattr(query, "uQbiCloseTypeNames", [])
        ),
    }


def _to_export_query_schema(
    data: DtsStatisticsQuerySchema | DtsStatisticsExportSchema | dict[str, Any],
) -> DtsStatisticsExportSchema:
    if isinstance(data, DtsStatisticsExportSchema):
        return data
    if isinstance(data, DtsStatisticsQuerySchema):
        return DtsStatisticsExportSchema(**data.dict())
    payload = data.dict() if hasattr(data, "dict") else dict(data or {})
    return DtsStatisticsExportSchema(**payload)


def _build_base_filter_payload(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
) -> dict[str, Any]:
    product_id, flow_states, severity_nos, update_time_begin, update_time_end = (
        _resolve_base_runtime_filters(query)
    )
    return {
        "productId": product_id,
        "flowStates": flow_states,
        "severityNos": severity_nos,
        "updateTimeBegin": update_time_begin,
        "updateTimeEnd": update_time_end,
        "fields": list(_DEFAULT_FIELDS),
    }


def _build_export_task_payload(query: DtsStatisticsExportSchema) -> dict[str, Any]:
    return query.dict()


def _resolve_prepared_cache_identity(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    user: Any = None,
) -> tuple[dict[str, Any], str, str]:
    payload = _build_base_filter_payload(query)
    fingerprint = _fingerprint_payload(payload)
    cache_key = _get_prepared_cache_key(fingerprint, user=user)
    return payload, fingerprint, cache_key


def _get_prepared_defects_by_cache_key(cache_key: str) -> list[dict[str, Any]] | None:
    cached = CacheManager.get(cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("defects"), list):
        return [item for item in cached["defects"] if isinstance(item, dict)]
    if isinstance(cached, list):
        return [item for item in cached if isinstance(item, dict)]
    return None


def _get_prepared_defects(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    user: Any = None,
) -> list[dict[str, Any]] | None:
    if not user or not getattr(user, "id", None):
        return None
    _, _, cache_key = _resolve_prepared_cache_identity(query, user=user)
    return _get_prepared_defects_by_cache_key(cache_key)


def _set_prepared_defects(cache_key: str, defects: list[dict[str, Any]]) -> None:
    CacheManager.set(
        cache_key,
        {
            "defects": defects,
        },
        _resolve_prepared_cache_ttl_seconds(),
    )


def _get_active_query_task(
    user: Any,
    fingerprint: str,
) -> DtsStatisticsQueryTask | None:
    if not user or not getattr(user, "id", None):
        return None
    return (
        DtsStatisticsQueryTask.objects.filter(
            user=user,
            fingerprint=fingerprint,
            status__in=_QUERY_TASK_ACTIVE_STATUSES,
            is_deleted=False,
        )
        .order_by("-sys_create_datetime")
        .first()
    )


def _get_active_export_task(
    user: Any,
    fingerprint: str,
) -> DtsStatisticsExportTask | None:
    if not user or not getattr(user, "id", None):
        return None
    return (
        DtsStatisticsExportTask.objects.filter(
            user=user,
            fingerprint=fingerprint,
            status__in=_EXPORT_TASK_ACTIVE_STATUSES,
            is_deleted=False,
        )
        .order_by("-sys_create_datetime")
        .first()
    )


def _is_export_task_expired(task: DtsStatisticsExportTask) -> bool:
    finished_at = task.finished_at
    if finished_at is None:
        return False
    expire_at = finished_at + datetime.timedelta(
        seconds=_resolve_export_file_ttl_seconds()
    )
    return timezone.now() > expire_at


def _is_export_task_downloadable(task: DtsStatisticsExportTask) -> bool:
    if task.status != DtsStatisticsExportTask.STATUS_SUCCESS:
        return False
    file_path = _clean_text(task.file_path)
    if not file_path:
        return False
    if _is_export_task_expired(task):
        return False
    return Path(file_path).is_file()


def _cleanup_expired_export_files(limit: int = 100) -> None:
    ttl_seconds = _resolve_export_file_ttl_seconds()
    expire_before = timezone.now() - datetime.timedelta(seconds=ttl_seconds)
    stale_tasks = (
        DtsStatisticsExportTask.objects.filter(
            status=DtsStatisticsExportTask.STATUS_SUCCESS,
            is_deleted=False,
            finished_at__lt=expire_before,
        )
        .order_by("finished_at")[: max(int(limit or 0), 1)]
    )

    for task in stale_tasks:
        file_path = _clean_text(task.file_path)
        if file_path:
            try:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
            except Exception:
                logger.warning(
                    "DtsStatistics cleanup export file failed task_id=%s file=%s",
                    task.id,
                    file_path,
                    exc_info=True,
                )
        DtsStatisticsExportTask.objects.filter(id=task.id).update(
            file_path="",
            file_name="",
            file_size=0,
        )


def _get_reusable_export_task(
    user: Any,
    fingerprint: str,
) -> DtsStatisticsExportTask | None:
    if not user or not getattr(user, "id", None):
        return None
    task = (
        DtsStatisticsExportTask.objects.filter(
            user=user,
            fingerprint=fingerprint,
            status=DtsStatisticsExportTask.STATUS_SUCCESS,
            is_deleted=False,
        )
        .order_by("-finished_at", "-sys_create_datetime")
        .first()
    )
    if task is None:
        return None
    if not _is_export_task_downloadable(task):
        return None
    return task


def _load_filtered_defects(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    progress_callback: Callable[[str, int, int, int], None] | None = None,
) -> list[dict[str, Any]]:
    product_id, flow_states, severity_nos, update_time_begin, update_time_end = (
        _resolve_base_runtime_filters(query)
    )
    if progress_callback:
        progress_callback("正在准备源数据", 2, 0, 0)
    source_rows = _load_source_rows_cached(
        product_id=product_id,
        update_time_begin=update_time_begin,
        update_time_end=update_time_end,
        progress_callback=progress_callback,
    )

    if progress_callback:
        progress_callback("正在标准化数据", 80, 0, 0)
    normalized_rows: list[dict[str, Any]] = []
    for row in source_rows:
        normalized = _normalize_source_row(row, product_id=product_id)
        if normalized:
            normalized_rows.append(normalized)

    if progress_callback:
        progress_callback("正在应用筛选条件", 90, 0, 0)
    filtered_rows = _apply_source_filters(
        normalized_rows,
        flow_states=flow_states,
        severity_nos=severity_nos,
    )
    sorted_rows = _sort_defects(filtered_rows)
    if progress_callback:
        progress_callback("查询数据准备完成", 98, 0, 0)
    return sorted_rows


def _match_time_range(value: Any, begin: int, end: int) -> bool:
    if begin <= 0 and end <= 0:
        return True
    dt = _parse_datetime(value)
    if dt is None:
        return False
    ts = int(dt.timestamp() * 1000)
    if begin > 0 and ts < begin:
        return False
    if end > 0 and ts > end:
        return False
    return True


def _match_keyword_like(value: Any, keyword: str) -> bool:
    normalized_keyword = _clean_text(keyword).lower()
    if not normalized_keyword:
        return True
    return normalized_keyword in _clean_text(value).lower()


def _match_any_keyword_like(value: Any, keywords: list[str]) -> bool:
    normalized_keywords = _normalize_text_list(keywords)
    if not normalized_keywords:
        return True
    return any(_match_keyword_like(value, keyword) for keyword in normalized_keywords)


def _apply_local_filters(
    rows: list[dict[str, Any]],
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    ignored_fields: set[str] | None = None,
) -> list[dict[str, Any]]:
    ignored = ignored_fields or set()
    local_filters = _resolve_local_runtime_filters(query)
    dts_biz_no_keyword = (
        "" if "dtsBizNo" in ignored else _clean_text(local_filters["dtsBizNoKeyword"])
    )
    last_dts009_handler_keywords = (
        []
        if "last_dts009_handler" in ignored
        else _normalize_text_list(local_filters["last_dts009_handlerKeywords"])
    )
    create_at_begin = (
        0 if "createAt" in ignored else int(local_filters["createAtBegin"] or 0)
    )
    create_at_end = (
        0 if "createAt" in ignored else int(local_filters["createAtEnd"] or 0)
    )
    close_time_begin = (
        0 if "dCloseTime" in ignored else int(local_filters["dCloseTimeBegin"] or 0)
    )
    close_time_end = (
        0 if "dCloseTime" in ignored else int(local_filters["dCloseTimeEnd"] or 0)
    )
    dept_values = set() if "sDeptOneNoName" in ignored else {
        item for item in _normalize_text_list(local_filters["sDeptOneNoNames"]) if item
    }
    subsystem_values = set() if "sSubsystemNoName" in ignored else {
        item
        for item in _normalize_text_list(local_filters["sSubsystemNoNames"])
        if item
    }
    config_flow_type_values = set() if "sConfigFlowType" in ignored else {
        item
        for item in _normalize_text_list(local_filters["sConfigFlowTypes"])
        if item and item in _ALLOWED_CONFIG_FLOW_TYPES
    }
    auto_pl_group_values = set() if "auto_pl_group_name" in ignored else {
        item
        for item in _normalize_text_list(local_filters["auto_pl_group_names"])
        if item
    }
    close_type_values = set() if "uQbiCloseTypeName" in ignored else {
        item
        for item in _normalize_text_list(local_filters["uQbiCloseTypeNames"])
        if item
    }

    result: list[dict[str, Any]] = []
    for row in rows:
        config_flow_type = _clean_text(row.get("sConfigFlowType"))
        if config_flow_type not in _ALLOWED_CONFIG_FLOW_TYPES:
            continue
        if (
            config_flow_type_values
            and config_flow_type not in config_flow_type_values
        ):
            continue
        if not _match_keyword_like(row.get("dtsBizNo"), dts_biz_no_keyword):
            continue
        if not _match_any_keyword_like(
            row.get("last_dts009_handler"),
            last_dts009_handler_keywords,
        ):
            continue
        if not _match_time_range(row.get("createAt"), create_at_begin, create_at_end):
            continue
        if not _match_time_range(
            row.get("dCloseTime"),
            close_time_begin,
            close_time_end,
        ):
            continue
        if dept_values and _clean_text(row.get("sDeptOneNoName")) not in dept_values:
            continue
        if subsystem_values and _clean_text(row.get("sSubsystemNoName")) not in subsystem_values:
            continue
        if (
            auto_pl_group_values
            and _clean_text(row.get("auto_pl_group_name")) not in auto_pl_group_values
        ):
            continue
        if close_type_values and _clean_text(row.get("uQbiCloseTypeName")) not in close_type_values:
            continue
        result.append(row)
    return result


def _ensure_supported_product_id(product_id: str) -> str:
    safe_product_id = _clean_text(product_id) or "250539396"
    if safe_product_id not in _SUPPORTED_PRODUCT_IDS:
        raise HttpError(422, "“全部”产品暂不支持查询，请选择座舱或车控")
    return safe_product_id


def _get_snapshot_meta(product_id: str) -> dict[str, Any] | None:
    cached = CacheManager.get(_snapshot_meta_key(product_id))
    if isinstance(cached, dict):
        return cached
    return None


def _cleanup_snapshot_version(meta: dict[str, Any] | None) -> None:
    if not isinstance(meta, dict):
        return
    product_id = _clean_text(meta.get("productId"))
    version = _clean_text(meta.get("version"))
    chunk_count = max(int(meta.get("chunkCount") or 0), 0)
    if not product_id or not version:
        return
    for chunk_index in range(chunk_count):
        CacheManager.delete(_snapshot_chunk_key(product_id, version, chunk_index))
    CacheManager.delete(_snapshot_field_set_key(product_id, version))


def _build_snapshot_field_sets(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    field_sets: dict[str, list[str]] = {}
    for field in _FIELD_SET_SUPPORTED_FIELDS:
        values = {
            _clean_text(item.get(field))
            for item in rows
            if _clean_text(item.get(field))
        }
        if field == "sConfigFlowType":
            values = {
                value for value in values if value in _ALLOWED_CONFIG_FLOW_TYPES
            }
        field_sets[field] = sorted(values)
    return field_sets


def _write_snapshot_payload(
    *,
    product_id: str,
    rows: list[dict[str, Any]],
    generated_at: datetime.datetime,
    window_begin: int,
    window_end: int,
) -> dict[str, Any]:
    ttl = _resolve_snapshot_cache_ttl_seconds()
    chunk_size = _resolve_snapshot_chunk_size()
    version_seed = f"{product_id}:{generated_at.isoformat()}:{len(rows)}"
    version = (
        f"{generated_at.strftime('%Y%m%d%H%M%S')}-"
        f"{hashlib.md5(version_seed.encode('utf-8')).hexdigest()[:8]}"
    )
    field_set_key = _snapshot_field_set_key(product_id, version)
    created_chunk_indexes: list[int] = []
    try:
        for chunk_index, chunk in enumerate(_iter_chunks(rows, chunk_size)):
            CacheManager.set(
                _snapshot_chunk_key(product_id, version, chunk_index),
                chunk,
                ttl,
            )
            created_chunk_indexes.append(chunk_index)
        CacheManager.set(field_set_key, _build_snapshot_field_sets(rows), ttl)
        meta = {
            "productId": product_id,
            "productName": _PRODUCT_ID_TO_NAME.get(product_id) or product_id,
            "version": version,
            "generatedAt": generated_at.isoformat(),
            "windowBegin": int(window_begin or 0),
            "windowEnd": int(window_end or 0),
            "rowCount": len(rows),
            "chunkCount": len(created_chunk_indexes),
            "isStale": False,
        }
        previous_meta = _get_snapshot_meta(product_id)
        CacheManager.set(_snapshot_meta_key(product_id), meta, ttl)
        if previous_meta and _clean_text(previous_meta.get("version")) != version:
            _cleanup_snapshot_version(previous_meta)
        return meta
    except Exception:
        for chunk_index in created_chunk_indexes:
            CacheManager.delete(_snapshot_chunk_key(product_id, version, chunk_index))
        CacheManager.delete(field_set_key)
        raise


def _mark_snapshot_stale(product_id: str) -> None:
    meta = _get_snapshot_meta(product_id)
    serialized = _serialize_snapshot_meta(meta)
    if meta is None or serialized is None:
        return
    next_meta = {
        **meta,
        "isStale": True,
        "generatedAt": serialized.get("generatedAt"),
        "windowBegin": serialized.get("windowBegin"),
        "windowEnd": serialized.get("windowEnd"),
        "rowCount": serialized.get("rowCount"),
    }
    CacheManager.set(
        _snapshot_meta_key(product_id),
        next_meta,
        _resolve_snapshot_cache_ttl_seconds(),
    )


def _load_snapshot_rows(meta: dict[str, Any]) -> list[dict[str, Any]]:
    product_id = _clean_text(meta.get("productId"))
    version = _clean_text(meta.get("version"))
    chunk_count = max(int(meta.get("chunkCount") or 0), 0)
    if not product_id or not version:
        raise HttpError(503, "DTS 快照元数据异常，请重新执行同步任务")
    rows: list[dict[str, Any]] = []
    for chunk_index in range(chunk_count):
        chunk = CacheManager.get(_snapshot_chunk_key(product_id, version, chunk_index))
        if chunk is None:
            raise HttpError(503, "DTS 快照数据缺失，请重新执行同步任务")
        if not isinstance(chunk, list):
            continue
        rows.extend(item for item in chunk if isinstance(item, dict))
    return rows


def _validate_snapshot_query_window(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    snapshot: dict[str, Any],
) -> None:
    _, _, _, update_time_begin, update_time_end = _resolve_base_runtime_filters(query)
    window_begin = max(int(snapshot.get("windowBegin") or 0), 0)
    window_end = max(int(snapshot.get("windowEnd") or 0), 0)
    if window_begin <= 0 or window_end <= 0:
        raise HttpError(503, "DTS 快照时间窗口异常，请重新执行同步任务")
    if update_time_begin > 0 and update_time_begin < window_begin:
        raise HttpError(422, "当前仅支持最近 2 个月更新时间数据")
    if update_time_end > 0 and update_time_end < window_begin:
        raise HttpError(422, "当前筛选时间早于缓存窗口，请调整到最近 2 个月内")
    if update_time_begin > 0 and update_time_begin > window_end:
        raise HttpError(422, "当前筛选时间晚于最近一次同步快照，请稍后重试")


def _build_filtered_result_payload(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    snapshot_version: str,
    ignored_fields: set[str] | None = None,
) -> dict[str, Any]:
    ignored = ignored_fields or set()
    product_id, flow_states, severity_nos, update_time_begin, update_time_end = (
        _resolve_base_runtime_filters(query)
    )
    local_filters = _resolve_local_runtime_filters(query)
    if "flowStates" in ignored:
        flow_states = []
    if "severityNos" in ignored:
        severity_nos = []
    if "updateAt" in ignored:
        update_time_begin = 0
        update_time_end = 0
    dts_biz_no_keyword = (
        "" if "dtsBizNo" in ignored else _clean_text(local_filters["dtsBizNoKeyword"])
    )
    last_dts009_handler_keywords = (
        []
        if "last_dts009_handler" in ignored
        else _normalize_text_list(local_filters["last_dts009_handlerKeywords"])
    )
    if "createAt" in ignored:
        local_filters["createAtBegin"] = 0
        local_filters["createAtEnd"] = 0
    if "dCloseTime" in ignored:
        local_filters["dCloseTimeBegin"] = 0
        local_filters["dCloseTimeEnd"] = 0
    if "sDeptOneNoName" in ignored:
        local_filters["sDeptOneNoNames"] = []
    if "sSubsystemNoName" in ignored:
        local_filters["sSubsystemNoNames"] = []
    if "sConfigFlowType" in ignored:
        local_filters["sConfigFlowTypes"] = []
    if "auto_pl_group_name" in ignored:
        local_filters["auto_pl_group_names"] = []
    if "uQbiCloseTypeName" in ignored:
        local_filters["uQbiCloseTypeNames"] = []
    return {
        "snapshotVersion": _clean_text(snapshot_version),
        "productId": product_id,
        "flowStates": flow_states,
        "severityNos": severity_nos,
        "updateTimeBegin": update_time_begin,
        "updateTimeEnd": update_time_end,
        "dtsBizNoKeyword": dts_biz_no_keyword,
        "last_dts009_handlerKeywords": last_dts009_handler_keywords,
        "createAtBegin": int(local_filters.get("createAtBegin") or 0),
        "createAtEnd": int(local_filters.get("createAtEnd") or 0),
        "dCloseTimeBegin": int(local_filters.get("dCloseTimeBegin") or 0),
        "dCloseTimeEnd": int(local_filters.get("dCloseTimeEnd") or 0),
        "sDeptOneNoNames": _normalize_text_list(local_filters.get("sDeptOneNoNames")),
        "sSubsystemNoNames": _normalize_text_list(
            local_filters.get("sSubsystemNoNames")
        ),
        "sConfigFlowTypes": _normalize_text_list(
            local_filters.get("sConfigFlowTypes")
        ),
        "auto_pl_group_names": _normalize_text_list(
            local_filters.get("auto_pl_group_names")
        ),
        "uQbiCloseTypeNames": _normalize_text_list(
            local_filters.get("uQbiCloseTypeNames")
        ),
        "ignoredFields": sorted(ignored),
    }


def _apply_snapshot_filters(
    rows: list[dict[str, Any]],
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    ignored_fields: set[str] | None = None,
) -> list[dict[str, Any]]:
    ignored = ignored_fields or set()
    _, flow_states, severity_nos, update_time_begin, update_time_end = (
        _resolve_base_runtime_filters(query)
    )
    filtered = rows
    if "updateAt" not in ignored and (update_time_begin > 0 or update_time_end > 0):
        filtered = [
            row
            for row in filtered
            if _match_time_range(row.get("updateAt"), update_time_begin, update_time_end)
        ]
    filtered = _apply_source_filters(
        filtered,
        flow_states=[] if "flowStates" in ignored else flow_states,
        severity_nos=[] if "severityNos" in ignored else severity_nos,
    )
    filtered = _apply_local_filters(filtered, query, ignored_fields=ignored)
    return _sort_defects(filtered)


def _get_snapshot_rows_for_query(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
) -> tuple[dict[str, Any], dict[str, Any]]:
    product_id = _ensure_supported_product_id(getattr(query, "productId", ""))
    raw_meta = _get_snapshot_meta(product_id)
    if raw_meta is None:
        raise HttpError(409, "DTS 快照数据准备中，请先执行同步任务")
    snapshot = _serialize_snapshot_meta(raw_meta)
    if snapshot is None:
        raise HttpError(503, "DTS 快照元数据异常，请重新执行同步任务")
    _validate_snapshot_query_window(query, snapshot)
    return raw_meta, snapshot


def _get_filtered_snapshot_rows(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    ignored_fields: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_meta, snapshot = _get_snapshot_rows_for_query(query)
    payload = _build_filtered_result_payload(
        query,
        snapshot_version=_clean_text(snapshot.get("version")),
        ignored_fields=ignored_fields,
    )
    cache_key, _ = _cache_key(_FILTERED_RESULT_CACHE_KEY_PREFIX, payload)
    cached = CacheManager.get(cache_key)
    if isinstance(cached, list):
        return [item for item in cached if isinstance(item, dict)], snapshot
    rows = _load_snapshot_rows(raw_meta)
    filtered = _apply_snapshot_filters(rows, query, ignored_fields=ignored_fields)
    CacheManager.set(
        cache_key,
        filtered,
        _resolve_filtered_result_cache_ttl_seconds(),
    )
    return filtered, snapshot


def _resolve_runtime_defects(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    user: Any = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    del user
    return _get_filtered_snapshot_rows(query)


def _collect_field_set_values(
    defects: list[dict[str, Any]],
    field: str,
) -> list[str]:
    values = sorted(
        {
            _clean_text(item.get(field))
            for item in defects
            if _clean_text(item.get(field))
        }
    )
    return values


def get_dts_statistics_field_sets(
    data: DtsFieldSetRequestSchema,
    *,
    user: Any = None,
) -> dict[str, Any]:
    del user
    requested_fields = _normalize_text_list(getattr(data, "fields", []))
    if not requested_fields:
        return {"fieldSets": {}}

    unsupported_fields = [
        field for field in requested_fields if field not in _FIELD_SET_SUPPORTED_FIELDS
    ]
    if unsupported_fields:
        raise HttpError(422, f"暂不支持的字段集合请求: {', '.join(unsupported_fields)}")

    field_sets: dict[str, list[str]] = {}
    for field in requested_fields:
        scoped_defects, _snapshot = _get_filtered_snapshot_rows(
            data,
            ignored_fields={field},
        )
        field_sets[field] = _collect_field_set_values(scoped_defects, field)
    return {"fieldSets": field_sets}


def _load_extensions_map_for_defects(
    defects: list[dict[str, Any]],
) -> dict[str, DtsExtension]:
    defect_nos = [
        _clean_text(item.get("dtsBizNo"))
        for item in defects
        if _clean_text(item.get("dtsBizNo"))
    ]

    extensions_map: dict[str, DtsExtension] = {}
    if not defect_nos:
        return extensions_map

    for chunk in _iter_chunks(defect_nos):
        items = (
            DtsExtension.objects.filter(defect_no__in=chunk)
            .select_related("pl_group", "dev_owner", "test_owner")
            .all()
        )
        for item in items:
            extensions_map[item.defect_no] = item
    return extensions_map


def _refresh_snapshot_for_product(product_id: str) -> dict[str, Any]:
    safe_product_id = _ensure_supported_product_id(product_id)
    lock_key = _snapshot_lock_key(safe_product_id)
    lock_ttl = _resolve_cache_ttl(
        "DTS_STATISTICS_SNAPSHOT_LOCK_TTL_SECONDS",
        30 * 60,
    )
    if not cache.add(lock_key, "1", lock_ttl):
        current_meta = _serialize_snapshot_meta(_get_snapshot_meta(safe_product_id))
        if current_meta is not None:
            logger.info(
                "DtsStatistics snapshot refresh skipped because lock exists product_id=%s",
                safe_product_id,
            )
            return current_meta
        raise HttpError(409, "DTS 快照刷新任务正在执行中")

    try:
        window_begin, window_end = _resolve_snapshot_window()
        logger.info(
            "DtsStatistics snapshot refresh start product_id=%s window=[%s,%s]",
            safe_product_id,
            window_begin,
            window_end,
        )
        merged_by_defect: dict[str, dict[str, Any]] = {}
        total_chunks = 0
        total_pages = 0
        for chunk_begin, chunk_end in _iter_time_chunks(
            window_begin,
            window_end,
            _MAX_TIME_SPAN_MS_PER_CHUNK,
        ):
            total_chunks += 1
            chunk_rows, scanned_pages, chunk_total_pages = _fetch_rows_for_time_chunk(
                product_id=safe_product_id,
                update_time_begin=chunk_begin,
                update_time_end=chunk_end,
            )
            for row in chunk_rows:
                _merge_duplicate_row_into(merged_by_defect, row)
            total_pages += max(chunk_total_pages, scanned_pages)

        merged_rows = list(merged_by_defect.values())
        normalized_rows: list[dict[str, Any]] = []
        for row in merged_rows:
            normalized = _normalize_source_row(row, product_id=safe_product_id)
            if normalized is not None:
                normalized_rows.append(normalized)
        normalized_rows, filter_stats = _filter_and_enrich_snapshot_rows(normalized_rows)
        normalized_rows = _sort_defects(normalized_rows)
        meta = _write_snapshot_payload(
            product_id=safe_product_id,
            rows=normalized_rows,
            generated_at=timezone.now(),
            window_begin=window_begin,
            window_end=window_end,
        )
        snapshot = _serialize_snapshot_meta(meta) or {}
        logger.info(
            (
                "DtsStatistics snapshot refresh success product_id=%s row_count=%s "
                "chunk_count=%s scanned_pages=%s scan_chunks=%s merged_total=%s "
                "brief_filtered=%s dept_filtered=%s final_total=%s"
            ),
            safe_product_id,
            snapshot.get("rowCount"),
            meta.get("chunkCount"),
            total_pages,
            total_chunks,
            filter_stats.get("merged_total"),
            filter_stats.get("brief_filtered"),
            filter_stats.get("dept_filtered"),
            filter_stats.get("final_total"),
        )
        return snapshot
    finally:
        cache.delete(lock_key)


@scheduler_task
def run_dts_statistics_snapshot_job(**kwargs) -> dict[str, Any]:
    del kwargs
    close_old_connections()
    results: list[dict[str, Any]] = []
    try:
        for product_id in _SUPPORTED_PRODUCT_IDS:
            try:
                snapshot = _refresh_snapshot_for_product(product_id)
                results.append(
                    {
                        "productId": product_id,
                        "productName": _PRODUCT_ID_TO_NAME.get(product_id) or product_id,
                        "status": "success",
                        "snapshot": snapshot,
                    }
                )
            except Exception as exc:
                logger.exception(
                    "DtsStatistics snapshot refresh failed product_id=%s",
                    product_id,
                )
                _mark_snapshot_stale(product_id)
                results.append(
                    {
                        "productId": product_id,
                        "productName": _PRODUCT_ID_TO_NAME.get(product_id) or product_id,
                        "status": "failed",
                        "error": str(exc),
                        "snapshot": _serialize_snapshot_meta(
                            _get_snapshot_meta(product_id)
                        ),
                    }
                )
        return {"items": results}
    finally:
        connection.close()


def _update_query_task_progress(
    task_id: str,
    *,
    message: str,
    progress: int,
    scanned_pages: int = 0,
    total_pages: int = 0,
    matched_count: int = 0,
) -> None:
    DtsStatisticsQueryTask.objects.filter(id=task_id).update(
        message=message,
        progress=max(0, min(int(progress or 0), 99)),
        scanned_pages=max(int(scanned_pages or 0), 0),
        total_pages=max(int(total_pages or 0), 0),
        matched_count=max(int(matched_count or 0), 0),
    )


def _run_dts_statistics_query_task(task_id: str) -> None:
    close_old_connections()
    try:
        task = DtsStatisticsQueryTask.objects.filter(
            id=task_id,
            is_deleted=False,
        ).first()
        if task is None:
            return

        DtsStatisticsQueryTask.objects.filter(id=task_id).update(
            status=DtsStatisticsQueryTask.STATUS_RUNNING,
            message="正在准备查询数据",
            error_message="",
            progress=3,
            started_at=timezone.now(),
            finished_at=None,
        )

        query = _to_export_query_schema(task.payload or {})
        progress_state = {
            "progress": -1,
            "scanned_pages": -1,
            "total_pages": -1,
            "last_ts": 0.0,
        }

        def _on_progress(
            message: str,
            progress: int,
            scanned_pages: int,
            total_pages: int,
        ) -> None:
            now_ts = time.time()
            if (
                progress == progress_state["progress"]
                and scanned_pages == progress_state["scanned_pages"]
                and total_pages == progress_state["total_pages"]
                and now_ts - progress_state["last_ts"] < 0.8
            ):
                return
            progress_state["progress"] = progress
            progress_state["scanned_pages"] = scanned_pages
            progress_state["total_pages"] = total_pages
            progress_state["last_ts"] = now_ts
            _update_query_task_progress(
                task_id,
                message=message,
                progress=progress,
                scanned_pages=scanned_pages,
                total_pages=total_pages,
            )

        defects = _load_filtered_defects(
            query,
            progress_callback=_on_progress,
        )
        _, _, cache_key = _resolve_prepared_cache_identity(query, user=task.user)
        _set_prepared_defects(cache_key, defects)
        DtsStatisticsQueryTask.objects.filter(id=task_id).update(
            status=DtsStatisticsQueryTask.STATUS_SUCCESS,
            message="查询数据准备完成",
            error_message="",
            progress=100,
            matched_count=len(defects),
            result_cache_key=cache_key,
            finished_at=timezone.now(),
        )
    except Exception as exc:
        logger.exception("Dts statistics query task failed: task_id=%s", task_id)
        DtsStatisticsQueryTask.objects.filter(id=task_id).update(
            status=DtsStatisticsQueryTask.STATUS_FAILED,
            message="查询数据准备失败",
            error_message=str(exc),
            finished_at=timezone.now(),
        )
    finally:
        connection.close()


def _start_dts_statistics_query_task_thread(task_id: str) -> None:
    thread = threading.Thread(
        target=_run_dts_statistics_query_task,
        args=(task_id,),
        daemon=True,
    )
    thread.start()


def prepare_dts_statistics_query(
    user: Any,
    data: DtsStatisticsExportSchema | dict[str, Any],
) -> dict[str, Any]:
    if not user or not getattr(user, "id", None):
        raise HttpError(401, "用户未登录")

    query = _to_export_query_schema(data)
    product_id = _ensure_supported_product_id(getattr(query, "productId", ""))
    snapshot = _serialize_snapshot_meta(_get_snapshot_meta(product_id))
    if snapshot is None:
        raise HttpError(409, "DTS 快照数据准备中，请先执行同步任务")
    _validate_snapshot_query_window(query, snapshot)
    return {"mode": "ready", "task": None}


def get_dts_statistics_query_task(user: Any, task_id: str) -> dict[str, Any]:
    if not user or not getattr(user, "id", None):
        raise HttpError(401, "用户未登录")
    task = DtsStatisticsQueryTask.objects.filter(
        id=task_id,
        user=user,
        is_deleted=False,
    ).first()
    if task is None:
        raise HttpError(404, "查询任务不存在")
    return _serialize_query_task(task) or {}


def get_dts_statistics_list(
    query: DtsStatisticsQuerySchema,
    *,
    user: Any = None,
) -> dict[str, Any]:
    defects, snapshot = _resolve_runtime_defects(query, user=user)
    total, page_items = _paginate(defects, query.pageIndex, query.pageSize)
    defect_nos = [
        _clean_text(item.get("dtsBizNo"))
        for item in page_items
        if _clean_text(item.get("dtsBizNo"))
    ]
    extensions = _load_extensions(defect_nos)
    items = [
        _merge_defect_with_extension(
            defect,
            extension=extensions.get(_clean_text(defect.get("dtsBizNo"))),
        )
        for defect in page_items
    ]
    return {"total": total, "items": items, "snapshot": snapshot}


def _distribution(counter: Counter[str], *, top_n: int | None = None) -> list[dict[str, Any]]:
    items = counter.most_common(top_n)
    return [{"label": label, "value": int(value)} for label, value in items if label]


def _normalize_yes(value: Any) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    return text in {"是", "yes", "y", "true", "1", "完成", "已完成"}


def _iter_chunks(values: list[str], chunk_size: int = 2000) -> Iterable[list[str]]:
    if chunk_size <= 0:
        chunk_size = 2000
    for idx in range(0, len(values), chunk_size):
        yield values[idx : idx + chunk_size]


def _join_lines(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join([_clean_text(item) for item in value if _clean_text(item)])
    return _clean_text(value)


def _format_cycle_integer_value(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return "-"
    try:
        decimal_value = Decimal(text)
    except (InvalidOperation, TypeError, ValueError):
        return text
    rounded = decimal_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return str(int(rounded))


_EXPORT_COLUMN_SPECS: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
    ("问题单号", lambda item: _clean_text(item.get("dtsBizNo"))),
    ("简要描述", lambda item: _clean_text(item.get("briefDesc"))),
    ("当前状态", lambda item: _clean_text(item.get("dtsStatusName"))),
    ("严重程度", lambda item: _clean_text(item.get("serverityNoName"))),
    ("父单单号", lambda item: _clean_text(item.get("parentNo"))),
    ("提单时间", lambda item: _clean_text(item.get("createAt"))),
    ("关闭时间", lambda item: _clean_text(item.get("dCloseTime"))),
    ("关闭类型", lambda item: _clean_text(item.get("uQbiCloseTypeName"))),
    ("流程类型", lambda item: _clean_text(item.get("sConfigFlowType"))),
    ("提出方部门", lambda item: _clean_text(item.get("sDeptOneNoName"))),
    ("提单来源", lambda item: _clean_text(item.get("auto_source_type"))),
    ("当前处理人", lambda item: _clean_text(item.get("currentHandler"))),
    ("提单人工号", lambda item: _clean_text(item.get("creator"))),
    ("提单人姓名", lambda item: _clean_text(item.get("sSubmitUserName"))),
    (
        "子系统",
        lambda item: _clean_text(item.get("sSubsystemNoName")),
    ),
    ("产品族名称", lambda item: _clean_text(item.get("sProdFamilyNoName"))),
    ("产品名称", lambda item: _clean_text(item.get("sProdXtdNoName"))),
    ("测试返回次数", lambda item: _clean_text(item.get("iTestBackCount"))),
    ("最后开发修改人", lambda item: _clean_text(item.get("last_dts009_handler"))),
    ("自动责任PL组", lambda item: _clean_text(item.get("auto_pl_group_name"))),
    ("最后审核修改人", lambda item: _clean_text(item.get("last_dts010_handler"))),
    ("最后测试回归人", lambda item: _clean_text(item.get("last_dts013_handler"))),
    ("关闭周期", lambda item: _format_cycle_integer_value(item.get("iNumOfCloseDays"))),
    ("确认周期", lambda item: _format_cycle_integer_value(item.get("iNumOfFirmDays"))),
    ("定位周期", lambda item: _format_cycle_integer_value(item.get("iNumOfLocateDays"))),
    ("修改周期", lambda item: _format_cycle_integer_value(item.get("iNumofModifyDays"))),
    ("回归测试周期", lambda item: _format_cycle_integer_value(item.get("iNumofTestDays"))),
    ("QA大类", lambda item: _clean_text(item.get("qa_category"))),
    ("责任PL组", lambda item: _clean_text(item.get("pl_group_name"))),
    ("是否下游", lambda item: _clean_text(item.get("is_downstream"))),
    ("过程质量分类", lambda item: _clean_text(item.get("process_quality_type"))),
    ("需开发分析", lambda item: _clean_text(item.get("need_dev_analyze"))),
    ("需测试分析", lambda item: _clean_text(item.get("need_test_analyze"))),
    ("开发责任人", lambda item: _clean_text(item.get("dev_owner_name"))),
    ("测试责任人", lambda item: _clean_text(item.get("test_owner_name"))),
    ("开发分析完成", lambda item: _clean_text(item.get("is_dev_analyzed"))),
    ("测试分析完成", lambda item: _clean_text(item.get("is_test_analyzed"))),
    ("QA备注", lambda item: _clean_text(item.get("qa_remark"))),
    ("问题小类", lambda item: _join_lines(item.get("dev_sub_category"))),
    ("问题原因", lambda item: _clean_text(item.get("dev_reason"))),
    ("引入原因", lambda item: _clean_text(item.get("dev_intro_reason"))),
    ("开发填报-改进措施", lambda item: _join_lines(item.get("dev_improvements"))),
    ("非底软说明", lambda item: _join_lines(item.get("dev_non_base_desc"))),
    ("开发填报-落地资产链接", lambda item: _clean_text(item.get("dev_asset_link"))),
    ("开发填报-改进状态", lambda item: _clean_text(item.get("dev_status"))),
    ("特效/功能", lambda item: _clean_text(item.get("test_feature"))),
    ("漏测原因", lambda item: _join_lines(item.get("test_miss_reason"))),
    (
        "规范问题描述",
        lambda item: _clean_text(item.get("test_standard_desc")),
    ),
    ("测试填报-改进措施", lambda item: _join_lines(item.get("test_improvements"))),
    ("非测试说明", lambda item: _clean_text(item.get("test_non_test_desc"))),
    ("测试填报-落地资产链接", lambda item: _clean_text(item.get("test_asset_link"))),
    ("测试填报-改进状态", lambda item: _clean_text(item.get("test_status"))),
]

_EXPORT_HEADERS = tuple(title for title, _ in _EXPORT_COLUMN_SPECS)


def _build_export_row(item: dict[str, Any]) -> list[Any]:
    return [resolver(item) for _, resolver in _EXPORT_COLUMN_SPECS]


def _build_export_response(workbook: openpyxl.Workbook) -> HttpResponse:
    timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="dts-statistics-{timestamp}.xlsx"'
    )
    workbook.save(response)
    return response


def _build_export_workbook(
    defects: list[dict[str, Any]],
    *,
    progress_callback: Callable[[str, int], None] | None = None,
) -> openpyxl.Workbook:
    extensions_map = _load_extensions_map_for_defects(defects)
    workbook = openpyxl.Workbook(write_only=True)
    worksheet = workbook.create_sheet(title=_EXPORT_SHEET_TITLE)
    worksheet.append(list(_EXPORT_HEADERS))

    total = len(defects)
    for index, defect in enumerate(defects, start=1):
        defect_no = _clean_text(defect.get("dtsBizNo"))
        merged = _merge_defect_with_extension(
            defect,
            extension=extensions_map.get(defect_no),
        )
        worksheet.append(_build_export_row(merged))
        if progress_callback and (
            index == 1 or index == total or index % 200 == 0
        ):
            progress_callback(
                "正在生成导出文件",
                min(95, 70 + int((index / max(total, 1)) * 25)),
            )
    return workbook


def _update_export_task_progress(
    task_id: str,
    *,
    message: str,
    progress: int,
) -> None:
    DtsStatisticsExportTask.objects.filter(id=task_id).update(
        message=message,
        progress=max(0, min(int(progress or 0), 99)),
    )


def _run_dts_statistics_export_task(task_id: str) -> None:
    close_old_connections()
    generated_file_path: Path | None = None
    try:
        task = DtsStatisticsExportTask.objects.filter(
            id=task_id,
            is_deleted=False,
        ).first()
        if task is None:
            return

        DtsStatisticsExportTask.objects.filter(id=task_id).update(
            status=DtsStatisticsExportTask.STATUS_RUNNING,
            message="正在准备导出数据",
            error_message="",
            progress=3,
            started_at=timezone.now(),
            finished_at=None,
            file_path="",
            file_name="",
            file_size=0,
        )

        query = _to_export_query_schema(task.payload or {})
        _update_export_task_progress(
            task_id,
            message="正在读取快照缓存",
            progress=18,
        )
        defects, _snapshot = _get_filtered_snapshot_rows(query)
        _update_export_task_progress(
            task_id,
            message="快照筛选完成，正在生成导出文件",
            progress=65,
        )
        workbook = _build_export_workbook(
            defects,
            progress_callback=lambda message, progress: _update_export_task_progress(
                task_id,
                message=message,
                progress=progress,
            ),
        )

        timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        file_name = f"dts-statistics-{timestamp}-{str(task.id)[:8]}.xlsx"
        file_path = _resolve_export_temp_dir() / file_name
        generated_file_path = file_path
        workbook.save(str(file_path))
        file_size = file_path.stat().st_size if file_path.exists() else 0

        DtsStatisticsExportTask.objects.filter(id=task_id).update(
            status=DtsStatisticsExportTask.STATUS_SUCCESS,
            message="导出文件生成完成",
            error_message="",
            progress=100,
            file_path=str(file_path),
            file_name=file_name,
            file_size=file_size,
            finished_at=timezone.now(),
        )
    except Exception as exc:
        if generated_file_path and generated_file_path.exists():
            try:
                generated_file_path.unlink()
            except Exception:
                logger.warning(
                    "DtsStatistics remove export temp file failed task_id=%s file=%s",
                    task_id,
                    generated_file_path,
                    exc_info=True,
                )
        logger.exception("Dts statistics export task failed: task_id=%s", task_id)
        DtsStatisticsExportTask.objects.filter(id=task_id).update(
            status=DtsStatisticsExportTask.STATUS_FAILED,
            message="导出任务失败",
            error_message=str(exc),
            finished_at=timezone.now(),
        )
    finally:
        connection.close()


def _start_dts_statistics_export_task_thread(task_id: str) -> None:
    thread = threading.Thread(
        target=_run_dts_statistics_export_task,
        args=(task_id,),
        daemon=True,
    )
    thread.start()


def prepare_dts_statistics_export(
    user: Any,
    data: DtsStatisticsExportSchema | dict[str, Any],
) -> dict[str, Any]:
    if not user or not getattr(user, "id", None):
        raise HttpError(401, "用户未登录")

    _cleanup_expired_export_files(limit=200)
    query = _to_export_query_schema(data)
    product_id = _ensure_supported_product_id(getattr(query, "productId", ""))
    snapshot = _serialize_snapshot_meta(_get_snapshot_meta(product_id))
    if snapshot is None:
        raise HttpError(409, "DTS 快照数据准备中，请先执行同步任务")
    _validate_snapshot_query_window(query, snapshot)
    task_payload = {
        **_build_export_task_payload(query),
        "snapshotVersion": _clean_text(snapshot.get("version")),
    }
    fingerprint = _fingerprint_payload(task_payload)

    active_task = _get_active_export_task(user, fingerprint)
    if active_task is not None:
        return {"mode": "async", "task": _serialize_export_task(active_task)}

    reusable_task = _get_reusable_export_task(user, fingerprint)
    if reusable_task is not None:
        return {"mode": "ready", "task": _serialize_export_task(reusable_task)}

    task = DtsStatisticsExportTask.objects.create(
        user=user,
        sys_creator=user,
        fingerprint=fingerprint,
        payload=task_payload,
        status=DtsStatisticsExportTask.STATUS_PENDING,
        message="导出任务已提交，正在排队执行",
    )
    _start_dts_statistics_export_task_thread(str(task.id))
    return {"mode": "async", "task": _serialize_export_task(task)}


def get_dts_statistics_export_task(user: Any, task_id: str) -> dict[str, Any]:
    if not user or not getattr(user, "id", None):
        raise HttpError(401, "用户未登录")
    task = DtsStatisticsExportTask.objects.filter(
        id=task_id,
        user=user,
        is_deleted=False,
    ).first()
    if task is None:
        raise HttpError(404, "导出任务不存在")
    return _serialize_export_task(task) or {}


def download_dts_statistics_export_file(user: Any, task_id: str) -> FileResponse:
    if not user or not getattr(user, "id", None):
        raise HttpError(401, "用户未登录")

    _cleanup_expired_export_files(limit=200)
    task = DtsStatisticsExportTask.objects.filter(
        id=task_id,
        user=user,
        is_deleted=False,
    ).first()
    if task is None:
        raise HttpError(404, "导出任务不存在")
    if task.status != DtsStatisticsExportTask.STATUS_SUCCESS:
        raise HttpError(409, "导出任务尚未完成")
    if _is_export_task_expired(task):
        raise HttpError(410, "导出文件已过期，请重新导出")

    file_path = _clean_text(task.file_path)
    if not file_path:
        raise HttpError(404, "导出文件不存在")
    path = Path(file_path)
    if not path.is_file():
        raise HttpError(404, "导出文件不存在")

    filename = _clean_text(task.file_name) or path.name
    return FileResponse(
        path.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def export_dts_statistics(
    query: DtsStatisticsExportSchema,
    *,
    user: Any = None,
) -> HttpResponse:
    defects, _snapshot = _resolve_runtime_defects(query, user=user)
    workbook = _build_export_workbook(defects)
    return _build_export_response(workbook)


def _is_closed(defect: dict[str, Any]) -> bool:
    status = _clean_text(defect.get("dtsStatusName"))
    if "关闭" in status or status in {"FS99", "closed", "close"}:
        return True
    return bool(_clean_text(defect.get("dCloseTime")))


def get_dts_statistics_summary(
    query: DtsStatisticsQuerySchema,
    *,
    user: Any = None,
) -> dict[str, Any]:
    defects, snapshot = _resolve_runtime_defects(query, user=user)
    total_count = len(defects)

    severity_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    team_counter: Counter[str] = Counter()
    stage_counter: Counter[str] = Counter()
    close_type_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    auto_pl_group_counter: Counter[str] = Counter()
    handler_counter: Counter[str] = Counter()
    project_counter: Counter[str] = Counter()

    open_count = 0
    closed_count = 0
    process_days_sum = 0.0
    process_days_count = 0

    for defect in defects:
        severity_counter[_clean_text(defect.get("serverityNoName"))] += 1
        status_counter[_clean_text(defect.get("dtsStatusName"))] += 1
        team_counter[_clean_text(defect.get("sDeptOneNoName"))] += 1
        stage_counter[_clean_text(defect.get("dtsStatusName"))] += 1
        close_type_label = _clean_text(defect.get("uQbiCloseTypeName"))
        if close_type_label:
            close_type_counter[close_type_label] += 1
        elif _is_closed(defect):
            close_type_counter["未填写"] += 1
        else:
            close_type_counter["未关闭"] += 1
        source_counter[_clean_text(defect.get("auto_source_type"))] += 1
        auto_pl_group_counter[_clean_text(defect.get("auto_pl_group_name"))] += 1
        handler_counter[_clean_text(defect.get("currentHandler"))] += 1
        project_counter[_clean_text(defect.get("sProdXtdNoName") or defect.get("productName"))] += 1

        if _is_closed(defect):
            closed_count += 1
        else:
            open_count += 1

        raw_days = defect.get("iNumOfCloseDays")
        try:
            days = float(str(raw_days).strip()) if raw_days is not None else None
        except Exception:
            days = None
        if days is not None:
            process_days_sum += days
            process_days_count += 1

    avg_process_days = round(process_days_sum / process_days_count, 2) if process_days_count else 0.0

    defect_nos = [
        _clean_text(item.get("dtsBizNo"))
        for item in defects
        if _clean_text(item.get("dtsBizNo"))
    ]

    qa_filled_count = 0
    dev_analyzed_count = 0
    test_analyzed_count = 0
    qa_category_counter: Counter[str] = Counter()
    dev_sub_category_counter: Counter[str] = Counter()
    test_miss_reason_counter: Counter[str] = Counter()
    pl_group_counter: Counter[str] = Counter()
    action_status_counter: Counter[str] = Counter()

    for chunk in _iter_chunks(defect_nos):
        extensions = (
            DtsExtension.objects.filter(defect_no__in=chunk)
            .select_related("pl_group")
            .only(
                "defect_no",
                "qa_category",
                "is_dev_analyzed",
                "is_test_analyzed",
                "dev_sub_category",
                "test_miss_reason",
                "pl_group",
                "pl_group__name",
                "dev_status",
                "test_status",
            )
            .all()
        )
        for ext in extensions:
            if _clean_text(ext.qa_category):
                qa_filled_count += 1
                qa_category_counter[_clean_text(ext.qa_category)] += 1
            if _normalize_yes(ext.is_dev_analyzed):
                dev_analyzed_count += 1
            if _normalize_yes(ext.is_test_analyzed):
                test_analyzed_count += 1

            for item in ext.dev_sub_category or []:
                dev_sub_category_counter[_clean_text(item)] += 1
            for item in ext.test_miss_reason or []:
                test_miss_reason_counter[_clean_text(item)] += 1
            if ext.pl_group and _clean_text(ext.pl_group.name):
                pl_group_counter[_clean_text(ext.pl_group.name)] += 1

            action_status = (
                _clean_text(ext.dev_status) or _clean_text(ext.test_status) or ""
            )
            if action_status:
                action_status_counter[action_status] += 1

    qa_completion_rate = round(qa_filled_count / total_count, 4) if total_count else 0.0
    dev_analysis_completion_rate = (
        round(dev_analyzed_count / total_count, 4) if total_count else 0.0
    )
    test_analysis_completion_rate = (
        round(test_analyzed_count / total_count, 4) if total_count else 0.0
    )

    return {
        "total_count": total_count,
        "open_count": open_count,
        "closed_count": closed_count,
        "avg_process_days": avg_process_days,
        "qa_filled_count": qa_filled_count,
        "qa_completion_rate": qa_completion_rate,
        "dev_analyzed_count": dev_analyzed_count,
        "dev_analysis_completion_rate": dev_analysis_completion_rate,
        "test_analyzed_count": test_analyzed_count,
        "test_analysis_completion_rate": test_analysis_completion_rate,
        "severity_dist": _distribution(severity_counter),
        "status_dist": _distribution(status_counter),
        "team_dist": _distribution(team_counter, top_n=30),
        "stage_dist": _distribution(stage_counter),
        "close_type_dist": _distribution(close_type_counter),
        "source_dist": _distribution(source_counter),
        "auto_pl_group_dist": _distribution(auto_pl_group_counter, top_n=20),
        "handler_dist": _distribution(handler_counter, top_n=20),
        "qa_category_dist": _distribution(qa_category_counter),
        "dev_sub_category_dist": _distribution(dev_sub_category_counter, top_n=20),
        "test_miss_reason_dist": _distribution(test_miss_reason_counter, top_n=20),
        "pl_group_dist": _distribution(pl_group_counter),
        "project_dist": _distribution(project_counter),
        "action_status_dist": _distribution(action_status_counter),
        "snapshot": snapshot,
    }


@transaction.atomic
def save_dts_extension(defect_no: str, data: DtsExtensionSaveSchema) -> dict[str, Any]:
    safe_defect_no = _clean_text(defect_no)
    if not safe_defect_no:
        raise HttpError(422, "defect_no 不能为空")

    payload = data.dict(exclude_unset=True)
    if payload:
        DtsExtension.objects.update_or_create(defect_no=safe_defect_no, defaults=payload)
    return {"success": True}


def get_dts_statistics_dict_options() -> dict[str, Any]:
    """
    聚合返回 DTS 模块所需字典选项，减少前端多次请求。

    说明：
    - 返回值采用 {label,value} 的 SelectOption 结构
    - value 默认与 label 相同（便于扩展字段直接落库/导出时可读）
    """

    code_map = {
        "yes_no": "yes_no",
        "qa_category": "dts_qa_category",
        "process_quality_type": "dts_process_quality_type",
        "dev_sub_category": "dts_dev_sub_category",
        "dev_non_base_desc": "dts_dev_non_base_desc",
        "test_miss_reason": "dts_test_miss_reason",
        "action_status": "dts_action_status",
    }

    rows = (
        DictItem.objects.select_related("dict")
        .filter(
            dict__code__in=set(code_map.values()),
            dict__status=True,
            dict__is_deleted=False,
            status=True,
            is_deleted=False,
        )
        .order_by("dict__code", "-sort", "sys_create_datetime")
    )

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)

    for item in rows:
        dict_obj = getattr(item, "dict", None)
        dict_code = _clean_text(getattr(dict_obj, "code", ""))
        if not dict_code:
            continue

        label = _clean_text(getattr(item, "label", "") or getattr(item, "value", ""))
        if not label:
            continue

        value = label
        if value in seen[dict_code]:
            continue
        seen[dict_code].add(value)
        grouped[dict_code].append({"label": label, "value": value})

    result: dict[str, Any] = {}
    for field, dict_code in code_map.items():
        options = grouped.get(dict_code, [])
        if field == "yes_no" and not options:
            options = [
                {"label": "是", "value": "是"},
                {"label": "否", "value": "否"},
            ]
        result[field] = options

    return result
