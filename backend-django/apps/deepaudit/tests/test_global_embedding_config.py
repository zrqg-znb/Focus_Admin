from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.test import SimpleTestCase, override_settings

from apps.deepaudit.config_resolver import resolve_embedding_config
from apps.deepaudit.rag.project_retriever import ProjectCodeRetriever
from apps.deepaudit.user_config import user_config_services
class GlobalEmbeddingConfigTestCase(SimpleTestCase):
    def test_global_ui_config_is_used_instead_of_task_creator_legacy_config(self) -> None:
        with patch(
            "apps.deepaudit.config_resolver.get_global_embedding_config",
            return_value={
                "provider": "ollama",
                "model": "bge-m3",
                "base_url": "http://ollama.internal:11434/v1",
                "api_key": "",
                "dimensions": None,
                "batch_size": 64,
            },
        ):
            resolved = resolve_embedding_config(
                {
                    "other_config": {
                        "embedding_config": {
                            "provider": "openai",
                            "model": "text-embedding-3-small",
                            "api_key": "legacy-key",
                        }
                    }
                }
            )

        self.assertEqual(resolved["config_source"], "global_ui")
        self.assertEqual(resolved["provider"], "ollama")
        self.assertEqual(resolved["model"], "bge-m3")
        self.assertEqual(resolved["base_url"], "http://ollama.internal:11434")
        self.assertEqual(resolved["dimensions"], 1024)

    @override_settings(
        EMBEDDING_CONFIG_LOCKED=True,
        EMBEDDING_PROVIDER="ollama",
        EMBEDDING_MODEL="nomic-embed-text",
        EMBEDDING_BASE_URL="http://locked-ollama:11434",
    )
    def test_locked_environment_config_has_priority_over_global_config(self) -> None:
        with patch(
            "apps.deepaudit.config_resolver.get_global_embedding_config",
            return_value={
                "provider": "ollama",
                "model": "bge-m3",
                "base_url": "http://ui-ollama:11434",
            },
        ):
            resolved = resolve_embedding_config(None)

        self.assertEqual(resolved["config_source"], "environment_locked")
        self.assertEqual(resolved["model"], "nomic-embed-text")
        self.assertEqual(resolved["base_url"], "http://locked-ollama:11434")

    def test_config_api_does_not_return_the_global_api_key(self) -> None:
        with patch(
            "apps.deepaudit.user_config.user_config_services.resolve_embedding_config",
            return_value={
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_key": "secret-key",
                "base_url": "https://embedding.example/v1",
                "dimensions": 1536,
                "batch_size": 100,
                "config_source": "global_ui",
            },
        ):
            payload = user_config_services.get_embedding_config(None)

        self.assertEqual(payload["api_key"], "")
        self.assertTrue(payload["api_key_configured"])
        self.assertEqual(payload["config_source"], "global_ui")


class ProjectRetrieverPreflightTestCase(SimpleTestCase):
    def test_preflight_calls_embedding_service_and_reports_index_metadata(self) -> None:
        class DummyIndexer:
            def __init__(self, **_kwargs):
                pass

            async def smart_index_directory(self, **_kwargs):
                yield SimpleNamespace(
                    update_mode="incremental",
                    total_files=2,
                    processed_files=2,
                    total_chunks=4,
                    indexed_chunks=0,
                    errors=[],
                )

        class DummyRetriever:
            def __init__(self, **_kwargs):
                pass

            async def initialize(self):
                return None

        service = SimpleNamespace(embed=AsyncMock(return_value=[0.0] * 1024))
        with tempfile.TemporaryDirectory() as workspace:
            with patch(
                "apps.deepaudit.rag.project_retriever.resolve_embedding_config",
                return_value={
                    "provider": "ollama",
                    "model": "bge-m3",
                    "base_url": "http://ollama.internal:11434",
                    "api_key": "",
                    "dimensions": 1024,
                    "batch_size": 64,
                    "config_source": "global_ui",
                },
            ), patch(
                "apps.deepaudit.rag.project_retriever.EmbeddingService",
                return_value=service,
            ) as embedding_service, patch(
                "apps.deepaudit.rag.project_retriever.CodeIndexer", DummyIndexer
            ), patch(
                "apps.deepaudit.rag.project_retriever.CodeRetriever", DummyRetriever
            ):
                retriever = ProjectCodeRetriever(project_root=workspace, project_id="project-1")
                result = asyncio.run(retriever.prepare())

        self.assertTrue(result["success"])
        self.assertTrue(result["health_probe"])
        self.assertEqual(result["returned_dimensions"], 1024)
        self.assertEqual(result["config_source"], "global_ui")
        self.assertEqual(result["index_mode"], "incremental")
        embedding_service.assert_called_once()
        service.embed.assert_awaited_once_with("DeepAudit RAG readiness probe")

    def test_preflight_degrades_when_embedding_dimension_is_wrong(self) -> None:
        service = SimpleNamespace(embed=AsyncMock(return_value=[0.0] * 768))
        with tempfile.TemporaryDirectory() as workspace:
            with patch(
                "apps.deepaudit.rag.project_retriever.resolve_embedding_config",
                return_value={
                    "provider": "ollama",
                    "model": "bge-m3",
                    "base_url": "http://ollama.internal:11434",
                    "api_key": "",
                    "dimensions": 1024,
                    "config_source": "global_ui",
                },
            ), patch(
                "apps.deepaudit.rag.project_retriever.EmbeddingService",
                return_value=service,
            ):
                result = asyncio.run(ProjectCodeRetriever(project_root=workspace).prepare())

        self.assertFalse(result["success"])
        self.assertIn("expected=1024, actual=768", result["reason"])
