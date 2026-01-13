from datetime import date
from typing import List, Optional

from ninja import Router, Query
from ninja.errors import HttpError

from common.fu_auth import BearerAuth as GlobalAuth
from apps.project_manager.project.project_model import Project
from .integration_schema import (
    ProjectConfigManageRow,
    ProjectConfigOut,
    ProjectConfigUpsertIn,
    SubscriptionToggleIn,
    HistoryQueryOut,
    HistoryRow,
    MetricCell,
)
from .integration_models import IntegrationMetricDefinition, IntegrationProjectMetricValue
from . import integration_service
from .integration_models import IntegrationProjectConfig


router = Router(tags=["Integration Report"], auth=GlobalAuth())


@router.get("/projects", response=List[ProjectConfigOut], summary="项目集成报告配置列表（含订阅与最新数据）")
def list_projects(request):
    return integration_service.list_projects_with_latest(request.auth)

@router.get("/configs", response=List[ProjectConfigManageRow], summary="项目配置表（维护用）")
def list_configs(request):
    rows = []
    qs = IntegrationProjectConfig.objects.select_related("project").filter(is_deleted=False).order_by("-sys_update_datetime")
    for cfg in qs:
        rows.append(
            ProjectConfigManageRow(
                project_id=str(cfg.project_id),
                project_name=cfg.project.name,
                enabled=cfg.enabled,
                code_check_task_id=cfg.code_check_task_id,
                bin_scope_task_id=cfg.bin_scope_task_id,
                build_check_task_id=cfg.build_check_task_id,
                compile_check_task_id=cfg.compile_check_task_id,
                dt_project_id=cfg.dt_project_id,
            )
        )
    return rows


@router.post("/configs/{project_id}", response=bool, summary="更新项目配置（维护用）")
def upsert_config(request, project_id: str, payload: ProjectConfigUpsertIn):
    IntegrationProjectConfig.objects.update_or_create(
        project_id=project_id,
        defaults=payload.dict(),
    )
    return True


@router.post("/configs/init", response=int, summary="为所有项目初始化配置行（维护用）")
def init_configs(request):
    count = 0
    projects = Project.objects.filter(is_deleted=False, is_closed=False)
    for p in projects:
        _, created = IntegrationProjectConfig.objects.get_or_create(project=p)
        if created:
            count += 1
    return count


@router.post("/subscriptions/{project_id}", response=bool, summary="订阅/取消订阅项目")
def toggle_sub(request, project_id: str, payload: SubscriptionToggleIn):
    return integration_service.toggle_subscription(request.auth, project_id, payload.enabled)


@router.get("/history", response=HistoryQueryOut, summary="历史监测数据（按日）")
def history(
    request,
    project_ids: List[str] = Query(None),
    start: Optional[date] = None,
    end: Optional[date] = None,
):
    if not start or not end:
        raise HttpError(400, "start/end 必填")

    defs = {d.key: d for d in IntegrationMetricDefinition.objects.filter(is_deleted=False, enabled=True)}
    qs = IntegrationProjectMetricValue.objects.select_related("project", "metric").filter(
        is_deleted=False,
        record_date__gte=start,
        record_date__lte=end,
        metric__enabled=True,
    )
    if project_ids:
        qs = qs.filter(project_id__in=project_ids)

    by_key = {}
    for v in qs:
        key = (v.record_date, str(v.project_id))
        by_key.setdefault(key, {"project": v.project, "code": {}, "dt": {}})
        defn = v.metric
        cell = MetricCell(
            key=defn.key,
            name=defn.name,
            value=v.value_number,
            unit=defn.unit,
            url=v.detail_url or "",
            level=integration_service._eval_level(defn, v.value_number),
        )
        (by_key[key]["code"] if defn.group == "code" else by_key[key]["dt"])[defn.key] = cell

    items: List[HistoryRow] = []
    for (d, pid), data in sorted(by_key.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True):
        proj = data["project"]
        code_cells = [data["code"].get(k) or MetricCell(key=k, name=defs[k].name, unit=defs[k].unit) for k in integration_service.CODE_KEYS if k in defs]
        dt_cells = [data["dt"].get(k) or MetricCell(key=k, name=defs[k].name, unit=defs[k].unit) for k in integration_service.DT_KEYS if k in defs]
        items.append(
            HistoryRow(
                record_date=d,
                project_id=str(proj.id),
                project_name=proj.name,
                code_metrics=code_cells,
                dt_metrics=dt_cells,
            )
        )

    return HistoryQueryOut(items=items)


@router.post("/mock/collect", response=bool, summary="Mock 采集一次（写入今日数据）")
def mock_collect(request, record_date: Optional[date] = None):
    integration_service.mock_collect_daily(record_date)
    return True


@router.post("/mock/send-emails", response=int, summary="Mock 发送一次邮件（按订阅拆分）")
def mock_send(request, record_date: Optional[date] = None):
    return integration_service.send_daily_emails(record_date)
