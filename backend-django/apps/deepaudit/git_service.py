from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import stat
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from django.conf import settings

from . import storage as deepaudit_storage

logger = logging.getLogger(__name__)


class GitServiceError(RuntimeError):
    pass


def repository_cache_enabled() -> bool:
    return bool(getattr(settings, 'DEEPAUDIT_REPO_CACHE_ENABLED', True))


def _git_clone_timeout() -> int:
    return max(1, int(getattr(settings, 'DEEPAUDIT_GIT_CLONE_TIMEOUT', 1800) or 1800))


def _git_ls_remote_timeout() -> int:
    return max(1, int(getattr(settings, 'DEEPAUDIT_GIT_LS_REMOTE_TIMEOUT', 120) or 120))


def _git_retry_count() -> int:
    return max(1, int(getattr(settings, 'DEEPAUDIT_GIT_RETRY_COUNT', 3) or 3))


def _repo_cache_ttl_seconds() -> int:
    return max(0, int(getattr(settings, 'DEEPAUDIT_REPO_CACHE_TTL_SECONDS', 1800) or 1800))


def _inject_token(repository_url: str, token: str) -> str:
    if not token or not repository_url.startswith(('http://', 'https://')):
        return repository_url
    parts = urlsplit(repository_url)
    safe_token = quote(token, safe='')
    netloc = f'oauth2:{safe_token}@{parts.hostname or ""}'
    if parts.port:
        netloc = f'{netloc}:{parts.port}'
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def build_clone_context(
    project,
    repository_url: str,
    branch_name: str,
    user_config: dict,
    ssh_private_key: str | None = None,
) -> tuple[str, dict[str, str]]:
    clone_url = repository_url
    env = os.environ.copy()
    env.setdefault('GIT_TERMINAL_PROMPT', '0')
    env.setdefault('GIT_LFS_SKIP_SMUDGE', '1')
    other_config = (user_config or {}).get('other_config', {}) if isinstance(user_config, dict) else {}
    repo_type = getattr(project, 'repository_type', 'other')

    token_map = {
        'github': other_config.get('github_token', ''),
        'gitlab': other_config.get('gitlab_token', ''),
        'gitea': other_config.get('gitea_token', ''),
    }
    token = token_map.get(repo_type) or ''
    clone_url = _inject_token(repository_url, token)

    if repository_url.startswith('git@') or repository_url.startswith('ssh://'):
        deepaudit_storage.ensure_storage_dirs()
        key_file = deepaudit_storage.SSH_DIR / f'{project.owner_id or project.id}_id_ed25519'
        if ssh_private_key:
            key_file.write_text(ssh_private_key, encoding='utf-8')
            key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            env['GIT_SSH_COMMAND'] = f'ssh -i {key_file} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
    env['DEEPAUDIT_BRANCH'] = branch_name or getattr(project, 'default_branch', 'main') or 'main'
    return clone_url, env


def _is_retryable_git_error(message: str) -> bool:
    error_text = (message or '').lower()
    retryable_markers = (
        'connection reset by peer',
        'recv failure',
        'operation timed out',
        'http/2 stream',
        'tls',
        'early eof',
        'empty reply from server',
        'network is unreachable',
        'failed to connect',
        'connection timed out',
    )
    return any(marker in error_text for marker in retryable_markers)


def _project_id(project) -> str:
    return str(getattr(project, 'id', '') or '')


def _branch_name(project, branch_name: str | None) -> str:
    return str(branch_name or getattr(project, 'default_branch', 'main') or 'main').strip() or 'main'


def _cache_branch_key(branch_name: str) -> str:
    branch = str(branch_name or 'main').strip() or 'main'
    safe_branch = ''.join(char if char.isalnum() or char in {'-', '_', '.'} else '_' for char in branch).strip('._') or 'branch'
    branch_hash = hashlib.sha1(branch.encode('utf-8')).hexdigest()[:12]
    return f'{safe_branch}-{branch_hash}'


def _cache_paths(project, branch_name: str) -> dict[str, Path]:
    cache_root = deepaudit_storage.get_project_repo_cache_root(_project_id(project)) / _cache_branch_key(branch_name)
    return {
        'root': cache_root,
        'repo': cache_root / 'repo',
        'state': cache_root / 'state.json',
        'lock': cache_root / 'refresh.lock',
    }


def _read_cache_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _write_cache_state(path: Path, *, branch_name: str, repository_url: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'branch_name': branch_name,
        'repository_url': repository_url,
        'last_synced_at': int(time.time()),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _cache_is_fresh(state: dict) -> bool:
    ttl_seconds = _repo_cache_ttl_seconds()
    if ttl_seconds <= 0:
        return False
    try:
        last_synced_at = int(state.get('last_synced_at') or 0)
    except (TypeError, ValueError):
        return False
    if last_synced_at <= 0:
        return False
    return (time.time() - last_synced_at) <= ttl_seconds


def _cache_exists(cache_repo: Path) -> bool:
    return cache_repo.exists() and (cache_repo / '.git').exists()


def _compact_git_error(raw_message: str) -> str:
    lines = [line.strip() for line in str(raw_message or '').splitlines() if line.strip()]
    if not lines:
        return '未知 Git 错误'
    return lines[-1]


def _timeout_message(*, project, branch_name: str, operation: str, timeout: int) -> str:
    return (
        f'{operation} 超时（{timeout} 秒）：项目 {_project_id(project)} 分支 {branch_name}。'
        '仓库较大或网络较慢，请稍后重试并检查仓库连通性。'
    )


def _failure_message(*, project, branch_name: str, operation: str, raw_message: str) -> str:
    return f'{operation} 失败：项目 {_project_id(project)} 分支 {branch_name}。{_compact_git_error(raw_message)}'


def _log_retry(*, operation: str, project, branch_name: str, attempt: int, attempts: int, elapsed: float, message: str) -> None:
    logger.warning(
        'DeepAudit %s failed on attempt %s/%s for project %s branch %s after %.2fs: %s',
        operation,
        attempt,
        attempts,
        _project_id(project),
        branch_name,
        elapsed,
        message,
    )


def _run_git_command(
    cmd: list[str],
    *,
    env: dict[str, str],
    timeout: int,
    project,
    branch_name: str,
    operation: str,
    retry_count: int | None = None,
) -> subprocess.CompletedProcess[str]:
    attempts = max(1, int(retry_count or _git_retry_count()))
    last_error = ''
    for attempt in range(1, attempts + 1):
        started_at = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            logger.info(
                'DeepAudit %s succeeded for project %s branch %s in %.2fs (attempt %s/%s)',
                operation,
                _project_id(project),
                branch_name,
                time.monotonic() - started_at,
                attempt,
                attempts,
            )
            return result
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - started_at
            last_error = _timeout_message(project=project, branch_name=branch_name, operation=operation, timeout=timeout)
            _log_retry(
                operation=operation,
                project=project,
                branch_name=branch_name,
                attempt=attempt,
                attempts=attempts,
                elapsed=elapsed,
                message=last_error,
            )
            if attempt < attempts:
                time.sleep(attempt)
                continue
            raise GitServiceError(last_error) from exc
        except subprocess.CalledProcessError as exc:
            elapsed = time.monotonic() - started_at
            raw_error = exc.stderr or exc.stdout or str(exc)
            last_error = _failure_message(project=project, branch_name=branch_name, operation=operation, raw_message=raw_error)
            if attempt < attempts and _is_retryable_git_error(raw_error):
                _log_retry(
                    operation=operation,
                    project=project,
                    branch_name=branch_name,
                    attempt=attempt,
                    attempts=attempts,
                    elapsed=elapsed,
                    message=last_error,
                )
                time.sleep(attempt)
                continue
            raise GitServiceError(last_error) from exc
    raise GitServiceError(last_error or f'{operation} 失败')


def _scrub_origin_url(target_path: Path, repository_url: str, env: dict[str, str]) -> None:
    try:
        subprocess.run(
            ['git', '-C', str(target_path), 'remote', 'set-url', 'origin', repository_url],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
    except Exception as exc:
        logger.warning('DeepAudit failed to scrub cached origin URL for %s: %s', target_path, exc)


def clone_repository(
    project,
    repository_url: str,
    branch_name: str,
    user_config: dict,
    ssh_private_key: str | None = None,
    *,
    target_path: Path | None = None,
) -> Path:
    clone_url, env = build_clone_context(project, repository_url, branch_name, user_config, ssh_private_key)
    branch = _branch_name(project, branch_name)
    workspace = target_path or deepaudit_storage.create_workspace(f'project-{project.id}')
    workspace.parent.mkdir(parents=True, exist_ok=True)
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    cmd = [
        'git',
        '-c',
        'http.version=HTTP/1.1',
        'clone',
        '--depth',
        '1',
        '--single-branch',
        '--no-tags',
        '--branch',
        branch,
        clone_url,
        str(workspace),
    ]
    try:
        _run_git_command(
            cmd,
            env=env,
            timeout=_git_clone_timeout(),
            project=project,
            branch_name=branch,
            operation='仓库克隆',
        )
        if clone_url != repository_url:
            _scrub_origin_url(workspace, repository_url, env)
        return workspace
    except Exception:
        if target_path is None:
            shutil.rmtree(workspace, ignore_errors=True)
        else:
            shutil.rmtree(workspace, ignore_errors=True)
        raise


def _update_repository_cache(
    project,
    *,
    cache_repo: Path,
    repository_url: str,
    clone_url: str,
    branch_name: str,
    env: dict[str, str],
) -> None:
    fetch_cmd = [
        'git',
        '-C',
        str(cache_repo),
        '-c',
        'http.version=HTTP/1.1',
        '-c',
        f'remote.origin.url={clone_url}',
        'fetch',
        '--depth',
        '1',
        '--no-tags',
        'origin',
        branch_name,
    ]
    _run_git_command(
        fetch_cmd,
        env=env,
        timeout=_git_clone_timeout(),
        project=project,
        branch_name=branch_name,
        operation='仓库同步',
    )
    for operation, cmd in (
        (
            '仓库检出',
            ['git', '-C', str(cache_repo), 'checkout', '--force', '-B', branch_name, 'FETCH_HEAD'],
        ),
        (
            '仓库重置',
            ['git', '-C', str(cache_repo), 'reset', '--hard', 'FETCH_HEAD'],
        ),
        (
            '仓库清理',
            ['git', '-C', str(cache_repo), 'clean', '-ffd'],
        ),
    ):
        _run_git_command(
            cmd,
            env=env,
            timeout=120,
            project=project,
            branch_name=branch_name,
            operation=operation,
            retry_count=1,
        )
    if clone_url != repository_url:
        _scrub_origin_url(cache_repo, repository_url, env)


@contextmanager
def _repository_cache_lock(lock_path: Path):
    deepaudit_storage.ensure_storage_dirs()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    wait_timeout = max(_git_clone_timeout(), 30)
    stale_after = max(wait_timeout * 2, 120)
    deadline = time.monotonic() + wait_timeout

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump({'pid': os.getpid(), 'created_at': int(time.time())}, handle)
            break
        except FileExistsError:
            try:
                created_at = int(lock_path.stat().st_mtime)
            except OSError:
                created_at = 0
            if created_at and (time.time() - created_at) > stale_after:
                try:
                    lock_path.unlink()
                    logger.warning('DeepAudit removed stale repository cache lock: %s', lock_path)
                    continue
                except OSError:
                    pass
            if time.monotonic() >= deadline:
                raise GitServiceError(f'仓库缓存锁等待超时：项目目录 {lock_path.parent.name}。请稍后重试。')
            time.sleep(0.5)

    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except OSError:
            pass


def ensure_repository_cache(
    project,
    repository_url: str,
    branch_name: str,
    user_config: dict,
    ssh_private_key: str | None = None,
    *,
    allow_stale_on_failure: bool = False,
) -> Path:
    branch = _branch_name(project, branch_name)
    cache_paths = _cache_paths(project, branch)
    clone_url, env = build_clone_context(project, repository_url, branch, user_config, ssh_private_key)
    cache_repo = cache_paths['repo']
    cache_root = cache_paths['root']
    initial_state = _read_cache_state(cache_paths['state'])
    initial_cache_exists = _cache_exists(cache_repo)
    if initial_cache_exists and _cache_is_fresh(initial_state):
        return cache_repo

    try:
        with _repository_cache_lock(cache_paths['lock']):
            state = _read_cache_state(cache_paths['state'])
            cache_exists = _cache_exists(cache_repo)
            if cache_exists and _cache_is_fresh(state):
                return cache_repo

            cache_root.mkdir(parents=True, exist_ok=True)
            if not cache_exists:
                clone_repository(
                    project,
                    repository_url,
                    branch,
                    user_config,
                    ssh_private_key=ssh_private_key,
                    target_path=cache_repo,
                )
            else:
                _update_repository_cache(
                    project,
                    cache_repo=cache_repo,
                    repository_url=repository_url,
                    clone_url=clone_url,
                    branch_name=branch,
                    env=env,
                )
            _write_cache_state(cache_paths['state'], branch_name=branch, repository_url=repository_url)
            return cache_repo
    except GitServiceError:
        if allow_stale_on_failure and initial_cache_exists:
            logger.warning(
                'DeepAudit using stale repository cache for project %s branch %s after refresh failure',
                _project_id(project),
                branch,
            )
            return cache_repo
        if not initial_cache_exists:
            shutil.rmtree(cache_root, ignore_errors=True)
        raise


def create_repository_workspace(
    project,
    repository_url: str,
    branch_name: str,
    user_config: dict,
    ssh_private_key: str | None = None,
    *,
    allow_stale_on_failure: bool = False,
) -> Path:
    if not repository_cache_enabled():
        return clone_repository(
            project,
            repository_url,
            branch_name,
            user_config,
            ssh_private_key=ssh_private_key,
        )

    branch = _branch_name(project, branch_name)
    cache_paths = _cache_paths(project, branch)
    clone_url, env = build_clone_context(project, repository_url, branch, user_config, ssh_private_key)

    try:
        with _repository_cache_lock(cache_paths['lock']):
            cache_repo = cache_paths['repo']
            state = _read_cache_state(cache_paths['state'])
            cache_exists = _cache_exists(cache_repo)

            if not cache_exists:
                cache_paths['root'].mkdir(parents=True, exist_ok=True)
                clone_repository(
                    project,
                    repository_url,
                    branch,
                    user_config,
                    ssh_private_key=ssh_private_key,
                    target_path=cache_repo,
                )
                _write_cache_state(cache_paths['state'], branch_name=branch, repository_url=repository_url)
            elif not _cache_is_fresh(state):
                try:
                    _update_repository_cache(
                        project,
                        cache_repo=cache_repo,
                        repository_url=repository_url,
                        clone_url=clone_url,
                        branch_name=branch,
                        env=env,
                    )
                    _write_cache_state(cache_paths['state'], branch_name=branch, repository_url=repository_url)
                except GitServiceError:
                    if not allow_stale_on_failure:
                        raise
                    logger.warning(
                        'DeepAudit using stale repository cache for workspace project %s branch %s after refresh failure',
                        _project_id(project),
                        branch,
                    )

            subprocess.run(
                ['git', '-C', str(cache_repo), 'worktree', 'prune'],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            workspace = deepaudit_storage.reserve_workspace_path(f'project-{project.id}')
            try:
                _run_git_command(
                    [
                        'git',
                        '-C',
                        str(cache_repo),
                        'worktree',
                        'add',
                        '--detach',
                        '--force',
                        str(workspace),
                        'HEAD',
                    ],
                    env=env,
                    timeout=120,
                    project=project,
                    branch_name=branch,
                    operation='工作区快照创建',
                    retry_count=1,
                )
                return workspace
            except Exception:
                shutil.rmtree(workspace, ignore_errors=True)
                raise
    except GitServiceError:
        if not cache_paths['repo'].exists():
            shutil.rmtree(cache_paths['root'], ignore_errors=True)
        raise


def list_repository_files(cache_repo: Path, *, exclude_patterns: list[str] | None = None) -> list[dict]:
    rows: list[dict] = []
    try:
        result = subprocess.run(
            ['git', '-C', str(cache_repo), 'ls-tree', '-r', '-l', '-z', '--full-tree', 'HEAD'],
            check=True,
            capture_output=True,
            timeout=30,
        )
        for entry in result.stdout.split(b'\0'):
            if not entry:
                continue
            header, _, raw_path = entry.partition(b'\t')
            if not raw_path:
                continue
            parts = header.decode('utf-8', errors='ignore').split()
            if len(parts) < 4 or parts[1] != 'blob':
                continue
            relative_path = raw_path.decode('utf-8', errors='ignore')
            if exclude_patterns and any(pattern and pattern in relative_path for pattern in exclude_patterns):
                continue
            try:
                size = int(parts[3])
            except (TypeError, ValueError):
                size = 0
            rows.append({'path': relative_path, 'size': size})
    except Exception as exc:
        logger.warning('DeepAudit falling back to filesystem file listing for %s: %s', cache_repo, exc)
        for path in cache_repo.rglob('*'):
            if not path.is_file():
                continue
            relative_path = str(path.relative_to(cache_repo)).replace('\\', '/')
            if relative_path == '.git' or relative_path.startswith('.git/'):
                continue
            if exclude_patterns and any(pattern and pattern in relative_path for pattern in exclude_patterns):
                continue
            rows.append({'path': relative_path, 'size': path.stat().st_size})

    rows.sort(key=lambda item: item['path'])
    return rows


def list_remote_branches(
    project,
    repository_url: str,
    user_config: dict,
    ssh_private_key: str | None = None,
) -> list[str]:
    branch_name = _branch_name(project, getattr(project, 'default_branch', 'main') or 'main')
    clone_url, env = build_clone_context(project, repository_url, branch_name, user_config, ssh_private_key)
    cmd = ['git', '-c', 'http.version=HTTP/1.1', 'ls-remote', '--heads', clone_url]
    result = _run_git_command(
        cmd,
        env=env,
        timeout=_git_ls_remote_timeout(),
        project=project,
        branch_name=branch_name,
        operation='远端分支查询',
    )
    branches: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip() or 'refs/heads/' not in line:
            continue
        branches.append(line.split('refs/heads/', 1)[1].strip())
    return branches
