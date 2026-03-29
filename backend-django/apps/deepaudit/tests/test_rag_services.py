from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from django.test import TestCase
from ninja.errors import HttpError

from apps.deepaudit.agent_engine.knowledge.rag_knowledge import security_knowledge_rag
from apps.deepaudit.rag import rag_services
from core.user.user_model import User


class RagKnowledgeServicesTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            username='knowledge-owner',
            password='not-used',
            name='Knowledge Owner',
        )
        self.temp_dir = Path(tempfile.mkdtemp(prefix='deepaudit-knowledge-test-'))
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))

    def test_save_list_and_delete_custom_knowledge_document(self) -> None:
        with patch('apps.deepaudit.agent_engine.knowledge.rag_knowledge.KNOWLEDGE_DIR', self.temp_dir):
            security_knowledge_rag.reload_knowledge_sources()

            rebuild_mock = AsyncMock(return_value={'enabled': False, 'chunk_count': 0, 'document_count': 1})
            with patch.object(security_knowledge_rag, 'rebuild_index', rebuild_mock):
                saved = rag_services.save_knowledge_document(
                    self.user,
                    {
                        'id': 'custom_oauth_review',
                        'title': 'OAuth Review Checklist',
                        'content': 'Check redirect_uri validation and token audience constraints.',
                        'category': 'best_practice',
                        'tags': ['oauth', 'auth'],
                        'metadata': {'scope': 'custom'},
                    },
                )

            self.assertTrue(saved['rebuilt'])
            self.assertEqual(saved['document']['id'], 'custom_oauth_review')

            listing = rag_services.list_knowledge_documents(self.user, keyword='OAuth')
            item_ids = {item['id'] for item in listing['items']}
            self.assertIn('custom_oauth_review', item_ids)

            detail = rag_services.get_knowledge_document(self.user, 'custom_oauth_review')
            self.assertEqual(detail['title'], 'OAuth Review Checklist')
            self.assertEqual(detail['metadata'].get('created_by_id'), str(self.user.id))

            with patch.object(security_knowledge_rag, 'rebuild_index', rebuild_mock):
                deleted = rag_services.delete_knowledge_document(self.user, 'custom_oauth_review')

            self.assertTrue(deleted['success'])
            self.assertIsNone(security_knowledge_rag.get_document('custom_oauth_review'))

    def test_validate_knowledge_modules_returns_valid_and_invalid_items(self) -> None:
        result = rag_services.validate_knowledge_modules(
            self.user,
            {'modules': ['sql_injection', 'unknown_custom_module']},
        )
        self.assertIn('sql_injection', result['valid'])
        self.assertIn('unknown_custom_module', result['invalid'])

    def test_upload_knowledge_document_supports_markdown_and_custom_module_validation(self) -> None:
        with patch('apps.deepaudit.agent_engine.knowledge.rag_knowledge.KNOWLEDGE_DIR', self.temp_dir):
            security_knowledge_rag.reload_knowledge_sources()

            rebuild_mock = AsyncMock(return_value={'enabled': False, 'chunk_count': 0, 'document_count': 1})
            with patch.object(security_knowledge_rag, 'rebuild_index', rebuild_mock):
                saved = rag_services.upload_knowledge_document(
                    self.user,
                    file_name='csrf-review.md',
                    file_bytes=b'Validate CSRF token rotation and SameSite cookie strategy.',
                    document_id='csrf_review',
                    title='CSRF Review',
                    category='best_practice',
                    tags=['csrf', 'django'],
                    severity='medium',
                    cwe_ids=['CWE-352'],
                )

            self.assertTrue(saved['rebuilt'])
            self.assertEqual(saved['document']['id'], 'csrf_review')
            self.assertEqual(saved['document']['metadata'].get('uploaded_file_name'), 'csrf-review.md')

            validation = rag_services.validate_knowledge_modules(self.user, {'modules': ['csrf_review']})
            self.assertIn('csrf_review', validation['valid'])
            self.assertNotIn('csrf_review', validation['invalid'])

    def test_upload_knowledge_document_rejects_unsupported_file_type(self) -> None:
        with self.assertRaises(HttpError) as context:
            rag_services.upload_knowledge_document(
                self.user,
                file_name='knowledge.pdf',
                file_bytes=b'%PDF-1.4',
            )

        self.assertEqual(context.exception.status_code, 422)
