from __future__ import annotations

from ninja import Router

from apps.deepaudit.tasks import dispatch_deepaudit_task, run_agent_task

from . import agent_task_services
from .agent_task_schemas import (
    AgentCheckpointSchema,
    AgentEventSchema,
    AgentFindingSchema,
    AgentFindingStatusUpdateSchema,
    AgentSummarySchema,
    AgentTaskCreateSchema,
    AgentTaskListSchema,
    AgentTaskSchema,
    AgentTreeNodeSchema,
)

router = Router(tags=['DeepAudit-AgentTasks'])


@router.get('', response=AgentTaskListSchema, summary='获取 Agent 任务列表')
def list_agent_tasks(request, project_id: str = '', status: str = '', page: int = 1, pageSize: int = 20):
    return agent_task_services.list_tasks(request.auth, project_id=project_id, status=status, page=page, page_size=pageSize)


@router.post('', response=AgentTaskSchema, summary='创建 Agent 任务')
def create_agent_task(request, data: AgentTaskCreateSchema):
    instance = agent_task_services.create_task(request.auth, data.dict())
    dispatch_error = dispatch_deepaudit_task(run_agent_task, str(instance.id))
    if dispatch_error:
        instance = agent_task_services.mark_dispatch_failed(instance, dispatch_error)
    return agent_task_services.serialize_task(instance)


@router.get('/{task_id}', response=AgentTaskSchema, summary='获取 Agent 任务详情')
def get_agent_task(request, task_id: str):
    return agent_task_services.serialize_task(agent_task_services.get_task(request.auth, task_id))


@router.post('/{task_id}/cancel', response=bool, summary='取消 Agent 任务')
def cancel_agent_task(request, task_id: str):
    return agent_task_services.cancel_task(request.auth, task_id)


@router.get('/{task_id}/events', response=list[AgentEventSchema], summary='获取 Agent 事件列表')
def list_agent_events(request, task_id: str, after_sequence: int = 0, limit: int = 200):
    return agent_task_services.list_events(request.auth, task_id, after_sequence=after_sequence, limit=limit)


@router.get('/{task_id}/findings', response=list[AgentFindingSchema], summary='获取 Agent Findings')
def list_agent_findings(request, task_id: str, severity: str = '', vulnerability_type: str = '', status: str = ''):
    return agent_task_services.list_findings(request.auth, task_id, severity=severity, vulnerability_type=vulnerability_type, status=status)


@router.put('/{task_id}/findings/{finding_id}', response=AgentFindingSchema, summary='更新 Agent Finding 状态')
def update_agent_finding(request, task_id: str, finding_id: str, data: AgentFindingStatusUpdateSchema):
    return agent_task_services.update_finding_status(request.auth, task_id, finding_id, data.status)


@router.get('/{task_id}/summary', response=AgentSummarySchema, summary='获取 Agent 任务摘要')
def get_agent_summary(request, task_id: str):
    return agent_task_services.build_summary(agent_task_services.get_task(request.auth, task_id))


@router.get('/{task_id}/checkpoints', response=list[AgentCheckpointSchema], summary='获取 Agent 任务检查点')
def list_agent_checkpoints(request, task_id: str):
    return agent_task_services.build_checkpoints(agent_task_services.get_task(request.auth, task_id))


@router.get('/{task_id}/tree', response=list[AgentTreeNodeSchema], summary='获取 Agent 树')
def get_agent_tree(request, task_id: str):
    return agent_task_services.build_tree(agent_task_services.get_task(request.auth, task_id))
