from ninja import Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import requirement_board_services
from .requirement_board_schemas import (
    RequirementBoardDataQuerySchema,
    RequirementBoardExportQuerySchema,
    RequirementBoardFilterPayloadSchema,
    RequirementBoardFilterOptionsSchema,
    RequirementBoardPageSchema,
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
    "/data",
    response=RequirementBoardPageSchema,
    summary="获取需求数据看板明细",
)
def get_requirement_board_data(request, data: RequirementBoardDataQuerySchema):
    return requirement_board_services.get_requirement_board_page(data)


@router.post(
    "/summary",
    response=RequirementBoardSummarySchema,
    summary="获取需求总结看板数据",
)
def get_requirement_board_summary(request, data: RequirementBoardSummaryQuerySchema):
    return requirement_board_services.get_requirement_board_summary(data)


@router.post(
    "/export",
    summary="导出需求数据看板明细",
)
def export_requirement_board_data(request, data: RequirementBoardExportQuerySchema):
    return requirement_board_services.export_requirement_board_data(data)
