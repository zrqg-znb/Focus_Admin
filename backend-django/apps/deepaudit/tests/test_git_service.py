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
            repository_type='other',
        )
        self.storage_patch = _storage_patch(self.temp_root)
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

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
        cache_paths = git_service._cache_paths(self.project, 'main')
        cache_paths['repo'].mkdir(parents=True, exist_ok=True)
        (cache_paths['repo'] / '.git').mkdir()
        cache_paths['state'].write_text(
            json.dumps({'last_synced_at': int(time.time()), 'branch_name': 'main'}),
            encoding='utf-8',
        )

        with patch('apps.deepaudit.git_service.subprocess.run', side_effect=AssertionError('should not refresh')):
            cache_repo = git_service.ensure_repository_cache(
                self.project,
                'https://example.com/repo.git',
                'main',
                {'other_config': {}},
            )

        self.assertEqual(cache_repo, cache_paths['repo'])

    @override_settings(DEEPAUDIT_REPO_CACHE_TTL_SECONDS=60)
    def test_ensure_repository_cache_refreshes_expired_cache(self) -> None:
        cache_paths = git_service._cache_paths(self.project, 'main')
        cache_paths['repo'].mkdir(parents=True, exist_ok=True)
        (cache_paths['repo'] / '.git').mkdir()
        cache_paths['state'].write_text(
            json.dumps({'last_synced_at': int(time.time()) - 3600, 'branch_name': 'main'}),
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
            )

        self.assertEqual(cache_repo, cache_paths['repo'])
        self.assertTrue(any('fetch' in command for command in commands))

    @override_settings(DEEPAUDIT_REPO_CACHE_TTL_SECONDS=60)
    def test_cache_refresh_lock_serializes_same_cache_path(self) -> None:
        cache_paths = git_service._cache_paths(self.project, 'main')
        cache_paths['repo'].mkdir(parents=True, exist_ok=True)
        (cache_paths['repo'] / '.git').mkdir()
        cache_paths['state'].write_text(
            json.dumps({'last_synced_at': int(time.time()) - 3600, 'branch_name': 'main'}),
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
