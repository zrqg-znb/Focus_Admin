from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Count, Max, Q

from apps.code_scan.models import ScanProject, ScanResult, ScanTask
from core.user.user_model import User

from .integration_models import (
    IntegrationEmailDelivery,
    IntegrationEmailSubscription,
    IntegrationMetricDefinition,
    IntegrationProjectConfig,
    IntegrationProjectMetricValue,
)
from .integration_fetcher import IntegrationDataFetcher
from .integration_schema import MetricCell, ProjectConfigOut
from .integration_email import build_daily_email_html, send_html_email


CODE_KEYS = [
    "codecheck_error_num",
    "bin_scope_error_num",
    "build_check_error_num",
    "compile_error_num",
    "tscan_error_num",
    "tsan_error_num",
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

SCAN_METRIC_TOOL_ALIAS_MAP = {
    "tscan_error_num": {"tscan"},
    "tsan_error_num": {"tsan"},
    "cppcheck_error_num": {"cppcheck"},
    "weggli_error_num": {"weggli"},
    "cooddy_error_num": {"cooddy"},
    "binexplorer_error_num": {"binexplorer"},
    "clang_tidy_error_num": {"clang-tidy", "clang_tidy", "clangtidy"},
}


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


def _build_scan_metric_defaults() -> Dict[str, tuple[float, str]]:
    return {metric_key: (0.0, "") for metric_key in SCAN_METRIC_TOOL_ALIAS_MAP}


def _fetch_code_scan_metrics(
    config: IntegrationProjectConfig,
    record_date: date,
) -> Dict[str, tuple[float, str]]:
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

    latest_task_by_metric: Dict[str, str] = {}
    tasks = (
        ScanTask.objects.filter(
            is_deleted=False,
            project=scan_project,
            status="success",
            sys_create_datetime__date__lte=record_date,
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

    if not latest_task_by_metric:
        detail_url = f"/code_scan/result?projectId={scan_project.id}"
        return {key: (0.0, detail_url) for key in SCAN_METRIC_TOOL_ALIAS_MAP}

    task_ids = list(set(latest_task_by_metric.values()))
    counts = (
        ScanResult.objects.filter(task_id__in=task_ids, is_deleted=False)
        .exclude(shield_status="Shielded")
        .values("task_id")
        .annotate(cnt=Count("id"))
    )
    count_map = {str(row["task_id"]): float(row["cnt"]) for row in counts}

    detail_url = f"/code_scan/result?projectId={scan_project.id}"
    for metric_key, task_id in latest_task_by_metric.items():
        metric_payload[metric_key] = (count_map.get(task_id, 0.0), detail_url)

    return metric_payload


def ensure_default_metric_definitions():
    defaults = [
        ("code", "codecheck_error_num", "CodeCheck 错误数", "number", "", ">", 0),
        ("code", "bin_scope_error_num", "Bin Scope 错误数", "number", "", ">", 0),
        ("code", "build_check_error_num", "Build 检测错误数", "number", "", ">", 0),
        ("code", "compile_error_num", "Compile 错误数", "number", "", ">", 0),
        ("code", "tscan_error_num", "TScan 问题数", "number", "", ">", 0),
        ("code", "tsan_error_num", "TSan 问题数", "number", "", ">", 0),
        ("code", "cppcheck_error_num", "Cppcheck 问题数", "number", "", ">", 0),
        ("code", "weggli_error_num", "Weggli 问题数", "number", "", ">", 0),
        ("code", "cooddy_error_num", "Cooddy 问题数", "number", "", ">", 0),
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

    configs = IntegrationProjectConfig.objects.select_related("project").filter(is_deleted=False, enabled=True)
    if config_ids:
        configs = configs.filter(id__in=config_ids)
    def_map = {d.key: d for d in IntegrationMetricDefinition.objects.filter(is_deleted=False, enabled=True)}

    for cfg in configs:
        fetcher = IntegrationDataFetcher(cfg).set_date(record_date)
        payload = fetcher.fetch_metrics()
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
                    "value_text": "error" if val is None else "",
                    "detail_url": url,
                },
            )


# 保持兼容性，指向新函数
mock_collect_daily = collect_daily_metrics


def list_configs_with_latest(user: User, keyword: Optional[str] = None) -> List[ProjectConfigOut]:
    ensure_default_metric_definitions()

    configs = (
        IntegrationProjectConfig.objects.select_related("project")
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
                code_scan_project_key=cfg.code_scan_project_key,
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
