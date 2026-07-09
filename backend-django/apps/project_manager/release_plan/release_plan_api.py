from typing import List

from ninja import Query, Router
from ninja.pagination import paginate

from common.fu_auth import BearerAuth as GlobalAuth
from common.fu_pagination import MyPagination

from .release_plan_schema import (
    ReleasePlanCalendarOut,
    ReleasePlanFilterSchema,
    ReleasePlanOut,
)
from . import release_plan_service

router = Router(tags=["Project Release Plan"], auth=GlobalAuth())


@router.get("/", response=List[ReleasePlanOut], summary="获取发布计划明细")
@paginate(MyPagination)
def list_release_plans(request, filters: ReleasePlanFilterSchema = Query(...)):
    """分页查询项目发布计划明细，供看板表格使用。"""
    return release_plan_service.list_release_plans(filters)


@router.get("/calendar", response=ReleasePlanCalendarOut, summary="获取发布计划日历看板")
def get_release_plan_calendar(request, filters: ReleasePlanFilterSchema = Query(...)):
    """按日期范围获取发布计划日历聚合和统计。"""
    return release_plan_service.get_release_plan_calendar(filters)
