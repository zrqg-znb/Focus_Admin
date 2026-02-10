from datetime import date
from typing import List, Optional

from django.shortcuts import get_object_or_404
from ninja import Router, Query
from ninja.pagination import paginate
from ninja.errors import HttpError

from common.fu_auth import BearerAuth as GlobalAuth
from apps.project_manager.project.project_model import Project
from core.user.user_model import User
from .integration_schema import (
    ProjectConfigManageRow,
    ProjectConfigOut,
    ProjectConfigUpsertIn,
    SubscriptionToggleIn,
    HistoryQueryOut,
    HistoryRow,
    MetricCell,
    ConfigFilterSchema,
    MockCollectIn,
    EmailDeliveryRow,
    EmailDeliveryQueryIn,
    EmailDeliveryQueryOut
)
from .integration_models import IntegrationMetricDefinition, IntegrationProjectMetricValue, IntegrationEmailDelivery, IntegrationEmailSubscription
from . import integration_service
from .integration_models import IntegrationProjectConfig


router = Router(tags=["Integration Report"], auth=GlobalAuth())


@router.get("/projects", response=List[ProjectConfigOut], summary="集成报告配置列表（用于订阅页）")
@paginate
def list_projects(request):
    # Actually returns Configs now
    return integration_service.list_configs_with_latest(request.auth)


@router.get("/configs", response=List[ProjectConfigManageRow], summary="配置列表（维护用）")
@paginate
def list_configs(request, filters: ConfigFilterSchema = Query(...)):
    qs = IntegrationProjectConfig.objects.select_related("project").filter(is_deleted=False).order_by("-sys_update_datetime")
    if filters.project_name:
        # Search by project name OR config name
        qs = qs.filter(project__name__icontains=filters.project_name) | qs.filter(name__icontains=filters.project_name)

    rows = []
    for cfg in qs:
        project_name = cfg.project.name if cfg.project else ""
        rows.append(
            ProjectConfigManageRow(
                id=str(cfg.id),
                name=cfg.name,
                project_id=str(cfg.project_id or ""),
                project_name=project_name,
                managers=",".join([u.name or u.username for u in cfg.managers.all()]),
                manager_ids=[str(u.id) for u in cfg.managers.all()],
                enabled=cfg.enabled,
                code_check_task_id=cfg.code_check_task_id,
                bin_scope_task_id=cfg.bin_scope_task_id,
                build_check_task_id=cfg.build_check_task_id,
                compile_check_task_id=cfg.compile_check_task_id,
                dt_project_id=cfg.dt_project_id,
            )
        )
    return rows


@router.post("/configs", response=str, summary="新建配置")
def create_config(request, payload: ProjectConfigUpsertIn):
    proj = None
    if payload.project_id:
        proj = Project.objects.filter(id=payload.project_id).first()
        if not proj:
            raise HttpError(404, "project_id 不存在")
    cfg = IntegrationProjectConfig.objects.create(
        project=proj,
        name=payload.name,
        enabled=payload.enabled,
        code_check_task_id=payload.code_check_task_id,
        bin_scope_task_id=payload.bin_scope_task_id,
        build_check_task_id=payload.build_check_task_id,
        compile_check_task_id=payload.compile_check_task_id,
        dt_project_id=payload.dt_project_id,
    )
    if payload.managers:
        cfg.managers.set(payload.managers)
    return str(cfg.id)


@router.put("/configs/{config_id}", response=bool, summary="更新配置")
def update_config(request, config_id: str, payload: ProjectConfigUpsertIn):
    cfg = get_object_or_404(IntegrationProjectConfig, id=config_id)
    cfg.name = payload.name
    fields_set = getattr(payload, "model_fields_set", None) or getattr(payload, "__fields_set__", None) or set()
    if "project_id" in fields_set:
        if payload.project_id:
            proj = Project.objects.filter(id=payload.project_id).first()
            if not proj:
                raise HttpError(404, "project_id 不存在")
            cfg.project = proj
        else:
            cfg.project = None
    if payload.managers is not None:
        cfg.managers.set(payload.managers)
    cfg.enabled = payload.enabled
    cfg.code_check_task_id = payload.code_check_task_id
    cfg.bin_scope_task_id = payload.bin_scope_task_id
    cfg.build_check_task_id = payload.build_check_task_id
    cfg.compile_check_task_id = payload.compile_check_task_id
    cfg.dt_project_id = payload.dt_project_id
    cfg.save()
    return True


@router.post("/configs/init", response=int, summary="为无配置的项目初始化默认配置")
def init_configs(request):
    count = 0
    projects = Project.objects.filter(is_deleted=False, is_closed=False)
    for p in projects:
        # If project has NO config, create one
        if not IntegrationProjectConfig.objects.filter(project=p).exists():
            cfg = IntegrationProjectConfig.objects.create(project=p, name=p.name)
            
            # Auto subscribe all active users
            users = User.objects.filter(is_deleted=False, is_active=True)
            subs = [IntegrationEmailSubscription(user=u, config=cfg, enabled=True) for u in users]
            IntegrationEmailSubscription.objects.bulk_create(subs)

            count += 1
    return count


@router.post("/subscriptions/{config_id}", response=bool, summary="订阅/取消订阅配置")
def toggle_sub(request, config_id: str, payload: SubscriptionToggleIn):
    return integration_service.toggle_subscription(request.auth, config_id, payload.enabled)


@router.get("/history", response=HistoryQueryOut, summary="历史监测数据（按日）")
def history(
    request,
    config_ids: List[str] = Query(None),
    start: Optional[date] = None,
    end: Optional[date] = None,
    keyword: Optional[str] = None,
):
    if not start or not end:
        raise HttpError(400, "start/end 必填")

    defs = {d.key: d for d in IntegrationMetricDefinition.objects.filter(is_deleted=False, enabled=True)}
    qs = IntegrationProjectMetricValue.objects.select_related("config", "config__project", "metric").filter(
        is_deleted=False,
        record_date__gte=start,
        record_date__lte=end,
        metric__enabled=True,
    )
    if config_ids:
        qs = qs.filter(config_id__in=config_ids)
    
    if keyword:
        from django.db.models import Q
        qs = qs.filter(Q(config__name__icontains=keyword) | Q(config__project__name__icontains=keyword))

    by_key = {}
    for v in qs:
        key = (v.record_date, str(v.config_id))
        by_key.setdefault(key, {"config": v.config, "code": {}, "dt": {}})
        defn = v.metric
        cell = MetricCell(
            key=defn.key,
            name=defn.name,
            value=v.value_number,
            text=v.value_text,
            unit=defn.unit,
            url=v.detail_url or "",
            level=integration_service._eval_level(defn, v.value_number),
        )
        (by_key[key]["code"] if defn.group == "code" else by_key[key]["dt"])[defn.key] = cell

    items: List[HistoryRow] = []
    for (d, cid), data in sorted(by_key.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True):
        cfg = data["config"]
        code_cells = [data["code"].get(k) or MetricCell(key=k, name=defs[k].name, unit=defs[k].unit) for k in integration_service.CODE_KEYS if k in defs]
        dt_cells = [data["dt"].get(k) or MetricCell(key=k, name=defs[k].name, unit=defs[k].unit) for k in integration_service.DT_KEYS if k in defs]
        items.append(
            HistoryRow(
                record_date=d,
                config_id=str(cfg.id),
                config_name=cfg.name,
                project_name=cfg.project.name if cfg.project else "",
                code_metrics=code_cells,
                dt_metrics=dt_cells,
            )
        )

    return HistoryQueryOut(items=items)


@router.post("/mock/collect", response=bool, summary="Mock 采集一次（写入今日数据）")
def mock_collect(request, payload: MockCollectIn):
    integration_service.mock_collect_daily(payload.record_date, payload.config_ids)
    return True


@router.post("/mock/send-emails", response=int, summary="Mock 发送一次邮件（按订阅拆分）")
def mock_send(request, record_date: Optional[date] = None):
    return integration_service.send_daily_emails(record_date)


@router.get("/email-deliveries", response=List[EmailDeliveryRow], summary="邮件投递日志查询")
@paginate
def list_email_deliveries(request, filters: EmailDeliveryQueryIn = Query(...)):
    qs = IntegrationEmailDelivery.objects.select_related("user").filter(is_deleted=False)
    
    if filters.status:
        qs = qs.filter(status=filters.status)
    if filters.start_date:
        qs = qs.filter(record_date__gte=filters.start_date)
    if filters.end_date:
        qs = qs.filter(record_date__lte=filters.end_date)
    if filters.user_id:
        qs = qs.filter(user_id=filters.user_id)
    if filters.to_email:
        qs = qs.filter(to_email__icontains=filters.to_email)
    
    qs = qs.order_by("-sys_create_datetime")
    
    rows = []
    for delivery in qs:
        rows.append(
            EmailDeliveryRow(
                id=str(delivery.id),
                record_date=delivery.record_date,
                user_id=str(delivery.user_id),
                user_name=delivery.user.name if delivery.user else None,
                to_email=delivery.to_email,
                subject=delivery.subject,
                status=delivery.status,
                error_message=delivery.error_message,
                sys_create_datetime=delivery.sys_create_datetime,
            )
        )
    return rows
