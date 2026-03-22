import json
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
from .state import AgentState, AgentStatus
from asgiref.sync import sync_to_async
from apps.deepaudit.agent_task.agent_task_model import AgentTask

logger = logging.getLogger(__name__)

class AgentStatePersistence:
    """Agent state persistence using Django ORM"""

    async def save_state(self, state: AgentState, checkpoint_name: Optional[str] = None) -> str:
        # In Django, we update the task's JSONField
        @sync_to_async
        def _save():
            task = AgentTask.objects.filter(id=state.agent_id).first()
            if task:
                task.audit_plan = self._serialize_state(state)
                task.save(update_fields=['audit_plan'])
        await _save()
        return "saved"

    async def load_latest_checkpoint(self, agent_id: str) -> Optional[AgentState]:
        @sync_to_async
        def _load():
            task = AgentTask.objects.filter(id=agent_id).first()
            if task and task.audit_plan and isinstance(task.audit_plan, dict):
                return self._deserialize_state(task.audit_plan)
            return None
        return await _load()

    def _serialize_state(self, state: AgentState) -> Dict[str, Any]:
        return json.loads(state.json())

    def _deserialize_state(self, data: Dict[str, Any]) -> AgentState:
        return AgentState(**data)

    async def create_checkpoint(self, state: AgentState, message: Optional[str] = None) -> Optional[str]:
        return await self.save_state(state, message)

    async def auto_checkpoint(self, state: AgentState) -> Optional[str]:
        return await self.save_state(state, "auto")

    async def load_state_for_agent(self, agent_id: str) -> Optional[AgentState]:
        return await self.load_latest_checkpoint(agent_id)

agent_persistence = AgentStatePersistence()
