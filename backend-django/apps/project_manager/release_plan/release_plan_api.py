from typing import List

from ninja import Query, Router
from ninja.pagination import paginate

from common.fu_auth import BearerAuth as GlobalAuth
from common.fu_pagination import MyPagination

from .release_plan_schema import (
    ReleasePlanFilterSchema,
    ReleasePlanOut,
    ReleasePlanProjectBoardOut,
)
from . import release_plan_service

router = Router(tags=["Project Release Plan"], auth=GlobalAuth())


@router.get("/", response=List[ReleasePlanOut], summary="获取发布计划明细")
@paginate(MyPagination)
def list_release_plans(request, filters: ReleasePlanFilterSchema = Query(...)):
    """分页查询项目发布计划明细，供看板表格使用。"""
    return release_plan_service.list_release_plans(filters)


@router.get(
    "/project-board",
    response=ReleasePlanProjectBoardOut,
    summary="获取项目维度发布计划看板",
)
def get_release_plan_project_board(
    request,
    filters: ReleasePlanFilterSchema = Query(...),
    page: int = 1,
    pageSize: int = 20,
):
    """按项目聚合发布计划，返回项目分页、展开明细和周趋势统计。"""
    return release_plan_service.get_release_plan_project_board(filters, page, pageSize)
