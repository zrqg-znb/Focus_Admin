from ninja import Router
from common.fu_auth import BearerAuth as GlobalAuth

from . import dts_statistics_services
from .dts_statistics_schemas import (
    DtsExtensionSaveSchema,
    DtsListResponseSchema,
    DtsSaveResponseSchema,
    DtsStatisticsQuerySchema,
    DtsSummarySchema,
)

router = Router(tags=["DTS统计看板"], auth=GlobalAuth())

@router.post("/list", response=DtsListResponseSchema)
def list_dts(request, query: DtsStatisticsQuerySchema):
    return dts_statistics_services.get_dts_statistics_list(query)

@router.post("/save-extension/{defect_no}", response=DtsSaveResponseSchema)
def save_extension(request, defect_no: str, data: DtsExtensionSaveSchema):
    return dts_statistics_services.save_dts_extension(defect_no, data)

@router.post("/summary", response=DtsSummarySchema)
def get_summary(request, query: DtsStatisticsQuerySchema):
    return dts_statistics_services.get_dts_statistics_summary(query)
