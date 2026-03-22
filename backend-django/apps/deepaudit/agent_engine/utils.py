import json
from asgiref.sync import sync_to_async
from apps.deepaudit.agent_task.agent_task_model import AgentTask, AgentFinding, AgentEvent

@sync_to_async
def get_task(task_id: str) -> AgentTask:
    return AgentTask.objects.filter(id=task_id).first()

@sync_to_async
def update_task(task_id: str, **kwargs):
    AgentTask.objects.filter(id=task_id).update(**kwargs)

@sync_to_async
def create_finding(**kwargs) -> AgentFinding:
    return AgentFinding.objects.create(**kwargs)

@sync_to_async
def create_event(**kwargs) -> AgentEvent:
    return AgentEvent.objects.create(**kwargs)
