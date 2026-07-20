from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import requests
from django.test import SimpleTestCase

from apps.deepaudit.user_config import user_config_services
from apps.deepaudit.rag.embeddings import OllamaEmbedding


class UserConfigServicesTestCase(SimpleTestCase):
    def test_ollama_embedding_falls_back_to_legacy_endpoint_with_selected_model(self) -> None:
        calls: list[tuple[str, dict]] = []

        class Response:
            def __init__(self, status_code: int, payload: dict) -> None:
                self.status_code = status_code
                self._payload = payload

            def raise_for_status(self) -> None:
                if self.status_code >= 400:
                    raise RuntimeError(f'HTTP {self.status_code}')

            def json(self) -> dict:
                return self._payload

        class Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args) -> None:
                return None

            async def post(self, url: str, json: dict):
                calls.append((url, json))
                if url.endswith('/api/embed'):
                    return Response(404, {})
                return Response(200, {'embedding': [0.1, 0.2]})

        with patch('apps.deepaudit.rag.embeddings.httpx.AsyncClient', return_value=Client()):
            results = asyncio.run(
                OllamaEmbedding(base_url='http://127.0.0.1:11434', model='bge-m3').embed_texts(['hello'])
            )

        self.assertEqual(results[0].embedding, [0.1, 0.2])
        self.assertEqual(calls[0][0], 'http://127.0.0.1:11434/api/embed')
        self.assertEqual(calls[0][1]['model'], 'bge-m3')
        self.assertEqual(calls[1][0], 'http://127.0.0.1:11434/api/embeddings')
        self.assertEqual(calls[1][1], {'model': 'bge-m3', 'prompt': 'hello'})

    @patch("apps.deepaudit.user_config.user_config_services.decrypt_value", side_effect=lambda value: value)
    def test_serialize_user_config_maps_legacy_token_to_codehub(self, _mock_decrypt) -> None:
        instance = SimpleNamespace(
            user_id="user-1",
            llm_config={},
            other_config={"github_token": "legacy-token"},
            sys_create_datetime=None,
            sys_update_datetime=None,
        )

        result = user_config_services.serialize_user_config(instance)

        self.assertEqual(result["other_config"]["codehub_token"], "legacy-token")
        self.assertNotIn("github_token", result["other_config"])

    @patch("apps.deepaudit.user_config.user_config_services.get_user_config")
    @patch("apps.deepaudit.user_config.user_config_services.requests.post")
    def test_llm_test_uses_saved_base_url_and_model(self, mock_post, mock_get_user_config) -> None:
        mock_get_user_config.return_value = {
            "llm_config": {
                "provider": "openai",
                "api_key": "saved-key",
                "model": "gpt-4o-mini",
                "base_url": "https://gateway.example/v1",
                "timeout": 150,
                "temperature": 0.2,
                "max_tokens": 1024,
            }
        }
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        response.text = ""
        mock_post.return_value = response

        result = user_config_services.test_llm_connection(object(), {"provider": "openai"})

        self.assertTrue(result["success"])
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://gateway.example/v1/chat/completions",
        )
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["model"],
            "gpt-4o-mini",
        )
        self.assertEqual(
            mock_post.call_args.kwargs["headers"]["Authorization"],
            "Bearer saved-key",
        )
        self.assertEqual(result["debug"]["provider_used"], "openai")
        self.assertEqual(result["debug"]["base_url_used"], "https://gateway.example/v1")

    @patch("apps.deepaudit.user_config.user_config_services.get_user_config")
    @patch(
        "apps.deepaudit.user_config.user_config_services.requests.post",
        side_effect=requests.RequestException("gateway down"),
    )
    def test_llm_test_does_not_fallback_to_ollama_on_primary_failure(
        self,
        mock_post,
        mock_get_user_config,
    ) -> None:
        mock_get_user_config.return_value = {
            "llm_config": {
                "provider": "openai",
                "timeout": 150,
                "temperature": 0.1,
                "max_tokens": 4096,
            }
        }

        result = user_config_services.test_llm_connection(
            object(),
            {
                "provider": "openai",
                "api_key": "test-key",
                "model": "gpt-5",
                "base_url": "https://gateway.example/v1",
            },
        )

        self.assertFalse(result["success"])
        self.assertEqual(mock_post.call_count, 1)
        self.assertIn("网络请求失败", result["message"])
        self.assertEqual(result["debug"]["provider_used"], "openai")
        self.assertEqual(result["debug"]["base_url_used"], "https://gateway.example/v1")
        self.assertNotEqual(result["debug"]["base_url_used"], "http://127.0.0.1:11434/v1")

    @patch("apps.deepaudit.user_config.user_config_services.EmbeddingService")
    def test_embedding_test_uses_real_embedding_service(self, mock_embedding_service) -> None:
        service = mock_embedding_service.return_value
        service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])

        result = user_config_services.test_embedding(
            None,
            {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_key": "test-key",
                "test_text": "hello",
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["dimensions"], 4)
        self.assertEqual(result["sample_embedding"], [0.1, 0.2, 0.3, 0.4])
        self.assertEqual(result["preview_vector_length"], 4)
        mock_embedding_service.assert_called_once()

    @patch("apps.deepaudit.user_config.user_config_services.EmbeddingService")
    def test_embedding_test_allows_ollama_without_api_key(self, mock_embedding_service) -> None:
        service = mock_embedding_service.return_value
        service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        result = user_config_services.test_embedding(
            None,
            {
                "provider": "ollama",
                "model": "bge-m3",
                "base_url": "http://10.0.0.8:11434/v1",
                "test_text": "hello",
            },
        )

        self.assertTrue(result["success"])
        self.assertEqual(mock_embedding_service.call_args.kwargs["provider"], "ollama")
        self.assertEqual(mock_embedding_service.call_args.kwargs["model"], "bge-m3")
        self.assertIsNone(mock_embedding_service.call_args.kwargs["api_key"])
        self.assertEqual(mock_embedding_service.call_args.kwargs["base_url"], "http://10.0.0.8:11434")

    def test_embedding_test_rejects_non_ascii_api_key(self) -> None:
        result = user_config_services.test_embedding(
            None,
            {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_key": "随便填",
            },
        )

        self.assertFalse(result["success"])
        self.assertIn("ASCII", result["message"])
