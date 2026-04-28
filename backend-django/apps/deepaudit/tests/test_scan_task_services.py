from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.test import SimpleTestCase, TestCase
from ninja.errors import HttpError

from apps.deepaudit.project.project_model import AuditProject
from apps.deepaudit.repo_specs import repository_spec_signature
from apps.deepaudit.scan_task.scan_task_model import AuditTask, InstantAnalysisRecord
from apps.deepaudit.scan_task.scan_task_services import (
    _scan_files_with_concurrency,
    create_task,
    execute_scan_task,
    export_instant_pdf_response,
    run_heuristic_scan_from_code,
    run_instant_analysis,
    serialize_instant_record,
)
from core.user.user_model import User


def _multi_runtime_payload() -> dict:
    return {
        'other_config': {},
        '_repository_runtime': {
            'workspace_source': 'multi_repo_cache_copy',
            'workspace': '/tmp/focusaudit-scan-workspace',
            'cache_repo': '/tmp/focusaudit-cache',
        },
    }


class ScanTaskServicesConcurrencyTestCase(SimpleTestCase):
    def test_scan_files_with_concurrency_respects_llm_concurrency(self) -> None:
        files = [
            {'path': f'app_{index}.py', 'content': 'print("ok")\n', 'lines': 1}
            for index in range(4)
        ]
        in_flight = 0
        max_in_flight = 0
        progress_updates: list[dict] = []

        async def fake_analyze(*_args, **_kwargs):
            nonlocal in_flight, max_in_flight
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.05)
            in_flight -= 1
            return {
                'issues': [],
                'quality_score': 92,
                'total_lines': 1,
            }

        def fake_progress(*_args, **kwargs):
            progress_updates.append(kwargs)

        with (
            patch('apps.deepaudit.scan_task.scan_task_services._analyze_code_payload_async', side_effect=fake_analyze),
            patch('apps.deepaudit.scan_task.scan_task_services._persist_scan_issues', return_value=0),
            patch('apps.deepaudit.scan_task.scan_task_services._update_scan_progress', side_effect=fake_progress),
            patch('apps.deepaudit.scan_task.scan_task_services._is_cancelled', return_value=False),
        ):
            summary = asyncio.run(
                _scan_files_with_concurrency(
                    task_id='scan-task-id',
                    created_by_id='user-id',
                    files=files,
                    user_payload={},
                    profile={},
                    llm_concurrency=2,
                    llm_gap_ms=0,
                )
            )

        self.assertFalse(summary['cancelled'])
        self.assertEqual(summary['scanned_files'], 4)
        self.assertEqual(max_in_flight, 2)
        self.assertEqual(len(progress_updates), 4)


class ScanTaskSnapshotTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            username='scan-owner',
            password='not-used',
            name='Scan Owner',
        )
        self.project = AuditProject.objects.create(
            name='FocusAudit Multi Repo',
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

    def test_create_task_snapshots_repository_spec(self) -> None:
        access = SimpleNamespace(project=self.project, role='owner')

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.require_project_role', return_value=access),
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
        ):
            task = create_task(
                self.user,
                {'project_id': str(self.project.id)},
                task_type='repository',
            )

        self.assertEqual(task.repository_type, 'multi')
        self.assertEqual(task.repository_url, 'https://codehub.example.com/platform/manifest.git')
        self.assertEqual(task.branch_name, 'release/main')
        self.assertEqual(task.manifest_xml, 'default.xml')
        self.assertEqual(task.group, 'platform')
        self.assertEqual(
            task.scan_config.get('repository_signature'),
            repository_spec_signature(
                {
                    'repository_type': 'multi',
                    'repository_url': 'https://codehub.example.com/platform/manifest.git',
                    'branch_name': 'release/main',
                    'manifest_xml': 'default.xml',
                    'group': 'platform',
                }
            ),
        )

    def test_create_task_ignores_mismatched_requested_repository_type(self) -> None:
        access = SimpleNamespace(project=self.project, role='owner')

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.require_project_role', return_value=access),
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
            self.assertLogs('apps.deepaudit.scan_task.scan_task_services', level='WARNING') as captured,
        ):
            task = create_task(
                self.user,
                {
                    'project_id': str(self.project.id),
                    'repository_type': 'single',
                },
                task_type='repository',
            )

        self.assertEqual(task.repository_type, 'multi')
        self.assertIn('repository_type mismatch', '\n'.join(captured.output))

    def test_create_task_rejects_stale_repository_signature_for_selected_files(self) -> None:
        access = SimpleNamespace(project=self.project, role='owner')

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.require_project_role', return_value=access),
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
            self.assertRaises(HttpError) as raised,
        ):
            create_task(
                self.user,
                {
                    'project_id': str(self.project.id),
                    'branch_name': 'release/main',
                    'manifest_xml': 'default.xml',
                    'group': 'platform',
                    'file_paths': ['src/module'],
                    'repository_signature': 'stale-signature',
                },
                task_type='repository',
            )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn('仓库规格已变化', str(raised.exception))

    def test_create_task_requires_repository_signature_for_selected_files(self) -> None:
        access = SimpleNamespace(project=self.project, role='owner')

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.require_project_role', return_value=access),
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
            self.assertRaises(HttpError) as raised,
        ):
            create_task(
                self.user,
                {
                    'project_id': str(self.project.id),
                    'file_paths': ['src/module'],
                },
                task_type='repository',
            )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn('文件选择会话未绑定仓库规格', str(raised.exception))

    def test_create_zip_task_allows_selected_files_without_repository_signature(self) -> None:
        zip_project = AuditProject.objects.create(
            name='FocusAudit ZIP Project',
            owner=self.user,
            source_type='zip',
            repository_url='',
            repository_type='single',
            default_branch='main',
            sys_creator=self.user,
            sys_modifier=self.user,
        )
        access = SimpleNamespace(project=zip_project, role='owner')

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.require_project_role', return_value=access),
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
        ):
            task = create_task(
                self.user,
                {
                    'project_id': str(zip_project.id),
                    'file_paths': ['src/module'],
                },
                task_type='zip',
            )

        self.assertEqual(task.task_type, 'zip')
        self.assertEqual(task.scan_config.get('file_paths'), ['src/module'])

    def test_execute_scan_task_rebinds_pending_snapshot_after_project_changes(self) -> None:
        task = AuditTask.objects.create(
            project=self.project,
            created_by=self.user,
            task_type='repository',
            status='pending',
            repository_url='https://codehub.example.com/platform/manifest.git',
            repository_type='multi',
            branch_name='release/main',
            manifest_xml='default.xml',
            group='platform',
            scan_config={
                'repository_signature': repository_spec_signature(
                    {
                        'repository_type': 'multi',
                        'repository_url': 'https://codehub.example.com/platform/manifest.git',
                        'branch_name': 'release/main',
                        'manifest_xml': 'default.xml',
                        'group': 'platform',
                    }
                ),
                'project_repository_signature': repository_spec_signature(
                    {
                        'repository_type': 'multi',
                        'repository_url': 'https://codehub.example.com/platform/manifest.git',
                        'branch_name': 'release/main',
                        'manifest_xml': 'default.xml',
                        'group': 'platform',
                    }
                ),
            },
            sys_creator=self.user,
            sys_modifier=self.user,
        )
        self.project.default_branch = 'release/hotfix'
        self.project.manifest_xml = 'hotfix.xml'
        self.project.group = 'vehicle-a'
        self.project.sys_modifier = self.user
        self.project.save(
            update_fields=[
                'default_branch',
                'manifest_xml',
                'group',
                'sys_modifier',
                'sys_update_datetime',
            ]
        )

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.prepare_repository_workspace',
                return_value=(Path('/tmp/focusaudit-scan-workspace'), _multi_runtime_payload()),
            ) as mock_prepare,
            patch('apps.deepaudit.scan_task.scan_task_services.list_project_files', return_value=[]),
            patch(
                'apps.deepaudit.scan_task.scan_task_services._scan_files_with_concurrency',
                new=AsyncMock(
                    return_value={
                        'cancelled': False,
                        'scanned_files': 0,
                        'skipped_files': 0,
                        'failed_files': 0,
                        'total_lines': 0,
                        'total_issues': 0,
                        'quality_scores': [],
                    }
                ),
            ),
            patch('apps.deepaudit.scan_task.scan_task_services._is_cancelled', return_value=False),
            patch('apps.deepaudit.scan_task.scan_task_services.cleanup_runtime_workspace'),
        ):
            execute_scan_task(str(task.id))

        repository_spec = mock_prepare.call_args.kwargs['repository_spec']
        self.assertEqual(repository_spec['repository_type'], 'multi')
        self.assertEqual(repository_spec['repository_url'], 'https://codehub.example.com/platform/manifest.git')
        self.assertEqual(repository_spec['branch_name'], 'release/hotfix')
        self.assertEqual(repository_spec['manifest_xml'], 'hotfix.xml')
        self.assertEqual(repository_spec['group'], 'vehicle-a')
        self.assertTrue(mock_prepare.call_args.kwargs['force_multi_sync'])
        task.refresh_from_db()
        self.assertEqual(task.branch_name, 'release/hotfix')
        self.assertEqual(task.manifest_xml, 'hotfix.xml')
        self.assertEqual(task.group, 'vehicle-a')

    def test_execute_scan_task_fails_when_all_selected_paths_disappear(self) -> None:
        task = AuditTask.objects.create(
            project=self.project,
            created_by=self.user,
            task_type='repository',
            status='pending',
            repository_url='https://codehub.example.com/platform/manifest.git',
            repository_type='multi',
            branch_name='release/main',
            manifest_xml='default.xml',
            group='platform',
            scan_config={'file_paths': ['src/missing-module']},
            sys_creator=self.user,
            sys_modifier=self.user,
        )

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.prepare_repository_workspace',
                return_value=(Path('/tmp/focusaudit-scan-workspace'), _multi_runtime_payload()),
            ),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.validate_selected_file_paths',
                return_value={'existing': [], 'missing': ['src/missing-module']},
            ),
            patch('apps.deepaudit.scan_task.scan_task_services.list_project_files', side_effect=AssertionError('should not list files')),
            patch('apps.deepaudit.scan_task.scan_task_services.cleanup_runtime_workspace'),
        ):
            execute_scan_task(str(task.id))

        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')
        self.assertIn('所选目录或文件在当前代码工作区中不存在', task.error_message or '')

    def test_execute_scan_task_continues_with_remaining_selected_paths(self) -> None:
        task = AuditTask.objects.create(
            project=self.project,
            created_by=self.user,
            task_type='repository',
            status='pending',
            repository_url='https://codehub.example.com/platform/manifest.git',
            repository_type='multi',
            branch_name='release/main',
            manifest_xml='default.xml',
            group='platform',
            scan_config={'file_paths': ['src/keep-module', 'src/missing-module']},
            sys_creator=self.user,
            sys_modifier=self.user,
        )

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.prepare_repository_workspace',
                return_value=(Path('/tmp/focusaudit-scan-workspace'), _multi_runtime_payload()),
            ),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.validate_selected_file_paths',
                return_value={
                    'existing': ['src/keep-module'],
                    'missing': ['src/missing-module'],
                },
            ),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.resolve_selected_file_paths',
                return_value=['src/keep-module/main.c'],
            ),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.list_project_files',
                return_value=[],
            ) as mock_list_files,
            patch(
                'apps.deepaudit.scan_task.scan_task_services._scan_files_with_concurrency',
                new=AsyncMock(
                    return_value={
                        'cancelled': False,
                        'scanned_files': 0,
                        'skipped_files': 0,
                        'failed_files': 0,
                        'total_lines': 0,
                        'total_issues': 0,
                        'quality_scores': [],
                    }
                ),
            ),
            patch('apps.deepaudit.scan_task.scan_task_services._is_cancelled', return_value=False),
            patch('apps.deepaudit.scan_task.scan_task_services.cleanup_runtime_workspace'),
        ):
            execute_scan_task(str(task.id))

        self.assertEqual(
            mock_list_files.call_args.kwargs['file_paths'],
            ['src/keep-module/main.c'],
        )

    def test_execute_scan_task_expands_selected_directories_before_listing(self) -> None:
        task = AuditTask.objects.create(
            project=self.project,
            created_by=self.user,
            task_type='repository',
            status='pending',
            repository_url='https://codehub.example.com/platform/manifest.git',
            repository_type='multi',
            branch_name='release/main',
            manifest_xml='default.xml',
            group='platform',
            scan_config={'file_paths': ['src/module']},
            sys_creator=self.user,
            sys_modifier=self.user,
        )

        with (
            patch('apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile', return_value={}),
            patch('apps.deepaudit.scan_task.scan_task_services.serialize_scan_profile', return_value={}),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.prepare_repository_workspace',
                return_value=(Path('/tmp/focusaudit-scan-workspace'), _multi_runtime_payload()),
            ),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.validate_selected_file_paths',
                return_value={'existing': ['src/module'], 'missing': []},
            ),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.resolve_selected_file_paths',
                return_value=['src/module/a.c', 'src/module/b.c'],
            ),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.list_project_files',
                return_value=[],
            ) as mock_list_files,
            patch(
                'apps.deepaudit.scan_task.scan_task_services._scan_files_with_concurrency',
                new=AsyncMock(
                    return_value={
                        'cancelled': False,
                        'scanned_files': 0,
                        'skipped_files': 0,
                        'failed_files': 0,
                        'total_lines': 0,
                        'total_issues': 0,
                        'quality_scores': [],
                    }
                ),
            ),
            patch('apps.deepaudit.scan_task.scan_task_services._is_cancelled', return_value=False),
            patch('apps.deepaudit.scan_task.scan_task_services.cleanup_runtime_workspace'),
        ):
            execute_scan_task(str(task.id))

        self.assertEqual(
            mock_list_files.call_args.kwargs['file_paths'],
            ['src/module/a.c', 'src/module/b.c'],
        )
        task.refresh_from_db()
        self.assertEqual(task.total_files, 2)
        self.assertEqual(task.scan_config.get('selection_stats', {}).get('selected_directory_count'), 1)
        self.assertEqual(task.scan_config.get('selection_stats', {}).get('resolved_file_count'), 2)


class InstantAnalysisServiceTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            username='instant-owner',
            password='not-used',
            name='Instant Owner',
        )

    def test_run_instant_analysis_passes_prompt_template_id_and_file_name(self) -> None:
        analysis_result = {
            'issues': [],
            'quality_score': 88,
            'summary': {
                'total_issues': 0,
                'critical_issues': 0,
                'high_issues': 0,
                'medium_issues': 0,
                'low_issues': 0,
            },
            'analysis_profile': {
                'prompt_template_id': 'template-c',
            },
        }
        profile = {
            'analysis_depth': 'standard',
            'prompt_template': None,
            'prompt_context': {},
            'rule_patterns': (),
            'severity_weights': {},
        }

        with (
            patch(
                'apps.deepaudit.scan_task.scan_task_services.user_config_services.get_user_config',
                return_value={'other_config': {'scan_config': {}}},
            ),
            patch(
                'apps.deepaudit.scan_task.scan_task_services.resolve_scan_profile',
                return_value=profile,
            ) as mock_resolve_profile,
            patch(
                'apps.deepaudit.scan_task.scan_task_services._analyze_c_family_candidates_async',
                return_value=analysis_result,
            ) as mock_analyze,
        ):
            result = run_instant_analysis(
                self.user,
                {
                    'code_content': 'printf(input);',
                    'language': 'c',
                    'file_name': 'demo.c',
                    'prompt_template_id': 'template-c',
                },
            )

        self.assertEqual(result['language'], 'c')
        self.assertEqual(
            mock_resolve_profile.call_args.args[1]['prompt_template_id'],
            'template-c',
        )
        self.assertTrue(mock_resolve_profile.call_args.kwargs['strict'])
        self.assertEqual(mock_analyze.call_args.kwargs['files'][0]['path'], 'demo.c')
        self.assertEqual(
            mock_analyze.call_args.kwargs['selected_file_paths'],
            ['demo.c'],
        )

    def test_serialize_instant_record_detail_includes_code_content(self) -> None:
        record = InstantAnalysisRecord.objects.create(
            user=self.user,
            language='c',
            code_content='int main(void) {\n  return 0;\n}\n',
            analysis_result={'issues': [], 'quality_score': 100},
            issues_count=0,
            quality_score=100,
            analysis_time=0.123,
            sys_creator=self.user,
            sys_modifier=self.user,
        )

        serialized = serialize_instant_record(record, include_code=True)

        self.assertEqual(serialized['code_content'], 'int main(void) {\n  return 0;\n}\n')
        self.assertEqual(serialized['language'], 'c')

    def test_export_instant_pdf_response_returns_pdf_bytes(self) -> None:
        record = InstantAnalysisRecord.objects.create(
            user=self.user,
            language='c',
            code_content='#include <stdio.h>\nint main(void) {\n  char buf[4];\n  gets(buf);\n  return 0;\n}\n',
            analysis_result={
                'quality_score': 42,
                'issues': [
                    {
                        'title': '潜在缓冲区溢出',
                        'severity': 'high',
                        'line_number': 4,
                        'issue_type': 'buffer_overflow',
                    }
                ],
            },
            issues_count=1,
            quality_score=42,
            analysis_time=0.456,
            sys_creator=self.user,
            sys_modifier=self.user,
        )

        response = export_instant_pdf_response(self.user, str(record.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(f'instant-{record.id}.pdf', response['Content-Disposition'])
        self.assertTrue(bytes(response.content).startswith(b'%PDF'))
        self.assertGreater(len(response.content), 1000)


class HeuristicScanLanguageTestCase(SimpleTestCase):
    def test_run_heuristic_scan_from_code_uses_c_extension(self) -> None:
        result = run_heuristic_scan_from_code(
            '#include <stdio.h>\n#include <string.h>\nvoid f(char *s){ char buf[8]; strcpy(buf, s); printf(s); }\n',
            'c',
        )

        self.assertGreaterEqual(result['summary']['total_issues'], 1)
        self.assertTrue(
            all(issue['file_path'] == 'snippet.c' for issue in result['issues'])
        )
