from __future__ import annotations

import asyncio
import os
import sys
import types
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.deepaudit.agent_engine.agents.base import AgentConfig, AgentResult, AgentType, BaseAgent
from apps.deepaudit.agent_engine.tools.base import AgentTool, ToolResult
from apps.deepaudit.agent_engine.tools.rag_tool import RAGQueryTool
from apps.deepaudit.agent_engine.tools.run_code import RunCodeTool
from apps.deepaudit.config_resolver import (
    coerce_llm_provider,
    normalize_runtime_user_config,
    resolve_embedding_config,
)
from apps.deepaudit.agent_engine.knowledge.rag_knowledge import SecurityKnowledgeRAG
from apps.deepaudit.llm.service import LLMService
from apps.deepaudit.llm import tokenizer


class _DummySearchTool(AgentTool):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "search_code"

    @property
    def description(self) -> str:
        return "dummy search"

    async def _execute(self, **kwargs) -> ToolResult:
        self.calls.append(dict(kwargs))
        keyword = kwargs.get("keyword") or ""
        return ToolResult(
            success=True,
            data=f"fallback search for {keyword}",
            metadata={"matches": 1},
        )


class _UnavailableRetriever:
    def __init__(self, reason: str = "retriever unavailable") -> None:
        self.reason = reason
        self.retrieve_calls = 0

    def get_unavailable_reason(self) -> str:
        return self.reason

    async def retrieve(self, **_kwargs):
        self.retrieve_calls += 1
        return []


class _FlakyRetriever:
    def __init__(self) -> None:
        self.retrieve_calls = 0

    def get_unavailable_reason(self):
        return None

    async def retrieve(self, **_kwargs):
        self.retrieve_calls += 1
        raise RuntimeError("vector index failed")


class _SlowRetriever:
    def __init__(self, delay_seconds: float = 2.0) -> None:
        self.delay_seconds = delay_seconds
        self.retrieve_calls = 0

    def get_unavailable_reason(self):
        return None

    async def retrieve(self, **_kwargs):
        self.retrieve_calls += 1
        await asyncio.sleep(self.delay_seconds)
        return []


class _ToolTimeoutLLMService:
    def __init__(self, tool_timeout: int) -> None:
        self._tool_timeout = tool_timeout

    def get_agent_timeout_config(self):
        return {
            "llm_first_token_timeout": 90,
            "llm_stream_timeout": 60,
            "agent_timeout": 1800,
            "sub_agent_timeout": 600,
            "tool_timeout": self._tool_timeout,
        }


class _DummyAgent(BaseAgent):
    def __init__(self, *, llm_service, tools):
        super().__init__(
            config=AgentConfig(name="dummy-agent", agent_type=AgentType.ANALYSIS),
            llm_service=llm_service,
            tools=tools,
        )

    async def run(self, input_data) -> AgentResult:
        return AgentResult(success=True, data=input_data)


class RuntimeFallbacksTestCase(SimpleTestCase):
    def setUp(self) -> None:
        tokenizer._encoders.clear()
        tokenizer._tiktoken_available = None
        tokenizer._logged_method = False

    def tearDown(self) -> None:
        tokenizer._encoders.clear()
        tokenizer._tiktoken_available = None
        tokenizer._logged_method = False

    def test_local_tiktoken_mode_skips_remote_bootstrap_without_cache(self) -> None:
        fake_tiktoken = types.ModuleType("tiktoken")

        def unexpected_get_encoding(_name: str):
            raise AssertionError("tiktoken.get_encoding should not run without local cache")

        fake_tiktoken.get_encoding = unexpected_get_encoding

        with patch.dict(os.environ, {"DEEPAUDIT_TIKTOKEN_MODE": "local"}, clear=False):
            with patch.dict(sys.modules, {"tiktoken": fake_tiktoken}):
                with patch.object(tokenizer, "_resolve_local_cached_encoding", return_value=None):
                    self.assertFalse(tokenizer._check_tiktoken_availability())
                    self.assertIsNone(tokenizer._get_tiktoken_encoder("gpt-4"))

    def test_local_tiktoken_mode_uses_cached_encoding_directly(self) -> None:
        fake_tiktoken = types.ModuleType("tiktoken")
        encoder_object = object()
        calls: list[str] = []

        def fake_get_encoding(name: str):
            calls.append(name)
            return encoder_object

        def unexpected_encoding_for_model(_model: str):
            raise AssertionError("encoding_for_model should not run in local-cache mode")

        fake_tiktoken.get_encoding = fake_get_encoding
        fake_tiktoken.encoding_for_model = unexpected_encoding_for_model

        with patch.dict(os.environ, {"DEEPAUDIT_TIKTOKEN_MODE": "local"}, clear=False):
            with patch.dict(sys.modules, {"tiktoken": fake_tiktoken}):
                with patch.object(tokenizer, "_resolve_local_cached_encoding", return_value="cl100k_base"):
                    encoder = tokenizer._get_tiktoken_encoder("gpt-5")

        self.assertIs(encoder, encoder_object)
        self.assertEqual(calls, ["cl100k_base"])

    def test_security_knowledge_rag_falls_back_when_embedding_key_missing(self) -> None:
        rag = SecurityKnowledgeRAG()

        with patch(
            "apps.deepaudit.agent_engine.knowledge.rag_knowledge.resolve_embedding_config",
            return_value={
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_key": "",
                "base_url": "",
                "dimensions": 1536,
            },
        ):
            with patch("apps.deepaudit.rag.EmbeddingService") as mock_embedding_service:
                asyncio.run(rag.initialize())

        self.assertTrue(rag._initialized)
        self.assertIsNone(rag._indexer)
        self.assertIsNone(rag._retriever)
        mock_embedding_service.assert_not_called()

    def test_legacy_llm_provider_is_normalized_to_internal_entry(self) -> None:
        normalized = normalize_runtime_user_config(
            {
                "llmConfig": {
                    "provider": "qwen",
                    "model": "qwen3-max-instruct",
                    "api_key": "legacy-key",
                    "base_url": "https://legacy.example/v1",
                }
            }
        )

        self.assertEqual(coerce_llm_provider("qwen"), "qwen")
        self.assertEqual(normalized["llm_config"]["provider"], "qwen")
        self.assertEqual(normalized["llm_config"]["model"], "qwen3-max-instruct")
        self.assertEqual(normalized["llm_config"]["api_key"], "legacy-key")
        self.assertEqual(normalized["llmConfig"]["llmProvider"], "qwen")

    def test_agent_timeout_config_raises_first_token_floor(self) -> None:
        service = LLMService(
            {
                "llmConfig": {
                    "llmProvider": "openai",
                    "llmFirstTokenTimeout": 30,
                    "llmStreamTimeout": 45,
                }
            }
        )

        timeout_config = service.get_agent_timeout_config()

        self.assertEqual(timeout_config["llm_first_token_timeout"], 90)
        self.assertEqual(timeout_config["llm_stream_timeout"], 60)

    @override_settings(
        EMBEDDING_CONFIG_LOCKED=True,
        EMBEDDING_PROVIDER="ollama",
        EMBEDDING_MODEL="bge-m3",
        EMBEDDING_BASE_URL="http://10.0.0.8:11434/v1",
        EMBEDDING_DIMENSIONS=1024,
    )
    def test_locked_embedding_config_prefers_system_ollama_settings(self) -> None:
        resolved = resolve_embedding_config(
            {
                "other_config": {
                    "embedding_config": {
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "api_key": "user-key",
                        "base_url": "https://gateway.example/v1",
                        "dimensions": 1536,
                    }
                }
            }
        )

        self.assertEqual(resolved["provider"], "ollama")
        self.assertEqual(resolved["model"], "bge-m3")
        self.assertEqual(resolved["base_url"], "http://10.0.0.8:11434")
        self.assertEqual(resolved["dimensions"], 1024)
        self.assertEqual(resolved["api_key"], "")

    def test_run_code_c_and_cpp_commands_enable_sanitizers(self) -> None:
        tool = RunCodeTool()

        c_command = tool._build_command("int main(void) { return 0; }", "c")
        cpp_command = tool._build_command("int main() { return 0; }", "cpp")

        self.assertIsNotNone(c_command)
        self.assertIsNotNone(cpp_command)
        self.assertIn("gcc -O0 -g -Wall -Wextra -fsanitize=address,undefined", c_command)
        self.assertIn("clang -O0 -g -Wall -Wextra -fsanitize=address,undefined", c_command)
        self.assertIn("g++ -O0 -g -Wall -Wextra -fsanitize=address,undefined", cpp_command)
        self.assertIn("clang++ -O0 -g -Wall -Wextra -fsanitize=address,undefined", cpp_command)

    def test_rag_query_degrades_to_search_when_retriever_is_unavailable(self) -> None:
        search_tool = _DummySearchTool()
        tool = RAGQueryTool(
            _UnavailableRetriever("RAG backend unavailable"),
            search_tool=search_tool,
            enable_keyword_fallback=True,
        )

        result = asyncio.run(tool.execute(query="查找 buffer overflow 风险", language="c"))

        self.assertTrue(result.success)
        self.assertTrue(result.metadata.get("degraded"))
        self.assertEqual(result.metadata.get("degraded_tool"), "search_code")
        self.assertEqual(result.metadata.get("fallback_reason_category"), "unavailable")
        self.assertIn("strcpy", result.metadata.get("fallback_keywords") or [])
        self.assertTrue(search_tool.calls)

    def test_rag_query_caches_unavailable_state_after_first_failure(self) -> None:
        search_tool = _DummySearchTool()
        retriever = _FlakyRetriever()
        tool = RAGQueryTool(
            retriever,
            search_tool=search_tool,
            enable_keyword_fallback=True,
        )

        first = asyncio.run(tool.execute(query="malloc/free pairing", language="c"))
        second = asyncio.run(tool.execute(query="malloc/free pairing", language="c"))

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(retriever.retrieve_calls, 1)
        self.assertGreaterEqual(len(search_tool.calls), 2)

    def test_base_agent_timeout_falls_back_to_search_for_rag_query(self) -> None:
        search_tool = _DummySearchTool()
        rag_tool = RAGQueryTool(
            _SlowRetriever(delay_seconds=2),
            search_tool=search_tool,
            enable_keyword_fallback=True,
        )
        agent = _DummyAgent(
            llm_service=_ToolTimeoutLLMService(tool_timeout=1),
            tools={"rag_query": rag_tool},
        )

        output = asyncio.run(
            agent.execute_tool(
                "rag_query",
                {
                    "query": "检查 memcpy 和 buffer overflow 风险",
                    "top_k": 5,
                    "language": "c",
                },
            )
        )

        self.assertIn("已切换为关键词搜索", output)
        self.assertTrue(search_tool.calls)
        self.assertIn("memcpy", output)
