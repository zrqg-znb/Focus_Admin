from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Tuple

from django.db import IntegrityError
from django.db.models import Q
from ninja.errors import HttpError

from common import fu_crud
from apps.project_manager.project.project_model import Project
from .code_quality_model import (
    CodeMetric,
    CodeMetricNode,
    CodeModule,
    CodeNodeOwnerConfig,
)
from .code_quality_schema import (
    CodeMetricSchema,
    ModuleConfigSchema,
    ModuleQualityDetailSchema,
    NodeOwnerUpdateSchema,
    ProjectQualitySummarySchema,
    QualityOverviewFilterSchema,
    QualityMetricValueSchema,
    QualityTreeNodeSchema,
)
from .quality_sync import (
    QUALITY_METRIC_LABELS,
    QUALITY_WARNING_RULES,
    sync_all_projects_quality,
    sync_project_quality_metrics,
)

SUM_METRIC_KEYS = {
    "code_size",
    "misra_delay_num",
    "misra_dismiss_num",
    "redundant_code_kloc",
    "redundant_code_total",
}

PERCENT_METRIC_KEYS = {
    "UT_branch_coverage",
    "UT_line_coverage",
    "UT_file_coverage",
    "UT_function_coverage",
    "UT_mcdc_coverage",
    "cmetrics_pass_rate",
    "code_duplication_ratio",
    "huge_headerfile_ratio",
}


def _module_owner_names(module: CodeModule) -> List[str]:
    return [item.name or item.username for item in module.owners.all()]


def _module_owner_ids(module: CodeModule) -> List[str]:
    return [str(item.id) for item in module.owners.all()]


def _node_owner_config_map(
    modules: List[CodeModule],
) -> Dict[Tuple[str, str], Dict[str, List[str]]]:
    module_ids = [module.id for module in modules]
    if not module_ids:
        return {}

    configs = (
        CodeNodeOwnerConfig.objects.filter(
            module_id__in=module_ids,
            is_deleted=False,
        )
        .prefetch_related("owners")
        .order_by("module_id", "node_key")
    )
    owner_map: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
    for config in configs:
        owner_map[(str(config.module_id), config.node_key)] = {
            "owner_ids": [str(item.id) for item in config.owners.all()],
            "owner_names": [
                item.name or item.username
                for item in config.owners.all()
            ],
        }
    return owner_map


def _latest_metric(module: CodeModule) -> CodeMetric | None:
    return (
        module.metrics.filter(is_deleted=False)
        .only(
            "id",
            "module_id",
            "record_date",
            "loc",
            "function_count",
            "dangerous_func_count",
            "duplication_rate",
            "is_clean_code",
            "clean_code_rate",
            "clean_code_total",
            "unachieved_clean_code",
            "warning_count",
            "warning_metrics",
            "total_node_count",
            "warning_node_count",
            "version_name",
            "summary_metrics",
        )
        .order_by("-record_date", "-sys_create_datetime")
        .first()
    )


def _pick_metric_by_date(
    module: CodeModule,
    record_date: date | None = None,
) -> CodeMetric | None:
    metrics = (
        module.metrics.filter(is_deleted=False)
        .only(
            "id",
            "module_id",
            "record_date",
            "loc",
            "function_count",
            "dangerous_func_count",
            "duplication_rate",
            "is_clean_code",
            "clean_code_rate",
            "clean_code_total",
            "unachieved_clean_code",
            "warning_count",
            "warning_metrics",
            "total_node_count",
            "warning_node_count",
            "version_name",
            "summary_metrics",
        )
        .order_by("-record_date", "-sys_create_datetime")
    )

    if record_date is not None:
        exact = metrics.filter(record_date=record_date).first()
        if exact is not None:
            return exact
        return None

    return metrics.first()


def parse_record_date(record_date: str | None = None) -> date | None:
    text = str(record_date or "").strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    raise HttpError(400, "record_date格式错误，支持YYYY-MM-DD或YYYYMMDD")


def _metric_values_to_list(raw_metric_values: Any) -> List[QualityMetricValueSchema]:
    if not raw_metric_values:
        return []

    values: List[Dict[str, Any]] = []
    if isinstance(raw_metric_values, dict):
        for metric_key, metric_value in raw_metric_values.items():
            if isinstance(metric_value, dict):
                payload = dict(metric_value)
                payload.setdefault("key", metric_key)
                payload.setdefault("label", metric_key)
                payload.setdefault("display", str(payload.get("raw", payload.get("num", "-"))))
                values.append(payload)
            else:
                values.append(
                    {
                        "key": metric_key,
                        "label": metric_key,
                        "display": str(metric_value),
                        "num": None,
                        "is_warning": False,
                        "raw": metric_value,
                    }
                )
    elif isinstance(raw_metric_values, list):
        for item in raw_metric_values:
            if not isinstance(item, dict):
                continue
            payload = dict(item)
            payload.setdefault("key", payload.get("label", "metric"))
            payload.setdefault("label", payload.get("key", "metric"))
            payload.setdefault("display", str(payload.get("raw", payload.get("num", "-"))))
            values.append(payload)

    values.sort(
        key=lambda item: (
            0 if bool(item.get("is_warning")) else 1,
            str(item.get("key", "")),
        )
    )

    output: List[QualityMetricValueSchema] = []
    for item in values:
        output.append(
            QualityMetricValueSchema(
                key=str(item.get("key", "")),
                label=str(item.get("label", item.get("key", ""))),
                display=str(item.get("display", "-")),
                num=item.get("num"),
                is_warning=bool(item.get("is_warning", False)),
                raw=item.get("raw"),
            )
        )
    return output


def _to_float_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("%"):
            text = text[:-1]
        try:
            return float(text)
        except Exception:
            return None
    return None


def _is_metric_warning(metric_key: str, num_value: float | None) -> bool:
    if num_value is None:
        return False
    rule = QUALITY_WARNING_RULES.get(metric_key)
    if not rule:
        return False

    op = str(rule.get("op", "")).strip()
    threshold = float(rule.get("threshold", 0))
    if op == ">":
        return num_value > threshold
    if op == ">=":
        return num_value >= threshold
    if op == "<":
        return num_value < threshold
    if op == "<=":
        return num_value <= threshold
    if op == "==":
        return num_value == threshold
    if op == "!=":
        return num_value != threshold
    return False


def _format_metric_display(metric_key: str, num_value: float | None) -> str:
    if num_value is None:
        return "-"
    if metric_key in PERCENT_METRIC_KEYS:
        return f"{round(num_value, 2)}%"
    if float(num_value).is_integer():
        return str(int(num_value))
    return str(round(num_value, 4))


def _aggregate_oem_metric_values(metrics: List[CodeMetric]) -> List[QualityMetricValueSchema]:
    metric_values_map: Dict[str, List[float]] = defaultdict(list)

    for metric in metrics:
        summary_metrics = metric.summary_metrics or {}
        if not isinstance(summary_metrics, dict):
            continue
        for metric_key, metric_payload in summary_metrics.items():
            if not isinstance(metric_payload, dict):
                continue
            raw_num = metric_payload.get("num")
            num_value = _to_float_value(raw_num)
            if num_value is None:
                num_value = _to_float_value(metric_payload.get("display"))
            if num_value is None:
                continue
            metric_values_map[metric_key].append(num_value)

    ordered_keys = list(QUALITY_METRIC_LABELS.keys())
    for metric_key in metric_values_map.keys():
        if metric_key not in QUALITY_METRIC_LABELS:
            ordered_keys.append(metric_key)

    aggregated: List[QualityMetricValueSchema] = []
    for metric_key in ordered_keys:
        values = metric_values_map.get(metric_key, [])
        if not values:
            continue
        if metric_key in SUM_METRIC_KEYS:
            num_value = float(sum(values))
        else:
            num_value = float(sum(values) / len(values))
        is_warning = _is_metric_warning(metric_key, num_value)
        aggregated.append(
            QualityMetricValueSchema(
                key=metric_key,
                label=QUALITY_METRIC_LABELS.get(metric_key, metric_key),
                display=_format_metric_display(metric_key, num_value),
                num=round(num_value, 6),
                is_warning=is_warning,
                raw=num_value,
            )
        )
    return aggregated


def _build_metric_tree(
    metric: CodeMetric,
    module: CodeModule,
    owner_map: Dict[Tuple[str, str], Dict[str, List[str]]],
) -> List[QualityTreeNodeSchema]:
    module_owner_names = _module_owner_names(module)
    module_owner_ids = _module_owner_ids(module)

    node_rows = list(
        CodeMetricNode.objects.filter(metric=metric, is_deleted=False).order_by(
            "depth",
            "order_index",
            "sys_create_datetime",
        ).only(
            "id",
            "parent_id",
            "node_key",
            "version_name",
            "depth",
            "order_index",
            "metric_values",
            "warning_metrics",
            "warning_count",
            "clean_code_rate",
            "clean_code_total",
            "unachieved_clean_code",
            "is_clean_code",
        )
    )
    if not node_rows:
        return []

    node_payload_map: Dict[str, QualityTreeNodeSchema] = {}
    roots: List[QualityTreeNodeSchema] = []
    row_map = {str(item.id): item for item in node_rows}

    for row in node_rows:
        owner_info = owner_map.get((str(module.id), row.node_key))
        owner_names = (
            list(owner_info.get("owner_names") or [])
            if owner_info
            else list(module_owner_names)
        )
        owner_ids = (
            list(owner_info.get("owner_ids") or [])
            if owner_info
            else list(module_owner_ids)
        )
        node_payload_map[str(row.id)] = QualityTreeNodeSchema(
            id=str(row.id),
            node_key=row.node_key,
            version_name=row.version_name,
            owner_names=owner_names,
            owner_ids=owner_ids,
            depth=row.depth,
            clean_code_rate=row.clean_code_rate,
            is_clean_code=row.is_clean_code,
            unachieved_clean_code=list(row.unachieved_clean_code or []),
            warning_count=row.warning_count,
            warning_metrics=list(row.warning_metrics or []),
            metric_values=_metric_values_to_list(row.metric_values),
            children=[],
        )

    for row in node_rows:
        node_id = str(row.id)
        parent_id = str(row.parent_id) if row.parent_id else None
        payload = node_payload_map[node_id]
        if parent_id and parent_id in node_payload_map:
            node_payload_map[parent_id].children.append(payload)
            continue
        if parent_id and parent_id not in row_map:
            roots.append(payload)
            continue
        if not parent_id:
            roots.append(payload)
    return roots


def _normalize_filter_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_project_type_filter(value: Any) -> str:
    text = _normalize_filter_text(value).lower()
    if not text:
        return ""
    if "vehicle" in text or "车控" in text:
        return "vehicle"
    if "cockpit" in text or "座舱" in text:
        return "cockpit"
    return text


def _build_project_type_query(project_type_filter: str) -> Q:
    if not project_type_filter:
        return Q()
    if project_type_filter == "vehicle":
        return Q(type__icontains="车控") | Q(type__icontains="vehicle")
    if project_type_filter == "cockpit":
        return Q(type__icontains="座舱") | Q(type__icontains="cockpit")
    return Q(type__icontains=project_type_filter)


def get_quality_overview(
    filters: QualityOverviewFilterSchema | None = None,
):
    filters = filters or QualityOverviewFilterSchema()
    project_name = _normalize_filter_text(filters.project_name)
    project_manager = _normalize_filter_text(filters.project_manager)
    project_type = _normalize_project_type_filter(filters.project_type)
    oem_name_keyword = _normalize_filter_text(filters.oem_name).lower()
    filter_record_date = parse_record_date(filters.date)

    query = Q(
        is_deleted=False,
        enable_quality=True,
        is_closed=False,
    )
    if project_name:
        query &= Q(name__icontains=project_name)
    if project_manager:
        query &= (
            Q(managers__name__icontains=project_manager)
            | Q(managers__username__icontains=project_manager)
        )
    query &= _build_project_type_query(project_type)

    projects = (
        Project.objects.filter(query)
        .prefetch_related("managers")
        .distinct()
    )

    result: List[ProjectQualitySummarySchema] = []
    for project in projects:
        modules = list(
            CodeModule.objects.filter(project=project, is_deleted=False).prefetch_related(
                "owners",
            )
        )
        managers = ",".join([item.name or item.username for item in project.managers.all()])

        modules_by_oem: Dict[str, List[CodeModule]] = defaultdict(list)
        for module in modules:
            oem_key = (module.oem_name or "").strip() or "UNKNOWN_OEM"
            modules_by_oem[oem_key].append(module)

        for oem_name, oem_modules in modules_by_oem.items():
            if oem_name_keyword and oem_name_keyword not in oem_name.lower():
                continue

            latest_metrics: List[Tuple[CodeModule, CodeMetric]] = []
            for module in oem_modules:
                latest = _latest_metric(module)
                if latest:
                    latest_metrics.append((module, latest))

            total_loc = 0
            total_function_count = 0
            total_dangerous = 0
            duplication_rates: List[float] = []
            clean_code_rates: List[float] = []
            clean_code_pass_modules = 0
            unachieved_clean_code: List[str] = []
            total_node_count = 0
            warning_node_count = 0
            latest_date = None

            for _, latest in latest_metrics:
                total_loc += int(latest.loc or 0)
                total_function_count += int(latest.function_count or 0)
                total_dangerous += int(latest.dangerous_func_count or 0)
                duplication_rates.append(float(latest.duplication_rate or 0.0))
                clean_code_rates.append(float(latest.clean_code_rate or 0.0))
                total_node_count += int(latest.total_node_count or 0)
                warning_node_count += int(latest.warning_node_count or 0)
                for issue in latest.unachieved_clean_code or []:
                    issue_text = str(issue or "").strip()
                    if issue_text and issue_text not in unachieved_clean_code:
                        unachieved_clean_code.append(issue_text)
                if latest.is_clean_code:
                    clean_code_pass_modules += 1
                if latest_date is None or latest.record_date > latest_date:
                    latest_date = latest.record_date

            if filter_record_date and latest_date != filter_record_date:
                continue

            metric_values = _aggregate_oem_metric_values(
                [metric for _, metric in latest_metrics],
            )
            warning_metrics = [item.key for item in metric_values if item.is_warning]
            if clean_code_pass_modules < len(oem_modules):
                warning_metrics.append("clean_code")

            avg_dup = (
                round(sum(duplication_rates) / len(duplication_rates), 4)
                if duplication_rates
                else 0.0
            )
            avg_clean_code_rate = (
                round(sum(clean_code_rates) / len(clean_code_rates), 6)
                if clean_code_rates
                else 0.0
            )

            result.append(
                ProjectQualitySummarySchema(
                    project_id=str(project.id),
                    project_name=project.name,
                    project_domain=project.domain,
                    project_type=project.type,
                    project_managers=managers,
                    record_date=latest_date,
                    oem_name=oem_name,
                    total_loc=total_loc,
                    total_function_count=total_function_count,
                    total_dangerous_func_count=total_dangerous,
                    avg_duplication_rate=avg_dup,
                    module_count=len(oem_modules),
                    clean_code_achieve_rate=avg_clean_code_rate,
                    clean_code_pass_modules=clean_code_pass_modules,
                    total_node_count=total_node_count,
                    warning_node_count=warning_node_count,
                    warning_count=len(set(warning_metrics)),
                    warning_metrics=list(dict.fromkeys(warning_metrics)),
                    unachieved_clean_code=unachieved_clean_code,
                    metric_values=metric_values,
                )
            )

    result.sort(key=lambda item: (item.project_name, item.oem_name))
    return result


def get_project_quality_details(
    project_id: str,
    include_tree: bool = True,
    record_date: date | None = None,
):
    modules = (
        CodeModule.objects.filter(project_id=project_id, is_deleted=False)
        .prefetch_related("owners")
        .order_by("oem_name", "module")
    )
    owner_map = _node_owner_config_map(list(modules))

    result: List[ModuleQualityDetailSchema] = []
    for module in modules:
        latest = _pick_metric_by_date(module, record_date)
        if record_date is not None and latest is None:
            continue
        metric_values = (
            _metric_values_to_list(latest.summary_metrics if latest else {})
            if include_tree
            else []
        )
        nodes = (
            _build_metric_tree(latest, module, owner_map)
            if latest and include_tree
            else []
        )
        result.append(
            ModuleQualityDetailSchema(
                id=str(module.id),
                oem_name=module.oem_name,
                module=module.module,
                owner_names=_module_owner_names(module),
                owner_ids=_module_owner_ids(module),
                record_date=latest.record_date if latest else None,
                loc=int(latest.loc or 0) if latest else 0,
                function_count=int(latest.function_count or 0) if latest else 0,
                dangerous_func_count=int(latest.dangerous_func_count or 0) if latest else 0,
                duplication_rate=float(latest.duplication_rate or 0.0) if latest else 0.0,
                is_clean_code=bool(latest.is_clean_code) if latest else False,
                clean_code_rate=float(latest.clean_code_rate or 0.0) if latest else 0.0,
                clean_code_total=int(latest.clean_code_total or 11) if latest else 11,
                unachieved_clean_code=list(latest.unachieved_clean_code or []) if latest else [],
                warning_count=int(latest.warning_count or 0) if latest else 0,
                warning_metrics=list(latest.warning_metrics or []) if latest else [],
                total_node_count=int(latest.total_node_count or 0) if latest else 0,
                warning_node_count=int(latest.warning_node_count or 0) if latest else 0,
                root_version_name=latest.version_name if latest else "",
                metric_values=metric_values,
                nodes=nodes,
            )
        )
    return result


def get_project_record_dates(project_id: str) -> List[str]:
    record_dates = (
        CodeMetric.objects.filter(
            module__project_id=project_id,
            module__is_deleted=False,
            is_deleted=False,
        )
        .exclude(record_date__isnull=True)
        .values_list("record_date", flat=True)
        .distinct()
        .order_by("-record_date")
    )
    return [item.strftime("%Y%m%d") for item in record_dates if item]


def refresh_project_quality(project_id: str):
    project = Project.objects.get(id=project_id)
    sync_project_quality_metrics(project)
    return True


def refresh_all_projects_quality():
    """
    全量刷新所有开启代码质量统计的项目数据。
    可供定时任务直接调用。
    """
    return sync_all_projects_quality()


def config_module(request, data: ModuleConfigSchema):
    data_dict = data.dict()
    module_id = data_dict.pop("id", None)
    owner_ids = data_dict.pop("owner_ids", [])

    project_id = str(data_dict.get("project_id") or "").strip()
    oem_name = str(data_dict.get("oem_name") or "").strip()
    module_name = str(data_dict.get("module") or "").strip()
    if not project_id or not oem_name or not module_name:
        raise HttpError(422, "project_id、oem_name、module 不能为空")

    try:
        if module_id:
            module = CodeModule.objects.filter(id=module_id, is_deleted=False).first()
            if not module:
                raise HttpError(404, "模块配置不存在")
            duplicated = (
                CodeModule.objects.filter(
                    project_id=project_id,
                    oem_name=oem_name,
                    module=module_name,
                    is_deleted=False,
                )
                .exclude(id=module_id)
                .exists()
            )
            if duplicated:
                raise HttpError(409, f"模块 {oem_name}-{module_name} 已存在")
            module.project_id = project_id
            module.oem_name = oem_name
            module.module = module_name
            module.save(update_fields=["project", "oem_name", "module", "sys_update_datetime"])
        else:
            existing = CodeModule.objects.filter(
                project_id=project_id,
                oem_name=oem_name,
                module=module_name,
                is_deleted=False,
            ).first()
            if existing:
                module = existing
            else:
                module = fu_crud.create(request, data_dict, CodeModule)
    except IntegrityError:
        raise HttpError(409, f"模块 {oem_name}-{module_name} 已存在")

    if owner_ids is not None:
        module.owners.set(owner_ids)

    try:
        project = Project.objects.get(id=project_id)
        if project.enable_quality:
            sync_project_quality_metrics(project)
    except Exception as exc:
        print(f"Initial quality sync failed: {exc}")
    return module


def delete_module(module_id: str):
    module = CodeModule.objects.filter(id=module_id, is_deleted=False).first()
    if not module:
        raise HttpError(404, "模块配置不存在")
    module.delete()
    return True


def record_module_metric(module_id: str, data: CodeMetricSchema):
    metric, _ = CodeMetric.objects.update_or_create(
        module_id=module_id,
        record_date=data.record_date,
        defaults=data.dict(exclude={"record_date"}),
    )
    return metric


def update_node_owner(data: NodeOwnerUpdateSchema):
    module = CodeModule.objects.filter(
        id=data.module_id,
        is_deleted=False,
    ).first()
    if not module:
        raise HttpError(404, "模块不存在")

    node_key = str(data.node_key or "").strip()
    if not node_key:
        raise HttpError(422, "node_key不能为空")

    owner_ids = [str(item).strip() for item in (data.owner_ids or []) if str(item).strip()]
    owner_ids = list(dict.fromkeys(owner_ids))

    latest_metric = _latest_metric(module)
    if latest_metric:
        exists = CodeMetricNode.objects.filter(
            metric=latest_metric,
            node_key=node_key,
            is_deleted=False,
        ).exists()
        if not exists:
            raise HttpError(404, "节点不存在")

    config = CodeNodeOwnerConfig.objects.filter(
        module=module,
        node_key=node_key,
    ).first()

    if not owner_ids:
        if config:
            config.owners.clear()
            config.is_deleted = True
            config.save(update_fields=["is_deleted", "sys_update_datetime"])
        return True

    if not config:
        config = CodeNodeOwnerConfig.objects.create(
            module=module,
            node_key=node_key,
        )
    elif config.is_deleted:
        config.is_deleted = False
        config.save(update_fields=["is_deleted", "sys_update_datetime"])

    config.owners.set(owner_ids)
    return True
