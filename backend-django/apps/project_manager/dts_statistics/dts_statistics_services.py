from __future__ import annotations

import datetime
import hashlib
import json
import logging
import math
import os
import random
import time
from collections import Counter, defaultdict
from typing import Any, Iterable

import openpyxl
import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from ninja.errors import HttpError

from common.fu_cache import CacheManager
from core.dict_item.dict_item_model import DictItem

from .dts_statistics_model import DtsExtension
from .dts_statistics_schemas import (
    DtsExtensionSaveSchema,
    DtsStatisticsExportSchema,
    DtsStatisticsQuerySchema,
)

logger = logging.getLogger(__name__)

_SOURCE_CACHE_KEY_PREFIX = "cache:dts_statistics:source:v2:"
_LOCK_KEY_PREFIX = "cache:dts_statistics:lock:v2:"

_DEFAULT_SOURCE_CACHE_TTL_SECONDS = 180
_DEFAULT_LOCK_TTL_SECONDS = 30

_DATA_LAKE_PAGE_SIZE = 500
_MAX_TIME_SPAN_MS_PER_CHUNK = 3 * 24 * 60 * 60 * 1000
_MAX_SCAN_PAGES_PER_CHUNK = 2000

_PRODUCT_ID_TO_NAME = {
    "250539396": "座舱",
    "250539397": "车控",
}

_DEFAULT_FIELDS = [
    "dtsBizNo",
    "briefDesc",
    "dtsStatus",
    "dtsStatusName",
    "serverityNoname",
    "serverityNoName",
    "serverityNo",
    "parentNo",
    "createAt",
    "dCkiseTime",
    "dCloseTime",
    "sDeptOneNoName",
    "flowState",
    "currentHandler",
    "creator",
    "sSubmitUserName",
    "sSubmitsystemNoName",
    "sTestorTestReport",
]

_SEVERITY_NAME_TO_CODE = {
    "提示": "Suggestion",
    "一般": "Minor",
    "严重": "Major",
    "关键": "Critical",
}

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
                    "dtsStatus": flow_state,
                    "dtsStatusName": flow_names.get(flow_state) or flow_state,
                    "serverityNo": severity_codes[severity_pos],
                    "serverityNoName": severity_names[severity_pos],
                    "parentNo": f"DTSP{index % 2000:04d}",
                    "createAt": create_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "dCloseTime": close_dt.strftime("%Y-%m-%d %H:%M:%S")
                    if close_dt
                    else None,
                    "sDeptOneNoName": f"研发{(index % 5) + 1}部",
                    "flowState": flow_state,
                    "currentHandler": f"user{(index % 15) + 1}",
                    "creator": f"creator{(index % 10) + 1}",
                    "sSubmitUserName": f"提交人{(index % 10) + 1}",
                    "sSubmitsystemNoName": f"子系统{(index % 6) + 1}",
                    "sTestorTestReport": f"<p>mock report {index + 1}</p>",
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
        defect_no = _clean_text(row.get("dtsBizNo") or row.get("defectNo"))
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
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fetched = 0
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

        if not page_rows:
            break
        if len(page_rows) < _DATA_LAKE_PAGE_SIZE:
            break
        if total > 0 and fetched >= total:
            break
    else:
        raise HttpError(422, "DTS 扫描页数过多，请缩小筛选范围")

    return rows


def _load_source_rows_cached(
    *,
    product_id: str,
    update_time_begin: int,
    update_time_end: int,
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
            return [item for item in waiting if isinstance(item, dict)]

    ttl = _resolve_cache_ttl(
        "DTS_STATISTICS_SOURCE_CACHE_TTL_SECONDS",
        _DEFAULT_SOURCE_CACHE_TTL_SECONDS,
    )
    try:
        scanned: list[dict[str, Any]] = []
        for chunk_begin, chunk_end in _iter_time_chunks(
            update_time_begin,
            update_time_end,
            _MAX_TIME_SPAN_MS_PER_CHUNK,
        ):
            scanned.extend(
                _fetch_rows_for_time_chunk(
                    product_id=product_id,
                    update_time_begin=chunk_begin,
                    update_time_end=chunk_end,
                )
            )
        merged = _merge_duplicate_rows(scanned)
        CacheManager.set(cache_key, merged, ttl)
        return merged
    finally:
        if lock_acquired:
            cache.delete(lock_key)


def _resolve_severity_code(row: dict[str, Any]) -> str:
    code = _clean_text(
        row.get("serverityNo")
        or row.get("severityNo")
        or row.get("severity_no")
    )
    if code:
        return code

    name = _clean_text(
        row.get("serverityNoName")
        or row.get("serverityNoname")
        or row.get("severity")
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
    defect_no = _clean_text(row.get("dtsBizNo") or row.get("defectNo"))
    if not defect_no:
        return None

    product_name = _PRODUCT_ID_TO_NAME.get(product_id) or product_id
    brief_desc = _clean_text(row.get("briefDesc") or row.get("brief"))
    status_name = _clean_text(row.get("dtsStatusName") or row.get("currentStatus"))
    flow_state = _clean_text(row.get("flowState") or row.get("dtsStatus"))
    severity_name = _clean_text(
        row.get("serverityNoName")
        or row.get("serverityNoname")
        or row.get("severity")
    )
    severity_code = _resolve_severity_code(row)
    create_at = _clean_text(row.get("createAt") or row.get("submitTime"))
    close_time = _clean_text(row.get("dCloseTime") or row.get("dCkiseTime"))
    team_name = _clean_text(
        row.get("sDeptOneNoName")
        or row.get("submitTeam")
        or row.get("currentTeam")
    )

    process_days = _clean_text(row.get("process_days"))
    if not process_days:
        process_days = _clean_text(_compute_process_days(create_at, close_time))

    close_type = "关闭" if flow_state == "FS99" else ""
    normalized = {
        # compatibility fields
        "defectNo": defect_no,
        "brief": brief_desc,
        "severity": severity_name or severity_code,
        "submitTime": create_at or None,
        "currentStatus": status_name or None,
        "currentHandler": _clean_text(row.get("currentHandler")) or None,
        "currentTeam": team_name or None,
        "currentStage": flow_state or None,
        "closeType": close_type or None,
        "process_days": process_days or None,
        "project_ids": [product_id],
        "project_names": [product_name],
        "team_names": [team_name] if team_name else [],
        "project_name": product_name,
        "team_name": team_name or None,
        # raw data-lake fields
        "dtsBizNo": defect_no,
        "briefDesc": brief_desc or None,
        "dtsStatus": _clean_text(row.get("dtsStatus")) or None,
        "dtsStatusName": status_name or None,
        "serverityNo": severity_code or None,
        "serverityNoName": severity_name or None,
        "parentNo": _clean_text(row.get("parentNo")) or None,
        "createAt": create_at or None,
        "dCloseTime": close_time or None,
        "sDeptOneNoName": team_name or None,
        "flowState": flow_state or None,
        "creator": _clean_text(row.get("creator")) or None,
        "sSubmitUserName": _clean_text(row.get("sSubmitUserName")) or None,
        "sSubmitsystemNoName": _clean_text(row.get("sSubmitsystemNoName")) or None,
        "sTestorTestReport": _clean_text(row.get("sTestorTestReport")) or None,
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
        row_flow = _clean_text(row.get("flowState")).upper()
        if flow_set and row_flow not in flow_set:
            continue

        row_severity_code = _clean_text(_resolve_severity_code(row)).lower()
        if severity_set and row_severity_code not in severity_set:
            continue
        result.append(row)
    return result


def _sort_defects(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]):
        dt = _parse_datetime(item.get("submitTime") or item.get("createAt"))
        safe_dt = dt or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        defect_no = _clean_text(item.get("defectNo") or item.get("dtsBizNo"))
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
    defect_no = _clean_text(merged.get("defectNo") or merged.get("dtsBizNo"))
    merged["defectNo"] = defect_no
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


def _load_filtered_defects(
    query: DtsStatisticsQuerySchema | DtsStatisticsExportSchema,
) -> list[dict[str, Any]]:
    product_id, flow_states, severity_nos, update_time_begin, update_time_end = (
        _resolve_runtime_filters(query)
    )
    source_rows = _load_source_rows_cached(
        product_id=product_id,
        update_time_begin=update_time_begin,
        update_time_end=update_time_end,
    )

    normalized_rows: list[dict[str, Any]] = []
    for row in source_rows:
        normalized = _normalize_source_row(row, product_id=product_id)
        if normalized:
            normalized_rows.append(normalized)

    filtered_rows = _apply_source_filters(
        normalized_rows,
        flow_states=flow_states,
        severity_nos=severity_nos,
    )
    return _sort_defects(filtered_rows)


def get_dts_statistics_list(query: DtsStatisticsQuerySchema) -> dict[str, Any]:
    defects = _load_filtered_defects(query)
    total, page_items = _paginate(defects, query.pageIndex, query.pageSize)
    defect_nos = [
        _clean_text(item.get("defectNo"))
        for item in page_items
        if _clean_text(item.get("defectNo"))
    ]
    extensions = _load_extensions(defect_nos)
    items = [
        _merge_defect_with_extension(
            defect,
            extension=extensions.get(_clean_text(defect.get("defectNo"))),
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
    return [
        _clean_text(item.get("defectNo")),
        _clean_text(item.get("project_name") or item.get("productName")),
        _clean_text(item.get("team_name") or item.get("sDeptOneNoName")),
        _clean_text(item.get("severity")),
        _clean_text(item.get("currentStatus")),
        _clean_text(item.get("currentHandler")),
        _clean_text(item.get("submitTime")),
        _clean_text(item.get("process_days")),
        _clean_text(item.get("brief")),
        _clean_text(item.get("currentStage")),
        _clean_text(item.get("closeType")),
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


def export_dts_statistics(query: DtsStatisticsExportSchema) -> HttpResponse:
    defects = _load_filtered_defects(query)
    defect_nos = [
        _clean_text(item.get("defectNo"))
        for item in defects
        if _clean_text(item.get("defectNo"))
    ]

    extensions_map: dict[str, DtsExtension] = {}
    if defect_nos:
        for chunk in _iter_chunks(defect_nos):
            items = (
                DtsExtension.objects.filter(defect_no__in=chunk)
                .select_related("pl_group", "dev_owner", "test_owner")
                .all()
            )
            for item in items:
                extensions_map[item.defect_no] = item

    workbook = openpyxl.Workbook(write_only=True)
    worksheet = workbook.create_sheet(title=_EXPORT_SHEET_TITLE)
    worksheet.append(list(_EXPORT_HEADERS))

    for defect in defects:
        defect_no = _clean_text(defect.get("defectNo"))
        merged = _merge_defect_with_extension(
            defect,
            extension=extensions_map.get(defect_no),
        )
        worksheet.append(_build_export_row(merged))

    return _build_export_response(workbook)


def _is_closed(defect: dict[str, Any]) -> bool:
    flow_state = _clean_text(defect.get("flowState")).upper()
    if flow_state == "FS99":
        return True
    status = _clean_text(defect.get("currentStatus"))
    if "关闭" in status:
        return True
    normalized = status.lower()
    return normalized in {"close", "closed", "done"}


def get_dts_statistics_summary(query: DtsStatisticsQuerySchema) -> dict[str, Any]:
    defects = _load_filtered_defects(query)
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
        severity_counter[_clean_text(defect.get("severity"))] += 1
        status_counter[_clean_text(defect.get("currentStatus"))] += 1
        team_counter[_clean_text(defect.get("team_name") or defect.get("sDeptOneNoName"))] += 1
        stage_counter[_clean_text(defect.get("flowState") or defect.get("currentStage"))] += 1
        close_type_counter[_clean_text(defect.get("closeType"))] += 1
        handler_counter[_clean_text(defect.get("currentHandler"))] += 1
        project_counter[_clean_text(defect.get("project_name") or defect.get("productName"))] += 1

        if _is_closed(defect):
            closed_count += 1
        else:
            open_count += 1

        raw_days = defect.get("process_days")
        try:
            days = float(str(raw_days).strip()) if raw_days is not None else None
        except Exception:
            days = None
        if days is not None:
            process_days_sum += days
            process_days_count += 1

    avg_process_days = round(process_days_sum / process_days_count, 2) if process_days_count else 0.0

    defect_nos = [
        _clean_text(item.get("defectNo"))
        for item in defects
        if _clean_text(item.get("defectNo"))
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
    payload.pop("project_ids", None)
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
