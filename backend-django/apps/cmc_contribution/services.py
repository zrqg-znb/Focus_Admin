"""CMC 数据湖同步、快照落库和看板查询服务。"""

from __future__ import annotations

import json
import logging
import threading
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import requests
from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Count, Sum
from django.utils import timezone
from ninja.errors import HttpError
from scheduler.module.executor import scheduler_task
from core.user.user_model import User

from .models import (
    SYNC_STATUS_FAILED,
    SYNC_STATUS_PENDING,
    SYNC_STATUS_RUNNING,
    SYNC_STATUS_SUCCESS,
    SYNC_TRIGGER_MANUAL,
    SYNC_TRIGGER_SCHEDULED,
    CmcContributionDailyRecord,
    CmcContributionSyncTask,
)

logger = logging.getLogger(__name__)

# 当前 v1 仅面向一个已确认的部门。固定业务参数收敛在服务内，避免无意义的部署配置。
CMC_FIXED_QUERY = {
    "CMC_LEVEL": 2,
    "CMCDEPTID": 100294,
    "FLAG": 3,
    "TAG": 1,
    "SORT_TYPE": "asc",
    "SORT_COLUMN": "SCORE",
    "DEPT_NAME": "底层软件开发部",
}
CMC_REQUEST_PAGE_SIZE = 100


def _setting(name: str, default: Any = None) -> Any:
    """读取可由部署环境覆盖的 CMC 配置。"""
    return getattr(settings, name, default)


def _safe_int(value: Any) -> int:
    """将数据湖可能为空的计数字段安全转换为整数。"""
    try:
        return int(Decimal(str(value or 0)))
    except Exception:
        return 0


def _rate(value: Any) -> Decimal:
    """将百分数字符串归一化为 0 到 1 的小数。"""
    raw = str(value or "").strip().replace("%", "")
    try:
        return max(Decimal("0"), Decimal(raw) / Decimal("100"))
    except Exception:
        return Decimal("0")


def _headers() -> dict[str, str]:
    """构造数据湖请求头，并兼容 Bearer 与裸 Token 配置。"""
    headers = {"Content-Type": "application/json"}
    token = str(_setting("CMC_CONTRIBUTION_API_TOKEN", "") or "").strip()
    if token:
        headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
    try:
        extra = json.loads(str(_setting("CMC_CONTRIBUTION_API_HEADERS_JSON", "{}") or "{}"))
        headers.update({str(key): str(value) for key, value in extra.items()})
    except (TypeError, ValueError, json.JSONDecodeError):
        logger.warning("CMC_CONTRIBUTION_API_HEADERS_JSON 不是合法 JSON，已忽略")
    return headers


def _payload(day: date, page_index: int) -> dict[str, Any]:
    """构造新版数据湖三字段请求体，分页字段不再混入业务 params。"""
    return {
        "pageIndex": page_index,
        "pageSize": CMC_REQUEST_PAGE_SIZE,
        "params": {
            "START_DATE": day.strftime("%Y%m%d"),
            "END_DATE": day.strftime("%Y%m%d"),
            **CMC_FIXED_QUERY,
        },
    }


def _response_rows(payload: Any) -> list[dict[str, Any]]:
    """读取新版数据湖响应顶层 result 列表。"""
    if not isinstance(payload, dict):
        return []
    rows = payload.get("result", [])
    return [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []


def _total_pages(payload: Any) -> int | None:
    """通过响应顶层 total/pageSize 计算总页数，缺失时仍由空页收敛。"""
    if not isinstance(payload, dict):
        return None
    total = _safe_int(payload.get("total"))
    page_size = _safe_int(payload.get("pageSize")) or CMC_REQUEST_PAGE_SIZE
    return (total + page_size - 1) // page_size if total > 0 else 0


def fetch_day(day: date) -> tuple[list[dict[str, Any]], int]:
    """逐页读取一个统计日的完整上游结果，返回行和实际请求页数。"""
    url = str(_setting("CMC_CONTRIBUTION_API_URL", "") or "").strip()
    if not url:
        raise HttpError(500, "未配置 CMC_CONTRIBUTION_API_URL")
    rows: list[dict[str, Any]] = []
    max_pages = max(_safe_int(_setting("CMC_CONTRIBUTION_MAX_PAGES", 500)), 1)
    timeout = float(_setting("CMC_CONTRIBUTION_API_TIMEOUT", 20))
    verify_ssl = bool(_setting("CMC_CONTRIBUTION_API_VERIFY_SSL", True))
    known_total: int | None = None
    for page in range(1, max_pages + 1):
        try:
            response = requests.post(url, json=_payload(day, page), headers=_headers(), timeout=timeout, verify=verify_ssl)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise HttpError(502, f"CMC 数据湖请求失败：{exc}") from exc
        page_rows = _response_rows(payload)
        rows.extend(page_rows)
        known_total = known_total or _total_pages(payload)
        # 响应未给总数时以空页停止；有 total 时按 total/pageSize 的页面边界结束。
        if known_total is not None and page >= known_total:
            return rows, page
        if known_total is None and not page_rows:
            return rows, page
    raise HttpError(502, f"CMC 数据湖分页超过最大页数 {max_pages}")


def _record_from_row(
    day: date,
    row: dict[str, Any],
    users_by_login: dict[str, User],
) -> CmcContributionDailyRecord:
    """标准化新版人员行，并严格校验其与 core.User 是同一人。"""
    user_name = str(row.get("name") or row.get("user") or "").strip()
    merged_login = str(row.get("merged_login") or "").strip()
    if not user_name or not merged_login:
        raise HttpError(422, "CMC 成员缺少 name 或 merged_login，无法关联 Focus 用户")
    user = users_by_login.get(merged_login)
    if user is None:
        raise HttpError(422, f"未找到 merged_login={merged_login} 对应的 Focus 用户")
    if str(user.name or "").strip() != user_name:
        raise HttpError(
            422,
            f"CMC 成员 {merged_login} 的 name={user_name} 与 Focus 用户姓名不一致",
        )
    total = _safe_int(row.get("cnt_total"))
    rate = _rate(row.get("not_0_comment_rate"))
    zero_count = int((Decimal(total) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return CmcContributionDailyRecord(
        statistic_date=day,
        user=user,
        user_name=user_name,
        merged_login=merged_login,
        cnt_total=total,
        major_comments_cnt=_safe_int(row.get("major_comments_cnt")),
        fatal_comments_cnt=_safe_int(row.get("fatal_comments_cnt")),
        minor_comments_cnt=_safe_int(row.get("minor_comments_cnt")),
        sugge_comments_cnt=_safe_int(row.get("sugge_comments_cnt")),
        cmt_issue=_safe_int(row.get("cmt_issue")),
        checked_mr_lines=_safe_int(row.get("checked_mr_lines")),
        cmt_lines=_safe_int(row.get("cmt_lines")),
        not_0_comment_rate=rate,
        zero_comment_mr_count=zero_count,
        raw_payload=row,
    )


def replace_day_snapshot(day: date, rows: list[dict[str, Any]]) -> int:
    """只有整日拉取成功后才原子替换本地快照，避免失败污染历史数据。"""
    logins = {str(row.get("merged_login") or "").strip() for row in rows}
    logins.discard("")
    # 先批量读取系统用户，避免随上游行数增加产生 N+1 查询。
    users_by_login = User.objects.in_bulk(logins, field_name="username")
    normalized = [_record_from_row(day, row, users_by_login) for row in rows]
    with transaction.atomic():
        CmcContributionDailyRecord.objects.filter(statistic_date=day).delete()
        CmcContributionDailyRecord.objects.bulk_create(normalized, batch_size=500)
    return len(normalized)


def _serialize_task(task: CmcContributionSyncTask) -> dict[str, Any]:
    """输出同步任务供前端轮询。"""
    return {
        "id": str(task.id), "trigger_type": task.trigger_type, "status": task.status,
        "start_date": task.start_date, "end_date": task.end_date,
        "requested_dates": [str(item) for item in task.requested_dates or []],
        "synced_dates": [str(item) for item in task.synced_dates or []],
        "fetched_pages": task.fetched_pages, "fetched_rows": task.fetched_rows,
        "error_message": task.error_message, "started_at": task.started_at, "finished_at": task.finished_at,
    }


def _dates(start: date, end: date) -> list[date]:
    """展开含首尾的自然日范围。"""
    return [start + timedelta(days=index) for index in range((end - start).days + 1)]


def create_manual_task(user: Any, start: date, end: date) -> dict[str, Any]:
    """校验管理员补数范围并异步执行。"""
    if not getattr(user, "is_superuser", False):
        raise HttpError(403, "仅管理员可以手动同步 CMC 数据")
    if end < start or (end - start).days + 1 > 31:
        raise HttpError(400, "手动同步日期范围必须为 1 至 31 个自然日")
    task = CmcContributionSyncTask.objects.create(user=user, trigger_type=SYNC_TRIGGER_MANUAL, start_date=start, end_date=end, requested_dates=[str(item) for item in _dates(start, end)])
    threading.Thread(target=execute_task, args=(str(task.id),), daemon=True).start()
    return _serialize_task(task)


def execute_task(task_id: str) -> dict[str, Any]:
    """执行日期范围同步，单日失败即停止以便保留可诊断的失败边界。"""
    close_old_connections()
    task = CmcContributionSyncTask.objects.get(id=task_id)
    task.status, task.started_at, task.error_message = SYNC_STATUS_RUNNING, timezone.now(), ""
    task.save(update_fields=["status", "started_at", "error_message"])
    pages = rows_count = 0
    synced: list[str] = []
    try:
        for day in _dates(task.start_date, task.end_date):
            rows, page_count = fetch_day(day)
            rows_count += len(rows)
            pages += page_count
            replace_day_snapshot(day, rows)
            synced.append(str(day))
        task.status = SYNC_STATUS_SUCCESS
    except Exception as exc:
        logger.exception("CMC contribution sync task failed task_id=%s", task_id)
        task.status, task.error_message = SYNC_STATUS_FAILED, str(exc)
    task.fetched_pages, task.fetched_rows, task.synced_dates, task.finished_at = pages, rows_count, synced, timezone.now()
    task.save(update_fields=["status", "error_message", "fetched_pages", "fetched_rows", "synced_dates", "finished_at"])
    close_old_connections()
    return _serialize_task(task)


@scheduler_task
def run_scheduled_cmc_contribution_sync(**kwargs) -> dict[str, Any]:
    """定时入口：每日 01:00 同步上海时区的前一自然日。"""
    yesterday = timezone.localdate() - timedelta(days=1)
    task = CmcContributionSyncTask.objects.create(trigger_type=SYNC_TRIGGER_SCHEDULED, start_date=yesterday, end_date=yesterday, requested_dates=[str(yesterday)])
    return execute_task(str(task.id))


def get_task(task_id: str) -> dict[str, Any]:
    """读取同步任务状态。"""
    try:
        return _serialize_task(CmcContributionSyncTask.objects.get(id=task_id, is_deleted=False))
    except CmcContributionSyncTask.DoesNotExist as exc:
        raise HttpError(404, "同步任务不存在") from exc


def _query(start: date, end: date, user_keyword: str = ""):
    """构建本地日期范围查询；所有看板数据都只来自已同步快照。"""
    if end < start:
        raise HttpError(400, "结束日期不能早于开始日期")
    queryset = CmcContributionDailyRecord.objects.filter(is_deleted=False, statistic_date__range=(start, end))
    keyword = user_keyword.strip()
    return queryset.filter(user_name__icontains=keyword) if keyword else queryset


def _metrics(values: dict[str, Any], contributor_count: int) -> dict[str, Any]:
    """从 SQL 聚合结果计算跨人员、跨日期的派生指标。"""
    data = {key: _safe_int(values.get(key)) for key in ("cnt_total", "zero_comment_mr_count", "major_comments_cnt", "fatal_comments_cnt", "minor_comments_cnt", "sugge_comments_cnt", "cmt_issue", "checked_mr_lines", "cmt_lines")}
    effective = data["major_comments_cnt"] + data["fatal_comments_cnt"] + data["minor_comments_cnt"] + data["sugge_comments_cnt"] + data["cmt_issue"]
    data.update({"effective_comment_count": effective, "effective_comment_density": round(effective / data["checked_mr_lines"], 6) if data["checked_mr_lines"] else None, "zero_comment_rate": round(data["zero_comment_mr_count"] / data["cnt_total"], 6) if data["cnt_total"] else 0, "contributor_count": contributor_count})
    return data


def get_summary(start: date, end: date) -> dict[str, Any]:
    """查询日期范围内 CMC 核心指标卡。"""
    queryset = _query(start, end)
    values = queryset.aggregate(**{field: Sum(field) for field in ("cnt_total", "zero_comment_mr_count", "major_comments_cnt", "fatal_comments_cnt", "minor_comments_cnt", "sugge_comments_cnt", "cmt_issue", "checked_mr_lines", "cmt_lines")})
    return _metrics(values, queryset.values("user_id").distinct().count())


def get_trend(start: date, end: date) -> list[dict[str, Any]]:
    """按日期聚合 CMC 关键产出，用于趋势图而不重新访问数据湖。"""
    fields = (
        "cnt_total", "zero_comment_mr_count", "major_comments_cnt",
        "fatal_comments_cnt", "minor_comments_cnt", "sugge_comments_cnt",
        "cmt_issue", "checked_mr_lines",
    )
    rows = _query(start, end).values("statistic_date").annotate(
        **{field: Sum(field) for field in fields},
    ).order_by("statistic_date")
    result = []
    for row in rows:
        metrics = _metrics(row, 0)
        result.append({
            "date": row["statistic_date"],
            "cnt_total": metrics["cnt_total"],
            "zero_comment_mr_count": metrics["zero_comment_mr_count"],
            "effective_comment_count": metrics["effective_comment_count"],
            "checked_mr_lines": metrics["checked_mr_lines"],
        })
    return result


def get_person_ranking(start: date, end: date, limit: int = 10) -> list[dict[str, Any]]:
    """按有效检视意见降序返回人员 Top 榜，密度作为同分排序依据。"""
    fields = (
        "cnt_total", "zero_comment_mr_count", "major_comments_cnt",
        "fatal_comments_cnt", "minor_comments_cnt", "sugge_comments_cnt",
        "cmt_issue", "checked_mr_lines", "cmt_lines",
    )
    rows = _query(start, end).values("user_id", "user_name", "merged_login").annotate(
        **{field: Sum(field) for field in fields},
    )
    rankings = []
    for row in rows:
        metrics = _metrics(row, 0)
        rankings.append({
            "user": row["user_name"],
            "cnt_total": metrics["cnt_total"],
            "effective_comment_count": metrics["effective_comment_count"],
            "checked_mr_lines": metrics["checked_mr_lines"],
            "effective_comment_density": metrics["effective_comment_density"],
        })
    return sorted(
        rankings,
        key=lambda item: (
            item["effective_comment_count"],
            item["effective_comment_density"] or 0,
        ),
        reverse=True,
    )[: max(min(int(limit or 10), 20), 1)]


def get_comment_distribution(start: date, end: date) -> list[dict[str, Any]]:
    """汇总四个意见等级与 Issue，供环形图展示组成。"""
    summary = get_summary(start, end)
    return [
        {"label": "严重", "value": summary["major_comments_cnt"]},
        {"label": "致命", "value": summary["fatal_comments_cnt"]},
        {"label": "一般", "value": summary["minor_comments_cnt"]},
        {"label": "建议", "value": summary["sugge_comments_cnt"]},
        {"label": "Issue", "value": summary["cmt_issue"]},
    ]


def list_persons(
    start: date,
    end: date,
    page: int,
    page_size: int,
    user_keyword: str = "",
    sort_field: str = "",
    sort_order: str = "",
) -> dict[str, Any]:
    """按人员聚合本地快照，完成白名单排序后返回稳定分页表格。"""
    fields = ("cnt_total", "zero_comment_mr_count", "major_comments_cnt", "fatal_comments_cnt", "minor_comments_cnt", "sugge_comments_cnt", "cmt_issue", "checked_mr_lines", "cmt_lines")
    grouped = _query(start, end, user_keyword).values(
        "user_id", "user_name", "merged_login",
    ).annotate(**{field: Sum(field) for field in fields})
    safe_page, safe_size = max(int(page or 1), 1), max(min(int(page_size or 20), 100), 1)
    items = []
    for row in grouped:
        metrics = _metrics(row, 0)
        metrics["user"] = row["user_name"]
        metrics.pop("contributor_count", None)
        items.append(metrics)

    sortable_fields = set(fields) | {
        "zero_comment_rate",
        "effective_comment_count",
        "effective_comment_density",
    }
    # 先按姓名排序作为所有数值相同场景的稳定次级规则，再处理用户指定的数值列排序。
    items.sort(key=lambda item: item["user"])
    if sort_field in sortable_fields and sort_order in {"asc", "desc"}:
        items.sort(
            key=lambda item: item[sort_field] if item[sort_field] is not None else -1,
            reverse=sort_order == "desc",
        )

    total = len(items)
    offset = (safe_page - 1) * safe_size
    return {"items": items[offset : offset + safe_size], "total": total}
