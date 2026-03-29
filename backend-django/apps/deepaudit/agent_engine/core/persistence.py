import json
import logging
from typing import Optional, Dict, Any
from asgiref.sync import sync_to_async

from apps.deepaudit.agent_task.agent_task_model import AgentCheckpoint, AgentTask
from apps.deepaudit.db_runtime import run_with_fresh_connection
from .state import AgentState

logger = logging.getLogger(__name__)


class AgentStatePersistence:
    """Agent state persistence using Django ORM"""

    def _resolve_task_id(self, state: AgentState) -> str | None:
        for container in (state.task_context or {}, state.inherited_context or {}):
            task_id = str(container.get("task_id") or container.get("root_task_id") or "").strip()
            if task_id:
                return task_id
        return None

    def is_restorable_payload(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        if isinstance(data.get("state"), dict):
            state_data = data.get("state") or {}
            return bool(state_data.get("agent_id")) and "status" in state_data
        return bool(data.get("agent_id")) and "status" in data

    def get_runtime_payload(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return {}
        runtime = data.get("runtime")
        if isinstance(runtime, dict):
            return runtime
        return {}

    async def save_state(
        self,
        state: AgentState,
        checkpoint_name: Optional[str] = None,
        *,
        payload: Dict[str, Any] | None = None,
    ) -> str:
        @sync_to_async
        def _save():
            def _persist() -> str:
                task_id = self._resolve_task_id(state)
                if not task_id:
                    logger.debug("Skip checkpoint persistence because task_id is missing for agent %s", state.agent_id)
                    return ""
                task = AgentTask.objects.filter(id=task_id, is_deleted=False).first()
                if not task:
                    logger.debug("Skip checkpoint persistence because task %s was not found", task_id)
                    return ""
                serialized = payload if isinstance(payload, dict) and payload else self._serialize_state(state)
                task.audit_plan = serialized
                task.sys_modifier = task.created_by
                task.save(update_fields=['audit_plan', 'sys_modifier', 'sys_update_datetime'])
                checkpoint = AgentCheckpoint.objects.create(
                    task=task,
                    agent_id=state.agent_id,
                    agent_name=state.agent_name,
                    agent_type=state.agent_type,
                    parent_agent_id=state.parent_id,
                    state_data=serialized,
                    iteration=state.iteration,
                    status=str(state.status),
                    total_tokens=state.total_tokens,
                    tool_calls=state.tool_calls,
                    findings_count=len(state.findings or []),
                    checkpoint_type='manual' if checkpoint_name and checkpoint_name not in {'auto', 'tool', 'llm'} else (checkpoint_name or 'auto'),
                    checkpoint_name=checkpoint_name or None,
                    checkpoint_metadata={
                        'phase': str((state.task_context or {}).get('phase') or '').strip() or None,
                        'task': state.task,
                        'errors_count': len(state.errors or []),
                        'messages_count': len(state.messages or []),
                    },
                    sys_creator=task.created_by,
                    sys_modifier=task.created_by,
                )
                stale_ids = list(
                    AgentCheckpoint.objects.filter(task=task, agent_id=state.agent_id, is_deleted=False)
                    .order_by('-sys_create_datetime')
                    .values_list('id', flat=True)[50:]
                )
                if stale_ids:
                    AgentCheckpoint.objects.filter(id__in=stale_ids).update(is_deleted=True, sys_modifier=task.created_by)
                return str(checkpoint.id)

            return run_with_fresh_connection(_persist)

        return await _save()

    async def load_latest_checkpoint(self, agent_id: str) -> Optional[AgentState]:
        @sync_to_async
        def _load():
            def _query():
                checkpoint = (
                    AgentCheckpoint.objects.filter(agent_id=agent_id, is_deleted=False)
                    .order_by('-sys_create_datetime')
                    .first()
                )
                if checkpoint and isinstance(checkpoint.state_data, dict):
                    return self._deserialize_state(checkpoint.state_data)
                return None

            return run_with_fresh_connection(_query)
        return await _load()

    def _serialize_state(self, state: AgentState) -> Dict[str, Any]:
        return {
            "version": "2.0",
            "state": json.loads(state.model_dump_json()),
        }

    def _deserialize_state(self, data: Dict[str, Any]) -> AgentState:
        state_data = data.get("state") if isinstance(data.get("state"), dict) else data
        return AgentState(**state_data)

    async def create_checkpoint(self, state: AgentState, message: Optional[str] = None) -> Optional[str]:
        return await self.save_state(state, message)

    async def auto_checkpoint(self, state: AgentState) -> Optional[str]:
        return await self.save_state(state, "auto")

    async def load_state_for_agent(self, agent_id: str) -> Optional[AgentState]:
        return await self.load_latest_checkpoint(agent_id)

agent_persistence = AgentStatePersistence()
