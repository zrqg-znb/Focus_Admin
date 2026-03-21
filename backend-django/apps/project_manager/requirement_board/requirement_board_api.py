from ninja import Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import requirement_board_services
from .requirement_board_schemas import (
    RequirementBoardDataQuerySchema,
    RequirementBoardExportQuerySchema,
    RequirementBoardFilterPayloadSchema,
    RequirementBoardFilterOptionsSchema,
    RequirementBoardPageSchema,
    RequirementBoardQueryPreparePayloadSchema,
    RequirementBoardQueryPrepareResponseSchema,
    RequirementBoardQueryTaskSchema,
    RequirementBoardSummaryQuerySchema,
    RequirementBoardSummarySchema,
)

router = Router(tags=["RequirementBoard"], auth=GlobalAuth())


@router.get(
    "/filter-options",
    response=RequirementBoardFilterOptionsSchema,
    summary="获取需求看板筛选项",
)
def get_requirement_board_filter_options(request):
    return requirement_board_services.get_filter_options(request.auth)


@router.put(
    "/filter-preference",
    response=bool,
    summary="保存需求看板筛选偏好",
)
def save_requirement_board_filter_preference(
    request,
    data: RequirementBoardFilterPayloadSchema,
):
    return requirement_board_services.save_filter_preference(request.auth, data)


@router.delete(
    "/filter-preference",
    response=bool,
    summary="清空需求看板筛选偏好",
)
def delete_requirement_board_filter_preference(request):
    return requirement_board_services.delete_filter_preference(request.auth)


@router.post(
    "/query-prepare",
    response=RequirementBoardQueryPrepareResponseSchema,
    summary="准备需求看板查询",
)
def prepare_requirement_board_query(
    request,
    data: RequirementBoardQueryPreparePayloadSchema,
):
    return requirement_board_services.prepare_requirement_board_query(
        request.auth,
        data,
    )


@router.get(
    "/query-task/{task_id}",
    response=RequirementBoardQueryTaskSchema,
    summary="获取需求看板查询准备任务状态",
)
def get_requirement_board_query_task(request, task_id: str):
    return requirement_board_services.get_requirement_board_query_task(
        request.auth,
        task_id,
    )


@router.post(
    "/data",
    response=RequirementBoardPageSchema,
    summary="获取需求数据看板明细",
)
def get_requirement_board_data(request, data: RequirementBoardDataQuerySchema):
    return requirement_board_services.get_requirement_board_page(data, user=request.auth)


@router.post(
    "/summary",
    response=RequirementBoardSummarySchema,
    summary="获取需求总结看板数据",
)
def get_requirement_board_summary(request, data: RequirementBoardSummaryQuerySchema):
    return requirement_board_services.get_requirement_board_summary(data, user=request.auth)


@router.post(
    "/export",
    summary="导出需求数据看板明细",
)
def export_requirement_board_data(request, data: RequirementBoardExportQuerySchema):
    return requirement_board_services.export_requirement_board_data(data, user=request.auth)
