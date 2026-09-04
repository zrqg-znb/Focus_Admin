import json

from ninja import File, Form, Query, Router
from ninja.files import UploadedFile
from ninja.errors import HttpError

from common.fu_auth import BearerAuth as GlobalAuth

from . import services
from .schemas import AuditIn, ProjectIn, ProjectResponsibilityIn, ReportIn, ResponsibilityIn, ShieldApplicationIn


router = Router(auth=GlobalAuth())


def _user(request):
    """获取当前登录用户。"""
    return request.auth or request.user


@router.get('/users', summary='用户选项')
def users(request):
    """查询负责人和审批人选择项。"""
    return services.list_users()


@router.get('/projects', summary='治理项目列表')
def projects(request, page: int = Query(1), pageSize: int = Query(20), keyword: str = Query('')):
    """分页查询代码问题治理项目。"""
    return services.list_projects(page, pageSize, keyword)


@router.post('/projects', summary='创建治理项目')
def create_project(request, payload: ProjectIn):
    """创建独立的代码问题治理项目。"""
    return services.save_project(_user(request), None, payload)


@router.put('/projects/{project_id}', summary='更新治理项目')
def update_project(request, project_id: str, payload: ProjectIn):
    """更新代码问题治理项目。"""
    return services.save_project(_user(request), project_id, payload)


@router.delete('/projects/{project_id}', summary='删除治理项目')
def delete_project(request, project_id: str):
    """软删除代码问题治理项目。"""
    return services.delete_project(_user(request), project_id)


@router.get('/responsibilities', summary='责任田列表')
def responsibilities(request, page: int = Query(1), pageSize: int = Query(20), keyword: str = Query('')):
    """分页查询责任田。"""
    return services.list_responsibilities(page, pageSize, keyword)


@router.post('/responsibilities', summary='创建责任田')
def create_responsibility(request, payload: ResponsibilityIn):
    """创建责任田及审批人员范围。"""
    return services.save_responsibility(_user(request), None, payload)


@router.put('/responsibilities/{responsibility_id}', summary='更新责任田')
def update_responsibility(request, responsibility_id: str, payload: ResponsibilityIn):
    """更新责任田及审批人员范围。"""
    return services.save_responsibility(_user(request), responsibility_id, payload)


@router.delete('/responsibilities/{responsibility_id}', summary='删除责任田')
def delete_responsibility(request, responsibility_id: str):
    """软删除责任田。"""
    return services.delete_responsibility(_user(request), responsibility_id)


@router.get('/project-responsibilities', summary='项目责任田关联列表')
def project_responsibilities(request, page: int = Query(1), pageSize: int = Query(20), keyword: str = Query('')):
    """分页查询项目责任田关联。"""
    return services.list_links(page, pageSize, keyword)


@router.post('/project-responsibilities', summary='创建项目责任田关联')
def create_project_responsibility(request, payload: ProjectResponsibilityIn):
    """创建项目责任田关联。"""
    return services.save_link(_user(request), None, payload)


@router.put('/project-responsibilities/{link_id}', summary='更新项目责任田关联')
def update_project_responsibility(request, link_id: str, payload: ProjectResponsibilityIn):
    """更新项目责任田关联。"""
    return services.save_link(_user(request), link_id, payload)


@router.delete('/project-responsibilities/{link_id}', summary='删除项目责任田关联')
def delete_project_responsibility(request, link_id: str):
    """软删除项目责任田关联。"""
    return services.delete_link(_user(request), link_id)


@router.post('/reports/ingest', summary='接入扫描 JSON')
def ingest_report(request, payload: ReportIn):
    """接收第三方扫描 JSON 并解析落库。"""
    return services.ingest_report(_user(request), payload.project_id, payload.responsibility_id, payload.tool_name, payload.report, 'api')


@router.post('/reports/upload', summary='上传扫描 JSON')
def upload_report(request, project_id: str = Form(...), responsibility_id: str = Form(...), tool_name: str = Form(...), file: UploadedFile = File(...)):
    """上传并解析第三方扫描 JSON 文件。"""
    try:
        payload = json.loads(file.read().decode('utf-8-sig'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpError(422, f'扫描文件不是有效 UTF-8 JSON：{exc}') from exc
    return services.ingest_report(_user(request), project_id, responsibility_id, tool_name, payload, 'upload')


@router.get('/reports', summary='扫描报告列表')
def reports(request, page: int = Query(1), pageSize: int = Query(20), project_id: str = Query(''), responsibility_id: str = Query('')):
    """分页查询扫描报告。"""
    return services.list_reports(page, pageSize, project_id, responsibility_id)


@router.get('/reports/{report_id}', summary='扫描报告详情')
def report_detail(request, report_id: str):
    """查询扫描报告详情。"""
    return services.get_report(report_id)


@router.get('/dashboard/summary', summary='治理看板统计')
def dashboard_summary(request, project_id: str = Query(''), responsibility_id: str = Query('')):
    """查询项目责任田问题统计和排名。"""
    return services.dashboard_summary(project_id, responsibility_id)


@router.get('/dashboard/trend', summary='治理趋势统计')
def dashboard_trend(request, project_id: str = Query(''), responsibility_id: str = Query(''), days: int = Query(30)):
    """查询最近扫描问题趋势。"""
    return services.dashboard_trend(project_id, responsibility_id, days)


@router.get('/findings', summary='问题明细列表')
def findings(request, page: int = Query(1), pageSize: int = Query(20), project_id: str = Query(''), responsibility_id: str = Query(''), tool_name: str = Query(''), severity: str = Query(''), shield_status: str = Query(''), keyword: str = Query('')):
    """分页查询稳定问题及其最近命中。"""
    return services.list_findings(page, pageSize, project_id, responsibility_id, tool_name, severity, shield_status, keyword)


@router.get('/findings/{finding_id}', summary='问题详情')
def finding_detail(request, finding_id: str):
    """查询问题详情、身份和证据。"""
    return services.get_finding(finding_id)


@router.post('/shield-applications', summary='提交屏蔽申请')
def create_shield_application(request, payload: ShieldApplicationIn):
    """批量提交问题屏蔽申请。"""
    return services.create_application(_user(request), payload)


@router.get('/shield-applications', summary='屏蔽申请列表')
def shield_applications(request, page: int = Query(1), pageSize: int = Query(20), mode: str = Query('my_audit'), status: str = Query(''), project_id: str = Query(''), responsibility_id: str = Query('')):
    """查询我的审批或我的申请。"""
    return services.list_applications(_user(request), page, pageSize, mode, status, project_id, responsibility_id)


@router.post('/shield-applications/{application_id}/approve', summary='通过屏蔽申请')
def approve_application(request, application_id: str, payload: AuditIn):
    """审批通过屏蔽申请。"""
    return services.audit_application(_user(request), application_id, 'Approved', payload.comment)


@router.post('/shield-applications/{application_id}/reject', summary='驳回屏蔽申请')
def reject_application(request, application_id: str, payload: AuditIn):
    """驳回屏蔽申请。"""
    return services.audit_application(_user(request), application_id, 'Rejected', payload.comment)


@router.get('/shield-applications/{application_id}/logs', summary='屏蔽申请日志')
def application_logs(request, application_id: str):
    """查询屏蔽申请操作日志。"""
    return services.list_audit_logs(application_id)
