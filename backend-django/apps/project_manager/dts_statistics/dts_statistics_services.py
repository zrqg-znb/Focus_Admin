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
from dataclasses import dataclass
from typing import Any, Iterable

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from ninja.errors import HttpError

from common.fu_cache import CacheManager

from apps.project_manager.project.project_model import Project

from .dts_statistics_model import DtsDefectProjectLink, DtsExtension
from .dts_statistics_schemas import DtsExtensionSaveSchema, DtsStatisticsQuerySchema

logger = logging.getLogger(__name__)

_DATA_TYPE = "today"
_EXCLUDE_INVALID = False

_PAGE_CACHE_KEY_PREFIX = "cache:dts_statistics:page:"
_SCAN_CACHE_KEY_PREFIX = "cache:dts_statistics:scan:"
_LOCK_KEY_PREFIX = "cache:dts_statistics:lock:"

_DEFAULT_PAGE_CACHE_TTL_SECONDS = 120
_DEFAULT_SCAN_CACHE_TTL_SECONDS = 180
_DEFAULT_LOCK_TTL_SECONDS = 30

_DEFAULT_SCAN_PAGE_SIZE = 500
_DEFAULT_MAX_SCAN_PAGES = 200


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

    candidate = text.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(candidate)
    except Exception:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ):
        try:
            return datetime.datetime.strptime(text, fmt)
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


def _resolve_scan_page_size() -> int:
    raw_value = _get_setting("DTS_STATISTICS_SCAN_PAGE_SIZE", _DEFAULT_SCAN_PAGE_SIZE)
    try:
        value = int(raw_value)
    except Exception:
        value = _DEFAULT_SCAN_PAGE_SIZE
    value = max(value, 1)
    return min(value, 1000)


def _resolve_max_scan_pages() -> int:
    raw_value = _get_setting("DTS_STATISTICS_SCAN_MAX_PAGES", _DEFAULT_MAX_SCAN_PAGES)
    try:
        value = int(raw_value)
    except Exception:
        value = _DEFAULT_MAX_SCAN_PAGES
    return max(value, 1)


@dataclass(frozen=True)
class _VersionGroup:
    version: str
    team_name_list: str
    team_to_project_ids: dict[str, list[str]]
    project_id_to_name: dict[str, str]

    @property
    def project_ids(self) -> set[str]:
        return set(self.project_id_to_name.keys())


def _group_projects(project_ids: list[str]) -> list[_VersionGroup]:
    projects = (
        Project.objects.filter(id__in=project_ids, enable_dts=True)
        .only("id", "name", "version_c", "di_teams", "enable_dts")
        .all()
    )
    version_to_group: dict[str, dict[str, Any]] = {}

    for project in projects:
        version = _clean_text(project.version_c)
        teams = _normalize_text_list(project.di_teams)
        if not version or not teams:
            continue

        group = version_to_group.setdefault(
            version,
            {
                "team_set": set(),
                "team_to_project_ids": defaultdict(list),
                "project_id_to_name": {},
            },
        )
        group["project_id_to_name"][project.id] = project.name
        for team in teams:
            group["team_set"].add(team)
            group["team_to_project_ids"][team].append(project.id)

    result: list[_VersionGroup] = []
    for version, group in version_to_group.items():
        teams_sorted = sorted(group["team_set"])
        team_name_list = ",".join(teams_sorted)
        team_to_project_ids = {k: list(dict.fromkeys(v)) for k, v in group["team_to_project_ids"].items()}
        result.append(
            _VersionGroup(
                version=version,
                team_name_list=team_name_list,
                team_to_project_ids=team_to_project_ids,
                project_id_to_name=dict(group["project_id_to_name"]),
            )
        )
    return result


def _extract_team_name(defect: dict[str, Any]) -> str:
    return _clean_text(defect.get("submitTeam") or defect.get("currentTeam") or "")


def _build_upstream_payload(
    *,
    version: str,
    team_name_list: str,
    column_type: str,
    start_time: str,
    end_time: str,
    page_no: int,
    page_size: int,
) -> dict[str, Any]:
    return {
        "version": version,
        "teamNameList": team_name_list,
        "dataType": _DATA_TYPE,
        "columnType": column_type,
        "excludeInvalid": _EXCLUDE_INVALID,
        "startTime": start_time,
        "endTime": end_time,
        "pageInfo": {"pageNo": page_no, "pageSize": page_size},
    }


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


def _mock_fetch_page(payload: dict[str, Any]) -> dict[str, Any]:
    base_payload = {k: v for k, v in payload.items() if k != "pageInfo"}
    digest = hashlib.md5(
        json.dumps(base_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    rng = random.Random(digest)

    team_names = [item for item in _clean_text(payload.get("teamNameList")).split(",") if item]
    if not team_names:
        team_names = ["MockTeam"]

    total = 1234
    page_info = payload.get("pageInfo") or {}
    page_no = int(page_info.get("pageNo") or 1)
    page_size = int(page_info.get("pageSize") or 20)
    page_size = max(min(page_size, 500), 1)
    start = max(page_no - 1, 0) * page_size
    end = min(start + page_size, total)

    base_time = datetime.datetime(2026, 3, 15, 12, 0, 0)
    severities = ["关键", "严重", "一般", "提示"]
    statuses = ["开发修复", "测试审核", "待定位", "已关闭"]

    items: list[dict[str, Any]] = []
    for idx in range(start, end):
        submit_time = base_time - datetime.timedelta(minutes=idx)
        team_name = rng.choice(team_names)
        items.append(
            {
                "defectNo": f"DTS{20260000000000 + idx}",
                "brief": f"Mock defect {idx + 1}",
                "severity": rng.choice(severities),
                "submitTime": submit_time.strftime("%Y-%m-%d %H:%M:%S"),
                "submitTeam": team_name,
                "currentTeam": team_name,
                "currentStatus": rng.choice(statuses),
                "currentHandler": f"user{rng.randint(1, 20)}",
                "process_days": str(rng.randint(0, 30)),
            }
        )

    return {
        "pageResult": {
            "total": total,
            "pageNo": page_no,
            "pageSize": page_size,
            "pageSum": math.ceil(total / page_size) if page_size else 0,
        },
        "dataList": items,
    }


def _fetch_upstream_page(payload: dict[str, Any]) -> dict[str, Any]:
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


def _extract_page_result(raw: dict[str, Any]) -> tuple[int, list[dict[str, Any]], dict[str, Any]]:
    page_result = raw.get("pageResult") or {}
    if not isinstance(page_result, dict):
        page_result = {}
    data_list = raw.get("dataList") or []
    if not isinstance(data_list, list):
        data_list = []
    total = page_result.get("total")
    try:
        total_int = int(total)
    except Exception:
        total_int = len(data_list)
    return total_int, [item for item in data_list if isinstance(item, dict)], page_result


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


def _bulk_upsert_links(
    *,
    group: _VersionGroup,
    defects: Iterable[dict[str, Any]],
) -> None:
    now = timezone.now()
    objs: list[DtsDefectProjectLink] = []
    seen: set[tuple[str, str]] = set()

    for defect in defects:
        defect_no = _clean_text(defect.get("defectNo"))
        if not defect_no:
            continue
        team_name = _extract_team_name(defect)
        if not team_name:
            continue
        project_ids = group.team_to_project_ids.get(team_name) or []
        for project_id in project_ids:
            key = (defect_no, project_id)
            if key in seen:
                continue
            seen.add(key)
            objs.append(
                DtsDefectProjectLink(
                    defect_no=defect_no,
                    project_id=project_id,
                    team_name=team_name,
                    version_c=group.version,
                    last_seen_at=now,
                )
            )

    if not objs:
        return

    DtsDefectProjectLink.objects.bulk_create(
        objs,
        batch_size=500,
        update_conflicts=True,
        update_fields=["team_name", "version_c", "last_seen_at"],
    )


def _bulk_upsert_links_for_sources(
    *,
    group_map: dict[str, _VersionGroup],
    defect_sources: dict[str, set[str]],
    defects: Iterable[dict[str, Any]],
) -> None:
    if not group_map:
        return

    now = timezone.now()
    objs: list[DtsDefectProjectLink] = []
    seen: set[tuple[str, str]] = set()

    for defect in defects:
        defect_no = _clean_text(defect.get("defectNo"))
        if not defect_no:
            continue
        team_name = _extract_team_name(defect)
        if not team_name:
            continue
        versions = defect_sources.get(defect_no) or set()
        for version in versions:
            group = group_map.get(version)
            if not group:
                continue
            project_ids = group.team_to_project_ids.get(team_name) or []
            for project_id in project_ids:
                key = (defect_no, project_id)
                if key in seen:
                    continue
                seen.add(key)
                objs.append(
                    DtsDefectProjectLink(
                        defect_no=defect_no,
                        project_id=project_id,
                        team_name=team_name,
                        version_c=version,
                        last_seen_at=now,
                    )
                )

    if not objs:
        return

    DtsDefectProjectLink.objects.bulk_create(
        objs,
        batch_size=500,
        update_conflicts=True,
        update_fields=["team_name", "version_c", "last_seen_at"],
    )


def _load_page_cached(
    *,
    group: _VersionGroup,
    column_type: str,
    start_time: str,
    end_time: str,
    page_no: int,
    page_size: int,
) -> tuple[int, list[dict[str, Any]]]:
    cache_payload = {
        "version": group.version,
        "teamNameList": group.team_name_list,
        "columnType": column_type,
        "startTime": start_time,
        "endTime": end_time,
        "pageNo": page_no,
        "pageSize": page_size,
        "dataType": _DATA_TYPE,
        "excludeInvalid": _EXCLUDE_INVALID,
    }
    cache_key, _ = _cache_key(_PAGE_CACHE_KEY_PREFIX, cache_payload)
    cached = CacheManager.get(cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("dataList"), list):
        total, defects, _ = _extract_page_result(cached)
        return total, defects

    payload = _build_upstream_payload(
        version=group.version,
        team_name_list=group.team_name_list,
        column_type=column_type,
        start_time=start_time,
        end_time=end_time,
        page_no=page_no,
        page_size=page_size,
    )
    raw = _fetch_upstream_page(payload)
    total, defects, page_result = _extract_page_result(raw)
    ttl = _resolve_cache_ttl(
        "DTS_STATISTICS_PAGE_CACHE_TTL_SECONDS",
        _DEFAULT_PAGE_CACHE_TTL_SECONDS,
    )
    CacheManager.set(
        cache_key,
        {"pageResult": page_result, "dataList": defects},
        ttl,
    )
    return total, defects


def _scan_all_cached(
    *,
    group: _VersionGroup,
    column_type: str,
    start_time: str,
    end_time: str,
) -> list[dict[str, Any]]:
    scan_page_size = _resolve_scan_page_size()
    cache_payload = {
        "version": group.version,
        "teamNameList": group.team_name_list,
        "columnType": column_type,
        "startTime": start_time,
        "endTime": end_time,
        "dataType": _DATA_TYPE,
        "excludeInvalid": _EXCLUDE_INVALID,
        "scanPageSize": scan_page_size,
    }
    cache_key, digest = _cache_key(_SCAN_CACHE_KEY_PREFIX, cache_payload)
    cached = CacheManager.get(cache_key)
    if isinstance(cached, list):
        return [item for item in cached if isinstance(item, dict)]

    lock_key = f"{_LOCK_KEY_PREFIX}{digest}"
    lock_ttl = _resolve_cache_ttl("DTS_STATISTICS_SCAN_LOCK_TTL_SECONDS", _DEFAULT_LOCK_TTL_SECONDS)
    lock_acquired = cache.add(lock_key, "1", lock_ttl)
    if not lock_acquired:
        waiting = _wait_for_cache(cache_key)
        if isinstance(waiting, list):
            return [item for item in waiting if isinstance(item, dict)]

        # 没拿到锁且缓存仍为空，允许降级扫描一次，避免一直空结果
        lock_acquired = False

    ttl = _resolve_cache_ttl(
        "DTS_STATISTICS_SCAN_CACHE_TTL_SECONDS",
        _DEFAULT_SCAN_CACHE_TTL_SECONDS,
    )
    max_pages = _resolve_max_scan_pages()
    defects: list[dict[str, Any]] = []
    fetched_total = 0

    try:
        stop_reason: str | None = None
        for page_no in range(1, max_pages + 1):
            payload = _build_upstream_payload(
                version=group.version,
                team_name_list=group.team_name_list,
                column_type=column_type,
                start_time=start_time,
                end_time=end_time,
                page_no=page_no,
                page_size=scan_page_size,
            )
            raw = _fetch_upstream_page(payload)
            total, page_defects, page_result = _extract_page_result(raw)
            defects.extend(page_defects)
            fetched_total += len(page_defects)
            _bulk_upsert_links(group=group, defects=page_defects)

            if not page_defects:
                stop_reason = "empty"
                break
            if len(page_defects) < scan_page_size:
                stop_reason = "partial_page"
                break

            page_sum = page_result.get("pageSum")
            try:
                page_sum_int = int(page_sum)
            except Exception:
                page_sum_int = 0

            if total and fetched_total >= total:
                stop_reason = "total"
                break
            if page_sum_int and page_no >= page_sum_int:
                stop_reason = "page_sum"
                break
        else:
            stop_reason = None

        if stop_reason is None and max_pages > 0:
            raise HttpError(422, "DTS 扫描页数过多，请缩小筛选范围")

        CacheManager.set(cache_key, defects, ttl)
        return defects
    finally:
        if lock_acquired:
            cache.delete(lock_key)


def _merge_duplicate_defects(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        defect_no = _clean_text(item.get("defectNo"))
        if not defect_no:
            continue
        existing = merged.get(defect_no)
        if existing is None:
            merged[defect_no] = dict(item)
            continue

        existing_dt = _parse_datetime(existing.get("submitTime"))
        incoming_dt = _parse_datetime(item.get("submitTime"))

        def is_empty(value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str) and not value.strip():
                return True
            if isinstance(value, (list, dict)) and not value:
                return True
            return False

        # submitTime: keep the latest if possible.
        if incoming_dt and (not existing_dt or incoming_dt > existing_dt):
            existing["submitTime"] = item.get("submitTime")

        # Prefer non-empty fields.
        for key, value in item.items():
            if key not in existing or is_empty(existing.get(key)) and not is_empty(value):
                existing[key] = value
    return list(merged.values())


def _sort_defects(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]):
        dt = _parse_datetime(item.get("submitTime"))
        safe_dt = dt or datetime.datetime.min
        defect_no = _clean_text(item.get("defectNo"))
        return safe_dt, defect_no

    return sorted(items, key=sort_key, reverse=True)


def _paginate(items: list[dict[str, Any]], page_no: int, page_size: int) -> tuple[int, list[dict[str, Any]]]:
    safe_page_no = max(int(page_no or 1), 1)
    safe_page_size = max(int(page_size or 20), 1)
    safe_page_size = min(safe_page_size, 500)
    total = len(items)
    start = max(safe_page_no - 1, 0) * safe_page_size
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


def _load_link_map(
    *,
    defect_nos: list[str],
    project_ids: set[str],
) -> dict[str, dict[str, Any]]:
    if not defect_nos or not project_ids:
        return {}

    links = (
        DtsDefectProjectLink.objects.filter(defect_no__in=defect_nos, project_id__in=project_ids)
        .select_related("project")
        .all()
    )
    mapping: dict[str, dict[str, Any]] = {}
    for link in links:
        bucket = mapping.setdefault(
            link.defect_no,
            {"project_ids": [], "project_names": [], "team_names": []},
        )
        if link.project_id and link.project_id not in bucket["project_ids"]:
            bucket["project_ids"].append(link.project_id)
        if link.project and link.project.name and link.project.name not in bucket["project_names"]:
            bucket["project_names"].append(link.project.name)
        team_name = _clean_text(link.team_name)
        if team_name and team_name not in bucket["team_names"]:
            bucket["team_names"].append(team_name)
    return mapping


def _merge_defect_with_extension(
    defect: dict[str, Any],
    *,
    extension: DtsExtension | None,
    link_info: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(defect)
    defect_no = _clean_text(defect.get("defectNo"))

    link_bucket = link_info or {}
    merged["project_ids"] = list(link_bucket.get("project_ids") or [])
    merged["project_names"] = list(link_bucket.get("project_names") or [])
    merged["team_names"] = list(link_bucket.get("team_names") or [])

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
                "dev_non_base_desc": None,
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
    merged["dev_non_base_desc"] = extension.dev_non_base_desc
    merged["dev_asset_link"] = extension.dev_asset_link
    merged["dev_status"] = extension.dev_status

    merged["test_feature"] = extension.test_feature
    merged["test_miss_reason"] = extension.test_miss_reason or []
    merged["test_standard_desc"] = extension.test_standard_desc
    merged["test_improvements"] = extension.test_improvements or []
    merged["test_non_test_desc"] = extension.test_non_test_desc
    merged["test_asset_link"] = extension.test_asset_link
    merged["test_status"] = extension.test_status

    # ensure defectNo is kept for response consumers
    merged["defectNo"] = defect_no or merged.get("defectNo")
    return merged


def get_dts_statistics_list(query: DtsStatisticsQuerySchema) -> dict[str, Any]:
    groups = _group_projects(query.project_ids)
    if not groups:
        return {"total": 0, "items": []}

    column_type = query.column_type
    start_time = query.start_time
    end_time = query.end_time
    selected_project_ids: set[str] = set()
    for group in groups:
        selected_project_ids.update(group.project_ids)

    # One group: use upstream paging + page cache for fast list response.
    if len(groups) == 1:
        group = groups[0]
        total, defects = _load_page_cached(
            group=group,
            column_type=column_type,
            start_time=start_time,
            end_time=end_time,
            page_no=query.page_no,
            page_size=query.page_size,
        )
        _bulk_upsert_links(group=group, defects=defects)
        defect_nos = [_clean_text(item.get("defectNo")) for item in defects if _clean_text(item.get("defectNo"))]
        extensions = _load_extensions(defect_nos)
        link_map = _load_link_map(defect_nos=defect_nos, project_ids=selected_project_ids)
        items = [
            _merge_defect_with_extension(
                defect,
                extension=extensions.get(_clean_text(defect.get("defectNo"))),
                link_info=link_map.get(_clean_text(defect.get("defectNo"))),
            )
            for defect in defects
        ]
        return {"total": total, "items": items}

    # Multiple groups: scan caches -> merge + local paging.
    group_map = {group.version: group for group in groups}
    defect_sources: dict[str, set[str]] = defaultdict(set)
    scanned: list[dict[str, Any]] = []
    for group in groups:
        group_defects = (
            _scan_all_cached(
                group=group,
                column_type=column_type,
                start_time=start_time,
                end_time=end_time,
            )
        )
        scanned.extend(group_defects)
        for defect in group_defects:
            defect_no = _clean_text(defect.get("defectNo"))
            if defect_no:
                defect_sources[defect_no].add(group.version)
    merged = _sort_defects(_merge_duplicate_defects(scanned))
    total, page_items = _paginate(merged, query.page_no, query.page_size)
    _bulk_upsert_links_for_sources(
        group_map=group_map,
        defect_sources=defect_sources,
        defects=page_items,
    )
    defect_nos = [_clean_text(item.get("defectNo")) for item in page_items if _clean_text(item.get("defectNo"))]
    extensions = _load_extensions(defect_nos)
    link_map = _load_link_map(defect_nos=defect_nos, project_ids=selected_project_ids)
    items = [
        _merge_defect_with_extension(
            defect,
            extension=extensions.get(_clean_text(defect.get("defectNo"))),
            link_info=link_map.get(_clean_text(defect.get("defectNo"))),
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


def get_dts_statistics_summary(query: DtsStatisticsQuerySchema) -> dict[str, Any]:
    groups = _group_projects(query.project_ids)
    if not groups:
        return {
            "total_count": 0,
            "open_count": 0,
            "closed_count": 0,
            "avg_process_days": 0.0,
            "qa_filled_count": 0,
            "qa_completion_rate": 0.0,
            "dev_analyzed_count": 0,
            "dev_analysis_completion_rate": 0.0,
            "test_analyzed_count": 0,
            "test_analysis_completion_rate": 0.0,
            "severity_dist": [],
            "status_dist": [],
            "qa_category_dist": [],
            "dev_sub_category_dist": [],
            "test_miss_reason_dist": [],
            "pl_group_dist": [],
            "project_dist": [],
            "action_status_dist": [],
        }

    column_type = query.column_type
    start_time = query.start_time
    end_time = query.end_time

    scanned: list[dict[str, Any]] = []
    for group in groups:
        scanned.extend(
            _scan_all_cached(
                group=group,
                column_type=column_type,
                start_time=start_time,
                end_time=end_time,
            )
        )
    defects = _merge_duplicate_defects(scanned)
    total_count = len(defects)

    severity_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    open_count = 0
    closed_count = 0
    process_days_sum = 0.0
    process_days_count = 0

    def is_closed(defect: dict[str, Any]) -> bool:
        if column_type == "openDefects":
            return False
        if column_type == "closeDefects":
            return True
        status = _clean_text(defect.get("currentStatus"))
        close_type = _clean_text(defect.get("closeType"))
        return bool(close_type) or ("关闭" in status) or status.lower() in {"closed", "close", "done"}

    for defect in defects:
        severity_counter[_clean_text(defect.get("severity"))] += 1
        status_counter[_clean_text(defect.get("currentStatus"))] += 1
        if is_closed(defect):
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

    selected_project_ids: set[str] = set()
    for group in groups:
        selected_project_ids.update(group.project_ids)

    project_counter: Counter[str] = Counter()
    if defect_nos and selected_project_ids:
        for chunk in _iter_chunks(defect_nos):
            links = (
                DtsDefectProjectLink.objects.filter(
                    defect_no__in=chunk, project_id__in=selected_project_ids
                )
                .select_related("project")
                .only("defect_no", "project", "project__name")
                .all()
            )
            for link in links:
                name = link.project.name if link.project else ""
                if name:
                    project_counter[name] += 1

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

    payload = data.dict()
    payload.pop("project_ids", None)
    DtsExtension.objects.update_or_create(defect_no=safe_defect_no, defaults=payload)
    return {"success": True}
