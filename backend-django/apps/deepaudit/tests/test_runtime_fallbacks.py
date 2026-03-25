from __future__ import annotations

import asyncio
import os
import sys
import types
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.deepaudit.agent_engine.knowledge.rag_knowledge import SecurityKnowledgeRAG
from apps.deepaudit.llm import tokenizer


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
