from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from django.test import TestCase
from ninja.errors import HttpError

from apps.deepaudit.agent_engine.knowledge.rag_knowledge import security_knowledge_rag
from apps.deepaudit.project.project_model import AuditProject
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
        with patch('apps.deepaudit.agent_engine.knowledge.rag_knowledge.deepaudit_storage.KNOWLEDGE_DIR', self.temp_dir):
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
            self.assertEqual(detail['metadata'].get('maintenance_scope'), 'personal')

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
        with patch('apps.deepaudit.agent_engine.knowledge.rag_knowledge.deepaudit_storage.KNOWLEDGE_DIR', self.temp_dir):
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

    def test_save_knowledge_document_requires_explicit_id_and_tags(self) -> None:
        with self.assertRaises(HttpError) as context:
            rag_services.save_knowledge_document(
                self.user,
                {
                    'title': 'Missing ID',
                    'content': 'Need explicit module id.',
                    'category': 'best_practice',
                    'tags': ['audit'],
                },
            )
        self.assertEqual(context.exception.status_code, 422)
        self.assertIn('模块 ID', str(context.exception))

        with self.assertRaises(HttpError) as tags_context:
            rag_services.save_knowledge_document(
                self.user,
                {
                    'id': 'custom_missing_tags',
                    'title': 'Missing Tags',
                    'content': 'Need at least one tag.',
                    'category': 'best_practice',
                    'tags': [],
                },
            )
        self.assertEqual(tags_context.exception.status_code, 422)
        self.assertIn('至少需要一个标签', str(tags_context.exception))

    def test_save_knowledge_document_rejects_reserved_prefix(self) -> None:
        with self.assertRaises(HttpError) as context:
            rag_services.save_knowledge_document(
                self.user,
                {
                    'id': 'vuln_custom_override',
                    'title': 'Bad Prefix',
                    'content': 'Should be rejected.',
                    'category': 'best_practice',
                    'tags': ['override'],
                },
            )

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn('内置知识前缀', str(context.exception))

    def test_save_knowledge_document_blocks_overwriting_other_users_custom_entry(self) -> None:
        other_user = User.objects.create(
            username='other-knowledge-owner',
            password='not-used',
            name='Other Knowledge Owner',
        )
        with patch('apps.deepaudit.agent_engine.knowledge.rag_knowledge.deepaudit_storage.KNOWLEDGE_DIR', self.temp_dir):
            security_knowledge_rag.reload_knowledge_sources()

            rebuild_mock = AsyncMock(return_value={'enabled': False, 'chunk_count': 0, 'document_count': 1})
            with patch.object(security_knowledge_rag, 'rebuild_index', rebuild_mock):
                rag_services.save_knowledge_document(
                    other_user,
                    {
                        'id': 'team_shared_auth_review',
                        'title': 'Shared Auth Review',
                        'content': 'Owned by another user.',
                        'category': 'best_practice',
                        'tags': ['auth', 'team'],
                    },
                )

                with self.assertRaises(HttpError) as context:
                    rag_services.save_knowledge_document(
                        self.user,
                        {
                            'id': 'team_shared_auth_review',
                            'title': 'Overwrite Attempt',
                            'content': 'Should not overwrite.',
                            'category': 'best_practice',
                            'tags': ['auth', 'team'],
                        },
                    )

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn('其他用户占用', str(context.exception))


class RagRepositoryScopeTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            username='rag-owner',
            password='not-used',
            name='RAG Owner',
        )
        self.project = AuditProject.objects.create(
            name='RAG Multi Repo',
            owner=self.user,
            source_type='repository',
            repository_url='https://codehub.example.com/platform/manifest.git',
            repository_type='multi',
            default_branch='release/main',
            manifest_xml='default.xml',
            group='platform',
            sys_creator=self.user,
            sys_modifier=self.user,
        )

    def test_query_project_rag_ignores_repository_type_override_for_multi_project(self) -> None:
        access = type('Access', (), {'project': self.project})()
        workspace = Path(tempfile.mkdtemp(prefix='deepaudit-rag-workspace-'))
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))

        retriever = type(
            'Retriever',
            (),
            {
                'collection_name': 'deepaudit_rag_scope',
                'get_unavailable_reason': lambda self: 'embedding unavailable',
                '_embedding_unavailable_reason': lambda self: 'embedding unavailable',
            },
        )()

        with (
            patch('apps.deepaudit.rag.rag_services.require_project_role', return_value=access),
            patch(
                'apps.deepaudit.rag.rag_services.prepare_workspace',
                return_value=(workspace, {'other_config': {}}),
            ) as mock_prepare,
            patch('apps.deepaudit.rag.rag_services.ProjectCodeRetriever', return_value=retriever),
            self.assertLogs('apps.deepaudit.rag.rag_services', level='WARNING') as captured,
        ):
            result = rag_services.query_project_rag(
                self.user,
                str(self.project.id),
                {
                    'query': 'find memcpy usage',
                    'repository_type': 'single',
                    'branch_name': 'release/hotfix',
                    'manifest_xml': 'vehicle.xml',
                    'group': 'vehicle-a',
                },
            )

        repository_spec = mock_prepare.call_args.kwargs['repository_spec']
        self.assertEqual(repository_spec['repository_type'], 'multi')
        self.assertEqual(repository_spec['repository_url'], self.project.repository_url)
        self.assertEqual(repository_spec['branch_name'], 'release/hotfix')
        self.assertEqual(repository_spec['manifest_xml'], 'vehicle.xml')
        self.assertEqual(repository_spec['group'], 'vehicle-a')
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['results'], [])
        self.assertEqual(result['unavailable_reason'], 'embedding unavailable')
        self.assertIn('ignored repository_type override', '\n'.join(captured.output))
