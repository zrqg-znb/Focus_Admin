from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from ninja.errors import HttpError

from apps.deepaudit import git_service
from apps.deepaudit import runtime
from apps.deepaudit import storage as deepaudit_storage
from apps.deepaudit.project import project_services
from apps.deepaudit.repo_specs import build_repository_spec, repository_spec_signature


def _storage_patch(temp_root: Path):
    return patch.multiple(
        deepaudit_storage,
        DEEPAUDIT_ROOT=temp_root,
        PROJECTS_DIR=temp_root / 'projects',
        ZIP_DIR=temp_root / 'zip',
        WORKSPACE_DIR=temp_root / 'workspaces',
        REPORTS_DIR=temp_root / 'reports',
        ARTIFACTS_DIR=temp_root / 'artifacts',
        VECTOR_DB_DIR=temp_root / 'vector_db',
        SSH_DIR=temp_root / 'ssh',
        KNOWLEDGE_DIR=temp_root / 'knowledge',
        REPO_CACHE_DIR=temp_root / 'repo_cache',
    )


class RuntimeRepositoryWorkspaceTestCase(SimpleTestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix='deepaudit-runtime-workspace-'))
        self.storage_patch = _storage_patch(self.temp_root)
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

    def _run_git(self, *args: str, cwd: Path | None = None) -> None:
        subprocess.run(
            ['git', *args],
            cwd=str(cwd) if cwd else None,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _create_origin_repo(self) -> Path:
        origin = self.temp_root / 'origin-repo'
        origin.mkdir(parents=True, exist_ok=True)
        self._run_git('init', '-b', 'main', cwd=origin)
        self._run_git('config', 'user.email', 'deepaudit@example.com', cwd=origin)
        self._run_git('config', 'user.name', 'DeepAudit Tests', cwd=origin)
        (origin / 'app.py').write_text("print('deepaudit')\n", encoding='utf-8')
        self._run_git('add', 'app.py', cwd=origin)
        self._run_git('commit', '-m', 'initial', cwd=origin)
        return origin

    @override_settings(
        DEEPAUDIT_REPO_CACHE_ENABLED=True,
        DEEPAUDIT_REPO_CACHE_TTL_SECONDS=1800,
        DEEPAUDIT_GIT_CLONE_TIMEOUT=180,
    )
    def test_prepare_workspace_returns_worktree_and_cleanup_preserves_cache(self) -> None:
        origin = self._create_origin_repo()
        project = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            default_branch='main',
            source_type='repository',
            repository_url=str(origin),
            repository_type='single',
            owner=SimpleNamespace(id='owner-1'),
        )

        with (
            patch('apps.deepaudit.runtime.load_user_config_payload', return_value={'llm_config': {}, 'other_config': {}}),
            patch('apps.deepaudit.runtime.load_ssh_private_key', return_value=None),
        ):
            workspace, _user_payload = runtime.prepare_workspace(project, branch_name='main', user_id='owner-1')

        cache_repo = git_service._cache_paths(
            project,
            build_repository_spec(str(origin), 'main', repository_type='single'),
        )['repo']
        self.assertTrue((workspace / '.git').is_file())
        self.assertTrue((workspace / 'app.py').exists())
        self.assertTrue(cache_repo.exists())

        runtime.cleanup_runtime_workspace(workspace)

        self.assertFalse(workspace.exists())
        self.assertTrue(cache_repo.exists())

    def test_prepare_workspace_passes_multi_repo_overrides(self) -> None:
        project = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            default_branch='main',
            source_type='repository',
            repository_url='https://example.com/repo.git',
            repository_type='multi',
            manifest_xml='default.xml',
            group='default-group',
            owner=SimpleNamespace(id='owner-1'),
        )
        workspace = self.temp_root / 'workspace'

        with (
            patch('apps.deepaudit.runtime.load_user_config_payload', return_value={'llm_config': {}, 'other_config': {}}),
            patch('apps.deepaudit.runtime.load_ssh_private_key', return_value=None),
            patch('apps.deepaudit.runtime.create_repository_workspace', return_value=workspace) as mock_create,
        ):
            result_workspace, _user_payload = runtime.prepare_workspace(
                project,
                branch_name='release',
                manifest_xml='custom.xml',
                group='team-a',
                user_id='owner-1',
            )

        self.assertEqual(result_workspace, workspace)
        self.assertEqual(mock_create.call_count, 1)
        self.assertEqual(mock_create.call_args.kwargs['repository_type'], 'multi')
        self.assertEqual(mock_create.call_args.kwargs['manifest_xml'], 'custom.xml')
        self.assertEqual(mock_create.call_args.kwargs['group'], 'team-a')

    def test_prepare_workspace_ignores_repository_type_override_for_multi_project(self) -> None:
        project = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            default_branch='main',
            source_type='repository',
            repository_url='https://example.com/manifest.git',
            repository_type='multi',
            manifest_xml='default.xml',
            group='platform',
            owner=SimpleNamespace(id='owner-1'),
        )
        workspace = self.temp_root / 'workspace'

        with (
            patch('apps.deepaudit.runtime.load_user_config_payload', return_value={'llm_config': {}, 'other_config': {}}),
            patch('apps.deepaudit.runtime.load_ssh_private_key', return_value=None),
            patch('apps.deepaudit.runtime.create_repository_workspace', return_value=workspace) as mock_create,
            self.assertLogs('apps.deepaudit.runtime', level='WARNING') as captured,
        ):
            runtime.prepare_workspace(
                project,
                repository_type='single',
                branch_name='release/main',
                manifest_xml='vehicle.xml',
                group='vehicle-a',
                user_id='owner-1',
            )

        repository_spec = mock_create.call_args.kwargs['repository_spec']
        self.assertEqual(mock_create.call_args.kwargs['repository_type'], 'multi')
        self.assertEqual(repository_spec['repository_type'], 'multi')
        self.assertEqual(repository_spec['repository_url'], 'https://example.com/manifest.git')
        self.assertEqual(repository_spec['branch_name'], 'release/main')
        self.assertEqual(repository_spec['manifest_xml'], 'vehicle.xml')
        self.assertEqual(repository_spec['group'], 'vehicle-a')
        self.assertIn('ignored repository_type override', '\n'.join(captured.output))

    def test_prepare_repository_workspace_uses_explicit_repository_spec(self) -> None:
        project = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            source_type='repository',
            repository_url='https://example.com/single.git',
            repository_type='single',
            default_branch='main',
            owner=SimpleNamespace(id='owner-1'),
        )
        repository_spec = build_repository_spec(
            'https://example.com/manifest.git',
            'release/main',
            repository_type='multi',
            manifest_xml='default.xml',
            group='platform',
        )
        workspace = self.temp_root / 'workspace'

        with (
            patch('apps.deepaudit.runtime.load_user_config_payload', return_value={'llm_config': {}, 'other_config': {}}),
            patch('apps.deepaudit.runtime.load_ssh_private_key', return_value=None),
            patch('apps.deepaudit.runtime.create_repository_workspace', return_value=workspace) as mock_create,
        ):
            result_workspace, _user_payload = runtime.prepare_repository_workspace(
                project,
                repository_spec=repository_spec,
                user_id='owner-1',
            )

        self.assertEqual(result_workspace, workspace)
        self.assertEqual(mock_create.call_count, 1)
        self.assertEqual(mock_create.call_args.kwargs['repository_spec'], repository_spec)
        self.assertEqual(mock_create.call_args.kwargs['repository_type'], 'multi')
        self.assertEqual(mock_create.call_args.kwargs['manifest_xml'], 'default.xml')
        self.assertEqual(mock_create.call_args.kwargs['group'], 'platform')

    def test_prepare_workspace_reuses_explicit_repository_spec(self) -> None:
        project = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            source_type='repository',
            repository_url='https://example.com/single.git',
            repository_type='single',
            default_branch='main',
            owner=SimpleNamespace(id='owner-1'),
        )
        repository_spec = build_repository_spec(
            'https://example.com/manifest.git',
            'release/main',
            repository_type='multi',
            manifest_xml='default.xml',
            group='platform',
        )
        workspace = self.temp_root / 'workspace'

        with (
            patch('apps.deepaudit.runtime.load_user_config_payload', return_value={'llm_config': {}, 'other_config': {}}),
            patch('apps.deepaudit.runtime.load_ssh_private_key', return_value=None),
            patch('apps.deepaudit.runtime.create_repository_workspace', return_value=workspace) as mock_create,
        ):
            result_workspace, _user_payload = runtime.prepare_workspace(
                project,
                repository_spec=repository_spec,
                user_id='owner-1',
            )

        self.assertEqual(result_workspace, workspace)
        self.assertEqual(mock_create.call_count, 1)
        self.assertEqual(mock_create.call_args.kwargs['repository_spec'], repository_spec)
        self.assertEqual(mock_create.call_args.kwargs['repository_type'], 'multi')

    def test_prepare_repository_workspace_forwards_event_callback(self) -> None:
        project = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            source_type='repository',
            repository_url='https://example.com/repo.git',
            repository_type='multi',
            default_branch='main',
            owner=SimpleNamespace(id='owner-1'),
        )
        repository_spec = build_repository_spec(
            'https://example.com/repo.git',
            'release/main',
            repository_type='multi',
            manifest_xml='default.xml',
            group='platform',
        )
        workspace = self.temp_root / 'workspace'

        def event_callback(*_args, **_kwargs):
            return None

        with (
            patch('apps.deepaudit.runtime.load_user_config_payload', return_value={'llm_config': {}, 'other_config': {}}),
            patch('apps.deepaudit.runtime.load_ssh_private_key', return_value=None),
            patch('apps.deepaudit.runtime.create_repository_workspace', return_value=workspace) as mock_create,
        ):
            runtime.prepare_repository_workspace(
                project,
                repository_spec=repository_spec,
                user_id='owner-1',
                event_callback=event_callback,
                log_context={'task_kind': 'agent', 'task_id': 'task-1'},
            )

        self.assertIs(mock_create.call_args.kwargs['event_callback'], event_callback)
        self.assertEqual(mock_create.call_args.kwargs['log_context'], {'task_kind': 'agent', 'task_id': 'task-1'})


class ProjectRepositoryFileListingTestCase(RuntimeRepositoryWorkspaceTestCase):
    def test_list_files_uses_cached_repository_listing(self) -> None:
        user = SimpleNamespace(id='user-1')
        project_instance = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            source_type='repository',
            repository_url='https://example.com/repo.git',
            default_branch='main',
        )
        access = SimpleNamespace(project=project_instance)
        expected_rows = [{'path': 'src/app.py', 'size': 128}]

        with (
            patch('apps.deepaudit.project.project_services.require_project_role', return_value=access),
            patch('apps.deepaudit.project.project_services.repository_cache_enabled', return_value=True),
            patch('apps.deepaudit.project.project_services.load_user_config_payload', return_value={'other_config': {}}),
            patch('apps.deepaudit.project.project_services.load_ssh_private_key', return_value=None),
            patch('apps.deepaudit.project.project_services.ensure_repository_cache', return_value=Path('/tmp/cache')),
            patch('apps.deepaudit.project.project_services.list_repository_files', return_value=expected_rows),
            patch('apps.deepaudit.project.project_services.prepare_workspace', side_effect=AssertionError('should not clone')),
        ):
            rows = project_services.list_files(user, 'project-1')

        self.assertEqual(rows, expected_rows)

    def test_browse_files_returns_paginated_directory_entries(self) -> None:
        user = SimpleNamespace(id='user-1')
        project_instance = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            source_type='repository',
            repository_url='https://example.com/repo.git',
            repository_type='multi',
            default_branch='main',
            manifest_xml='default.xml',
            group='platform',
        )
        access = SimpleNamespace(project=project_instance)
        cache_repo = self.temp_root / 'cache-repo'
        (cache_repo / 'src').mkdir(parents=True, exist_ok=True)
        (cache_repo / 'src' / 'app.py').write_text("print('ok')\n", encoding='utf-8')
        (cache_repo / 'README.md').write_text('# demo\n', encoding='utf-8')

        with (
            patch('apps.deepaudit.project.project_services.require_project_role', return_value=access),
            patch('apps.deepaudit.project.project_services.repository_cache_enabled', return_value=True),
            patch('apps.deepaudit.project.project_services.load_user_config_payload', return_value={'other_config': {}}),
            patch('apps.deepaudit.project.project_services.load_ssh_private_key', return_value=None),
            patch('apps.deepaudit.project.project_services.ensure_repository_cache', return_value=cache_repo),
            patch(
                'apps.deepaudit.project.project_services.get_repository_cache_info',
                return_value={
                    'cache_root': cache_repo.parent,
                    'cache_repo': cache_repo,
                    'state_path': cache_repo.parent / 'state.json',
                    'cache_exists': True,
                    'last_synced_at': 1234567890,
                    'repository_spec': build_repository_spec(
                        'https://example.com/repo.git',
                        'main',
                        repository_type='multi',
                        manifest_xml='default.xml',
                        group='platform',
                    ),
                },
            ),
        ):
            payload = project_services.browse_files(
                user,
                'project-1',
                repository_type='multi',
                branch_name='main',
                manifest_xml='default.xml',
                group='platform',
                limit=10,
            )

        self.assertEqual(payload['total'], 2)
        self.assertEqual(payload['items'][0]['kind'], 'directory')
        self.assertEqual(payload['items'][0]['path'], 'src')
        self.assertEqual(payload['items'][1]['kind'], 'file')
        self.assertEqual(payload['items'][1]['path'], 'README.md')
        self.assertEqual(payload['repository_spec']['repository_type'], 'multi')
        self.assertEqual(
            payload['repository_signature'],
            repository_spec_signature(
                build_repository_spec(
                    'https://example.com/repo.git',
                    'main',
                    repository_type='multi',
                    manifest_xml='default.xml',
                    group='platform',
                )
            ),
        )
        self.assertEqual(payload['last_synced_at'], 1234567890)

    def test_browse_files_ignores_repository_type_override_for_multi_project(self) -> None:
        user = SimpleNamespace(id='user-1')
        project_instance = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            source_type='repository',
            repository_url='https://example.com/manifest.git',
            repository_type='multi',
            default_branch='release/main',
            manifest_xml='default.xml',
            group='platform',
        )
        access = SimpleNamespace(project=project_instance)
        cache_repo = self.temp_root / 'cache-override-repo'
        cache_repo.mkdir(parents=True, exist_ok=True)

        with (
            patch('apps.deepaudit.project.project_services.require_project_role', return_value=access),
            patch('apps.deepaudit.project.project_services.repository_cache_enabled', return_value=True),
            patch('apps.deepaudit.project.project_services.load_user_config_payload', return_value={'other_config': {}}),
            patch('apps.deepaudit.project.project_services.load_ssh_private_key', return_value=None),
            patch('apps.deepaudit.project.project_services.ensure_repository_cache', return_value=cache_repo) as mock_cache,
            patch(
                'apps.deepaudit.project.project_services.get_repository_cache_info',
                return_value={
                    'cache_root': cache_repo.parent,
                    'cache_repo': cache_repo,
                    'state_path': cache_repo.parent / 'state.json',
                    'cache_exists': True,
                    'last_synced_at': 1234567890,
                    'repository_spec': build_repository_spec(
                        'https://example.com/manifest.git',
                        'release/main',
                        repository_type='multi',
                        manifest_xml='default.xml',
                        group='platform',
                    ),
                },
            ),
            self.assertLogs('apps.deepaudit.project.project_services', level='WARNING') as captured,
        ):
            project_services.browse_files(
                user,
                'project-1',
                repository_type='single',
                branch_name='release/hotfix',
                manifest_xml='vehicle.xml',
                group='vehicle-a',
                limit=10,
            )

        repository_spec = mock_cache.call_args.kwargs['repository_spec']
        self.assertEqual(repository_spec['repository_type'], 'multi')
        self.assertEqual(repository_spec['repository_url'], 'https://example.com/manifest.git')
        self.assertEqual(repository_spec['branch_name'], 'release/hotfix')
        self.assertEqual(repository_spec['manifest_xml'], 'vehicle.xml')
        self.assertEqual(repository_spec['group'], 'vehicle-a')
        self.assertIn('ignored repository_type override', '\n'.join(captured.output))

    def test_browse_files_refresh_disables_stale_cache_fallback(self) -> None:
        user = SimpleNamespace(id='user-1')
        project_instance = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            source_type='repository',
            repository_url='https://example.com/manifest.git',
            repository_type='multi',
            default_branch='release/main',
            manifest_xml='default.xml',
            group='platform',
        )
        access = SimpleNamespace(project=project_instance)

        with (
            patch('apps.deepaudit.project.project_services.require_project_role', return_value=access),
            patch('apps.deepaudit.project.project_services.repository_cache_enabled', return_value=True),
            patch('apps.deepaudit.project.project_services.load_user_config_payload', return_value={'other_config': {}}),
            patch('apps.deepaudit.project.project_services.load_ssh_private_key', return_value=None),
            patch(
                'apps.deepaudit.project.project_services.ensure_repository_cache',
                side_effect=git_service.GitServiceError('multi repo sync failed'),
            ) as mock_cache,
        ):
            with self.assertRaises(HttpError) as raised:
                project_services.browse_files(
                    user,
                    'project-1',
                    repository_type='multi',
                    branch_name='release/main',
                    manifest_xml='default.xml',
                    group='platform',
                    refresh=True,
                )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn('multi repo sync failed', str(raised.exception))
        self.assertFalse(mock_cache.call_args.kwargs['allow_stale_on_failure'])
        self.assertTrue(mock_cache.call_args.kwargs['force_refresh'])
        self.assertTrue(mock_cache.call_args.kwargs['force_multi_sync'])


class RuntimeSelectedFilesValidationTestCase(RuntimeRepositoryWorkspaceTestCase):
    def test_validate_selected_file_paths_splits_existing_and_missing(self) -> None:
        workspace = self.temp_root / 'validation-workspace'
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / 'src').mkdir(parents=True, exist_ok=True)
        (workspace / 'src' / 'main.c').write_text('int main(void) { return 0; }\n', encoding='utf-8')

        result = runtime.validate_selected_file_paths(
            workspace,
            file_paths=['src/main.c', 'src/missing.c', './src/main.c'],
        )

        self.assertEqual(result['existing'], ['src/main.c'])
        self.assertEqual(result['missing'], ['src/missing.c'])

    def test_validate_selected_file_paths_accepts_directories(self) -> None:
        workspace = self.temp_root / 'validation-directories-workspace'
        (workspace / 'src').mkdir(parents=True, exist_ok=True)
        (workspace / 'src' / 'module').mkdir(parents=True, exist_ok=True)
        (workspace / 'src' / 'module' / 'main.c').write_text(
            'int main(void) { return 0; }\n',
            encoding='utf-8',
        )

        result = runtime.validate_selected_file_paths(
            workspace,
            file_paths=['src/module', './src/module', 'src/missing'],
        )

        self.assertEqual(result['existing'], ['src/module'])
        self.assertEqual(result['missing'], ['src/missing'])

    def test_list_project_files_expands_directory_targets_recursively(self) -> None:
        workspace = self.temp_root / 'listing-workspace'
        (workspace / 'src').mkdir(parents=True, exist_ok=True)
        (workspace / 'src' / 'module').mkdir(parents=True, exist_ok=True)
        (workspace / 'src' / 'module' / 'main.c').write_text(
            'int main(void) { return 0; }\n',
            encoding='utf-8',
        )
        (workspace / 'src' / 'module' / 'helper.h').write_text(
            '#pragma once\n',
            encoding='utf-8',
        )
        (workspace / 'src' / 'notes.txt').write_text(
            'plain text note\n',
            encoding='utf-8',
        )
        (workspace / 'README.md').write_text('# root\n', encoding='utf-8')

        files = runtime.list_project_files(
            workspace,
            file_paths=['src/module', 'src/module/main.c'],
            include_docs=True,
        )

        self.assertEqual(
            [item['path'] for item in files],
            ['src/module/helper.h', 'src/module/main.c'],
        )

    def test_resolve_selected_file_paths_expands_directory_targets_recursively(self) -> None:
        workspace = self.temp_root / 'resolve-selection-workspace'
        (workspace / 'src' / 'module').mkdir(parents=True, exist_ok=True)
        (workspace / 'src' / 'module' / 'main.c').write_text(
            'int main(void) { return 0; }\n',
            encoding='utf-8',
        )
        (workspace / 'src' / 'module' / 'helper.h').write_text(
            '#pragma once\n',
            encoding='utf-8',
        )
        (workspace / 'src' / 'module' / 'README.md').write_text(
            '# docs\n',
            encoding='utf-8',
        )

        files = runtime.resolve_selected_file_paths(
            workspace,
            file_paths=['src/module'],
            include_docs=False,
        )

        self.assertEqual(
            files,
            ['src/module/helper.h', 'src/module/main.c'],
        )
