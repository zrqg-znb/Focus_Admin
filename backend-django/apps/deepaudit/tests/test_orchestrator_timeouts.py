from django.test import SimpleTestCase

from apps.deepaudit.agent_engine.agents.orchestrator import OrchestratorAgent


class _DummyLLMService:
    def __init__(self, sub_agent_timeout: int):
        self._sub_agent_timeout = sub_agent_timeout

    def get_agent_timeout_config(self):
        return {
            "llm_first_token_timeout": 90,
            "llm_stream_timeout": 60,
            "agent_timeout": 1800,
            "sub_agent_timeout": self._sub_agent_timeout,
            "tool_timeout": 60,
        }


class OrchestratorTimeoutsTestCase(SimpleTestCase):
    def test_recon_timeout_follows_sub_agent_timeout(self):
        orchestrator = OrchestratorAgent(
            llm_service=_DummyLLMService(sub_agent_timeout=900),
            tools={},
        )

        self.assertEqual(orchestrator._get_sub_agent_timeout("recon"), 900)
        self.assertEqual(orchestrator._get_sub_agent_timeout("analysis"), 900)
        self.assertEqual(orchestrator._get_sub_agent_timeout("verification"), 900)
        self.assertEqual(orchestrator._get_sub_agent_timeout("unknown"), 900)
