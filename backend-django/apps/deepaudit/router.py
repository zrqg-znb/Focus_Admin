from __future__ import annotations

from ninja import Router

from apps.deepaudit.agent_task import agent_task_services
from apps.deepaudit.agent_task.agent_task_api import router as agent_task_router
from apps.deepaudit.audit_rule.audit_rule_api import router as audit_rule_router
from apps.deepaudit.dashboard.dashboard_api import dashboard_router, data_tools_router
from apps.deepaudit.project import project_services
from apps.deepaudit.project.project_api import router as project_router
from apps.deepaudit.project.project_schemas import ProjectMemberSaveSchema, ProjectMemberSchema, ProjectOwnerTransferSchema
from apps.deepaudit.prompt_template.prompt_template_api import router as prompt_template_router
from apps.deepaudit.rag.rag_api import router as rag_router
from apps.deepaudit.scan_task import scan_task_services
from apps.deepaudit.scan_task.scan_task_api import scan_router, tasks_router
from apps.deepaudit.user_config.user_config_api import embedding_router, settings_router, ssh_router


router = Router(tags=['Apps-DeepAudit'])
members_router = Router(tags=['DeepAudit-Members'])
reports_router = Router(tags=['DeepAudit-Reports'])


@members_router.get('/{project_id}', response=list[ProjectMemberSchema], summary='获取项目成员')
def list_members(request, project_id: str):
    return project_services.list_members(request.auth, project_id)


@members_router.post('/{project_id}', response=ProjectMemberSchema, summary='新增项目成员')
def add_member(request, project_id: str, data: ProjectMemberSaveSchema):
    return project_services.add_member(request.auth, project_id, data.dict())


@members_router.put('/{project_id}/{member_id}', response=ProjectMemberSchema, summary='更新项目成员')
def update_member(request, project_id: str, member_id: str, data: ProjectMemberSaveSchema):
    return project_services.update_member(request.auth, project_id, member_id, data.dict())


@members_router.delete('/{project_id}/{member_id}', response=bool, summary='删除项目成员')
def remove_member(request, project_id: str, member_id: str):
    return project_services.remove_member(request.auth, project_id, member_id)


@members_router.post('/{project_id}/transfer-owner', response=bool, summary='转移项目所有权')
def transfer_owner(request, project_id: str, data: ProjectOwnerTransferSchema):
    return project_services.transfer_owner(request.auth, project_id, data.user_id)


@reports_router.get('/tasks/{task_id}/json', summary='导出扫描任务 JSON')
def export_task_json(request, task_id: str):
    return scan_task_services.export_task_json_response(request.auth, task_id)


@reports_router.get('/tasks/{task_id}/pdf', summary='导出扫描任务 PDF')
def export_task_pdf(request, task_id: str):
    return scan_task_services.export_task_pdf_response(request.auth, task_id)


@reports_router.get('/instant/{record_id}/json', summary='导出即时分析 JSON')
def export_instant_json(request, record_id: str):
    return scan_task_services.export_instant_json_response(request.auth, record_id)


@reports_router.get('/instant/{record_id}/pdf', summary='导出即时分析 PDF')
def export_instant_pdf(request, record_id: str):
    return scan_task_services.export_instant_pdf_response(request.auth, record_id)


@reports_router.get('/agent-tasks/{task_id}/json', summary='导出 Agent 任务 JSON')
def export_agent_json(request, task_id: str):
    return agent_task_services.export_agent_json_response(request.auth, task_id)


@reports_router.get('/agent-tasks/{task_id}/pdf', summary='导出 Agent 任务 PDF')
def export_agent_pdf(request, task_id: str):
    return agent_task_services.export_agent_pdf_response(request.auth, task_id)


router.add_router('/projects', project_router)
router.add_router('/members', members_router)
router.add_router('/tasks', tasks_router)
router.add_router('/scan', scan_router)
router.add_router('/agent-tasks', agent_task_router)
router.add_router('/rules', audit_rule_router)
router.add_router('/prompts', prompt_template_router)
router.add_router('/settings', settings_router)
router.add_router('/embedding', embedding_router)
router.add_router('/rag', rag_router)
router.add_router('/ssh-keys', ssh_router)
router.add_router('/reports', reports_router)
router.add_router('/dashboard', dashboard_router)
router.add_router('/data-tools', data_tools_router)
