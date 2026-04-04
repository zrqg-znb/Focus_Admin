from __future__ import annotations

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

from .dts_statistics_model import (
    DtsExtension,
    DtsStatisticsExportTask,
    DtsStatisticsQueryTask,
)
from .dts_statistics_schemas import (
    DtsExtensionSaveSchema,
    DtsStatisticsExportSchema,
    DtsStatisticsQuerySchema,
)

logger = logging.getLogger(__name__)

_SOURCE_CACHE_KEY_PREFIX = "cache:dts_statistics:source:v2:"
_PREPARED_CACHE_KEY_PREFIX = "cache:dts_statistics:prepared:v1:"
_LOCK_KEY_PREFIX = "cache:dts_statistics:lock:v2:"

_DEFAULT_SOURCE_CACHE_TTL_SECONDS = 180
_DEFAULT_LOCK_TTL_SECONDS = 30
_DEFAULT_PREPARED_CACHE_TTL_SECONDS = 10 * 60
_DEFAULT_EXPORT_FILE_TTL_SECONDS = 24 * 60 * 60

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

_DEFAULT_FIELDS = [
    "dtsBizNo",
    "briefDesc",
    "dtsStatusName",
    "serverityNoName",
    "parentNo",
    "createAt",
    "dCloseTime",
    "sDeptOneNoName",
    "currentHandler",
    "creator",
    "sSubmitUserName",
    "sSubmitsystemNoName",
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

_EXPORT_SHEET_TITLE = "DTS统计"
_EXPORT_HEADERS = (
    "DTS单号",
    "项目",
    "团队",
    "级别",
    "状态",
    "处理人",
    "提交时间",
    "处理天数",
    "描述",
    "阶段",
    "关闭类型",
    "QA大类",
    "责任PL组",
    "是否下游",
    "过程质量分类",
    "需开发分析",
    "需测试分析",
    "开发责任人",
    "测试责任人",
    "开发分析完成",
    "测试分析完成",
    "QA备注",
    "问题小类(开发)",
    "问题原因(开发)",
    "引入原因(开发)",
    "改进措施(开发)",
    "非底软说明(开发)",
    "落地资产链接(开发)",
    "改进状态(开发)",
    "特效/功能(测试)",
    "漏测原因(测试)",
    "规范问题描述(测试)",
    "改进措施(测试)",
    "非测试说明(测试)",
    "落地资产链接(测试)",
    "改进状态(测试)",
)


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


def _parse_datetime(value: Any) -> datetime.datetime | None:
    text = _clean_text(value)
    if not text:
        return None

    normalized_text = text.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(normalized_text)
        if dt.tzinfo is None:
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
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
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
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
                    "parentNo": f"DTSP{index % 2000:04d}",
                    "createAt": create_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "dCloseTime": close_dt.strftime("%Y-%m-%d %H:%M:%S")
                    if close_dt
                    else None,
                    "sDeptOneNoName": f"研发{(index % 5) + 1}部",
                    "currentHandler": f"user{(index % 15) + 1}",
                    "creator": f"creator{(index % 10) + 1}",
                    "sSubmitUserName": f"提交人{(index % 10) + 1}",
                    "sSubmitsystemNoName": f"子系统{(index % 6) + 1}",
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


def _merge_duplicate_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        defect_no = _clean_text(row.get("dtsBizNo"))
        if not defect_no:
            continue
        existing = merged.get(defect_no)
        if existing is None:
            current = dict(row)
            current["dtsBizNo"] = defect_no
            merged[defect_no] = current
            continue

        existing_dt = _parse_datetime(existing.get("createAt"))
        incoming_dt = _parse_datetime(row.get("createAt"))
        if incoming_dt and (not existing_dt or incoming_dt > existing_dt):
            existing["createAt"] = row.get("createAt")

        for key, value in row.items():
            if key not in existing or (_is_empty_value(existing.get(key)) and not _is_empty_value(value)):
                existing[key] = value

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
    create_at = _clean_text(row.get("createAt"))
    close_time = _clean_text(row.get("dCloseTime"))
    team_name = _clean_text(row.get("sDeptOneNoName"))
    close_days = _clean_text(row.get("iNumOfCloseDays"))
    if not close_days:
        close_days = _clean_text(_compute_process_days(create_at, close_time))

    normalized = {
        "dtsBizNo": defect_no,
        "briefDesc": brief_desc or None,
        "dtsStatusName": status_name or None,
        "serverityNoName": severity_name or None,
        "parentNo": _clean_text(row.get("parentNo")) or None,
        "createAt": create_at or None,
        "dCloseTime": close_time or None,
        "sDeptOneNoName": team_name or None,
        "currentHandler": _clean_text(row.get("currentHandler")) or None,
        "creator": _clean_text(row.get("creator")) or None,
        "sSubmitUserName": _clean_text(row.get("sSubmitUserName")) or None,
        "sSubmitsystemNoName": _clean_text(row.get("sSubmitsystemNoName")) or None,
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
    }
    return normalized


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
        safe_dt = dt or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
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


def _resolve_runtime_filters(
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


def _to_export_query_schema(
    data: DtsStatisticsQuerySchema | DtsStatisticsExportSchema | dict[str, Any],
) -> DtsStatisticsExportSchema:
    if isinstance(data, DtsStatisticsExportSchema):
        return data
    if isinstance(data, DtsStatisticsQuerySchema):
        return DtsStatisticsExportSchema(**data.dict())
    payload = data.dict() if hasattr(data, "dict") else dict(data or {})
    return DtsStatisticsExportSchema(**payload)


def _build_runtime_filter_payload(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
) -> dict[str, Any]:
    product_id, flow_states, severity_nos, update_time_begin, update_time_end = (
        _resolve_runtime_filters(query)
    )
    return {
        "productId": product_id,
        "flowStates": flow_states,
        "severityNos": severity_nos,
        "updateTimeBegin": update_time_begin,
        "updateTimeEnd": update_time_end,
        "fields": list(_DEFAULT_FIELDS),
    }


def _resolve_prepared_cache_identity(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    user: Any = None,
) -> tuple[dict[str, Any], str, str]:
    payload = _build_runtime_filter_payload(query)
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
        _resolve_runtime_filters(query)
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


def _resolve_runtime_defects(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
    *,
    user: Any = None,
) -> list[dict[str, Any]]:
    prepared = _get_prepared_defects(query, user=user)
    if prepared is not None:
        return prepared
    return _load_filtered_defects(query)


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
    payload, fingerprint, cache_key = _resolve_prepared_cache_identity(query, user=user)
    prepared = _get_prepared_defects_by_cache_key(cache_key)
    if prepared is not None:
        return {"mode": "ready", "task": None}

    active_task = _get_active_query_task(user, fingerprint)
    if active_task is not None:
        return {"mode": "async", "task": _serialize_query_task(active_task)}

    task = DtsStatisticsQueryTask.objects.create(
        user=user,
        sys_creator=user,
        fingerprint=fingerprint,
        payload=payload,
        status=DtsStatisticsQueryTask.STATUS_PENDING,
        message="查询任务已提交，正在排队执行",
        result_cache_key=cache_key,
    )
    _start_dts_statistics_query_task_thread(str(task.id))
    return {"mode": "async", "task": _serialize_query_task(task)}


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
    defects = _resolve_runtime_defects(query, user=user)
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
    return {"total": total, "items": items}


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


def _build_export_row(item: dict[str, Any]) -> list[Any]:
    close_type = "关闭" if _is_closed(item) else "未关闭"
    return [
        _clean_text(item.get("dtsBizNo")),
        _clean_text(item.get("sProdXtdNoName") or item.get("productName")),
        _clean_text(item.get("sDeptOneNoName")),
        _clean_text(item.get("serverityNoName")),
        _clean_text(item.get("dtsStatusName")),
        _clean_text(item.get("currentHandler")),
        _clean_text(item.get("createAt")),
        _clean_text(item.get("iNumOfCloseDays")),
        _clean_text(item.get("briefDesc")),
        _clean_text(item.get("dtsStatusName")),
        close_type,
        _clean_text(item.get("qa_category")),
        _clean_text(item.get("pl_group_name")),
        _clean_text(item.get("is_downstream")),
        _clean_text(item.get("process_quality_type")),
        _clean_text(item.get("need_dev_analyze")),
        _clean_text(item.get("need_test_analyze")),
        _clean_text(item.get("dev_owner_name")),
        _clean_text(item.get("test_owner_name")),
        _clean_text(item.get("is_dev_analyzed")),
        _clean_text(item.get("is_test_analyzed")),
        _clean_text(item.get("qa_remark")),
        _join_lines(item.get("dev_sub_category")),
        _clean_text(item.get("dev_reason")),
        _clean_text(item.get("dev_intro_reason")),
        _join_lines(item.get("dev_improvements")),
        _join_lines(item.get("dev_non_base_desc")),
        _clean_text(item.get("dev_asset_link")),
        _clean_text(item.get("dev_status")),
        _clean_text(item.get("test_feature")),
        _join_lines(item.get("test_miss_reason")),
        _clean_text(item.get("test_standard_desc")),
        _join_lines(item.get("test_improvements")),
        _clean_text(item.get("test_non_test_desc")),
        _clean_text(item.get("test_asset_link")),
        _clean_text(item.get("test_status")),
    ]


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
        _, _, prepared_cache_key = _resolve_prepared_cache_identity(query, user=task.user)
        defects = _get_prepared_defects_by_cache_key(prepared_cache_key)

        if defects is None:
            progress_state = {
                "progress": -1,
                "last_ts": 0.0,
            }

            def _on_prepare_progress(
                message: str,
                progress: int,
                _scanned_pages: int,
                _total_pages: int,
            ) -> None:
                mapped_progress = min(65, 5 + int(progress * 0.6))
                now_ts = time.time()
                if (
                    mapped_progress == progress_state["progress"]
                    and now_ts - progress_state["last_ts"] < 0.8
                ):
                    return
                progress_state["progress"] = mapped_progress
                progress_state["last_ts"] = now_ts
                _update_export_task_progress(
                    task_id,
                    message=message or "正在准备导出数据",
                    progress=mapped_progress,
                )

            defects = _load_filtered_defects(query, progress_callback=_on_prepare_progress)
            _set_prepared_defects(prepared_cache_key, defects)
        else:
            _update_export_task_progress(
                task_id,
                message="命中查询缓存，正在生成导出文件",
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
    payload, fingerprint, _ = _resolve_prepared_cache_identity(query, user=user)

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
        payload=payload,
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
    defects = _resolve_runtime_defects(query, user=user)
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
    defects = _resolve_runtime_defects(query, user=user)
    total_count = len(defects)

    severity_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    team_counter: Counter[str] = Counter()
    stage_counter: Counter[str] = Counter()
    close_type_counter: Counter[str] = Counter()
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
        close_type_counter["关闭" if _is_closed(defect) else "未关闭"] += 1
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
        "handler_dist": _distribution(handler_counter, top_n=20),
        "qa_category_dist": _distribution(qa_category_counter),
        "dev_sub_category_dist": _distribution(dev_sub_category_counter, top_n=20),
        "test_miss_reason_dist": _distribution(test_miss_reason_counter, top_n=20),
        "pl_group_dist": _distribution(pl_group_counter),
        "project_dist": _distribution(project_counter),
        "action_status_dist": _distribution(action_status_counter),
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
