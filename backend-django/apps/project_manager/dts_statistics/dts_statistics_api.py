from ninja import Router
from common.fu_auth import BearerAuth as GlobalAuth

from . import dts_statistics_services
from .dts_statistics_schemas import (
    DtsBatchExtensionSaveSchema,
    DtsBatchSaveResponseSchema,
    DtsDictOptionsSchema,
    DtsExtensionSaveSchema,
    DtsExportPrepareResponseSchema,
    DtsExportTaskSchema,
    DtsFieldSetRequestSchema,
    DtsFieldSetResponseSchema,
    DtsListResponseSchema,
    DtsQueryPrepareResponseSchema,
    DtsQueryTaskSchema,
    DtsSaveResponseSchema,
    DtsStatisticsExportSchema,
    DtsStatisticsQuerySchema,
    DtsSummarySchema,
)

router = Router(tags=["DTS统计看板"], auth=GlobalAuth())


@router.post("/list", response=DtsListResponseSchema)
def list_dts(request, query: DtsStatisticsQuerySchema):
    return dts_statistics_services.get_dts_statistics_list(query, user=request.auth)


@router.post(
    "/query-prepare",
    response=DtsQueryPrepareResponseSchema,
    summary="准备 DTS 查询数据",
)
def prepare_dts_query(request, data: DtsStatisticsExportSchema):
    return dts_statistics_services.prepare_dts_statistics_query(request.auth, data)


@router.get(
    "/query-task/{task_id}",
    response=DtsQueryTaskSchema,
    summary="获取 DTS 查询准备任务状态",
)
def get_dts_query_task(request, task_id: str):
    return dts_statistics_services.get_dts_statistics_query_task(request.auth, task_id)


@router.post("/save-extension/{defect_no}", response=DtsSaveResponseSchema)
def save_extension(request, defect_no: str, data: DtsExtensionSaveSchema):
    return dts_statistics_services.save_dts_extension(defect_no, data)


@router.post("/batch-save-extension", response=DtsBatchSaveResponseSchema)
def batch_save_extension(request, data: DtsBatchExtensionSaveSchema):
    return dts_statistics_services.batch_save_dts_extension(data)


@router.post("/summary", response=DtsSummarySchema)
def get_summary(request, query: DtsStatisticsQuerySchema):
    return dts_statistics_services.get_dts_statistics_summary(query, user=request.auth)


@router.get("/dict-options", response=DtsDictOptionsSchema, summary="获取 DTS 模块字典选项")
def get_dict_options(request):
    return dts_statistics_services.get_dts_statistics_dict_options()


@router.post(
    "/field-sets",
    response=DtsFieldSetResponseSchema,
    summary="获取 DTS 字段候选值集合",
)
def get_field_sets(request, data: DtsFieldSetRequestSchema):
    return dts_statistics_services.get_dts_statistics_field_sets(
        data,
        user=request.auth,
    )


@router.post("/export", summary="导出 DTS 统计明细")
def export_dts_statistics(request, query: DtsStatisticsExportSchema):
    return dts_statistics_services.export_dts_statistics(query, user=request.auth)


@router.post(
    "/export-prepare",
    response=DtsExportPrepareResponseSchema,
    summary="准备 DTS 导出任务",
)
def prepare_dts_export(request, data: DtsStatisticsExportSchema):
    return dts_statistics_services.prepare_dts_statistics_export(request.auth, data)


@router.get(
    "/export-task/{task_id}",
    response=DtsExportTaskSchema,
    summary="获取 DTS 导出任务状态",
)
def get_dts_export_task(request, task_id: str):
    return dts_statistics_services.get_dts_statistics_export_task(request.auth, task_id)


@router.get(
    "/export-task/{task_id}/download",
    summary="下载 DTS 导出任务文件",
)
def download_dts_export_task_file(request, task_id: str):
    return dts_statistics_services.download_dts_statistics_export_file(
        request.auth,
        task_id,
    )
