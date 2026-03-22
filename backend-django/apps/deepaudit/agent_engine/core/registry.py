import logging
from typing import Optional, Dict, Any, List
from .state import AgentState
from apps.deepaudit.agent_task.agent_task_model import AgentTask
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class AgentRegistry:
    def __init__(self):
        self._agent_states: Dict[str, "AgentState"] = {}
        self._hierarchy: Dict[str, List[str]] = {}

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        parent_id: Optional[str] = None,
        state: Optional["AgentState"] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if state:
            self._agent_states[agent_id] = state
        if parent_id:
            if parent_id not in self._hierarchy:
                self._hierarchy[parent_id] = []
            if agent_id not in self._hierarchy[parent_id]:
                self._hierarchy[parent_id].append(agent_id)
        return True

    def get_agent_state(self, agent_id: str) -> Optional["AgentState"]:
        return self._agent_states.get(agent_id)

    async def update_agent_status(
        self,
        agent_id: str,
        status: str,
        message: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        state = self._agent_states.get(agent_id)
        if state:
            state.status = status
            if error:
                state.error = error
        
        @sync_to_async
        def _update():
            AgentTask.objects.filter(id=agent_id).update(status=status)
        await _update()
        return True

    def unregister_agent(self, agent_id: str) -> bool:
        self._agent_states.pop(agent_id, None)
        return True

agent_registry = AgentRegistry()
