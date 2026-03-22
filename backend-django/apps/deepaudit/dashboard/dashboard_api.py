from __future__ import annotations

from ninja import Router

from . import dashboard_services
from .dashboard_schemas import (
    DataClearResultSchema,
    DashboardOverviewSchema,
    DataCleanupRequestSchema,
    DataCleanupResultSchema,
    DataExportSchema,
    DataImportRequestSchema,
    DataImportResultSchema,
    DataStatisticsSchema,
    HealthReportSchema,
)


dashboard_router = Router(tags=['DeepAudit-Dashboard'])
data_tools_router = Router(tags=['DeepAudit-DataTools'])


@dashboard_router.get('/overview', response=DashboardOverviewSchema, summary='获取 DeepAudit 仪表盘概览')
def get_overview(request, limit: int = 10):
    return dashboard_services.get_dashboard_overview(request.auth, limit=limit)


@data_tools_router.get('/health', response=HealthReportSchema, summary='获取 DeepAudit 健康检查')
def get_health(request):
    return dashboard_services.get_health_report(request.auth)


@data_tools_router.get('/stats', response=DataStatisticsSchema, summary='获取 DeepAudit 数据统计校验')
def get_stats(request):
    return dashboard_services.get_data_statistics(request.auth)


@data_tools_router.get('/export', response=DataExportSchema, summary='导出 DeepAudit 域数据')
def export_data(request, project_id: str = ''):
    return dashboard_services.export_domain_data(request.auth, project_id=project_id)


@data_tools_router.post('/import', response=DataImportResultSchema, summary='导入 DeepAudit 域数据')
def import_data(request, data: DataImportRequestSchema):
    return dashboard_services.import_domain_data(request.auth, data.payload)


@data_tools_router.post('/cleanup', response=DataCleanupResultSchema, summary='清理 DeepAudit 运行时数据')
def cleanup_data(request, data: DataCleanupRequestSchema):
    return dashboard_services.cleanup_runtime_storage(days=data.days, remove_reports=data.remove_reports)


@data_tools_router.post('/clear', response=DataClearResultSchema, summary='清空当前用户的 DeepAudit 域数据')
def clear_data(request):
    return dashboard_services.clear_domain_data(request.auth)
