from __future__ import annotations

from ninja import Router

from . import scan_task_services
from .scan_task_schemas import (
    AuditIssueSchema,
    AuditIssueUpdateSchema,
    AuditTaskCreateSchema,
    AuditTaskDetailSchema,
    AuditTaskListSchema,
    AuditTaskSchema,
    InstantAnalysisListSchema,
    InstantAnalysisRecordSchema,
    InstantAnalysisRequestSchema,
)

from apps.deepaudit.tasks import dispatch_deepaudit_task, run_scan_task

tasks_router = Router(tags=['DeepAudit-Tasks'])
scan_router = Router(tags=['DeepAudit-Scan'])
reports_router = Router(tags=['DeepAudit-Reports'])


@tasks_router.get('', response=AuditTaskListSchema, summary='获取扫描任务列表')
def list_tasks(request, project_id: str = '', status: str = '', task_type: str = '', page: int = 1, pageSize: int = 20):
    return scan_task_services.list_tasks(
        request.auth,
        project_id=project_id,
        status=status,
        task_type=task_type,
        page=page,
        page_size=pageSize,
    )


@tasks_router.get('/{task_id}', response=AuditTaskDetailSchema, summary='获取扫描任务详情')
def get_task(request, task_id: str):
    return scan_task_services.serialize_task(scan_task_services.get_task(request.auth, task_id), include_issues=True)


@tasks_router.get('/{task_id}/issues', response=dict, summary='获取任务问题列表')
def list_task_issues(request, task_id: str, severity: str = '', status: str = '', keyword: str = '', page: int = 1, pageSize: int = 50):
    return scan_task_services.list_issues(
        request.auth,
        task_id,
        severity=severity,
        status=status,
        keyword=keyword,
        page=page,
        page_size=pageSize,
    )


@tasks_router.put('/{task_id}/issues/{issue_id}', response=AuditIssueSchema, summary='更新问题状态')
def update_task_issue(request, task_id: str, issue_id: str, data: AuditIssueUpdateSchema):
    return scan_task_services.update_issue_status(request.auth, task_id, issue_id, data.status)


@tasks_router.post('/{task_id}/cancel', response=bool, summary='取消扫描任务')
def cancel_task(request, task_id: str):
    return scan_task_services.cancel_task(request.auth, task_id)


@scan_router.post('/repository', response=AuditTaskSchema, summary='创建仓库扫描任务')
def create_repository_scan(request, data: AuditTaskCreateSchema):
    task = scan_task_services.create_task(request.auth, data.dict(), task_type='repository')
    dispatch_error = dispatch_deepaudit_task(run_scan_task, str(task.id))
    if dispatch_error:
        task = scan_task_services.mark_dispatch_failed(task, dispatch_error)
    return scan_task_services.serialize_task(task)


@scan_router.post('/zip', response=AuditTaskSchema, summary='创建 ZIP 扫描任务')
def create_zip_scan(request, data: AuditTaskCreateSchema):
    task = scan_task_services.create_task(request.auth, data.dict(), task_type='zip')
    dispatch_error = dispatch_deepaudit_task(run_scan_task, str(task.id))
    if dispatch_error:
        task = scan_task_services.mark_dispatch_failed(task, dispatch_error)
    return scan_task_services.serialize_task(task)


@scan_router.post('/instant', response=InstantAnalysisRecordSchema, summary='即时分析')
def instant_analysis(request, data: InstantAnalysisRequestSchema):
    return scan_task_services.run_instant_analysis(request.auth, data.dict())


@scan_router.get('/instant/history', response=InstantAnalysisListSchema, summary='获取即时分析历史')
def list_instant_history(request, language: str = '', page: int = 1, pageSize: int = 20):
    return scan_task_services.list_instant_records(request.auth, page=page, page_size=pageSize, language=language)


@scan_router.get('/instant/history/{record_id}', response=InstantAnalysisRecordSchema, summary='获取即时分析详情')
def get_instant_history_record(request, record_id: str):
    return scan_task_services.serialize_instant_record(scan_task_services.get_instant_record(request.auth, record_id), include_code=True)


@scan_router.delete('/instant/history/{record_id}', response=bool, summary='删除即时分析记录')
def delete_instant_history_record(request, record_id: str):
    return scan_task_services.delete_instant_record(request.auth, record_id)


@scan_router.delete('/instant/history', response=bool, summary='清空即时分析历史')
def delete_all_instant_history(request):
    return scan_task_services.delete_all_instant_records(request.auth)


@reports_router.get('/tasks/{task_id}/json', summary='导出扫描任务 JSON 报告')
def export_task_json(request, task_id: str):
    return scan_task_services.export_task_json_response(request.auth, task_id)


@reports_router.get('/tasks/{task_id}/pdf', summary='导出扫描任务 PDF 报告')
def export_task_pdf(request, task_id: str):
    return scan_task_services.export_task_pdf_response(request.auth, task_id)


@reports_router.get('/instant/{record_id}/json', summary='导出即时分析 JSON')
def export_instant_json(request, record_id: str):
    return scan_task_services.export_instant_json_response(request.auth, record_id)


@reports_router.get('/instant/{record_id}/pdf', summary='导出即时分析 PDF')
def export_instant_pdf(request, record_id: str):
    return scan_task_services.export_instant_pdf_response(request.auth, record_id)
