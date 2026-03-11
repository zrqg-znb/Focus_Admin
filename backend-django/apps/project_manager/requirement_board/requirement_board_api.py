from ninja import Router

from common.fu_auth import BearerAuth as GlobalAuth

from . import requirement_board_services
from .requirement_board_schemas import (
    RequirementBoardDataQuerySchema,
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
    return requirement_board_services.get_filter_options()


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
