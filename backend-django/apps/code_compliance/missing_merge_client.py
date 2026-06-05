from __future__ import annotations

import hashlib
import json
import logging
import math
import random
from datetime import datetime, timedelta
from typing import Any, Iterable
from urllib.parse import quote, urlencode

import requests
from django.conf import settings
from django.utils import dateparse, timezone
from ninja.errors import HttpError


logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
DEFAULT_API_TIMEOUT = 15.0
DEFAULT_API_VERIFY_SSL = True
BEIJING_TZ = timezone.get_fixed_timezone(8 * 60)
DEFAULT_CR_API_URL_TEMPLATE = "http://apig.yinwang.com/api/v4/groups/{group_id}/change_requests"
CRRequestParams = dict[str, list[str] | str]


def _clean_text(value: Any) -> str:
    """把上游和配置值统一转换成去空格字符串。"""
    if value is None:
        return ""
    return str(value).strip()


def _to_bool(value: Any, default: bool = False) -> bool:
    """解析 settings 中常见的布尔配置写法。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _get_setting(name: str, default: Any = None) -> Any:
    """读取 Django settings，便于测试用 override_settings 覆盖。"""
    return getattr(settings, name, default)


def format_data_lake_datetime(value: datetime) -> str:
    """按数据湖要求输出 2026-06-11T16:20:20.000+08:00 格式。"""
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    local_value = timezone.localtime(value, BEIJING_TZ)
    millis = local_value.strftime("%f")[:3]
    return local_value.strftime(f"%Y-%m-%dT%H:%M:%S.{millis}+08:00")


def parse_data_lake_datetime(value: Any) -> datetime | None:
    """兼容数据湖 ISO 时间、常规时间字符串和空值。"""
    raw = _clean_text(value)
    if not raw:
        return None
    parsed = dateparse.parse_datetime(raw)
    if parsed is None:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, BEIJING_TZ)
    return parsed


def build_cr_request_params(
    *,
    page: int,
    per_page: int,
    target_branch: str,
    projects: Iterable[str],
    merged_after: datetime,
    merged_before: datetime,
    only_count: bool,
) -> CRRequestParams:
    """校验并构造 CR 数据湖 GET 查询参数。"""
    branch = _clean_text(target_branch)
    if not branch:
        raise HttpError(400, "target_branch 不能为空")

    project_values = [_clean_text(item) for item in projects if _clean_text(item)]
    if not project_values:
        raise HttpError(400, "projects 不能为空")

    safe_page = max(int(page or 1), 1)
    safe_per_page = max(min(int(per_page or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE), 1)
    if merged_after > merged_before:
        raise HttpError(400, "merged_after 不能晚于 merged_before")

    return {
        "page": str(safe_page),
        "per_page": str(safe_per_page),
        "state": "merged",
        "target_branch": branch,
        "projects": project_values,
        "merged_after": format_data_lake_datetime(merged_after),
        "merged_before": format_data_lake_datetime(merged_before),
        "only_count": "True" if only_count else "False",
    }


def build_cr_encoded_query(params: CRRequestParams) -> str:
    """将查询参数 URL 编码，尤其保证 +08:00 中的加号不会被误解为空格。"""
    return urlencode(params, doseq=True, quote_via=quote)


def build_cr_request_url(url_template: str, group_id: str, params: CRRequestParams) -> str:
    """把组织 group_id 注入固定数据湖 URL 模板，并拼接 GET 查询串。"""
    group = _clean_text(group_id)
    if not group:
        raise HttpError(400, "group_id 不能为空")

    template = _clean_text(url_template) or DEFAULT_CR_API_URL_TEMPLATE
    if "{group_id}" not in template:
        raise HttpError(500, "代码合规数据湖 URL 模板必须包含 {group_id}")

    endpoint = template.replace("{group_id}", quote(group, safe=""))
    separator = "&" if "?" in endpoint else "?"
    return f"{endpoint}{separator}{build_cr_encoded_query(params)}"


def normalize_cr_detail(row: dict[str, Any]) -> dict[str, Any] | None:
    """把数据湖 CR 明细归一成漏合检测服务使用的字段。"""
    if not isinstance(row, dict):
        return None
    author = row.get("author") if isinstance(row.get("author"), dict) else {}
    project = row.get("project") if isinstance(row.get("project"), dict) else {}
    change_key = _clean_text(row.get("change_key"))
    if not change_key:
        return None
    return {
        "project_id": _clean_text(
            row.get("project_id") or row.get("projectId") or project.get("id")
        ),
        "change_request_iid": _clean_text(
            row.get("change_request_iid") or row.get("iid") or row.get("id")
        ),
        "change_key": change_key,
        "title": _clean_text(row.get("title")),
        "description": _clean_text(row.get("description")),
        "web_url": _clean_text(row.get("web_url") or row.get("url")),
        "added_lines": _safe_int(row.get("added_lines")),
        "removed_lines": _safe_int(row.get("removed_lines")),
        "merged_at": parse_data_lake_datetime(row.get("merged_at")),
        "target_branch": _clean_text(row.get("target_branch")),
        "author_username": _clean_text(author.get("username") or row.get("author_username")),
    }


def _safe_int(value: Any) -> int:
    """把数据湖可能返回的字符串数字安全转成整数。"""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _build_request_headers() -> dict[str, str]:
    """构造数据湖请求头，支持 Token 和 JSON 形式的额外请求头。"""
    headers = {"Accept": "application/json"}
    token = _clean_text(_get_setting("CODE_COMPLIANCE_CR_API_TOKEN", ""))
    if token:
        headers["Authorization"] = (
            token if token.lower().startswith("bearer ") else f"Bearer {token}"
        )

    raw_extra = _clean_text(_get_setting("CODE_COMPLIANCE_CR_API_HEADERS_JSON", ""))
    if raw_extra:
        try:
            parsed = json.loads(raw_extra)
        except json.JSONDecodeError as exc:
            raise HttpError(500, f"代码合规数据湖请求头配置非法: {exc}") from exc
        if not isinstance(parsed, dict):
            raise HttpError(500, "代码合规数据湖请求头配置必须是 JSON 对象")
        for key, value in parsed.items():
            text = _clean_text(value)
            if key and text:
                headers[str(key)] = text
    return headers


def _extract_count(raw: Any) -> int:
    """从 only_count 响应中提取 merged/all 统计数量。"""
    if isinstance(raw, dict):
        for key in ("merged", "all", "total", "count"):
            if key in raw:
                return _safe_int(raw.get(key))
        for key in ("data", "result"):
            if isinstance(raw.get(key), dict):
                count = _extract_count(raw[key])
                if count:
                    return count
    return 0


def _extract_detail_rows(raw: Any) -> list[dict[str, Any]]:
    """兼容列表、data/result/items/dataList 等常见上游包裹格式。"""
    if isinstance(raw, list):
        candidates = raw
    elif isinstance(raw, dict):
        candidates = []
        for key in ("items", "dataList", "records", "result", "data"):
            value = raw.get(key)
            if isinstance(value, list):
                candidates = value
                break
            if isinstance(value, dict):
                nested = _extract_detail_rows(value)
                if nested:
                    return nested
    else:
        candidates = []

    rows: list[dict[str, Any]] = []
    for item in candidates:
        node = item.get("data") if isinstance(item, dict) and isinstance(item.get("data"), dict) else item
        if isinstance(node, dict):
            rows.append(node)
    return rows


class CodeComplianceCRClient:
    """代码合规 CR 数据湖 client，封装真实 GET 请求和开发期 mock。"""

    def __init__(self):
        self.url_template = DEFAULT_CR_API_URL_TEMPLATE
        self.force_mock = _to_bool(_get_setting("CODE_COMPLIANCE_CR_FORCE_MOCK", False), False)
        self.timeout = DEFAULT_API_TIMEOUT
        self.verify_ssl = DEFAULT_API_VERIFY_SSL

    def fetch_count(
        self,
        *,
        group_id: str,
        target_branch: str,
        projects: Iterable[str],
        merged_after: datetime,
        merged_before: datetime,
    ) -> int:
        """请求 only_count=True 的统计结果。"""
        params = build_cr_request_params(
            page=1,
            per_page=1,
            target_branch=target_branch,
            projects=projects,
            merged_after=merged_after,
            merged_before=merged_before,
            only_count=True,
        )
        return _extract_count(self._request(params, group_id=group_id))

    def fetch_page(
        self,
        *,
        group_id: str,
        page: int,
        per_page: int,
        target_branch: str,
        projects: Iterable[str],
        merged_after: datetime,
        merged_before: datetime,
    ) -> list[dict[str, Any]]:
        """请求 only_count=False 的单页 CR 明细。"""
        params = build_cr_request_params(
            page=page,
            per_page=per_page,
            target_branch=target_branch,
            projects=projects,
            merged_after=merged_after,
            merged_before=merged_before,
            only_count=False,
        )
        rows = _extract_detail_rows(self._request(params, group_id=group_id))
        return [item for item in (normalize_cr_detail(row) for row in rows) if item]

    def fetch_all(
        self,
        *,
        group_id: str,
        target_branch: str,
        projects: Iterable[str],
        merged_after: datetime,
        merged_before: datetime,
        per_page: int = DEFAULT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        """先取总数再分页拉取全量 CR 明细。"""
        project_values = [_clean_text(item) for item in projects if _clean_text(item)]
        total = self.fetch_count(
            group_id=group_id,
            target_branch=target_branch,
            projects=project_values,
            merged_after=merged_after,
            merged_before=merged_before,
        )
        if total <= 0:
            return []

        safe_per_page = max(min(int(per_page or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE), 1)
        total_pages = max(math.ceil(total / safe_per_page), 1)
        rows: list[dict[str, Any]] = []
        for page in range(1, total_pages + 1):
            rows.extend(
                self.fetch_page(
                    group_id=group_id,
                    page=page,
                    per_page=safe_per_page,
                    target_branch=target_branch,
                    projects=project_values,
                    merged_after=merged_after,
                    merged_before=merged_before,
                )
            )
        return rows

    def _request(self, params: CRRequestParams, *, group_id: str) -> Any:
        """按配置在 mock 和真实数据湖 GET 请求之间切换。"""
        if self.force_mock:
            logger.info("CodeCompliance CR data lake mock group_id=%s params=%s", group_id, params)
            return _mock_response(params)

        request_url = build_cr_request_url(self.url_template, group_id, params)
        try:
            response = requests.get(
                request_url,
                headers=_build_request_headers(),
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:
            raise HttpError(502, f"请求代码合规数据湖失败: {exc}") from exc

        if response.status_code >= 400:
            raise HttpError(502, f"代码合规数据湖响应异常: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise HttpError(502, "代码合规数据湖响应不是合法 JSON") from exc


def _mock_response(params: CRRequestParams) -> Any:
    """返回与真实 CR 数据湖同构的开发期 mock 数据。"""
    rows = _mock_rows(params)
    if params.get("only_count") == "True":
        return {
            "all": len(rows),
            "opened": 0,
            "closed": 0,
            "merged": len(rows),
        }

    page = max(_safe_int(params.get("page")), 1)
    per_page = max(min(_safe_int(params.get("per_page")) or DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE), 1)
    start = (page - 1) * per_page
    end = start + per_page
    return rows[start:end]


def _get_project_values(params: CRRequestParams) -> list[str]:
    """兼容数组项目参数和旧逗号字符串，供 mock 与测试复用。"""
    raw_projects = params.get("projects", [])
    if isinstance(raw_projects, list):
        return [_clean_text(item) for item in raw_projects if _clean_text(item)]
    return [_clean_text(item) for item in _clean_text(raw_projects).split(",") if _clean_text(item)]


def _mock_rows(params: CRRequestParams) -> list[dict[str, Any]]:
    """按项目和分支生成稳定 mock；发布分支固定缺少部分主干 change_key。"""
    projects = _get_project_values(params)
    branch = _clean_text(params.get("target_branch"))
    merged_after = parse_data_lake_datetime(params.get("merged_after")) or timezone.now()
    rows: list[dict[str, Any]] = []
    for project_id in projects:
        seed = hashlib.md5(f"{project_id}:{branch}".encode("utf-8")).hexdigest()
        rng = random.Random(seed)
        is_release = "release" in branch.lower() or "rel" in branch.lower()
        for index in range(1, 9):
            # 发布分支少返回一部分 key，便于前端和后端联调时稳定看到漏合风险。
            if is_release and index % 3 == 0:
                continue
            change_key = f"mock-{project_id}-{index:03d}"
            merged_at = merged_after + timedelta(minutes=index * 7)
            rows.append(
                {
                    "project_id": project_id,
                    "change_request_iid": str(10_000 + index),
                    "change_key": change_key,
                    "title": f"Mock CR {index:03d} for {project_id}",
                    "description": f"Mock change {change_key} merged into {branch}",
                    "web_url": f"https://git.example.com/{project_id}/merge_requests/{index}",
                    "added_lines": rng.randint(10, 180),
                    "removed_lines": rng.randint(1, 90),
                    "merged_at": format_data_lake_datetime(merged_at),
                    "target_branch": branch,
                    "author": {"username": f"user{index:02d}"},
                }
            )
    return rows
