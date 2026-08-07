import logging
import os
import threading
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import close_old_connections, transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from apps.code_scan.models import ScanProject, ScanResult, ScanResultOccurrence, ScanTask
from core.user.user_model import User

from .integration_models import (
    IntegrationDomainDirectoryRule,
    IntegrationDomainDirectorySet,
    IntegrationDtFuzzSnapshot,
    IntegrationEmailDelivery,
    IntegrationEmailSubscription,
    IntegrationMetricDefinition,
    IntegrationProjectConfig,
    IntegrationProjectMetricValue,
)
from .integration_fetcher import IntegrationDataFetcher
from .integration_schema import DtFuzzNode, MetricCell, ProjectConfigOut
from .integration_email import build_daily_email_html, send_html_email


CODE_KEYS = [
    "codecheck_error_num",
    "dt_bin_error_num",
    "cooddy_check_error_num",
    "bin_scope_error_num",
    "build_check_error_num",
    "compile_error_num",
    "tscan_error_num",
    "tsan_error_num",
    "valgrind_error_num",
    "cppcheck_error_num",
    "weggli_error_num",
    "cooddy_error_num",
    "binexplorer_error_num",
    "clang_tidy_error_num",
]
DT_KEYS = [
    "dt_pass_rate",
    "dt_pass_num",
    "dt_line_coverage",
    "dt_method_coverage",
]

DOMAIN_METRIC_TASK_FIELDS = {
    "codecheck_error_num": ("code_check_task_ids", "code_check_task_id", "codecheck"),
    "dt_bin_error_num": ("dt_bin_task_ids", "dt_bin_task_id", "dt-bin"),
    "cooddy_check_error_num": (
        "cooddy_check_task_ids",
        "cooddy_check_task_id",
        "cooddy-check",
    ),
    "bin_scope_error_num": ("bin_scope_task_ids", "bin_scope_task_id", "bin-scope"),
}
DOMAIN_ISSUE_PAGE_SIZE = 100
DOMAIN_METRIC_DETAIL_CACHE_TTL = 24 * 60 * 60
DOMAIN_METRIC_DETAIL_CACHE_PREFIX = "integration_report:domain_metric_detail"


class DomainMetricUpstreamError(RuntimeError):
    """责任田问题详情数据湖请求失败。"""


def _mock_domain_issue_page(task_id: str, directory: str, page: int) -> tuple[int, list[dict]]:
    """本地未配置数据湖地址时生成稳定的领域问题 Mock 数据。"""
    seed = sha256(f"{task_id}:{directory}".encode("utf-8")).hexdigest()
    total = int(seed[:2], 16) % 3 + 1
    items = []
    for index in range(total):
        line_num = 20 + int(seed[2 + index * 2 : 4 + index * 2], 16) % 180
        items.append(
            {
                "file_name": f"mock_issue_{index + 1}.c",
                "file_path": f"{directory.rstrip('/')}/mock_issue_{index + 1}.c",
                "function_name": f"mock_function_{index + 1}",
                "fragment": [
                    {
                        "line_num": str(line_num),
                        "file_path": f"{directory.rstrip('/')}/mock_issue_{index + 1}.c",
                        "description": f"Mock 问题 {index + 1}（任务 {task_id}）",
                        "codeContextStartLine": max(1, line_num - 2),
                        "codeContext": (
                            f"// Mock data for {task_id}\n"
                            f"int mock_function_{index + 1}(void) {{\n"
                            "  return 0;\n"
                            "}"
                        ),
                    }
                ],
            }
        )
    start = (page - 1) * DOMAIN_ISSUE_PAGE_SIZE
    return total, items[start : start + DOMAIN_ISSUE_PAGE_SIZE]


SCAN_METRIC_TOOL_ALIAS_MAP = {
    "tscan_error_num": {"tscan"},
    "tsan_error_num": {"tsan"},
    "valgrind_error_num": {"valgrind"},
    "cppcheck_error_num": {"cppcheck"},
    "weggli_error_num": {"weggli"},
    "cooddy_error_num": {"cooddy"},
    "binexplorer_error_num": {"binexplorer"},
    "clang_tidy_error_num": {"clang-tidy", "clang_tidy", "clangtidy"},
}

SCAN_METRIC_PRIMARY_TOOL_MAP = {
    "tscan_error_num": "tscan",
    "tsan_error_num": "tsan",
    "valgrind_error_num": "valgrind",
    "cppcheck_error_num": "cppcheck",
    "weggli_error_num": "weggli",
    "cooddy_error_num": "cooddy",
    "binexplorer_error_num": "binexplorer",
    "clang_tidy_error_num": "clang-tidy",
}
SUB_MODULE_SCOPED_METRICS = {"tsan_error_num", "valgrind_error_num"}
EXCLUDED_SHIELD_STATUSES = {"Shielded"}

logger = logging.getLogger(__name__)


def _eval_level(defn: IntegrationMetricDefinition, value: Optional[float]) -> str:
    if not defn.warn_operator or defn.warn_value is None or value is None:
        return "normal"
    op = defn.warn_operator
    threshold = defn.warn_value
    hit = False
    if op == ">":
        hit = value > threshold
    elif op == ">=":
        hit = value >= threshold
    elif op == "<":
        hit = value < threshold
    elif op == "<=":
        hit = value <= threshold
    elif op == "==":
        hit = value == threshold
    elif op == "!=":
        hit = value != threshold
    return "danger" if hit else "normal"


def _build_scan_metric_defaults() -> Dict[str, tuple[Optional[float], str]]:
    return {metric_key: (None, "") for metric_key in SCAN_METRIC_TOOL_ALIAS_MAP}


def normalize_sub_modules(raw_value) -> List[str]:
    if raw_value is None:
        return []

    if isinstance(raw_value, str):
        values = raw_value.replace(",", "\n").splitlines()
    elif isinstance(raw_value, (list, tuple, set)):
        values = raw_value
    else:
        return []

    normalized: List[str] = []
    seen: set[str] = set()
    for item in values:
        value = str(item).strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(value)
    return normalized


def normalize_dt_fuzz_branches(raw_value) -> List[str]:
    return normalize_sub_modules(raw_value)


def normalize_metric_task_ids(raw_value, legacy_value: str = "") -> List[str]:
    """归一化指标多任务 ID，保留顺序去重，并在新字段为空时兼容旧单 ID。"""
    normalized = normalize_sub_modules(raw_value)
    if normalized:
        return normalized
    legacy = (legacy_value or "").strip()
    return [legacy] if legacy else []


def _request_domain_issue_page(task_id: str, directory: str, page: int) -> tuple[int, list[dict]]:
    """请求数据湖的一页领域问题，并校验上游固定响应结构。"""
    url = (os.environ.get("INTEGRATION_REPORT_DOMAIN_ISSUE_API_URL") or "").strip()
    if not url:
        if settings.DEBUG:
            return _mock_domain_issue_page(task_id, directory, page)
        raise DomainMetricUpstreamError("未配置领域问题数据湖接口地址")

    payload = {
        "task_id": task_id,
        "file_path": directory,
        "page": page,
        "pageSize": DOMAIN_ISSUE_PAGE_SIZE,
    }
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise DomainMetricUpstreamError(f"请求数据湖失败: {exc}") from exc

    if response.status_code >= 400:
        raise DomainMetricUpstreamError(f"数据湖响应异常: HTTP {response.status_code}")
    try:
        data = response.json()
    except ValueError as exc:
        raise DomainMetricUpstreamError("数据湖响应不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise DomainMetricUpstreamError("数据湖响应格式异常")
    if data.get("status") != "success" or data.get("error"):
        raise DomainMetricUpstreamError(
            f"数据湖返回失败: {data.get('error') or data.get('status') or '未知错误'}"
        )

    result = data.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("info"), list):
        raise DomainMetricUpstreamError("数据湖响应缺少 result.info")
    try:
        total = int(result.get("total"))
    except (TypeError, ValueError) as exc:
        raise DomainMetricUpstreamError("数据湖响应 total 格式异常") from exc
    if total < 0:
        raise DomainMetricUpstreamError("数据湖响应 total 不能小于 0")

    info_items = [item for item in result["info"] if isinstance(item, dict)]
    if len(info_items) != len(result["info"]):
        raise DomainMetricUpstreamError("数据湖响应 info 包含非法条目")
    return total, info_items


def _fetch_domain_issue_info(task_id: str, directory: str) -> list[dict]:
    """按数据湖 total 顺序拉取一个 task ID 与目录下的全部问题。"""
    page = 1
    total, info_items = _request_domain_issue_page(task_id, directory, page)
    all_items = list(info_items)
    if len(all_items) > total:
        raise DomainMetricUpstreamError("数据湖首批问题数超过 total")

    # 首批数据不足 total 时继续翻页；空页意味着上游 total 与实际数据不一致。
    while len(all_items) < total:
        page += 1
        _, page_items = _request_domain_issue_page(task_id, directory, page)
        if not page_items:
            raise DomainMetricUpstreamError("数据湖分页提前返回空数据")
        all_items.extend(page_items)
        if len(all_items) > total:
            raise DomainMetricUpstreamError("数据湖分页问题数超过 total")
    return all_items


def _build_domain_metric_issue_rows(task_id: str, directory: str, info_items: list[dict]) -> list[dict]:
    """将数据湖 info 中的全部 fragment 展平为领域详情表格行。"""
    rows: list[dict] = []
    for info_index, info in enumerate(info_items):
        fragments = info.get("fragment")
        if not isinstance(fragments, list) or not fragments:
            fragments = [{}]
        for fragment_index, fragment in enumerate(fragments):
            fragment = fragment if isinstance(fragment, dict) else {}
            start_line = fragment.get("codeContextStartLine")
            try:
                start_line = int(start_line) if start_line is not None else None
            except (TypeError, ValueError):
                start_line = None
            rows.append(
                {
                    "id": f"{task_id}:{directory}:{info_index}:{fragment_index}",
                    "task_id": task_id,
                    "task_detail_url": f"http://codecheck.rnd.com/{quote(task_id, safe='')}",
                    "directory": directory,
                    "file_name": str(info.get("file_name") or ""),
                    "file_path": str(
                        fragment.get("file_path") or info.get("file_path") or ""
                    ),
                    "function_name": str(info.get("function_name") or ""),
                    "line_num": str(fragment.get("line_num") or ""),
                    "description": str(fragment.get("description") or ""),
                    "code_context_start_line": start_line,
                    "code_context": str(fragment.get("codeContext") or ""),
                }
            )
    return rows


def _domain_metric_detail_cache_key(
    config_id: str,
    record_date: date,
    metric_key: str,
) -> str:
    """生成按采集日期隔离的领域问题详情 Redis 键。"""
    return ":".join(
        [DOMAIN_METRIC_DETAIL_CACHE_PREFIX, record_date.isoformat(), str(config_id), metric_key]
    )


def _build_domain_metric_snapshot(
    config: IntegrationProjectConfig,
    record_date: date,
    metric_key: str,
) -> Optional[dict]:
    """采集单项领域指标的完整问题详情，并构造可缓存快照。"""
    if metric_key not in DOMAIN_METRIC_TASK_FIELDS:
        raise ValueError("该指标不支持按责任田领域查看详情")

    directory_set = config.domain_directory_set
    if not directory_set or directory_set.is_deleted or not directory_set.enabled:
        raise DomainMetricUpstreamError("当前项目未绑定可用的责任田目录配置")

    ensure_default_metric_definitions()
    metric = IntegrationMetricDefinition.objects.filter(
        key=metric_key,
        is_deleted=False,
    ).first()
    if not metric:
        raise ValueError("指标定义不存在")

    task_ids_field, legacy_task_id_field, _ = DOMAIN_METRIC_TASK_FIELDS[metric_key]
    task_ids = normalize_metric_task_ids(
        getattr(config, task_ids_field, []),
        getattr(config, legacy_task_id_field, ""),
    )
    if not task_ids:
        return None

    domains: list[dict] = []
    domains_by_name: dict[str, dict] = {}
    directories_by_domain: dict[str, set[str]] = defaultdict(set)
    upstream_cache: dict[tuple[str, str], list[dict]] = {}
    # 保留跨领域重复目录；同一领域的重复目录合并为一行，避免重复展示同一查看入口。
    rules = directory_set.rules.filter(is_deleted=False, enabled=True).order_by(
        "sort_order",
        "sys_create_datetime",
    )
    for rule in rules:
        domain_name = (rule.domain_name or "").strip() or "未命名领域"
        directory = (rule.directory or "").strip()
        if not directory or directory in directories_by_domain[domain_name]:
            continue
        directories_by_domain[domain_name].add(directory)
        domain = domains_by_name.get(domain_name)
        if not domain:
            domain = {"domain_name": domain_name, "issue_count": 0, "issues": []}
            domains_by_name[domain_name] = domain
            domains.append(domain)

        for task_id in task_ids:
            cache_key = (task_id, directory)
            if cache_key not in upstream_cache:
                upstream_cache[cache_key] = _fetch_domain_issue_info(task_id, directory)
            info_items = upstream_cache[cache_key]
            domain["issue_count"] += len(info_items)
            domain["issues"].extend(
                _build_domain_metric_issue_rows(task_id, directory, info_items)
            )

    if not domains:
        raise DomainMetricUpstreamError("当前项目未配置可用的责任田目录")

    return {
        "config_id": str(config.id),
        "config_name": config.name,
        "project_name": config.project.name if config.project else "",
        "record_date": record_date,
        "metric_key": metric_key,
        "metric_name": metric.name,
        "domain_directory_set_name": directory_set.name,
        "issue_count": sum(domain["issue_count"] for domain in domains),
        "domains": domains,
    }


def _cache_domain_metric_snapshot(
    config_id: str,
    record_date: date,
    metric_key: str,
    payload: dict,
) -> None:
    """将领域指标详情或采集失败信息写入 Redis 一天。"""
    cache.set(
        _domain_metric_detail_cache_key(config_id, record_date, metric_key),
        payload,
        timeout=DOMAIN_METRIC_DETAIL_CACHE_TTL,
    )


def get_domain_metric_history_details(
    config_id: str,
    record_date: date,
    metric_key: str,
) -> dict:
    """读取每日采集时写入 Redis 的领域问题详情快照。"""
    if metric_key not in DOMAIN_METRIC_TASK_FIELDS:
        raise ValueError("该指标不支持按责任田领域查看详情")
    snapshot = cache.get(_domain_metric_detail_cache_key(config_id, record_date, metric_key))
    if not isinstance(snapshot, dict):
        raise LookupError("当日领域问题明细缓存不存在或已过期")
    if snapshot.get("error"):
        raise LookupError(str(snapshot["error"]))
    return snapshot


def validate_domain_metric_config_payload(payload) -> None:
    """校验按责任田领域获取的项目配置，确保开启后绑定了可用目录配置集。"""
    if not getattr(payload, "enable_domain_metrics", False):
        return

    set_id = (getattr(payload, "domain_directory_set_id", "") or "").strip()
    if not set_id:
        raise ValueError("启用按领域获取时必须选择责任田目录配置")
    if not IntegrationDomainDirectorySet.objects.filter(id=set_id, is_deleted=False).exists():
        raise ValueError("责任田目录配置不存在或已删除")


def validate_dt_fuzz_config_payload(payload) -> None:
    if not getattr(payload, "enable_dt_fuzz", False):
        return

    missing = []
    if not (payload.dt_fuzz_version_name or "").strip():
        missing.append("versionName")
    if not normalize_dt_fuzz_branches(payload.dt_fuzz_branches):
        missing.append("branch")
    if not (payload.dt_fuzz_pbi_id or "").strip():
        missing.append("pbiId")
    if not (payload.dt_fuzz_domain_id or "").strip():
        missing.append("domian-id")
    if not (payload.dt_fuzz_project_id or "").strip():
        missing.append("project-id")
    if missing:
        raise ValueError(f"启用 DT_FUZZ 时以下字段必填：{', '.join(missing)}")


def _record_date_end_datetime(record_date: date) -> datetime:
    """生成目标日期的结束时间，并兼容项目当前 USE_TZ 设置。"""
    naive_end = datetime.combine(record_date, time.max)
    if settings.USE_TZ:
        return timezone.make_aware(naive_end)
    return naive_end


def _dt_fuzz_due_date(record_date: date) -> str:
    return f"{record_date.isoformat()} 12:00:00"


def _is_empty_dt_fuzz_payload(payload) -> bool:
    if payload is None:
        return True
    if isinstance(payload, (list, tuple)):
        return len(payload) == 0
    if isinstance(payload, dict):
        if not payload:
            return True
        if not str(payload.get("name") or "").strip() and not payload.get("children"):
            return True
    return False


def _normalize_dt_fuzz_payload(payload):
    if isinstance(payload, list):
        return payload[0] if payload else {}
    if isinstance(payload, dict):
        return payload
    return {}


def _collect_dt_fuzz_for_config(config: IntegrationProjectConfig, record_date: date):
    if not config.enable_dt_fuzz:
        return

    branches = normalize_dt_fuzz_branches(config.dt_fuzz_branches)
    if not branches:
        return

    fetcher = IntegrationDataFetcher(config).set_date(record_date)
    today_due_date = _dt_fuzz_due_date(record_date)
    fallback_due_date = _dt_fuzz_due_date(record_date - timedelta(days=1))

    for branch in branches:
        payload = fetcher.fetch_dt_fuzz(branch, today_due_date)
        source_due_date = today_due_date
        if _is_empty_dt_fuzz_payload(payload):
            payload = fetcher.fetch_dt_fuzz(branch, fallback_due_date)
            source_due_date = fallback_due_date
        if _is_empty_dt_fuzz_payload(payload):
            continue

        normalized_payload = _normalize_dt_fuzz_payload(payload)
        IntegrationDtFuzzSnapshot.objects.update_or_create(
            config=config,
            record_date=record_date,
            branch=branch,
            defaults={
                "source_due_date": source_due_date,
                "raw_payload": payload,
                "tree_payload": normalized_payload,
                "is_deleted": False,
            },
        )


def _stringify_dt_fuzz_value(payload: dict, key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    return str(value)


def build_dt_fuzz_node(payload: dict, branch: str, owner: str, prefix: str) -> DtFuzzNode:
    children_payload = payload.get("children") if isinstance(payload, dict) else []
    if not isinstance(children_payload, list):
        children_payload = []
    name = _stringify_dt_fuzz_value(payload, "name") or "-"
    node_key = f"{prefix}:{name}"
    children = [
        build_dt_fuzz_node(child, branch, owner, f"{node_key}:{index}")
        for index, child in enumerate(children_payload)
        if isinstance(child, dict)
    ]
    return DtFuzzNode(
        node_key=node_key,
        name=name,
        type=_stringify_dt_fuzz_value(payload, "type"),
        highRiskApiCover=_stringify_dt_fuzz_value(payload, "highRiskApiCover"),
        highRiskApiTotal=_stringify_dt_fuzz_value(payload, "highRiskApiTotal"),
        highRiskApiCoverage=_stringify_dt_fuzz_value(payload, "highRiskApiCoverage"),
        secLineCover=_stringify_dt_fuzz_value(payload, "secLineCover"),
        secLineTotal=_stringify_dt_fuzz_value(payload, "secLineTotal"),
        secLineCoverage=_stringify_dt_fuzz_value(payload, "secLineCoverage"),
        secReportUrl=_stringify_dt_fuzz_value(payload, "secReportUrl"),
        lcovLineCover=_stringify_dt_fuzz_value(payload, "lcovLineCover"),
        lcovLineTotal=_stringify_dt_fuzz_value(payload, "lcovLineTotal"),
        lcovLineCoverage=_stringify_dt_fuzz_value(payload, "lcovLineCoverage"),
        lcovReportUrl=_stringify_dt_fuzz_value(payload, "lcovReportUrl"),
        defectNumber=_stringify_dt_fuzz_value(payload, "defectNumber"),
        casePass=_stringify_dt_fuzz_value(payload, "casePass"),
        casePassRate=_stringify_dt_fuzz_value(payload, "casePassRate"),
        caseActive=_stringify_dt_fuzz_value(payload, "caseActive"),
        caseActiveRate=_stringify_dt_fuzz_value(payload, "caseActiveRate"),
        caseTotal=_stringify_dt_fuzz_value(payload, "caseTotal"),
        reportUrl=_stringify_dt_fuzz_value(payload, "reportUrl"),
        branch=branch,
        owner=owner,
        children=children,
    )


def _build_code_scan_detail_url(
    scan_project_id: str,
    metric_key: str,
    sub_modules: Optional[List[str]] = None,
) -> str:
    params = {"projectId": str(scan_project_id)}
    tool_name = SCAN_METRIC_PRIMARY_TOOL_MAP.get(metric_key)
    if tool_name:
        params["tool"] = tool_name
    if sub_modules:
        params["sub_modules"] = ",".join(sub_modules)
    return f"/code_scan/result?{urlencode(params)}"


def _count_code_scan_results_by_task(task_ids: List[str]) -> Dict[str, float]:
    if not task_ids:
        return {}

    count_map: Dict[str, float] = {}
    occurrence_counts = (
        ScanResultOccurrence.objects.filter(task_id__in=task_ids, is_deleted=False)
        .exclude(shield_status__in=EXCLUDED_SHIELD_STATUSES)
        .values("task_id")
        .annotate(cnt=Count("id"))
    )
    legacy_counts = (
        ScanResult.objects.filter(
            task_id__in=task_ids,
            is_deleted=False,
            normalized_occurrence__isnull=True,
        )
        .exclude(shield_status__in=EXCLUDED_SHIELD_STATUSES)
        .values("task_id")
        .annotate(cnt=Count("id"))
    )
    for row in occurrence_counts:
        task_id = str(row["task_id"])
        count_map[task_id] = count_map.get(task_id, 0.0) + float(row["cnt"])
    for row in legacy_counts:
        task_id = str(row["task_id"])
        count_map[task_id] = count_map.get(task_id, 0.0) + float(row["cnt"])
    return count_map


def _count_results_for_sub_modules(
    scan_project: ScanProject,
    tool_name: str,
    record_date: date,
    sub_modules: List[str],
) -> tuple[float, list[str]]:
    """按子模块匹配当天已产生的最新扫描任务，并统计对应问题数。"""
    module_lower_set = {item.lower() for item in sub_modules}
    record_end = _record_date_end_datetime(record_date)
    tasks = (
        ScanTask.objects.filter(
            is_deleted=False,
            project=scan_project,
            tool_name=tool_name,
            status="success",
            # 以当天结束时间作为边界，避免数据库 DATE cast 或时区差异漏掉当天任务。
            sys_create_datetime__lte=record_end,
        )
        .order_by("-sys_create_datetime")
        .values("id", "sub_module")
    )

    latest_task_by_module: Dict[str, str] = {}
    unscoped_fallback_task_id = ""
    for task in tasks:
        module_value = str(task.get("sub_module") or "").strip()
        if not module_value:
            if not unscoped_fallback_task_id:
                unscoped_fallback_task_id = str(task["id"])
            continue
        lowered = module_value.lower()
        if lowered not in module_lower_set:
            continue
        if lowered in latest_task_by_module:
            continue
        latest_task_by_module[lowered] = str(task["id"])
        if len(latest_task_by_module) == len(module_lower_set):
            break

    task_ids = list(set(latest_task_by_module.values()))
    if not task_ids and unscoped_fallback_task_id:
        task_ids = [unscoped_fallback_task_id]
        logger.warning(
            "code_scan sub_module fallback: project_key=%s tool=%s configured_sub_modules=%s fallback_task_id=%s",
            scan_project.project_key,
            tool_name,
            sub_modules,
            unscoped_fallback_task_id,
        )
    if not task_ids:
        return 0.0, []
    count = sum(_count_code_scan_results_by_task(task_ids).values())
    return count, task_ids


def _fetch_code_scan_metrics(
    config: IntegrationProjectConfig,
    record_date: date,
) -> Dict[str, tuple[Optional[float], str]]:
    """从代码扫描模块读取最新任务并转换为集成报告指标。"""
    metric_payload = _build_scan_metric_defaults()
    project_key = (config.code_scan_project_key or "").strip()
    if not project_key:
        return metric_payload

    scan_project = ScanProject.objects.filter(
        is_deleted=False,
        project_key=project_key,
    ).first()
    if not scan_project:
        return metric_payload

    fallback_urls = {
        key: _build_code_scan_detail_url(scan_project.id, key)
        for key in SCAN_METRIC_TOOL_ALIAS_MAP
    }

    latest_task_by_metric: Dict[str, str] = {}
    record_end = _record_date_end_datetime(record_date)
    tasks = (
        ScanTask.objects.filter(
            is_deleted=False,
            project=scan_project,
            status="success",
            # 取目标日期当天结束前的最新任务，保证当天晚些时候生成的任务可被统计。
            sys_create_datetime__lte=record_end,
        )
        .order_by("-sys_create_datetime")
        .values("id", "tool_name")
    )
    for item in tasks:
        raw_tool = (item.get("tool_name") or "").strip().lower()
        if not raw_tool:
            continue
        for metric_key, aliases in SCAN_METRIC_TOOL_ALIAS_MAP.items():
            if raw_tool in aliases and metric_key not in latest_task_by_metric:
                latest_task_by_metric[metric_key] = str(item["id"])

    if latest_task_by_metric:
        task_ids = list(set(latest_task_by_metric.values()))
        count_map = _count_code_scan_results_by_task(task_ids)
        for metric_key, task_id in latest_task_by_metric.items():
            if metric_key in SUB_MODULE_SCOPED_METRICS:
                continue
            metric_payload[metric_key] = (
                count_map.get(task_id, 0.0),
                fallback_urls[metric_key],
            )

    shared_modules = normalize_sub_modules(
        getattr(config, "valgrind_sub_modules", []),
    )
    metric_modules_map = {
        metric_key: shared_modules
        for metric_key in SUB_MODULE_SCOPED_METRICS
    }
    for metric_key in SUB_MODULE_SCOPED_METRICS:
        bound_modules = metric_modules_map.get(metric_key) or []
        if not bound_modules:
            metric_payload[metric_key] = (None, "")
            continue
        tool_name = SCAN_METRIC_PRIMARY_TOOL_MAP[metric_key]
        count, _ = _count_results_for_sub_modules(
            scan_project=scan_project,
            tool_name=tool_name,
            record_date=record_date,
            sub_modules=bound_modules,
        )
        metric_payload[metric_key] = (
            count,
            _build_code_scan_detail_url(
                scan_project.id,
                metric_key,
                sub_modules=bound_modules,
            ),
        )

    if not latest_task_by_metric and not shared_modules:
        return {
            key: (
                None,
                "" if key in SUB_MODULE_SCOPED_METRICS else fallback_urls[key],
            )
            for key in SCAN_METRIC_TOOL_ALIAS_MAP
        }

    for metric_key, (value, url) in list(metric_payload.items()):
        if url or metric_key in SUB_MODULE_SCOPED_METRICS:
            continue
        metric_payload[metric_key] = (value, fallback_urls[metric_key])

    return metric_payload


def ensure_default_metric_definitions():
    defaults = [
        ("code", "codecheck_error_num", "CodeCheck 错误数", "number", "", ">", 0),
        ("code", "dt_bin_error_num", "DT_Bin错误数", "number", "", ">", 0),
        ("code", "cooddy_check_error_num", "Cooddy Check错误数", "number", "", ">", 0),
        ("code", "bin_scope_error_num", "Bin Scope 错误数", "number", "", ">", 0),
        ("code", "build_check_error_num", "Build 检测错误数", "number", "", ">", 0),
        ("code", "compile_error_num", "Compile 错误数", "number", "", ">", 0),
        ("code", "tscan_error_num", "TScan 问题数", "number", "", ">", 0),
        ("code", "tsan_error_num", "TSan 问题数", "number", "", ">", 0),
        ("code", "valgrind_error_num", "Valgrind 问题数", "number", "", ">", 0),
        ("code", "cppcheck_error_num", "Cppcheck 问题数", "number", "", ">", 0),
        ("code", "weggli_error_num", "Weggli 问题数", "number", "", ">", 0),
        ("code", "cooddy_error_num", "Cooddy问题数（代码扫描）", "number", "", ">", 0),
        ("code", "binexplorer_error_num", "BinExplorer 问题数", "number", "", ">", 0),
        ("code", "clang_tidy_error_num", "Clang-Tidy 问题数", "number", "", ">", 0),
        ("dt", "dt_pass_rate", "DT 通过率", "percent", "%", "<", 95),
        ("dt", "dt_pass_num", "DT 通过数", "number", "", "", None),
        ("dt", "dt_line_coverage", "行覆盖率", "percent", "%", "<", 80),
        ("dt", "dt_method_coverage", "方法覆盖率", "percent", "%", "<", 75),
    ]
    for group, key, name, value_type, unit, op, warn in defaults:
        IntegrationMetricDefinition.objects.update_or_create(
            key=key,
            defaults={
                "group": group,
                "name": name,
                "value_type": value_type,
                "unit": unit,
                "warn_operator": op or "",
                "warn_value": warn,
                "enabled": True,
            },
        )


@transaction.atomic
def collect_daily_metrics(record_date: Optional[date] = None, config_ids: Optional[List[str]] = None):
    """
    采集每日指标数据。
    使用 IntegrationDataFetcher 根据配置中的各个 ID 获取数据。
    """
    ensure_default_metric_definitions()
    if record_date is None:
        record_date = date.today()

    configs = IntegrationProjectConfig.objects.select_related(
        "project",
        "domain_directory_set",
    ).filter(is_deleted=False, enabled=True)
    if config_ids:
        configs = configs.filter(id__in=config_ids)
    def_map = {d.key: d for d in IntegrationMetricDefinition.objects.filter(is_deleted=False, enabled=True)}

    for cfg in configs:
        fetcher = IntegrationDataFetcher(cfg).set_date(record_date)
        payload = fetcher.fetch_metrics()
        domain_metric_errors: set[str] = set()
        if cfg.enable_domain_metrics:
            for metric_key in DOMAIN_METRIC_TASK_FIELDS:
                try:
                    snapshot = _build_domain_metric_snapshot(cfg, record_date, metric_key)
                    if snapshot is None:
                        cache.delete(
                            _domain_metric_detail_cache_key(
                                str(cfg.id),
                                record_date,
                                metric_key,
                            )
                        )
                        payload[metric_key] = (None, "")
                        continue
                    _cache_domain_metric_snapshot(
                        str(cfg.id),
                        record_date,
                        metric_key,
                        snapshot,
                    )
                    payload[metric_key] = (float(snapshot["issue_count"]), "")
                except DomainMetricUpstreamError as exc:
                    domain_metric_errors.add(metric_key)
                    _cache_domain_metric_snapshot(
                        str(cfg.id),
                        record_date,
                        metric_key,
                        {"error": str(exc)},
                    )
                    payload[metric_key] = (None, "")
        payload.update(_fetch_code_scan_metrics(cfg, record_date))

        for key, (val, url) in payload.items():
            defn = def_map.get(key)
            if not defn:
                continue
            IntegrationProjectMetricValue.objects.update_or_create(
                config=cfg,
                record_date=record_date,
                metric=defn,
                defaults={
                    "value_number": val,
                    "value_text": (
                        "error"
                        if key in domain_metric_errors
                        else ""
                        if key in SCAN_METRIC_TOOL_ALIAS_MAP or val is not None or not url
                        else ("error" if val is None else "")
                    ),
                    "detail_url": url,
                },
            )
        _collect_dt_fuzz_for_config(cfg, record_date)


def collect_daily_metrics_async(record_date: Optional[date] = None, config_ids: Optional[List[str]] = None):
    normalized_config_ids = [
        str(config_id).strip()
        for config_id in (config_ids or [])
        if str(config_id).strip()
    ]
    target_date = record_date or date.today()

    def _worker():
        close_old_connections()
        try:
            logger.info(
                "integration report mock collect started: date=%s, config_count=%s",
                target_date.isoformat(),
                len(normalized_config_ids) or "all",
            )
            collect_daily_metrics(
                record_date=target_date,
                config_ids=normalized_config_ids or None,
            )
            logger.info(
                "integration report mock collect finished: date=%s, config_count=%s",
                target_date.isoformat(),
                len(normalized_config_ids) or "all",
            )
        except Exception:
            logger.exception(
                "integration report mock collect failed: date=%s, config_count=%s",
                target_date.isoformat(),
                len(normalized_config_ids) or "all",
            )
        finally:
            close_old_connections()

    threading.Thread(
        target=_worker,
        name="integration-report-mock-collect",
        daemon=True,
    ).start()


# 保持兼容性，指向新函数
mock_collect_daily = collect_daily_metrics
mock_collect_daily_async = collect_daily_metrics_async


def list_configs_with_latest(user: User, keyword: Optional[str] = None) -> List[ProjectConfigOut]:
    ensure_default_metric_definitions()

    configs = (
        IntegrationProjectConfig.objects.select_related("project", "domain_directory_set")
        .prefetch_related("managers")
        .filter(is_deleted=False)
        .order_by("-sys_update_datetime")
    )
    if keyword:
        configs = configs.filter(
            Q(name__icontains=keyword) | Q(project__name__icontains=keyword),
        )
    subscribed_ids = set(
        IntegrationEmailSubscription.objects.filter(
            is_deleted=False,
            user=user,
            enabled=True,
            config__is_deleted=False,
        ).values_list("config_id", flat=True)
    )
    latest_dates = (
        IntegrationProjectMetricValue.objects.filter(is_deleted=False)
        .values("config_id")
        .annotate(latest=Max("record_date"))
    )
    latest_map = {row["config_id"]: row["latest"] for row in latest_dates}

    def_map = {d.key: d for d in IntegrationMetricDefinition.objects.filter(is_deleted=False, enabled=True)}

    result = []
    for cfg in configs:
        proj = cfg.project
        latest_date = latest_map.get(str(cfg.id))
        values = []
        if latest_date:
            values = list(
                IntegrationProjectMetricValue.objects.select_related("metric")
                .filter(is_deleted=False, config=cfg, record_date=latest_date, metric__enabled=True)
            )
        cell_by_key: Dict[str, MetricCell] = {}
        for v in values:
            defn = v.metric
            val = v.value_number
            unit = defn.unit
            cell_by_key[defn.key] = MetricCell(
                key=defn.key,
                name=defn.name,
                value=val,
                text=v.value_text,
                unit=unit,
                url=v.detail_url or "",
                level=_eval_level(defn, val),
            )

        def make_cells(keys: List[str]) -> List[MetricCell]:
            cells = []
            for k in keys:
                d = def_map.get(k)
                if not d:
                    continue
                cells.append(cell_by_key.get(k) or MetricCell(key=k, name=d.name, unit=d.unit))
            return cells

        proj_managers_str = ",".join([m.name or m.username for m in proj.managers.all()]) if proj else ""
        config_managers_str = ",".join([u.name or u.username for u in cfg.managers.all()])
        result.append(
            ProjectConfigOut(
                id=str(cfg.id),
                name=cfg.name,
                project_id=str(proj.id) if proj else "",
                project_name=proj.name if proj else "",
                project_domain=(proj.domain or "") if proj else "",
                project_type=proj.type if proj else "",
                project_managers=proj_managers_str,
                managers=config_managers_str,
                enabled=cfg.enabled,
                subscribed=str(cfg.id) in subscribed_ids,
                latest_date=latest_date,
                dt_bin_task_id=cfg.dt_bin_task_id,
                cooddy_check_task_id=cfg.cooddy_check_task_id,
                enable_domain_metrics=cfg.enable_domain_metrics,
                domain_directory_set_id=str(cfg.domain_directory_set_id or ""),
                domain_directory_set_name=cfg.domain_directory_set.name if cfg.domain_directory_set else "",
                code_check_task_ids=normalize_metric_task_ids(
                    cfg.code_check_task_ids,
                    cfg.code_check_task_id,
                ),
                dt_bin_task_ids=normalize_metric_task_ids(
                    cfg.dt_bin_task_ids,
                    cfg.dt_bin_task_id,
                ),
                cooddy_check_task_ids=normalize_metric_task_ids(
                    cfg.cooddy_check_task_ids,
                    cfg.cooddy_check_task_id,
                ),
                bin_scope_task_ids=normalize_metric_task_ids(
                    cfg.bin_scope_task_ids,
                    cfg.bin_scope_task_id,
                ),
                code_scan_project_key=cfg.code_scan_project_key,
                valgrind_sub_modules=normalize_sub_modules(cfg.valgrind_sub_modules),
                enable_dt_fuzz=cfg.enable_dt_fuzz,
                dt_fuzz_version_name=cfg.dt_fuzz_version_name,
                dt_fuzz_branches=normalize_dt_fuzz_branches(cfg.dt_fuzz_branches),
                dt_fuzz_pbi_id=cfg.dt_fuzz_pbi_id,
                dt_fuzz_domain_id=cfg.dt_fuzz_domain_id,
                dt_fuzz_project_id=cfg.dt_fuzz_project_id,
                code_metrics=make_cells(CODE_KEYS),
                dt_metrics=make_cells(DT_KEYS),
            )
        )
    return result


@transaction.atomic
def toggle_subscription(user: User, config_id: str, enabled: bool) -> bool:
    if not IntegrationProjectConfig.objects.filter(id=config_id, is_deleted=False).exists():
        raise ValueError("配置不存在")
    sub, _ = IntegrationEmailSubscription.objects.update_or_create(
        user=user,
        config_id=config_id,
        defaults={"enabled": enabled},
    )
    return sub.enabled


def send_daily_emails(record_date: Optional[date] = None) -> int:
    if record_date is None:
        record_date = date.today()

    ensure_default_metric_definitions()
    subs = (
        IntegrationEmailSubscription.objects.select_related("user", "config", "config__project")
        .filter(
            is_deleted=False,
            enabled=True,
            user__is_active=True,
            config__is_deleted=False,
            config__enabled=True,
        )
        .order_by("user_id")
    )
    by_user: Dict[str, List[IntegrationProjectConfig]] = defaultdict(list)
    for s in subs:
        by_user[str(s.user_id)].append(s.config)

    if not by_user:
        return 0

    config_ids = sorted({str(cfg.id) for cfgs in by_user.values() for cfg in cfgs})
    collect_daily_metrics(record_date=record_date, config_ids=config_ids)

    def_map = {d.key: d for d in IntegrationMetricDefinition.objects.filter(is_deleted=False, enabled=True)}
    sent = 0
    for user_id, configs in by_user.items():
        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            continue
        to_email = user.email or ""
        if not to_email:
            continue

        project_rows = []
        for cfg in configs:
            qs = (
                IntegrationProjectMetricValue.objects.select_related("metric")
                .filter(is_deleted=False, config=cfg, record_date=record_date)
            )
            cell_by_key = {}
            for v in qs:
                defn = v.metric
                val = v.value_number
                cell_by_key[defn.key] = MetricCell(
                    key=defn.key,
                    name=defn.name,
                    value=val,
                    text=v.value_text,
                    unit=defn.unit,
                    url=v.detail_url or "",
                    level=_eval_level(defn, val),
                )

            code_cells = [cell_by_key.get(k) or MetricCell(key=k, name=def_map[k].name, unit=def_map[k].unit) for k in CODE_KEYS if k in def_map]
            dt_cells = [cell_by_key.get(k) or MetricCell(key=k, name=def_map[k].name, unit=def_map[k].unit) for k in DT_KEYS if k in def_map]
            project_rows.append(
                {
                    "project_name": cfg.name,  # Use Config Name as Display Name
                    "project_domain": (cfg.project.domain or "") if cfg.project else "",
                    "code_metrics": code_cells,
                    "dt_metrics": dt_cells,
                }
            )

        subject = f"每日集成报告 {record_date.isoformat()}"
        html = build_daily_email_html(record_date, project_rows)
        delivery = IntegrationEmailDelivery.objects.create(
            record_date=record_date,
            user_id=user_id,
            to_email=to_email,
            subject=subject,
            status="pending",
        )
        try:
            send_html_email(to_email, subject, html)
            delivery.status = "sent"
            delivery.save(update_fields=["status"])
            sent += 1
        except Exception as e:
            delivery.status = "failed"
            delivery.error_message = str(e)
            delivery.save(update_fields=["status", "error_message"])
    return sent


def _normalize_page(page: Optional[int], page_size: Optional[int]) -> tuple[int, int]:
    """规范分页参数，避免管理页传入异常分页值导致切片错误。"""
    normalized_page = max(int(page or 1), 1)
    normalized_page_size = min(max(int(page_size or 20), 1), 5000)
    return normalized_page, normalized_page_size


def _serialize_domain_directory_set_row(directory_set: IntegrationDomainDirectorySet) -> dict:
    """序列化责任田目录配置集列表行，并统计领域和目录数量。"""
    cached_rules = getattr(directory_set, "_prefetched_objects_cache", {}).get("rules")
    if cached_rules is not None:
        active_rules = [rule for rule in cached_rules if not rule.is_deleted]
        domain_count = len({rule.domain_name for rule in active_rules})
        directory_count = len(active_rules)
    else:
        rule_qs = directory_set.rules.filter(is_deleted=False)
        domain_count = rule_qs.values("domain_name").distinct().count()
        directory_count = rule_qs.count()
    return {
        "id": str(directory_set.id),
        "name": directory_set.name,
        "description": directory_set.description,
        "enabled": directory_set.enabled,
        "domain_count": domain_count,
        "directory_count": directory_count,
        "sys_update_datetime": directory_set.sys_update_datetime,
    }


def query_domain_directory_sets(filters):
    """分页查询责任田目录配置集。"""
    page, page_size = _normalize_page(filters.page, filters.page_size)
    qs = IntegrationDomainDirectorySet.objects.filter(is_deleted=False)
    if filters.keyword:
        qs = qs.filter(
            Q(name__icontains=filters.keyword)
            | Q(description__icontains=filters.keyword)
            | Q(rules__domain_name__icontains=filters.keyword)
            | Q(rules__directory__icontains=filters.keyword),
        )
    if filters.enabled is not None:
        qs = qs.filter(enabled=filters.enabled)
    qs = qs.distinct().prefetch_related("rules").order_by("-sys_update_datetime")

    count = qs.count()
    rows = [
        _serialize_domain_directory_set_row(item)
        for item in qs[(page - 1) * page_size : page * page_size]
    ]
    return rows, count, page, page_size


def list_domain_directory_set_options():
    """查询可绑定到项目配置的启用责任田目录配置集。"""
    return [
        {"id": str(item.id), "name": item.name}
        for item in IntegrationDomainDirectorySet.objects.filter(
            is_deleted=False,
            enabled=True,
        ).order_by("name")
    ]


def get_domain_directory_set_detail(set_id: str) -> dict:
    """查询责任田目录配置集详情和完整规则列表。"""
    directory_set = IntegrationDomainDirectorySet.objects.filter(
        id=set_id,
        is_deleted=False,
    ).first()
    if not directory_set:
        raise ValueError("责任田目录配置不存在")
    row = _serialize_domain_directory_set_row(directory_set)
    row["rules"] = [
        {
            "id": str(rule.id),
            "domain_name": rule.domain_name,
            "directory": rule.directory,
            "sort_order": rule.sort_order,
            "enabled": rule.enabled,
        }
        for rule in directory_set.rules.filter(is_deleted=False).order_by(
            "sort_order",
            "sys_create_datetime",
        )
    ]
    return row


def _normalize_domain_directory_rules(rules) -> List[dict]:
    """清洗责任田目录规则，保留重复目录配置，不添加业务唯一性限制。"""
    normalized = []
    for index, rule in enumerate(rules or []):
        domain_name = (rule.domain_name or "").strip()
        directory = (rule.directory or "").strip()
        if not domain_name and not directory:
            continue
        if not domain_name or not directory:
            raise ValueError("责任田领域和目录均不能为空")
        normalized.append(
            {
                "domain_name": domain_name,
                "directory": directory,
                "sort_order": rule.sort_order if rule.sort_order is not None else index,
                "enabled": rule.enabled,
            }
        )
    return normalized


@transaction.atomic
def create_domain_directory_set(payload) -> str:
    """创建责任田目录配置集和规则。"""
    name = (payload.name or "").strip()
    if not name:
        raise ValueError("配置集名称不能为空")
    directory_set = IntegrationDomainDirectorySet.objects.create(
        name=name,
        description=(payload.description or "").strip(),
        enabled=payload.enabled,
    )
    for rule in _normalize_domain_directory_rules(payload.rules):
        IntegrationDomainDirectoryRule.objects.create(directory_set=directory_set, **rule)
    return str(directory_set.id)


@transaction.atomic
def update_domain_directory_set(set_id: str, payload) -> bool:
    """更新责任田目录配置集，规则采用全量替换以保持页面维护语义简单明确。"""
    directory_set = IntegrationDomainDirectorySet.objects.filter(
        id=set_id,
        is_deleted=False,
    ).first()
    if not directory_set:
        raise ValueError("责任田目录配置不存在")
    name = (payload.name or "").strip()
    if not name:
        raise ValueError("配置集名称不能为空")
    directory_set.name = name
    directory_set.description = (payload.description or "").strip()
    directory_set.enabled = payload.enabled
    directory_set.save(update_fields=["name", "description", "enabled", "sys_update_datetime"])
    directory_set.rules.filter(is_deleted=False).update(is_deleted=True)
    for rule in _normalize_domain_directory_rules(payload.rules):
        IntegrationDomainDirectoryRule.objects.create(directory_set=directory_set, **rule)
    return True


@transaction.atomic
def delete_domain_directory_set(set_id: str) -> bool:
    """软删除责任田目录配置集，同时保留项目上的历史绑定字段供审计。"""
    directory_set = IntegrationDomainDirectorySet.objects.filter(
        id=set_id,
        is_deleted=False,
    ).first()
    if not directory_set:
        raise ValueError("责任田目录配置不存在")
    directory_set.is_deleted = True
    directory_set.enabled = False
    directory_set.save(update_fields=["is_deleted", "enabled", "sys_update_datetime"])
    directory_set.rules.filter(is_deleted=False).update(is_deleted=True, enabled=False)
    return True


def _join_subscription_user_names(users) -> str:
    """拼接订阅管理列表中展示的负责人名称。"""
    return ",".join([user.name or user.username for user in users])


def _get_subscription_config(config_id: str) -> IntegrationProjectConfig:
    """获取可管理的集成报告配置，不存在时抛出业务异常。"""
    config = IntegrationProjectConfig.objects.filter(
        id=config_id,
        is_deleted=False,
    ).first()
    if not config:
        raise ValueError("配置不存在")
    return config


def _validate_subscription_user_ids(user_ids: List[str]) -> List[str]:
    """校验订阅用户 ID，并保持前端选择顺序去重。"""
    normalized_ids = list(dict.fromkeys([str(user_id).strip() for user_id in user_ids if str(user_id).strip()]))
    if not normalized_ids:
        return []

    found_ids = set(
        User.objects.filter(
            id__in=normalized_ids,
            is_deleted=False,
        ).values_list("id", flat=True)
    )
    missing_ids = [user_id for user_id in normalized_ids if user_id not in found_ids]
    if missing_ids:
        raise ValueError(f"用户不存在或已删除: {', '.join(missing_ids)}")
    return normalized_ids


def _validate_subscription_config_ids(config_ids: List[str]) -> List[str]:
    """校验订阅配置 ID，并保持前端批量选择顺序去重。"""
    normalized_ids = list(dict.fromkeys([str(config_id).strip() for config_id in config_ids if str(config_id).strip()]))
    if not normalized_ids:
        return []

    found_ids = set(
        IntegrationProjectConfig.objects.filter(
            id__in=normalized_ids,
            is_deleted=False,
        ).values_list("id", flat=True)
    )
    missing_ids = [config_id for config_id in normalized_ids if config_id not in found_ids]
    if missing_ids:
        raise ValueError(f"配置不存在或已删除: {', '.join(missing_ids)}")
    return normalized_ids


def query_subscription_management_projects(filters):
    """分页查询邮件订阅管理项目配置列表。"""
    page, page_size = _normalize_page(filters.page, filters.page_size)
    qs = (
        IntegrationProjectConfig.objects.select_related("project")
        .prefetch_related("managers", "project__managers")
        .filter(is_deleted=False)
        .annotate(
            subscriber_count=Count(
                "subscriptions",
                filter=Q(subscriptions__is_deleted=False, subscriptions__enabled=True),
                distinct=True,
            ),
            missing_email_count=Count(
                "subscriptions",
                filter=(
                    Q(subscriptions__is_deleted=False)
                    & Q(subscriptions__enabled=True)
                    & (Q(subscriptions__user__email__isnull=True) | Q(subscriptions__user__email=""))
                ),
                distinct=True,
            ),
        )
    )
    if filters.keyword:
        qs = qs.filter(
            Q(name__icontains=filters.keyword)
            | Q(project__name__icontains=filters.keyword),
        )
    if filters.enabled is not None:
        qs = qs.filter(enabled=filters.enabled)
    if filters.has_subscribers is not None:
        # 订阅人数筛选依赖聚合结果，必须在 annotate 之后执行。
        qs = qs.filter(subscriber_count__gt=0) if filters.has_subscribers else qs.filter(subscriber_count=0)
    if filters.has_missing_email is not None:
        qs = qs.filter(missing_email_count__gt=0) if filters.has_missing_email else qs.filter(missing_email_count=0)

    count = qs.count()
    rows = []
    for config in qs.order_by("-sys_update_datetime")[(page - 1) * page_size : page * page_size]:
        project = config.project
        rows.append(
            {
                "id": str(config.id),
                "name": config.name,
                "project_id": str(project.id) if project else "",
                "project_name": project.name if project else "",
                "managers": _join_subscription_user_names(config.managers.all()),
                "project_managers": _join_subscription_user_names(project.managers.all()) if project else "",
                "enabled": config.enabled,
                "subscriber_count": int(config.subscriber_count or 0),
                "missing_email_count": int(config.missing_email_count or 0),
                "sys_update_datetime": config.sys_update_datetime,
            }
        )
    return rows, count, page, page_size


def query_subscription_subscribers(config_id: str, filters):
    """分页查询单个项目配置的订阅人。"""
    _get_subscription_config(config_id)
    page, page_size = _normalize_page(filters.page, filters.page_size)
    qs = (
        IntegrationEmailSubscription.objects.select_related("user")
        .filter(config_id=config_id, is_deleted=False)
        .order_by("-enabled", "user__name", "user__username")
    )
    if filters.keyword:
        qs = qs.filter(
            Q(user__name__icontains=filters.keyword)
            | Q(user__username__icontains=filters.keyword)
            | Q(user__email__icontains=filters.keyword),
        )
    if filters.enabled is not None:
        qs = qs.filter(enabled=filters.enabled)

    count = qs.count()
    rows = []
    for subscription in qs[(page - 1) * page_size : page * page_size]:
        user = subscription.user
        rows.append(
            {
                "id": str(subscription.id),
                "user_id": str(subscription.user_id),
                "username": user.username if user else "",
                "name": user.name if user else "",
                "email": user.email if user else "",
                "enabled": subscription.enabled,
                "sys_update_datetime": subscription.sys_update_datetime,
            }
        )
    return rows, count, page, page_size


@transaction.atomic
def replace_subscription_users(config_id: str, user_ids: List[str]) -> int:
    """全量保存单个项目配置的订阅人集合。"""
    config = _get_subscription_config(config_id)
    normalized_ids = _validate_subscription_user_ids(user_ids)
    requested_ids = set(normalized_ids)
    changed_count = 0

    for user_id in normalized_ids:
        existing = IntegrationEmailSubscription.objects.filter(
            user_id=user_id,
            config=config,
        ).first()
        _, created = IntegrationEmailSubscription.objects.update_or_create(
            user_id=user_id,
            config=config,
            defaults={"enabled": True, "is_deleted": False},
        )
        if created or (existing and (existing.is_deleted or not existing.enabled)):
            changed_count += 1

    stale_qs = IntegrationEmailSubscription.objects.filter(
        config=config,
        is_deleted=False,
    ).exclude(user_id__in=requested_ids)
    # 全量保存只收敛当前配置，未保留的订阅软删除后不会进入邮件发送。
    changed_count += stale_qs.update(is_deleted=True, enabled=False)
    return changed_count


@transaction.atomic
def add_subscription_users(config_id: str, user_ids: List[str]) -> int:
    """批量追加项目配置订阅人，已存在关系会被重新启用。"""
    config = _get_subscription_config(config_id)
    normalized_ids = _validate_subscription_user_ids(user_ids)
    changed_count = 0
    for user_id in normalized_ids:
        existing = IntegrationEmailSubscription.objects.filter(
            user_id=user_id,
            config=config,
        ).first()
        _, created = IntegrationEmailSubscription.objects.update_or_create(
            user_id=user_id,
            config=config,
            defaults={"enabled": True, "is_deleted": False},
        )
        if created or (existing and (existing.is_deleted or not existing.enabled)):
            changed_count += 1
    return changed_count


@transaction.atomic
def batch_add_subscription_users(config_ids: List[str], user_ids: List[str]) -> int:
    """批量给多个项目配置追加订阅人。"""
    normalized_config_ids = _validate_subscription_config_ids(config_ids)
    normalized_user_ids = _validate_subscription_user_ids(user_ids)
    changed_count = 0
    for config_id in normalized_config_ids:
        changed_count += add_subscription_users(config_id, normalized_user_ids)
    return changed_count


@transaction.atomic
def remove_subscription_users(config_id: str, user_ids: List[str]) -> int:
    """批量移除项目配置订阅人，采用软删除保证历史关系可追溯。"""
    _get_subscription_config(config_id)
    normalized_ids = _validate_subscription_user_ids(user_ids)
    if not normalized_ids:
        return 0
    return IntegrationEmailSubscription.objects.filter(
        config_id=config_id,
        user_id__in=normalized_ids,
        is_deleted=False,
    ).update(is_deleted=True, enabled=False)
