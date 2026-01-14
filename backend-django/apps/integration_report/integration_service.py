from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Max

from apps.project_manager.project.project_model import Project
from core.user.user_model import User

from .integration_models import (
    IntegrationEmailDelivery,
    IntegrationEmailSubscription,
    IntegrationMetricDefinition,
    IntegrationProjectConfig,
    IntegrationProjectMetricValue,
)
from .integration_mock import mock_fetch
from .integration_schema import MetricCell, ProjectConfigOut
from .integration_email import build_daily_email_html, send_html_email


CODE_KEYS = [
    "codecheck_error_num",
    "bin_scope_error_num",
    "build_check_error_num",
    "compile_error_num",
]
DT_KEYS = [
    "dt_pass_rate",
    "dt_pass_num",
    "dt_line_coverage",
    "dt_method_coverage",
]


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


def ensure_default_metric_definitions():
    defaults = [
        ("code", "codecheck_error_num", "CodeCheck 错误数", "number", "", ">", 0),
        ("code", "bin_scope_error_num", "Bin Scope 错误数", "number", "", ">", 0),
        ("code", "build_check_error_num", "Build 检测错误数", "number", "", ">", 0),
        ("code", "compile_error_num", "Compile 错误数", "number", "", ">", 0),
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
def mock_collect_daily(record_date: Optional[date] = None, config_ids: Optional[List[str]] = None):
    ensure_default_metric_definitions()
    if record_date is None:
        record_date = date.today()

    configs = IntegrationProjectConfig.objects.select_related("project").filter(is_deleted=False, enabled=True)
    if config_ids:
        configs = configs.filter(id__in=config_ids)
    def_map = {d.key: d for d in IntegrationMetricDefinition.objects.filter(is_deleted=False, enabled=True)}

    for cfg in configs:
        # Mock fetch using the Config Name (since user wants separate display name)
        # But for task IDs we use what's configured
        payload = mock_fetch(cfg.name, record_date, {
            "code_check_task_id": cfg.code_check_task_id,
            "bin_scope_task_id": cfg.bin_scope_task_id,
            "build_check_task_id": cfg.build_check_task_id,
            "compile_check_task_id": cfg.compile_check_task_id,
            "dt_project_id": cfg.dt_project_id,
        })

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
                    "value_text": "",
                    "detail_url": url,
                },
            )


def list_configs_with_latest(user: User) -> List[ProjectConfigOut]:
    ensure_default_metric_definitions()

    configs = (
        IntegrationProjectConfig.objects.select_related("project")
        .filter(is_deleted=False)
        .order_by("-sys_update_datetime")
    )
    subscribed_ids = set(
        IntegrationEmailSubscription.objects.filter(is_deleted=False, user=user, enabled=True).values_list("config_id", flat=True)
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

        proj_managers_str = ",".join([m.name or m.username for m in proj.managers.all()])
        config_managers_str = ",".join([u.name or u.username for u in cfg.managers.all()])
        result.append(
            ProjectConfigOut(
                id=str(cfg.id),
                name=cfg.name,
                project_id=str(proj.id),
                project_name=proj.name,
                project_domain=proj.domain,
                project_type=proj.type,
                project_managers=proj_managers_str,
                managers=config_managers_str,
                enabled=cfg.enabled,
                subscribed=str(cfg.id) in subscribed_ids,
                latest_date=latest_date,
                code_metrics=make_cells(CODE_KEYS),
                dt_metrics=make_cells(DT_KEYS),
            )
        )
    return result


@transaction.atomic
def toggle_subscription(user: User, config_id: str, enabled: bool) -> bool:
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
        .filter(is_deleted=False, enabled=True, user__is_active=True)
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
                    unit=defn.unit,
                    url=v.detail_url or "",
                    level=_eval_level(defn, val),
                )

            code_cells = [cell_by_key.get(k) or MetricCell(key=k, name=def_map[k].name, unit=def_map[k].unit) for k in CODE_KEYS if k in def_map]
            dt_cells = [cell_by_key.get(k) or MetricCell(key=k, name=def_map[k].name, unit=def_map[k].unit) for k in DT_KEYS if k in def_map]
            project_rows.append(
                {
                    "project_name": cfg.name,  # Use Config Name as Display Name
                    "project_domain": cfg.project.domain or "",
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
