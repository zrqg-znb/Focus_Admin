import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from asgiref.sync import sync_to_async

from apps.deepaudit.agent_task.agent_task_model import AgentEvent, AgentFinding
from apps.deepaudit.db_runtime import run_with_fresh_connection
from apps.deepaudit.realtime import push_task_event

logger = logging.getLogger(__name__)


SNAPSHOT_EVENT_TYPES = {
    "dispatch",
    "dispatch_complete",
    "error",
    "finding_new",
    "finding_verified",
    "info",
    "llm_complete",
    "phase_complete",
    "phase_start",
    "progress",
    "task_cancel",
    "task_complete",
    "task_error",
    "tool_call",
    "tool_result",
    "tool_start",
    "tool_end",
    "warning",
}

SNAPSHOT_FORCE_EVENT_TYPES = {
    "phase_start",
    "phase_complete",
    "finding_new",
    "finding_verified",
    "task_complete",
    "task_error",
    "task_cancel",
    "error",
}

SNAPSHOT_REFRESH_MIN_INTERVAL_SECONDS = 2.0
SNAPSHOT_REFRESH_MIN_SEQUENCE_GAP = 25


def _sanitize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    # 当前 MySQL 表字符集无法稳定落库 4-byte emoji，统一降级掉非 BMP 字符。
    return ''.join(ch for ch in str(value) if ord(ch) <= 0xFFFF)


def _normalize_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {
            str(key): _normalize_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, (int, float, bool)):
        return value
    if hasattr(value, "to_dict"):
        return _normalize_json_value(value.to_dict())
    return _sanitize_text(str(value))


@dataclass
class AgentEventData:
    event_type: str
    phase: Optional[str] = None
    message: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    tool_duration_ms: Optional[int] = None
    finding_id: Optional[str] = None
    tokens_used: int = 0
    metadata: Optional[Dict[str, Any]] = None


class AgentEventEmitter:
    """
    兼容原 DeepAudit Agent 事件发射器接口。
    底层仍复用当前 Django 侧 EventManager 持久化与推送逻辑。
    """

    def __init__(self, task_id: str, event_manager: 'EventManager'):
        self.task_id = task_id
        self.event_manager = event_manager
        self._current_phase: Optional[str] = None

    @property
    def current_phase(self) -> Optional[str]:
        return self._current_phase

    async def emit(self, event_data: AgentEventData):
        phase = event_data.phase or self._current_phase
        metadata = dict(event_data.metadata or {})
        if event_data.finding_id and 'finding_id' not in metadata:
            metadata['finding_id'] = event_data.finding_id

        await self.event_manager.emit(
            event_type=event_data.event_type,
            phase=phase,
            message=event_data.message,
            tool_name=event_data.tool_name,
            tool_input=event_data.tool_input,
            tool_output=event_data.tool_output,
            tool_duration_ms=event_data.tool_duration_ms,
            tokens_used=event_data.tokens_used,
            event_metadata=metadata,
        )

    async def emit_phase_start(self, phase: str, message: Optional[str] = None):
        self._current_phase = phase
        await self.emit(
            AgentEventData(
                event_type="phase_start",
                phase=phase,
                message=message or f"开始 {phase} 阶段",
            )
        )

    async def emit_phase_complete(self, phase: str, message: Optional[str] = None):
        await self.emit(
            AgentEventData(
                event_type="phase_complete",
                phase=phase,
                message=message or f"{phase} 阶段完成",
            )
        )

    async def emit_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        message: Optional[str] = None,
    ):
        await self.emit(
            AgentEventData(
                event_type="tool_call",
                tool_name=tool_name,
                tool_input=tool_input,
                message=message or f"调用工具: {tool_name}",
            )
        )

    async def emit_tool_result(
        self,
        tool_name: str,
        tool_output: Any,
        duration_ms: int,
        message: Optional[str] = None,
    ):
        if hasattr(tool_output, 'to_dict'):
            output_payload = tool_output.to_dict()
        elif isinstance(tool_output, dict):
            output_payload = tool_output
        elif isinstance(tool_output, str):
            output_payload = {"result": tool_output[:2000]}
        else:
            output_payload = {"result": str(tool_output)[:2000]}

        await self.emit(
            AgentEventData(
                event_type="tool_result",
                tool_name=tool_name,
                tool_output=output_payload,
                tool_duration_ms=duration_ms,
                message=message or f"工具 {tool_name} 执行完成 ({duration_ms}ms)",
            )
        )

    async def emit_finding(
        self,
        finding_id: str,
        title: str,
        severity: str,
        vulnerability_type: str,
        is_verified: bool = False,
    ):
        event_type = "finding_verified" if is_verified else "finding_new"
        await self.emit(
            AgentEventData(
                event_type=event_type,
                finding_id=finding_id,
                message=f"{'已验证' if is_verified else '新发现'}: [{severity.upper()}] {title}",
                metadata={
                    "id": finding_id,
                    "title": title,
                    "severity": severity,
                    "vulnerability_type": vulnerability_type,
                    "is_verified": is_verified,
                },
            )
        )

    async def emit_task_complete(
        self,
        findings_count: int,
        duration_ms: int,
        message: Optional[str] = None,
    ):
        await self.emit(
            AgentEventData(
                event_type="task_complete",
                message=message or f"审计完成，发现 {findings_count} 个漏洞",
                metadata={
                    "findings_count": findings_count,
                    "duration_ms": duration_ms,
                },
            )
        )

    async def emit_task_error(self, error: str, message: Optional[str] = None):
        await self.emit(
            AgentEventData(
                event_type="task_error",
                message=message or f"任务失败: {error}",
                metadata={"error": error},
            )
        )

class EventManager:
    def __init__(self, task_id: str, websocket_manager=None):
        self.task_id = task_id
        self.websocket_manager = websocket_manager
        self.sequence = 0
        self._last_snapshot_refresh_at = 0.0
        self._last_snapshot_refresh_sequence = 0

    def _should_refresh_snapshot(self, event_type: str) -> bool:
        if event_type in SNAPSHOT_FORCE_EVENT_TYPES:
            return True

        now = time.monotonic()
        if (
            self.sequence - self._last_snapshot_refresh_sequence
            >= SNAPSHOT_REFRESH_MIN_SEQUENCE_GAP
        ):
            return True
        if now - self._last_snapshot_refresh_at >= SNAPSHOT_REFRESH_MIN_INTERVAL_SECONDS:
            return True
        return False

    async def init_sequence(self):
        # Get the latest sequence from db safely
        @sync_to_async
        def get_max_sequence():
            def _query():
                last_event = AgentEvent.objects.filter(task_id=self.task_id).order_by('-sequence').first()
                return last_event.sequence if last_event else 0

            return run_with_fresh_connection(_query)
        self.sequence = await get_max_sequence()

    async def emit(self, event_type: str, phase: str = None, message: str = None, **kwargs):
        self.sequence += 1

        normalized_tool_input = _normalize_json_value(kwargs.get("tool_input")) or {}
        normalized_tool_output = _normalize_json_value(kwargs.get("tool_output")) or {}
        normalized_metadata = _normalize_json_value(kwargs.get("event_metadata")) or {}

        event_data = {
            "task_id": self.task_id,
            "event_type": _sanitize_text(event_type) or "",
            "phase": _sanitize_text(phase),
            "message": _sanitize_text(message),
            "sequence": self.sequence,
            "tool_input": normalized_tool_input,
            "tool_output": normalized_tool_output,
            "event_metadata": normalized_metadata,
        }

        allowed_fields = [
            "tool_name",
            "tool_duration_ms",
            "progress_percent",
            "tokens_used",
        ]
        for field in allowed_fields:
            value = kwargs.get(field)
            if value is None:
                continue
            if field == "tool_name":
                event_data[field] = _sanitize_text(value)
            else:
                event_data[field] = value

        finding = kwargs.get('finding')
        if finding:
            event_data["finding"] = finding
        
        # Async db write
        @sync_to_async
        def save_event():
            return run_with_fresh_connection(AgentEvent.objects.create, **event_data)
        
        try:
            await save_event()
        except Exception as e:
            logger.error(f"Failed to save AgentEvent: {e}")
        else:
            if event_type in SNAPSHOT_EVENT_TYPES:
                try:
                    from apps.deepaudit.agent_task.agent_task_services import persist_checkpoint, refresh_task_snapshot

                    if self._should_refresh_snapshot(event_type):
                        await sync_to_async(refresh_task_snapshot)(self.task_id)
                        self._last_snapshot_refresh_at = time.monotonic()
                        self._last_snapshot_refresh_sequence = self.sequence
                    if event_type in {'phase_complete', 'task_complete', 'task_error', 'task_cancel'}:
                        checkpoint_type = {
                            'phase_complete': 'auto',
                            'task_complete': 'final',
                            'task_error': 'error',
                            'task_cancel': 'manual',
                        }.get(event_type, 'auto')
                        await sync_to_async(persist_checkpoint)(
                            self.task_id,
                            checkpoint_type=checkpoint_type,
                            checkpoint_name=message,
                            phase=phase,
                            sequence=self.sequence,
                        )
                except Exception as e:
                    logger.error(f"Failed to refresh AgentTask snapshot: {e}")

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
