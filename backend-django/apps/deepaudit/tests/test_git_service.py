from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.deepaudit import storage as deepaudit_storage
from apps.deepaudit import git_service
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


class GitServiceTestCase(SimpleTestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix='deepaudit-git-service-'))
        self.project = SimpleNamespace(
            id='project-1',
            owner_id='owner-1',
            default_branch='main',
            repository_type='single',
        )
        self.storage_patch = _storage_patch(self.temp_root)
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

    def _repo_spec(self, *, branch_name: str = 'main', repository_type: str = 'single', manifest_xml: str = '', group: str = '') -> dict:
        return build_repository_spec(
            'https://example.com/repo.git',
            branch_name,
            repository_type=repository_type,
            manifest_xml=manifest_xml,
            group=group,
        )

    @override_settings(DEEPAUDIT_GIT_CLONE_TIMEOUT=321, DEEPAUDIT_GIT_RETRY_COUNT=2)
    def test_clone_repository_uses_no_tags_timeout_and_lfs_skip(self) -> None:
        target_path = self.temp_root / 'workspace'
        calls: list[tuple[list[str], dict]] = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return SimpleNamespace(stdout='', stderr='', returncode=0)

        with patch('apps.deepaudit.git_service.subprocess.run', side_effect=fake_run):
            result = git_service.clone_repository(
                self.project,
                'https://example.com/repo.git',
                'main',
                {'other_config': {}},
                target_path=target_path,
            )

        self.assertEqual(result, target_path)
        self.assertTrue(calls)
        clone_cmd, clone_kwargs = calls[0]
        self.assertIn('--no-tags', clone_cmd)
        self.assertEqual(clone_kwargs['timeout'], 321)
        self.assertEqual(clone_kwargs['env']['GIT_LFS_SKIP_SMUDGE'], '1')
        self.assertEqual(clone_kwargs['env']['GIT_TERMINAL_PROMPT'], '0')

    @override_settings(DEEPAUDIT_GIT_LS_REMOTE_TIMEOUT=222)
    def test_list_remote_branches_uses_configured_timeout(self) -> None:
        def fake_run(*_args, **kwargs):
            self.assertEqual(kwargs['timeout'], 222)
            return SimpleNamespace(
                stdout='abc123\trefs/heads/main\ndef456\trefs/heads/dev\n',
                stderr='',
                returncode=0,
            )

        with patch('apps.deepaudit.git_service.subprocess.run', side_effect=fake_run):
            branches = git_service.list_remote_branches(
                self.project,
                'https://example.com/repo.git',
                {'other_config': {}},
            )

        self.assertEqual(branches, ['main', 'dev'])

    @override_settings(DEEPAUDIT_REPO_CACHE_TTL_SECONDS=1800)
    def test_ensure_repository_cache_skips_refresh_when_cache_is_fresh(self) -> None:
        repo_spec = self._repo_spec()
        cache_paths = git_service._cache_paths(self.project, repo_spec)
        cache_paths['repo'].mkdir(parents=True, exist_ok=True)
        (cache_paths['repo'] / '.git').mkdir()
        cache_paths['state'].write_text(
            json.dumps({'last_synced_at': int(time.time()), 'repository_spec': repo_spec}),
            encoding='utf-8',
        )

        with patch('apps.deepaudit.git_service.subprocess.run', side_effect=AssertionError('should not refresh')):
            cache_repo = git_service.ensure_repository_cache(
                self.project,
                'https://example.com/repo.git',
                'main',
                {'other_config': {}},
                repository_type='single',
            )

        self.assertEqual(cache_repo, cache_paths['repo'])

    @override_settings(DEEPAUDIT_REPO_CACHE_TTL_SECONDS=60)
    def test_ensure_repository_cache_refreshes_expired_cache(self) -> None:
        repo_spec = self._repo_spec()
        cache_paths = git_service._cache_paths(self.project, repo_spec)
        cache_paths['repo'].mkdir(parents=True, exist_ok=True)
        (cache_paths['repo'] / '.git').mkdir()
        cache_paths['state'].write_text(
            json.dumps({'last_synced_at': int(time.time()) - 3600, 'repository_spec': repo_spec}),
            encoding='utf-8',
        )
        commands: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            commands.append(cmd)
            return SimpleNamespace(stdout='', stderr='', returncode=0)

        with patch('apps.deepaudit.git_service.subprocess.run', side_effect=fake_run):
            cache_repo = git_service.ensure_repository_cache(
                self.project,
                'https://example.com/repo.git',
                'main',
                {'other_config': {}},
                repository_type='single',
            )

        self.assertEqual(cache_repo, cache_paths['repo'])
        self.assertTrue(any('fetch' in command for command in commands))

    @override_settings(DEEPAUDIT_REPO_CACHE_TTL_SECONDS=60)
    def test_cache_refresh_lock_serializes_same_cache_path(self) -> None:
        repo_spec = self._repo_spec()
        cache_paths = git_service._cache_paths(self.project, repo_spec)
        cache_paths['repo'].mkdir(parents=True, exist_ok=True)
        (cache_paths['repo'] / '.git').mkdir()
        cache_paths['state'].write_text(
            json.dumps({'last_synced_at': int(time.time()) - 3600, 'repository_spec': repo_spec}),
            encoding='utf-8',
        )
        fetch_started = threading.Event()
        release_fetch = threading.Event()
        fetch_count = 0
        errors: list[Exception] = []

        def fake_run(cmd, **_kwargs):
            nonlocal fetch_count
            if 'fetch' in cmd:
                fetch_count += 1
                fetch_started.set()
                release_fetch.wait(timeout=3)
            return SimpleNamespace(stdout='', stderr='', returncode=0)

        def worker() -> None:
            try:
                git_service.ensure_repository_cache(
                    self.project,
                    'https://example.com/repo.git',
                    'main',
                    {'other_config': {}},
                    repository_type='single',
                )
            except Exception as exc:
                errors.append(exc)

        with patch('apps.deepaudit.git_service.subprocess.run', side_effect=fake_run):
            first = threading.Thread(target=worker)
            second = threading.Thread(target=worker)
            first.start()
            self.assertTrue(fetch_started.wait(timeout=1))
            second.start()
            time.sleep(0.2)
            release_fetch.set()
            first.join(timeout=5)
            second.join(timeout=5)

        self.assertFalse(errors)
        self.assertEqual(fetch_count, 1)

    @override_settings(DEEPAUDIT_GIT_CLONE_TIMEOUT=321)
    def test_clone_repository_multi_runs_mm_init_and_sync(self) -> None:
        target_path = self.temp_root / 'workspace'
        calls: list[tuple[list[str], dict]] = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return SimpleNamespace(stdout='', stderr='', returncode=0)

        with patch('apps.deepaudit.git_service.subprocess.run', side_effect=fake_run):
            result = git_service.clone_repository(
                self.project,
                'https://example.com/repo.git',
                'main',
                {'other_config': {}},
                target_path=target_path,
                repository_type='multi',
                manifest_xml='default.xml',
                group='platform',
            )

        self.assertEqual(result, target_path)
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(calls[0][0][:3], ['git', 'mm', 'init'])
        self.assertEqual(calls[1][0], ['git', 'mm', 'sync'])
        self.assertEqual(calls[0][1]['cwd'], str(target_path))
        self.assertEqual(calls[1][1]['cwd'], str(target_path))

    @override_settings(DEEPAUDIT_GIT_CLONE_TIMEOUT=321)
    def test_clone_repository_multi_soft_fails_on_mm_sync_nonzero(self) -> None:
        target_path = self.temp_root / 'workspace'

        def fake_run(cmd, **_kwargs):
            if cmd[:3] == ['git', 'mm', 'init']:
                return SimpleNamespace(stdout='init ok', stderr='', returncode=0)
            if cmd == ['git', 'mm', 'sync']:
                return SimpleNamespace(stdout='partial sync', stderr='permission denied on child repo', returncode=23)
            raise AssertionError(f'unexpected command: {cmd}')

        with (
            patch('apps.deepaudit.git_service.subprocess.run', side_effect=fake_run),
            self.assertLogs('apps.deepaudit.git_service', level='WARNING') as captured,
        ):
            result = git_service.clone_repository(
                self.project,
                'https://example.com/repo.git',
                'main',
                {'other_config': {}},
                target_path=target_path,
                repository_type='multi',
                manifest_xml='default.xml',
                group='platform',
            )

        self.assertEqual(result, target_path)
        self.assertTrue(target_path.exists())
        self.assertIn('soft-failed', '\n'.join(captured.output))

    def test_update_repository_cache_refuses_multi_repo_single_path(self) -> None:
        repo_spec = self._repo_spec(repository_type='multi', manifest_xml='default.xml', group='platform')

        with (
            patch('apps.deepaudit.git_service.subprocess.run', side_effect=AssertionError('should not run single-repo commands')),
            self.assertLogs('apps.deepaudit.git_service', level='WARNING') as captured,
        ):
            with self.assertRaises(git_service.GitServiceError):
                git_service._update_repository_cache(
                    self.project,
                    cache_repo=self.temp_root / 'cache-repo',
                    repository_url=repo_spec['repository_url'],
                    clone_url=repo_spec['repository_url'],
                    branch_name=repo_spec['branch_name'],
                    env={},
                    repository_spec=repo_spec,
                    log_context={'task_kind': 'agent', 'task_id': 'task-1'},
                )

        self.assertIn('entering single-repo 缓存刷新 path', '\n'.join(captured.output))

    def test_cache_paths_depend_on_effective_repository_spec(self) -> None:
        spec_a = self._repo_spec(branch_name='main', repository_type='multi', manifest_xml='a.xml', group='platform')
        spec_b = self._repo_spec(branch_name='dev', repository_type='multi', manifest_xml='b.xml', group='platform')
        paths_a = git_service._cache_paths(self.project, spec_a)
        paths_b = git_service._cache_paths(self.project, spec_b)

        self.assertNotEqual(paths_a['root'], paths_b['root'])
        self.assertNotEqual(paths_a['repo'], paths_b['repo'])

    @override_settings(DEEPAUDIT_REPO_CACHE_ENABLED=True)
    def test_create_repository_workspace_multi_copies_cache_without_clone_or_worktree(self) -> None:
        repo_spec = self._repo_spec(repository_type='multi', manifest_xml='default.xml', group='platform')
        cache_repo = self.temp_root / 'repo-cache' / 'workspace'
        cache_repo.mkdir(parents=True, exist_ok=True)
        (cache_repo / 'manifest.xml').write_text('<manifest />\n', encoding='utf-8')

        with (
            patch('apps.deepaudit.git_service.ensure_repository_cache', return_value=cache_repo),
            patch('apps.deepaudit.git_service.clone_repository', side_effect=AssertionError('should not git clone')),
            patch('apps.deepaudit.git_service.subprocess.run', side_effect=AssertionError('should not use git worktree')),
        ):
            workspace = git_service.create_repository_workspace(
                self.project,
                repo_spec['repository_url'],
                repo_spec['branch_name'],
                {'other_config': {}},
                repository_spec=repo_spec,
            )

        self.assertTrue(workspace.exists())
        self.assertTrue((workspace / 'manifest.xml').exists())

    @override_settings(DEEPAUDIT_REPO_CACHE_ENABLED=True)
    def test_create_repository_workspace_multi_keeps_partial_sync_without_single_repo_fallback(self) -> None:
        repo_spec = self._repo_spec(repository_type='multi', manifest_xml='default.xml', group='platform')
        commands: list[list[str]] = []

        def fake_run(cmd, **_kwargs):
            commands.append(cmd)
            if cmd[:3] == ['git', 'mm', 'init']:
                return SimpleNamespace(stdout='init ok', stderr='', returncode=0)
            if cmd == ['git', 'mm', 'sync']:
                return SimpleNamespace(stdout='partial sync', stderr='permission denied on child repo', returncode=23)
            raise AssertionError(f'unexpected command: {cmd}')

        with patch('apps.deepaudit.git_service.subprocess.run', side_effect=fake_run):
            workspace = git_service.create_repository_workspace(
                self.project,
                repo_spec['repository_url'],
                repo_spec['branch_name'],
                {'other_config': {}},
                repository_spec=repo_spec,
            )

        self.assertTrue(workspace.exists())
        self.assertTrue(any(cmd[:3] == ['git', 'mm', 'init'] for cmd in commands))
        self.assertTrue(any(cmd == ['git', 'mm', 'sync'] for cmd in commands))
        self.assertFalse(any(cmd[0] == 'git' and 'clone' in cmd for cmd in commands))
        self.assertFalse(any(cmd[:3] == ['git', '-C', str(workspace)] and 'worktree' in cmd for cmd in commands))

    def test_git_command_logs_are_sanitized(self) -> None:
        target_path = self.temp_root / 'workspace'
        token = 'super-secret-token'

        def fake_run(cmd, **_kwargs):
            return SimpleNamespace(stdout=f'Cloning from https://oauth2:{token}@example.com/repo.git', stderr='', returncode=0)

        with (
            patch('apps.deepaudit.git_service.subprocess.run', side_effect=fake_run),
            self.assertLogs('apps.deepaudit.git_service', level='INFO') as captured,
        ):
            git_service.clone_repository(
                self.project,
                'https://example.com/repo.git',
                'main',
                {'other_config': {'codehub_token': token}},
                target_path=target_path,
            )

        joined = '\n'.join(captured.output)
        self.assertNotIn(token, joined)
        self.assertIn('https://example.com/repo.git', joined)
