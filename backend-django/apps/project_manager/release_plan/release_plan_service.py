from collections import Counter, OrderedDict
from datetime import date, timedelta

from django.db.models import Q
from ninja.errors import HttpError

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


def _unique_values(values):
    """按出现顺序压缩摘要字段，避免项目行重复展示。"""
    result = []
    seen = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _week_bucket(day):
    """把发布日期归档到 ISO 周的周一，保证趋势统计稳定。"""
    week_start = day - timedelta(days=day.weekday())
    iso_year, iso_week, _ = day.isocalendar()
    return f"{iso_year}-W{iso_week:02d}", week_start


def _build_weekly_trends(rows):
    """基于当前筛选结果生成未来发布周趋势和版本类型周趋势。"""
    today = date.today()
    weekly_counter = Counter()
    version_weekly_counter = Counter()

    for row in rows:
        if row["release_date"] < today:
            continue
        week, week_start = _week_bucket(row["release_date"])
        weekly_counter[(week_start, week)] += 1
        version_weekly_counter[
            (week_start, week, row["version_type_label"] or row["version_type"])
        ] += 1

    weekly_trend = [
        {"week": week, "week_start": week_start, "count": count}
        for (week_start, week), count in sorted(weekly_counter.items())
    ]
    version_weekly_trend = [
        {
            "week": week,
            "week_start": week_start,
            "version_type": version_type,
            "count": count,
        }
        for (week_start, week, version_type), count in sorted(
            version_weekly_counter.items()
        )
    ]
    return weekly_trend, version_weekly_trend


def get_release_plan_project_board(filters, page=1, page_size=20):
    """按项目聚合发布计划，返回项目分页、展开明细和周趋势统计。"""
    if filters.scenario not in {"vehicle", "cockpit"}:
        raise HttpError(422, "发布场景必须为 vehicle 或 cockpit")

    rows = [
        serialize_release_plan(item)
        for item in build_release_plan_queryset(filters).order_by(
            "project__name",
            "project__code",
            "branch_name",
            "release_date",
            "order",
            "id",
        )
    ]

    grouped = OrderedDict()
    for row in rows:
        grouped.setdefault(row["project_id"], []).append(row)

    today = date.today()
    project_groups = []
    for project_rows in grouped.values():
        first = project_rows[0]
        release_dates = [row["release_date"] for row in project_rows]
        future_dates = [
            release_day for release_day in release_dates if release_day >= today
        ]
        project_groups.append(
            {
                "project_id": first["project_id"],
                "project_name": first["project_name"],
                "project_code": first["project_code"],
                "project_domain": first["project_domain"],
                "manager_names": first["manager_names"],
                "plan_count": len(project_rows),
                "branch_count": len({row["branch_name"] for row in project_rows}),
                "next_release_date": min(future_dates) if future_dates else None,
                "latest_release_date": max(release_dates) if release_dates else None,
                "branch_names": _unique_values(
                    row["branch_name"] for row in project_rows
                ),
                "version_types": _unique_values(
                    row["version_type_label"] or row["version_type"]
                    for row in project_rows
                ),
                "platform_names": _unique_values(
                    row["platform_name"] for row in project_rows
                ),
                "release_vehicles": _unique_values(
                    vehicle
                    for row in project_rows
                    for vehicle in (row["release_vehicles"] or [])
                ),
                "plans": project_rows,
            }
        )

    current_page = max(int(page or 1), 1)
    current_page_size = max(int(page_size or 20), 1)
    start = (current_page - 1) * current_page_size
    end = start + current_page_size
    weekly_trend, version_weekly_trend = _build_weekly_trends(rows)

    return {
        "items": project_groups[start:end],
        "total": len(project_groups),
        "weekly_trend": weekly_trend,
        "version_weekly_trend": version_weekly_trend,
    }


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
