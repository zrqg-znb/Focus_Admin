from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.deepaudit import git_service
from apps.deepaudit import runtime
from apps.deepaudit import storage as deepaudit_storage
from apps.deepaudit.project import project_services
from apps.deepaudit.repo_specs import build_repository_spec


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


class ProjectRepositoryFileListingTestCase(SimpleTestCase):
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
