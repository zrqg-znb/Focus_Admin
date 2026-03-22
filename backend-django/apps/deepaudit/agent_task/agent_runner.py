import asyncio
import logging
from typing import Dict, Any
from asgiref.sync import sync_to_async

from apps.deepaudit.agent_task.agent_task_model import AgentTask
from apps.deepaudit.agent_engine.event_manager import EventManager, AgentEventEmitter
from apps.deepaudit.agent_engine.agents.orchestrator import OrchestratorAgent
from apps.deepaudit.agent_engine.config import AgentConfig
from apps.deepaudit.agent_engine.core.registry import agent_registry
from apps.deepaudit.agent_engine.core.persistence import agent_persistence
# Import the mocked LLMService or Litellm Service depending on environment
# We assume LLMService is available in original codebase
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../DeepAudit/backend'))
try:
    from app.services.llm.service import llm_service
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Original LLMService not found, using mock for compilation check")
    class MockLLMService:
        pass
    llm_service = MockLLMService()

logger = logging.getLogger(__name__)

async def run_orchestrator_agent_async(task_id: str, input_data: Dict[str, Any], workspace: str):
    """
    异步运行 OrchestratorAgent。
    """
    event_manager = EventManager(task_id=task_id)
    await event_manager.init_sequence()
    event_emitter = AgentEventEmitter(task_id, event_manager)
    
    # 模拟外部依赖配置
    tools = {}  # 实际应当从原库继承或组装真实 Tools
    
    orchestrator = OrchestratorAgent(
        llm_service=llm_service,
        tools=tools,
        event_emitter=event_emitter
    )
    
    try:
        await event_emitter.emit_phase_start("planning", "Starting Orchestrator Agent planning phase")
        result = await orchestrator.run(input_data)
        await event_emitter.emit_task_complete(
            findings_count=len(result.data.get("findings", [])),
            duration_ms=0,
            message="Orchestrator run completed."
        )
    except Exception as e:
        logger.error(f"Agent Execution failed for task {task_id}: {e}", exc_info=True)
        await event_emitter.emit_task_error(str(e))
        raise e

def run_orchestrator_agent_sync(task_id: str, input_data: Dict[str, Any], workspace: str):
    """
    由于 Celery worker 通常是同步运行，我们需要创建一个 event loop 来执行真正的 asyncio agent 逻辑。
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_orchestrator_agent_async(task_id, input_data, workspace))
    finally:
        loop.close()
