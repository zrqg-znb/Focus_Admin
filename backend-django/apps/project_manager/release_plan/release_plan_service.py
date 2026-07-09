from collections import Counter, OrderedDict
from datetime import date, timedelta

from django.db.models import Q

from apps.project_manager.project.project_model import ProjectReleasePlan


def _version_type_label(item: ProjectReleasePlan) -> str:
    """解析发布计划的版本类型展示名称。"""
    return item.version_type


def _platform_name(item: ProjectReleasePlan) -> str:
    """按发布场景解析平台名称。"""
    if item.scenario == "vehicle":
        return item.idvp_platform.name if item.idvp_platform else ""
    if item.scenario == "cockpit":
        return item.cdc_platform.name if item.cdc_platform else ""
    return ""


def serialize_release_plan(item: ProjectReleasePlan) -> dict:
    """将发布计划模型转换为前端看板需要的扁平结构。"""
    managers = list(item.project.managers.all())
    return {
        "id": str(item.id),
        "project_id": str(item.project_id),
        "project_name": item.project.name,
        "project_code": item.project.code,
        "project_domain": item.project.domain,
        "manager_names": [manager.name or manager.username for manager in managers],
        "branch_name": item.branch_name,
        "release_date": item.release_date,
        "version_type": item.version_type,
        "version_type_label": _version_type_label(item),
        "scenario": item.scenario,
        "idvp_platform_id": str(item.idvp_platform_id) if item.idvp_platform_id else None,
        "idvp_platform_name": item.idvp_platform.name if item.idvp_platform else None,
        "cdc_platform_id": str(item.cdc_platform_id) if item.cdc_platform_id else None,
        "cdc_platform_name": item.cdc_platform.name if item.cdc_platform else None,
        "platform_name": _platform_name(item),
        "release_vehicles": item.release_vehicles or [],
        "order": item.order,
    }


def build_release_plan_queryset(filters):
    """按看板筛选条件构造发布计划查询集。"""
    query = Q(is_deleted=False, project__is_deleted=False)

    if filters.keyword:
        keyword = filters.keyword.strip()
        query &= (
            Q(project__name__icontains=keyword)
            | Q(project__code__icontains=keyword)
            | Q(branch_name__icontains=keyword)
        )
    if filters.project_id:
        query &= Q(project_id=filters.project_id)
    if filters.branch_name:
        query &= Q(branch_name__icontains=filters.branch_name.strip())
    if filters.version_type:
        query &= Q(version_type=filters.version_type)
    if filters.scenario:
        query &= Q(scenario=filters.scenario)
    if filters.release_date_start:
        query &= Q(release_date__gte=filters.release_date_start)
    if filters.release_date_end:
        query &= Q(release_date__lte=filters.release_date_end)
    if filters.platform_keyword:
        keyword = filters.platform_keyword.strip()
        query &= (
            Q(idvp_platform__name__icontains=keyword)
            | Q(cdc_platform__name__icontains=keyword)
        )
    if filters.vehicle_keyword:
        # MySQL JSONField 上 icontains 可覆盖字符串数组内的车型名称模糊查询。
        query &= Q(release_vehicles__icontains=filters.vehicle_keyword.strip())

    return (
        ProjectReleasePlan.objects.filter(query)
        .select_related("project", "idvp_platform", "cdc_platform")
        .prefetch_related("project__managers")
        .order_by("release_date", "project__name", "branch_name", "order", "id")
    )


def list_release_plans(filters):
    """返回发布计划查询集，交由分页器处理。"""
    return [serialize_release_plan(item) for item in build_release_plan_queryset(filters)]


def get_release_plan_calendar(filters):
    """按日期聚合发布计划并返回看板统计。"""
    today = date.today()
    start_date = filters.release_date_start or today.replace(day=1)
    end_date = filters.release_date_end or (today + timedelta(days=60))
    filters.release_date_start = start_date
    filters.release_date_end = end_date

    rows = [serialize_release_plan(item) for item in build_release_plan_queryset(filters)]
    grouped = OrderedDict()
    for row in rows:
        grouped.setdefault(row["release_date"], []).append(row)

    version_counter = Counter(row["version_type_label"] for row in rows)
    version_stats = [
        {
            "version_type": label,
            "version_type_label": label,
            "count": count,
        }
        for label, count in version_counter.most_common()
    ]

    return {
        "total": len(rows),
        "upcoming_count": sum(1 for row in rows if row["release_date"] >= today),
        "active_project_count": len({row["project_id"] for row in rows}),
        "start_date": start_date,
        "end_date": end_date,
        "version_stats": version_stats,
        "days": [{"date": day, "items": items} for day, items in grouped.items()],
    }
