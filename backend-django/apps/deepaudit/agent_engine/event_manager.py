import json
import logging
from typing import Any, Dict, Optional
from asgiref.sync import sync_to_async

from apps.deepaudit.agent_task.agent_task_model import AgentEvent, AgentFinding
from apps.deepaudit.realtime import push_task_event

logger = logging.getLogger(__name__)

class EventManager:
    def __init__(self, task_id: str, websocket_manager=None):
        self.task_id = task_id
        self.websocket_manager = websocket_manager
        self.sequence = 0

    async def init_sequence(self):
        # Get the latest sequence from db safely
        @sync_to_async
        def get_max_sequence():
            last_event = AgentEvent.objects.filter(task_id=self.task_id).order_by('-sequence').first()
            return last_event.sequence if last_event else 0
        self.sequence = await get_max_sequence()

    async def emit(self, event_type: str, phase: str = None, message: str = None, **kwargs):
        self.sequence += 1
        
        # Build event data
        event_data = {
            "task_id": self.task_id,
            "event_type": event_type,
            "phase": phase,
            "message": message,
            "sequence": self.sequence,
        }
        
        allowed_fields = ["tool_name", "tool_input", "tool_output", "tool_duration_ms", "progress_percent", "tokens_used", "event_metadata"]
        for field in allowed_fields:
            if field in kwargs:
                event_data[field] = kwargs[field]

        finding = kwargs.get('finding')
        if finding:
            event_data["finding"] = finding
        
        # Async db write
        @sync_to_async
        def save_event():
            AgentEvent.objects.create(**event_data)
        
        try:
            await save_event()
        except Exception as e:
            logger.error(f"Failed to save AgentEvent: {e}")

        # Async WebSocket push via Focus_Admin's realtime.py
        payload = event_data.copy()
        if finding:
            payload["finding_id"] = str(finding.id)
            del payload["finding"]
            
        try:
            # push_task_event is sync in Focus_Admin, wrap it
            @sync_to_async
            def push_ws():
                push_task_event(self.task_id, payload)
            await push_ws()
        except Exception as e:
            logger.error(f"Failed to push ws event: {e}")

    async def emit_tool_start(self, tool_name: str, tool_input: Dict[str, Any], phase: str = None):
        await self.emit(
            event_type="tool_start",
            phase=phase,
            message=f"Starting tool {tool_name}",
            tool_name=tool_name,
            tool_input=tool_input
        )

    async def emit_tool_end(self, tool_name: str, tool_output: Any, phase: str = None, duration_ms: int = None):
        await self.emit(
            event_type="tool_end",
            phase=phase,
            message=f"Tool {tool_name} completed",
            tool_name=tool_name,
            tool_output=tool_output,
            tool_duration_ms=duration_ms
        )

    async def emit_finding(self, finding: AgentFinding, phase: str = None):
        await self.emit(
            event_type="finding_new",
            phase=phase,
            message=f"Discovered vulnerability: {finding.title}",
            finding=finding
        )
