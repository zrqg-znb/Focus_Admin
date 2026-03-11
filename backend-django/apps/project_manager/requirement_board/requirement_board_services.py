import hashlib
import json
import math
import os
import random
import time
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from ninja.errors import HttpError

from apps.project_manager.project.project_model import Project

from .requirement_board_model import (
    CATEGORY_ORDER,
    STATUS_LABELS,
    STATUS_ORDER,
    UNKNOWN_TEAM_NAME,
)
from .requirement_board_schemas import (
    RequirementBoardDataQuerySchema,
    RequirementBoardSummaryQuerySchema,
)

_DATA_CACHE_TTL_SECONDS = 10 * 60
_SUMMARY_CACHE_TTL_SECONDS = 10 * 60
_SUMMARY_LOCK_TTL_SECONDS = 30
_SUMMARY_SCAN_PAGE_SIZE = 200
_SUMMARY_MAX_SCAN_PAGES = 200
_STATUS_FIELD_MAP = {
    "I": "i_count",
    "D": "d_count",
    "P": "p_count",
    "C": "c_count",
    "A": "a_count",
}
_STATUS_ALIASES = {
    "I": "I",
    "INIT": "I",
    "INITIAL": "I",
    "INITIALIZED": "I",
    "INITIALIZATION": "I",
    "初始化": "I",
    "D": "D",
    "DEFINE": "D",
    "DEFINED": "D",
    "DEFINITION": "D",
    "已完成定义": "D",
    "P": "P",
    "PROGRESS": "P",
    "INPROGRESS": "P",
    "IN_PROGRESS": "P",
    "IN PROGRESS": "P",
    "WORKING": "P",
    "正在工作": "P",
    "C": "C",
    "COMPLETE": "C",
    "COMPLETED": "C",
    "CODECOMPLETE": "C",
    "CODE_COMPLETE": "C",
    "开发已完成": "C",
    "A": "A",
    "ACCEPT": "A",
    "ACCEPTED": "A",
    "ACCEPTANCE": "A",
    "测试验收完成": "A",
}


def _get_setting(name: str, default: Any = None):
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


def _normalize_text_list(values) -> list[str]:
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


def _normalize_categories(values) -> list[str]:
    normalized = _normalize_text_list(values)
    if not normalized:
        return list(CATEGORY_ORDER)

    result: list[str] = []
    for item in normalized:
        category = item.upper()
        if category not in CATEGORY_ORDER:
            raise HttpError(422, f"非法需求类型: {item}")
        if category not in result:
            result.append(category)
    return result


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = _clean_text(value).replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except Exception:
        return 0.0


def _parse_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return parsed if parsed > 0 else default


def _round_metric(value: float) -> float:
    return round(float(value or 0.0), 2)


def _normalize_status(raw_status: Any) -> tuple[str, str]:
    text = _clean_text(raw_status)
    token = text.upper().replace("-", "_").replace(" ", "")
    normalized = _STATUS_ALIASES.get(token) or _STATUS_ALIASES.get(text.upper())
    if not normalized:
        normalized = "P"
    return normalized, STATUS_LABELS[normalized]


def _cache_key(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.md5(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return f"{prefix}:{digest}"


def _build_request_payload(
    design_ids: list[str],
    sub_teams: list[str],
    categories: list[str],
    page_no: int,
    page_size: int,
) -> dict[str, Any]:
    domain_field = _clean_text(_get_setting("REQUIREMENT_BOARD_DOMAIN_FIELD", "domainid"))
    payload = {
        domain_field or "domainid": design_ids,
        "sub_teams": sub_teams,
        "categories": categories,
        "page": {
            "page_no": page_no,
            "page_size": page_size,
        },
    }
    alias_field = _clean_text(_get_setting("REQUIREMENT_BOARD_DESIGN_ALIAS_FIELD", ""))
    if alias_field and alias_field not in payload:
        payload[alias_field] = design_ids
    return payload


def _build_request_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    token = _clean_text(_get_setting("REQUIREMENT_BOARD_API_TOKEN", ""))
    if token:
        headers["Authorization"] = (
            token if token.lower().startswith("bearer ") else f"Bearer {token}"
        )

    raw_extra_headers = _clean_text(
        _get_setting("REQUIREMENT_BOARD_API_HEADERS_JSON", "")
    )
    if raw_extra_headers:
        try:
            extra_headers = json.loads(raw_extra_headers)
        except json.JSONDecodeError as exc:
            raise HttpError(500, f"需求看板请求头配置非法: {exc}") from exc
        if not isinstance(extra_headers, dict):
            raise HttpError(500, "需求看板请求头配置必须是 JSON 对象")
        for key, value in extra_headers.items():
            headers[str(key)] = str(value)
    return headers


def _mock_fetch_page(
    design_ids: list[str],
    sub_teams: list[str],
    categories: list[str],
    page_no: int,
    page_size: int,
) -> dict[str, Any]:
    seed = json.dumps(
        {
            "design_ids": design_ids,
            "sub_teams": sub_teams,
            "categories": categories,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(seed)
    team_pool = sub_teams or [UNKNOWN_TEAM_NAME]
    all_items: list[dict[str, Any]] = []

    for design_id in design_ids:
        requirement_total = rng.randint(24, 48)
        for index in range(requirement_total):
            status = rng.choices(STATUS_ORDER, weights=(0.08, 0.16, 0.34, 0.24, 0.18), k=1)[0]
            category = rng.choice(categories)
            month = (index % 9) + 1
            day = (index % 27) + 1
            team_name = rng.choice(team_pool)
            all_items.append(
                {
                    "category": category,
                    "id": f"{design_id}-{category}-{index + 1:04d}",
                    "title": f"{category}需求-{index + 1:04d}",
                    "schedule_state": status,
                    "requirement2domain": design_id,
                    "planned_test_time": f"2026-{month:02d}-{day:02d} 00:00:00",
                    "due_date": f"2026-{month:02d}-{min(day + 3, 28):02d} 00:00:00",
                    "workload_kloc": round(rng.uniform(0.3, 30.0), 2),
                    "workload_man_day": round(rng.uniform(1.0, 25.0), 2),
                    "service_name": team_name,
                    "develop_user": f"z{rng.randint(60000000, 69999999)}",
                    "test_user": f"z{rng.randint(60000000, 69999999)}",
                }
            )

    start = max(page_no - 1, 0) * page_size
    end = start + page_size
    page_sum = math.ceil(len(all_items) / page_size) if page_size else 0
    return {
        "code": 200,
        "data": {
            "result": all_items[start:end],
            "page": {
                "page_sum": page_sum,
                "page_no": page_no,
                "page_size": page_size,
                "total": len(all_items),
            },
        },
        "message": "success",
    }


def _fetch_raw_page(
    design_ids: list[str],
    sub_teams: list[str],
    categories: list[str],
    page_no: int,
    page_size: int,
) -> dict[str, Any]:
    url = _clean_text(_get_setting("REQUIREMENT_BOARD_API_URL", ""))
    if not url:
        return _mock_fetch_page(design_ids, sub_teams, categories, page_no, page_size)

    payload = _build_request_payload(design_ids, sub_teams, categories, page_no, page_size)
    headers = _build_request_headers()
    timeout = float(_get_setting("REQUIREMENT_BOARD_API_TIMEOUT", 15))
    verify = _to_bool(_get_setting("REQUIREMENT_BOARD_API_VERIFY_SSL", True), True)

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

    if response.status_code != 200:
        raise HttpError(502, f"数据湖返回异常状态码: {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise HttpError(502, "数据湖返回的不是合法 JSON") from exc

    if int(payload.get("code") or 0) != 200:
        raise HttpError(502, payload.get("message") or "数据湖返回失败")
    return payload


def _extract_raw_page(raw_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = raw_payload.get("data") or {}
    result = data.get("result")
    if result is None:
        result = data.get("items") or []
    if not isinstance(result, list):
        raise HttpError(502, "数据湖返回的需求结果格式错误")
    page = data.get("page") or {}
    if not isinstance(page, dict):
        page = {}
    return result, page


def _resolve_page_sum(page: dict[str, Any], page_no: int, page_size: int, item_count: int) -> int:
    raw_page_sum = _parse_positive_int(page.get("page_sum"), 0)
    if raw_page_sum > 0:
        return raw_page_sum

    total = _resolve_total(page, page_no, page_size, item_count)
    if total <= 0:
        return 0
    return math.ceil(total / page_size) if page_size else 0


def _resolve_total(page: dict[str, Any], page_no: int, page_size: int, item_count: int) -> int:
    for key in ("total", "total_count", "count", "row_sum", "record_sum"):
        parsed = _parse_positive_int(page.get(key), 0)
        if parsed > 0:
            return parsed

    page_sum = _parse_positive_int(page.get("page_sum"), 0)
    if page_sum > 0:
        if page_no >= page_sum:
            return max((page_sum - 1) * page_size + item_count, item_count)
        return page_sum * page_size

    return max((page_no - 1) * page_size + item_count, item_count)


def _project_payload(project: Project | None, design_id: str) -> tuple[str, str]:
    if project is None:
        return "", design_id or "未匹配项目"
    return str(project.id), project.name


def _standardize_requirement_items(
    items: list[dict[str, Any]],
    design_project_map: dict[str, Project],
) -> list[dict[str, Any]]:
    standardized: list[dict[str, Any]] = []
    fallback_project = next(iter(design_project_map.values()), None)

    for item in items:
        design_id = _clean_text(
            item.get("requirement2domain") or item.get("domainid") or item.get("design_id")
        )
        project = design_project_map.get(design_id)
        if project is None and len(design_project_map) == 1:
            project = fallback_project
        project_id, project_name = _project_payload(project, design_id)
        status_code, status_label = _normalize_status(item.get("schedule_state"))
        team_name = _clean_text(item.get("service_name") or item.get("servioce_name"))
        if not team_name:
            team_name = UNKNOWN_TEAM_NAME

        category = _clean_text(item.get("category")).upper()
        if category not in CATEGORY_ORDER:
            category = category or "AR"

        requirement_id = _clean_text(item.get("id") or item.get("requirement_id"))
        if not requirement_id:
            requirement_id = f"{design_id or 'unknown'}-{category}"

        standardized.append(
            {
                "requirement_id": requirement_id,
                "title": _clean_text(item.get("title")) or requirement_id,
                "category": category,
                "status_code": status_code,
                "status_label": status_label,
                "raw_status": _clean_text(item.get("schedule_state")),
                "project_id": project_id,
                "project_name": project_name,
                "design_id": design_id or None,
                "team_name": team_name,
                "planned_test_time": _clean_text(item.get("planned_test_time")) or None,
                "due_date": _clean_text(item.get("due_date")) or None,
                "workload_kloc": _round_metric(_to_float(item.get("workload_kloc"))),
                "workload_man_day": _round_metric(_to_float(item.get("workload_man_day"))),
                "develop_user": _clean_text(item.get("develop_user")),
                "test_user": _clean_text(item.get("test_user")),
            }
        )
    return standardized


def _resolve_query_context(
    project_ids: list[str],
    sub_teams,
    categories,
) -> dict[str, Any]:
    ordered_project_ids = _normalize_text_list(project_ids)
    if not ordered_project_ids:
        raise HttpError(422, "请至少选择一个项目")

    project_qs = Project.objects.filter(id__in=ordered_project_ids, is_deleted=False)
    project_map = {str(item.id): item for item in project_qs}
    missing_ids = [item for item in ordered_project_ids if item not in project_map]
    if missing_ids:
        raise HttpError(404, f"部分项目不存在或已删除: {', '.join(missing_ids)}")

    ordered_projects = [project_map[item] for item in ordered_project_ids]

    design_project_map: dict[str, Project] = {}
    design_ids: list[str] = []
    allowed_teams: list[str] = []
    allowed_team_set: set[str] = set()
    invalid_projects: list[str] = []

    for project in ordered_projects:
        design_id = _clean_text(project.design_id)
        project_teams = _normalize_text_list(project.sub_teams)
        if not design_id or not project_teams:
            invalid_projects.append(project.name)
            continue

        conflict = design_project_map.get(design_id)
        if conflict and conflict.id != project.id:
            raise HttpError(
                422,
                f"项目 {conflict.name} 与 {project.name} 的 design_id 重复，无法匹配需求归属",
            )

        design_project_map[design_id] = project
        design_ids.append(design_id)
        for team in project_teams:
            if team in allowed_team_set:
                continue
            allowed_team_set.add(team)
            allowed_teams.append(team)

    if invalid_projects:
        raise HttpError(
            422,
            f"以下项目未完成需求数据源配置: {', '.join(invalid_projects)}",
        )

    selected_teams = _normalize_text_list(sub_teams)
    if selected_teams:
        invalid_teams = [team for team in selected_teams if team not in allowed_team_set]
        if invalid_teams:
            raise HttpError(422, f"存在无效责任团队: {', '.join(invalid_teams)}")
    else:
        selected_teams = allowed_teams[:]

    selected_categories = _normalize_categories(categories)
    return {
        "projects": ordered_projects,
        "design_project_map": design_project_map,
        "design_ids": design_ids,
        "sub_teams": selected_teams,
        "categories": selected_categories,
        "cache_payload": {
            "project_ids": ordered_project_ids,
            "design_ids": design_ids,
            "sub_teams": selected_teams,
            "categories": selected_categories,
        },
    }


def _load_page_payload(
    context: dict[str, Any],
    page_no: int,
    page_size: int,
) -> dict[str, Any]:
    payload = {**context["cache_payload"], "page_no": page_no, "page_size": page_size}
    key = _cache_key("pm:requirement-board:data", payload)
    cached = cache.get(key)
    if isinstance(cached, dict) and isinstance(cached.get("items"), list):
        return cached

    raw_payload = _fetch_raw_page(
        design_ids=context["design_ids"],
        sub_teams=context["sub_teams"],
        categories=context["categories"],
        page_no=page_no,
        page_size=page_size,
    )
    raw_items, raw_page = _extract_raw_page(raw_payload)
    normalized_page_no = _parse_positive_int(raw_page.get("page_no"), page_no)
    normalized_page_size = _parse_positive_int(raw_page.get("page_size"), page_size)
    items = _standardize_requirement_items(raw_items, context["design_project_map"])
    result = {
        "items": items,
        "total": _resolve_total(raw_page, normalized_page_no, normalized_page_size, len(items)),
        "page_no": normalized_page_no,
        "page_size": normalized_page_size,
        "page_sum": _resolve_page_sum(
            raw_page,
            normalized_page_no,
            normalized_page_size,
            len(items),
        ),
    }
    cache.set(key, result, _DATA_CACHE_TTL_SECONDS)
    return result


def get_filter_options() -> dict[str, Any]:
    projects = (
        Project.objects.filter(is_deleted=False)
        .order_by("is_closed", "name")
        .only("id", "name", "design_id", "sub_teams", "is_closed")
    )
    return {
        "projects": [
            {
                "id": str(project.id),
                "name": project.name,
                "design_id": _clean_text(project.design_id) or None,
                "sub_teams": _normalize_text_list(project.sub_teams),
                "config_complete": bool(
                    _clean_text(project.design_id) and _normalize_text_list(project.sub_teams)
                ),
            }
            for project in projects
        ]
    }


def get_requirement_board_page(
    data: RequirementBoardDataQuerySchema,
) -> dict[str, Any]:
    context = _resolve_query_context(data.project_ids, data.sub_teams, data.categories)
    page_no = _parse_positive_int(data.page_no, 1)
    page_size = min(_parse_positive_int(data.page_size, 20), 200)
    return _load_page_payload(context, page_no=page_no, page_size=page_size)


def _create_empty_completion_payload() -> dict[str, Any]:
    return {
        "count": 0,
        "workload_man_day": 0.0,
        "workload_kloc": 0.0,
        "count_rate": 0.0,
        "workload_man_day_rate": 0.0,
        "workload_kloc_rate": 0.0,
    }


def _create_summary_accumulator() -> dict[str, Any]:
    return {
        "total_count": 0,
        "total_workload_man_day": 0.0,
        "total_workload_kloc": 0.0,
        "status_counts": {status: 0 for status in STATUS_ORDER},
        "type_summary": {},
        "project_summary": {},
        "team_summary": {},
    }


def _update_completion_payload(payload: dict[str, Any], item: dict[str, Any]) -> None:
    payload["count"] += 1
    payload["workload_man_day"] += _to_float(item.get("workload_man_day"))
    payload["workload_kloc"] += _to_float(item.get("workload_kloc"))


def _aggregate_item(summary: dict[str, Any], item: dict[str, Any]) -> None:
    status_code = item["status_code"]
    category = item["category"]
    project_id = item.get("project_id") or ""
    project_name = item.get("project_name") or "未匹配项目"
    team_name = item.get("team_name") or UNKNOWN_TEAM_NAME
    workload_man_day = _to_float(item.get("workload_man_day"))
    workload_kloc = _to_float(item.get("workload_kloc"))

    summary["total_count"] += 1
    summary["total_workload_man_day"] += workload_man_day
    summary["total_workload_kloc"] += workload_kloc
    summary["status_counts"][status_code] += 1

    type_row = summary["type_summary"].setdefault(
        category,
        {
            "category": category,
            "total_count": 0,
            "total_workload_man_day": 0.0,
            "total_workload_kloc": 0.0,
        },
    )
    type_row["total_count"] += 1
    type_row["total_workload_man_day"] += workload_man_day
    type_row["total_workload_kloc"] += workload_kloc

    project_key = project_id or project_name
    project_row = summary["project_summary"].setdefault(
        project_key,
        {
            "project_id": project_id,
            "project_name": project_name,
            "total_count": 0,
            "total_workload_man_day": 0.0,
            "total_workload_kloc": 0.0,
        },
    )
    project_row["total_count"] += 1
    project_row["total_workload_man_day"] += workload_man_day
    project_row["total_workload_kloc"] += workload_kloc

    team_row = summary["team_summary"].setdefault(
        team_name,
        {
            "team_name": team_name,
            "total_count": 0,
            "total_workload_man_day": 0.0,
            "total_workload_kloc": 0.0,
            "i_count": 0,
            "d_count": 0,
            "p_count": 0,
            "c_count": 0,
            "a_count": 0,
            "dev_done": _create_empty_completion_payload(),
            "acceptance_done": _create_empty_completion_payload(),
        },
    )
    team_row["total_count"] += 1
    team_row["total_workload_man_day"] += workload_man_day
    team_row["total_workload_kloc"] += workload_kloc
    team_row[_STATUS_FIELD_MAP[status_code]] += 1

    if status_code in {"C", "A"}:
        _update_completion_payload(team_row["dev_done"], item)
    if status_code == "A":
        _update_completion_payload(team_row["acceptance_done"], item)


def _finalize_completion_payload(
    payload: dict[str, Any],
    total_count: int,
    total_workload_man_day: float,
    total_workload_kloc: float,
) -> dict[str, Any]:
    count_rate = payload["count"] / total_count if total_count else 0.0
    man_day_rate = (
        payload["workload_man_day"] / total_workload_man_day
        if total_workload_man_day
        else 0.0
    )
    kloc_rate = (
        payload["workload_kloc"] / total_workload_kloc if total_workload_kloc else 0.0
    )
    return {
        "count": int(payload["count"]),
        "workload_man_day": _round_metric(payload["workload_man_day"]),
        "workload_kloc": _round_metric(payload["workload_kloc"]),
        "count_rate": round(count_rate, 4),
        "workload_man_day_rate": round(man_day_rate, 4),
        "workload_kloc_rate": round(kloc_rate, 4),
    }


def _finalize_summary_payload(summary: dict[str, Any]) -> dict[str, Any]:
    status_summary = [
        {
            "status_code": status,
            "status_label": STATUS_LABELS[status],
            "count": int(summary["status_counts"][status]),
        }
        for status in STATUS_ORDER
    ]

    type_summary = [
        {
            "category": category,
            "total_count": int(summary["type_summary"].get(category, {}).get("total_count", 0)),
            "total_workload_man_day": _round_metric(
                summary["type_summary"].get(category, {}).get("total_workload_man_day", 0.0)
            ),
            "total_workload_kloc": _round_metric(
                summary["type_summary"].get(category, {}).get("total_workload_kloc", 0.0)
            ),
        }
        for category in CATEGORY_ORDER
        if category in summary["type_summary"]
    ]

    project_summary = sorted(
        (
            {
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "total_count": int(row["total_count"]),
                "total_workload_man_day": _round_metric(row["total_workload_man_day"]),
                "total_workload_kloc": _round_metric(row["total_workload_kloc"]),
            }
            for row in summary["project_summary"].values()
        ),
        key=lambda item: (
            -int(item["total_count"]),
            -float(item["total_workload_man_day"]),
            item["project_name"],
        ),
    )

    team_summary = []
    for row in summary["team_summary"].values():
        team_summary.append(
            {
                "team_name": row["team_name"],
                "total_count": int(row["total_count"]),
                "total_workload_man_day": _round_metric(row["total_workload_man_day"]),
                "total_workload_kloc": _round_metric(row["total_workload_kloc"]),
                "i_count": int(row["i_count"]),
                "d_count": int(row["d_count"]),
                "p_count": int(row["p_count"]),
                "c_count": int(row["c_count"]),
                "a_count": int(row["a_count"]),
                "dev_done": _finalize_completion_payload(
                    row["dev_done"],
                    int(row["total_count"]),
                    float(row["total_workload_man_day"]),
                    float(row["total_workload_kloc"]),
                ),
                "acceptance_done": _finalize_completion_payload(
                    row["acceptance_done"],
                    int(row["total_count"]),
                    float(row["total_workload_man_day"]),
                    float(row["total_workload_kloc"]),
                ),
            }
        )

    team_summary.sort(
        key=lambda item: (
            -int(item["total_count"]),
            -float(item["total_workload_man_day"]),
            item["team_name"],
        )
    )

    return {
        "total_count": int(summary["total_count"]),
        "total_workload_man_day": _round_metric(summary["total_workload_man_day"]),
        "total_workload_kloc": _round_metric(summary["total_workload_kloc"]),
        "status_summary": status_summary,
        "type_summary": type_summary,
        "project_summary": project_summary,
        "team_summary": team_summary,
    }


def _compute_summary(context: dict[str, Any]) -> dict[str, Any]:
    page_size = min(
        _parse_positive_int(_get_setting("REQUIREMENT_BOARD_SUMMARY_PAGE_SIZE", _SUMMARY_SCAN_PAGE_SIZE), _SUMMARY_SCAN_PAGE_SIZE),
        500,
    )
    max_pages = max(
        _parse_positive_int(_get_setting("REQUIREMENT_BOARD_SUMMARY_MAX_PAGES", _SUMMARY_MAX_SCAN_PAGES), _SUMMARY_MAX_SCAN_PAGES),
        1,
    )
    summary = _create_summary_accumulator()
    page_no = 1
    scanned_pages = 0

    while True:
        scanned_pages += 1
        if scanned_pages > max_pages:
            raise HttpError(502, "需求总结扫描页数过多，请缩小筛选范围")

        page_payload = _load_page_payload(context, page_no=page_no, page_size=page_size)
        items = page_payload["items"]
        for item in items:
            _aggregate_item(summary, item)

        page_sum = _parse_positive_int(page_payload.get("page_sum"), 0)
        if page_sum > 0 and page_no >= page_sum:
            break
        if not items or len(items) < page_payload["page_size"]:
            break
        page_no += 1

    return _finalize_summary_payload(summary)


def get_requirement_board_summary(
    data: RequirementBoardSummaryQuerySchema,
) -> dict[str, Any]:
    context = _resolve_query_context(data.project_ids, data.sub_teams, data.categories)
    summary_key = _cache_key("pm:requirement-board:summary", context["cache_payload"])
    cached = cache.get(summary_key)
    if isinstance(cached, dict) and isinstance(cached.get("team_summary"), list):
        return cached

    lock_key = f"{summary_key}:lock"
    lock_acquired = cache.add(lock_key, "1", _SUMMARY_LOCK_TTL_SECONDS)
    if not lock_acquired:
        for _ in range(10):
            time.sleep(0.3)
            cached = cache.get(summary_key)
            if isinstance(cached, dict) and isinstance(cached.get("team_summary"), list):
                return cached

    try:
        summary = _compute_summary(context)
        cache.set(summary_key, summary, _SUMMARY_CACHE_TTL_SECONDS)
        return summary
    finally:
        if lock_acquired:
            cache.delete(lock_key)
