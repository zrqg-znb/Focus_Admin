"""
Agent 注册表和动态Agent树管理

提供：
- Agent实例注册和管理
- 动态Agent树结构
- Agent状态追踪
- 子Agent创建和销毁
"""

import logging
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .state import AgentState

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Agent 注册表

    管理所有Agent实例，维护动态Agent树结构
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._agent_graph: Dict[str, Any] = {
            "nodes": {},
            "edges": [],
        }
        self._agent_instances: Dict[str, Any] = {}
        self._agent_states: Dict[str, "AgentState"] = {}
        self._agent_messages: Dict[str, List[Dict[str, Any]]] = {}
        self._root_agent_id: Optional[str] = None
        self._running_agents: Dict[str, threading.Thread] = {}

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        task: str,
        parent_id: Optional[str] = None,
        agent_instance: Any = None,
        state: Optional["AgentState"] = None,
        knowledge_modules: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            node = {
                "id": agent_id,
                "name": agent_name,
                "type": agent_type,
                "task": task,
                "status": "running",
                "parent_id": parent_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "result": None,
                "knowledge_modules": knowledge_modules or [],
                "children": [],
            }

            self._agent_graph["nodes"][agent_id] = node

            if agent_instance:
                self._agent_instances[agent_id] = agent_instance

            if state:
                self._agent_states[agent_id] = state

            if agent_id not in self._agent_messages:
                self._agent_messages[agent_id] = []

            if parent_id:
                self._agent_graph["edges"].append(
                    {
                        "from": parent_id,
                        "to": agent_id,
                        "type": "delegation",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                if parent_id in self._agent_graph["nodes"]:
                    self._agent_graph["nodes"][parent_id]["children"].append(agent_id)

            if parent_id is None and self._root_agent_id is None:
                self._root_agent_id = agent_id

            logger.debug("Registered agent %s (%s)", agent_name, agent_id)
            return node

    def unregister_agent(self, agent_id: str) -> None:
        with self._lock:
            if agent_id in self._agent_graph["nodes"]:
                del self._agent_graph["nodes"][agent_id]

            self._agent_instances.pop(agent_id, None)
            self._agent_states.pop(agent_id, None)
            self._agent_messages.pop(agent_id, None)
            self._running_agents.pop(agent_id, None)
            self._agent_graph["edges"] = [
                edge
                for edge in self._agent_graph["edges"]
                if edge["from"] != agent_id and edge["to"] != agent_id
            ]

    def update_agent_status(
        self,
        agent_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            if agent_id not in self._agent_graph["nodes"]:
                return
            node = self._agent_graph["nodes"][agent_id]
            node["status"] = status
            if status in ["completed", "failed", "stopped"]:
                node["finished_at"] = datetime.now(timezone.utc).isoformat()
            if result:
                node["result"] = result

    def get_agent_status(self, agent_id: str) -> Optional[str]:
        with self._lock:
            node = self._agent_graph["nodes"].get(agent_id)
            return node.get("status") if node else None

    def get_agent(self, agent_id: str) -> Optional[Any]:
        return self._agent_instances.get(agent_id)

    def get_agent_state(self, agent_id: str) -> Optional["AgentState"]:
        return self._agent_states.get(agent_id)

    def get_agent_node(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self._agent_graph["nodes"].get(agent_id)

    def get_root_agent_id(self) -> Optional[str]:
        return self._root_agent_id

    def get_children(self, agent_id: str) -> List[str]:
        with self._lock:
            node = self._agent_graph["nodes"].get(agent_id)
            if node:
                return node.get("children", [])
            return []

    def get_parent(self, agent_id: str) -> Optional[str]:
        with self._lock:
            node = self._agent_graph["nodes"].get(agent_id)
            if node:
                return node.get("parent_id")
            return None

    def get_agent_tree(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "nodes": dict(self._agent_graph["nodes"]),
                "edges": list(self._agent_graph["edges"]),
                "root_agent_id": self._root_agent_id,
            }

    def get_agent_tree_view(self, agent_id: Optional[str] = None) -> str:
        with self._lock:
            lines = ["=== AGENT TREE ==="]
            root_id = agent_id or self._root_agent_id
            if not root_id or root_id not in self._agent_graph["nodes"]:
                return "No agents in the tree"

            def _build_tree(current_agent_id: str, depth: int = 0) -> None:
                node = self._agent_graph["nodes"].get(current_agent_id)
                if not node:
                    return

                indent = "  " * depth
                status_emoji = {
                    "running": "[RUN]",
                    "waiting": "[WAIT]",
                    "completed": "[OK]",
                    "failed": "[ERR]",
                    "stopped": "[STOP]",
                }.get(node["status"], "[?]")

                lines.append(f"{indent}{status_emoji} {node['name']} ({current_agent_id})")
                lines.append(f"{indent}   Task: {node['task'][:50]}...")
                lines.append(f"{indent}   Status: {node['status']}")

                if node.get("knowledge_modules"):
                    lines.append(f"{indent}   Modules: {', '.join(node['knowledge_modules'])}")

                for child_id in node.get("children", []):
                    _build_tree(child_id, depth + 1)

            _build_tree(root_id)
            return "\n".join(lines)

    def get_statistics(self) -> Dict[str, int]:
        with self._lock:
            stats = {
                "total": len(self._agent_graph["nodes"]),
                "running": 0,
                "waiting": 0,
                "completed": 0,
                "failed": 0,
                "stopped": 0,
            }

            for node in self._agent_graph["nodes"].values():
                status = node.get("status", "unknown")
                if status in stats:
                    stats[status] += 1

            return stats

    def clear(self) -> None:
        with self._lock:
            self._agent_graph = {"nodes": {}, "edges": []}
            self._agent_instances.clear()
            self._agent_states.clear()
            self._agent_messages.clear()
            self._running_agents.clear()
            self._root_agent_id = None

    def cleanup_finished_agents(self) -> int:
        with self._lock:
            finished_ids = [
                agent_id
                for agent_id, node in self._agent_graph["nodes"].items()
                if node["status"] in ["completed", "failed", "stopped"]
            ]

            for agent_id in finished_ids:
                self._agent_instances.pop(agent_id, None)
                self._running_agents.pop(agent_id, None)

            return len(finished_ids)


agent_registry = AgentRegistry()
