from __future__ import annotations

import json
import logging
import os
import re
import shlex
import shutil
import stat
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlsplit, urlunsplit

from django.conf import settings

from . import storage as deepaudit_storage
from .heuristics import should_exclude
from .repo_specs import (
    build_repository_spec,
    format_repository_spec_for_log,
    is_multi_repository_type,
    normalize_repository_type,
    normalize_repo_override,
    repository_spec_cache_key,
    repository_spec_state,
    repository_spec_state_matches,
)

logger = logging.getLogger(__name__)

GitEventCallback = Callable[[str, str, dict[str, Any]], None]
GIT_OUTPUT_TAIL_LIMIT = 1200
GIT_TEXT_SCRUB_RE = re.compile(r'(https?://)([^/\s:@]+(?::[^@\s/]+)?@)')


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


def _sanitize_url_for_log(value: str) -> str:
    text = str(value or '').strip()
    if not text.startswith(('http://', 'https://')):
        return text
    parts = urlsplit(text)
    if not parts.username and '@' not in parts.netloc:
        return text
    netloc = parts.hostname or ''
    if parts.port:
        netloc = f'{netloc}:{parts.port}'
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _sanitize_text_for_log(value: Any) -> str:
    text = str(value or '')
    if not text:
        return ''
    return GIT_TEXT_SCRUB_RE.sub(r'\1***@', text)


def _sanitize_command_for_log(cmd: list[str]) -> str:
    return shlex.join([_sanitize_url_for_log(_sanitize_text_for_log(arg)) for arg in cmd])


def _summarize_process_output(value: Any, *, limit: int = GIT_OUTPUT_TAIL_LIMIT) -> str:
    text = _sanitize_text_for_log(value).strip()
    if not text:
        return ''
    if len(text) <= limit:
        return text
    return f'...[truncated {len(text) - limit} chars] {text[-limit:]}'


def _format_log_context(log_context: dict[str, Any] | None) -> str:
    if not log_context:
        return ''
    parts: list[str] = []
    for key in ('task_kind', 'task_id', 'user_id'):
        value = str(log_context.get(key) or '').strip()
        if value:
            parts.append(f'{key}={value}')
    return ' '.join(parts)


def _build_command_metadata(
    *,
    cmd: list[str],
    cwd: Path | None,
    attempt: int,
    attempts: int,
    exit_code: int | None = None,
    duration_ms: int | None = None,
    stdout_tail: str = '',
    stderr_tail: str = '',
    soft_failed: bool = False,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        'command': _sanitize_command_for_log(cmd),
        'cwd': str(cwd) if cwd else '',
        'attempt': attempt,
        'attempts': attempts,
        'soft_failed': bool(soft_failed),
    }
    if exit_code is not None:
        metadata['exit_code'] = int(exit_code)
    if duration_ms is not None:
        metadata['duration_ms'] = int(duration_ms)
    if stdout_tail:
        metadata['stdout_tail'] = stdout_tail
    if stderr_tail:
        metadata['stderr_tail'] = stderr_tail
    return metadata


def _emit_git_event(
    event_callback: GitEventCallback | None,
    level: str,
    message: str,
    metadata: dict[str, Any],
) -> None:
    if event_callback is None:
        return
    try:
        event_callback(level, message, metadata)
    except Exception as exc:
        logger.warning('DeepAudit failed to emit git progress event: %s', exc)


def _guard_single_repo_path_for_multi_spec(
    *,
    operation: str,
    project,
    repository_spec: dict[str, Any],
    log_context: dict[str, Any] | None = None,
    event_callback: GitEventCallback | None = None,
) -> None:
    if not is_multi_repository_type(repository_spec.get('repository_type')):
        return
    metadata = {
        'operation': operation,
        'repository_type': normalize_repository_type(repository_spec.get('repository_type')),
        'repository_url': str(repository_spec.get('repository_url') or '').strip(),
        'branch_name': str(repository_spec.get('branch_name') or '').strip(),
        'manifest_xml': str(repository_spec.get('manifest_xml') or '').strip(),
        'group': str(repository_spec.get('group') or '').strip(),
    }
    logger.warning(
        'DeepAudit detected multi-repo spec entering single-repo %s path and will abort: project=%s %s %s',
        operation,
        _project_id(project),
        format_repository_spec_for_log(repository_spec),
        _format_log_context(log_context),
    )
    _emit_git_event(
        event_callback,
        'warning',
        f'检测到多仓仓库误入单仓{operation}分支，已阻止回退到 git clone/worktree',
        metadata,
    )
    raise GitServiceError('多仓仓库初始化误入单仓执行分支，已中止执行')


def build_clone_context(
    project,
    repository_url: str,
    branch_name: str,
    user_config: dict,
    ssh_private_key: str | None = None,
    *,
    repository_type: str | None = None,
) -> tuple[str, dict[str, str]]:
    clone_url = repository_url
    env = os.environ.copy()
    env.setdefault('GIT_TERMINAL_PROMPT', '0')
    env.setdefault('GIT_LFS_SKIP_SMUDGE', '1')
    other_config = (user_config or {}).get('other_config', {}) if isinstance(user_config, dict) else {}
    repo_type = normalize_repository_type(repository_type or getattr(project, 'repository_type', 'single'))

    token = str(
        other_config.get('codehub_token')
        or other_config.get('github_token')
        or other_config.get('gitlab_token')
        or other_config.get('gitea_token')
        or ''
    ).strip()
    clone_url = _inject_token(repository_url, token)

    if repository_url.startswith('git@') or repository_url.startswith('ssh://'):
        deepaudit_storage.ensure_storage_dirs()
        key_file = deepaudit_storage.SSH_DIR / f'{project.owner_id or project.id}_id_ed25519'
        if ssh_private_key:
            key_file.write_text(ssh_private_key, encoding='utf-8')
            key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            env['GIT_SSH_COMMAND'] = f'ssh -i {key_file} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
    env['DEEPAUDIT_BRANCH'] = branch_name or getattr(project, 'default_branch', 'main') or 'main'
    env['DEEPAUDIT_REPOSITORY_TYPE'] = repo_type
    logger.debug(
        'DeepAudit clone context prepared for project=%s repository_type=%s branch=%s repository_url=%s has_ssh_command=%s',
        _project_id(project),
        repo_type,
        env['DEEPAUDIT_BRANCH'],
        _sanitize_url_for_log(repository_url),
        bool(env.get('GIT_SSH_COMMAND')),
    )
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


def _effective_repository_spec(
    project,
    repository_url: str,
    branch_name: str | None,
    *,
    repository_type: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
) -> dict[str, str]:
    branch_override = normalize_repo_override(branch_name)
    manifest_override = normalize_repo_override(manifest_xml)
    group_override = normalize_repo_override(group)
    return build_repository_spec(
        repository_url or getattr(project, 'repository_url', ''),
        branch_override if branch_override is not None else _branch_name(project, branch_name),
        repository_type=repository_type or getattr(project, 'repository_type', 'single'),
        manifest_xml=manifest_override if manifest_override is not None else getattr(project, 'manifest_xml', ''),
        group=group_override if group_override is not None else getattr(project, 'group', ''),
    )


def _resolved_repository_spec(
    project,
    repository_url: str,
    branch_name: str | None,
    *,
    repository_spec: dict[str, Any] | None = None,
    repository_type: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
) -> dict[str, str]:
    if repository_spec is not None:
        return build_repository_spec(
            repository_spec.get('repository_url'),
            repository_spec.get('branch_name'),
            repository_type=repository_spec.get('repository_type'),
            manifest_xml=repository_spec.get('manifest_xml'),
            group=repository_spec.get('group'),
        )
    return _effective_repository_spec(
        project,
        repository_url,
        branch_name,
        repository_type=repository_type,
        manifest_xml=manifest_xml,
        group=group,
    )


def _validate_repository_spec(repository_spec: dict[str, Any]) -> dict[str, str]:
    normalized = repository_spec_state(repository_spec)
    if not normalized['repository_url']:
        raise GitServiceError('仓库地址为空，无法初始化代码工作区')
    if is_multi_repository_type(normalized['repository_type']) and not normalized['manifest_xml']:
        raise GitServiceError('多仓仓库缺少 manifest_xml，无法执行 git mm init')
    return normalized


def _cache_paths(project, repository_spec: dict[str, Any]) -> dict[str, Path]:
    spec_key = repository_spec_cache_key(repository_spec)
    cache_root = deepaudit_storage.get_project_repo_cache_root(_project_id(project)) / spec_key
    repo_dir_name = 'workspace' if is_multi_repository_type(repository_spec.get('repository_type')) else 'repo'
    return {
        'root': cache_root,
        'repo': cache_root / repo_dir_name,
        'state': cache_root / 'state.json',
        'lock': cache_root / 'refresh.lock',
    }


def get_repository_cache_info(project, repository_spec: dict[str, Any]) -> dict[str, Any]:
    normalized_spec = _validate_repository_spec(repository_spec)
    cache_paths = _cache_paths(project, normalized_spec)
    state = _read_cache_state(cache_paths['state'])
    return {
        'cache_root': cache_paths['root'],
        'cache_repo': cache_paths['repo'],
        'state_path': cache_paths['state'],
        'cache_exists': _cache_exists(
            cache_paths['repo'],
            repository_type=normalized_spec['repository_type'],
        ),
        'last_synced_at': int(state.get('last_synced_at') or 0),
        'repository_spec': normalized_spec,
    }


def _read_cache_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _write_cache_state(path: Path, *, repository_spec: dict[str, Any], branch_name: str, repository_url: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'repository_spec': repository_spec_state(repository_spec),
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


def _cache_state_matches(state: dict, repository_spec: dict[str, Any]) -> bool:
    stored_spec = state.get('repository_spec') or state
    return repository_spec_state_matches(stored_spec, repository_spec)


def _cache_exists(cache_repo: Path, *, repository_type: str) -> bool:
    if not cache_repo.exists():
        return False
    if is_multi_repository_type(repository_type):
        try:
            return any(cache_repo.iterdir())
        except OSError:
            return False
    return (cache_repo / '.git').exists()


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


def _log_retry(
    *,
    operation: str,
    project,
    branch_name: str,
    attempt: int,
    attempts: int,
    elapsed: float,
    message: str,
    repository_spec: dict[str, Any] | None = None,
    log_context: dict[str, Any] | None = None,
    cwd: Path | None = None,
    cmd: list[str] | None = None,
) -> None:
    parts: list[str] = []
    if repository_spec is not None:
        parts.append(format_repository_spec_for_log(repository_spec))
    context_text = _format_log_context(log_context)
    if context_text:
        parts.append(context_text)
    if cwd is not None:
        parts.append(f'cwd={cwd}')
    if cmd:
        parts.append(f'command={_sanitize_command_for_log(cmd)}')
    logger.warning(
        'DeepAudit %s failed on attempt %s/%s for project %s branch %s after %.2fs: %s %s',
        operation,
        attempt,
        attempts,
        _project_id(project),
        branch_name,
        elapsed,
        message,
        ' '.join(parts).strip(),
    )


def _run_git_command(
    cmd: list[str],
    *,
    env: dict[str, str],
    timeout: int,
    project,
    branch_name: str,
    operation: str,
    cwd: Path | None = None,
    retry_count: int | None = None,
    repository_spec: dict[str, Any] | None = None,
    log_context: dict[str, Any] | None = None,
    event_callback: GitEventCallback | None = None,
    soft_fail: bool = False,
) -> subprocess.CompletedProcess[str]:
    attempts = max(1, int(retry_count or _git_retry_count()))
    last_error = ''
    command_text = _sanitize_command_for_log(cmd)
    spec_text = format_repository_spec_for_log(repository_spec) if repository_spec is not None else ''
    context_text = _format_log_context(log_context)
    for attempt in range(1, attempts + 1):
        started_at = time.monotonic()
        logger.info(
            'DeepAudit %s started for project %s branch %s attempt %s/%s: command=%s cwd=%s %s %s',
            operation,
            _project_id(project),
            branch_name,
            attempt,
            attempts,
            command_text,
            str(cwd) if cwd else '-',
            spec_text,
            context_text,
        )
        _emit_git_event(
            event_callback,
            'info',
            f'{operation}命令开始执行',
            _build_command_metadata(
                cmd=cmd,
                cwd=cwd,
                attempt=attempt,
                attempts=attempts,
            ),
        )
        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(cwd) if cwd else None,
            )
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            stdout_tail = _summarize_process_output(result.stdout)
            stderr_tail = _summarize_process_output(result.stderr)
            metadata = _build_command_metadata(
                cmd=cmd,
                cwd=cwd,
                attempt=attempt,
                attempts=attempts,
                exit_code=result.returncode,
                duration_ms=elapsed_ms,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                soft_failed=soft_fail and result.returncode != 0,
            )
            if result.returncode == 0:
                logger.info(
                    'DeepAudit %s succeeded for project %s branch %s in %.2fs: exit_code=%s command=%s cwd=%s stdout_tail=%s stderr_tail=%s %s %s',
                    operation,
                    _project_id(project),
                    branch_name,
                    elapsed_ms / 1000,
                    result.returncode,
                    command_text,
                    str(cwd) if cwd else '-',
                    stdout_tail or '-',
                    stderr_tail or '-',
                    spec_text,
                    context_text,
                )
                _emit_git_event(event_callback, 'info', f'{operation}命令执行完成', metadata)
                return result
            raw_error = result.stderr or result.stdout or f'command exited with {result.returncode}'
            last_error = _failure_message(project=project, branch_name=branch_name, operation=operation, raw_message=raw_error)
            if soft_fail:
                logger.warning(
                    'DeepAudit %s soft-failed for project %s branch %s in %.2fs and will continue: exit_code=%s command=%s cwd=%s stdout_tail=%s stderr_tail=%s %s %s',
                    operation,
                    _project_id(project),
                    branch_name,
                    elapsed_ms / 1000,
                    result.returncode,
                    command_text,
                    str(cwd) if cwd else '-',
                    stdout_tail or '-',
                    stderr_tail or '-',
                    spec_text,
                    context_text,
                )
                _emit_git_event(
                    event_callback,
                    'warning',
                    f'{operation}命令返回非 0，已按 warning 继续执行',
                    metadata,
                )
                return result
            if attempt < attempts and _is_retryable_git_error(raw_error):
                _log_retry(
                    operation=operation,
                    project=project,
                    branch_name=branch_name,
                    attempt=attempt,
                    attempts=attempts,
                    elapsed=elapsed_ms / 1000,
                    message=last_error,
                    repository_spec=repository_spec,
                    log_context=log_context,
                    cwd=cwd,
                    cmd=cmd,
                )
                _emit_git_event(event_callback, 'warning', f'{operation}命令执行失败，准备重试', metadata)
                time.sleep(attempt)
                continue
            logger.error(
                'DeepAudit %s failed for project %s branch %s in %.2fs: exit_code=%s command=%s cwd=%s stdout_tail=%s stderr_tail=%s %s %s',
                operation,
                _project_id(project),
                branch_name,
                elapsed_ms / 1000,
                result.returncode,
                command_text,
                str(cwd) if cwd else '-',
                stdout_tail or '-',
                stderr_tail or '-',
                spec_text,
                context_text,
            )
            _emit_git_event(event_callback, 'warning', f'{operation}命令执行失败', metadata)
            raise GitServiceError(last_error)
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
                repository_spec=repository_spec,
                log_context=log_context,
                cwd=cwd,
                cmd=cmd,
            )
            _emit_git_event(
                event_callback,
                'warning',
                f'{operation}命令执行超时',
                _build_command_metadata(
                    cmd=cmd,
                    cwd=cwd,
                    attempt=attempt,
                    attempts=attempts,
                    duration_ms=int(elapsed * 1000),
                ),
            )
            if attempt < attempts:
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
    repository_spec: dict[str, Any] | None = None,
    repository_type: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
    event_callback: GitEventCallback | None = None,
    log_context: dict[str, Any] | None = None,
) -> Path:
    repository_spec = _validate_repository_spec(_resolved_repository_spec(
        project,
        repository_url,
        branch_name,
        repository_spec=repository_spec,
        repository_type=repository_type,
        manifest_xml=manifest_xml,
        group=group,
    ))
    branch = repository_spec['branch_name']
    repo_type = repository_spec['repository_type']
    clone_url, env = build_clone_context(
        project,
        repository_spec['repository_url'],
        repository_spec['branch_name'],
        user_config,
        ssh_private_key,
        repository_type=repository_spec['repository_type'],
    )
    workspace = target_path or deepaudit_storage.create_workspace(f'project-{project.id}')
    workspace.parent.mkdir(parents=True, exist_ok=True)
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    logger.info(
        'DeepAudit starting repository initialization for project %s target=%s: %s',
        _project_id(project),
        workspace,
        format_repository_spec_for_log(repository_spec),
    )
    logger.debug(
        'DeepAudit clone_repository resolved workspace initialization: project=%s target=%s repository_type=%s',
        _project_id(project),
        workspace,
        repo_type,
    )
    try:
        if repo_type == 'multi':
            workspace.mkdir(parents=True, exist_ok=True)
            init_cmd = [
                'git',
                'mm',
                'init',
                '-u',
                clone_url,
                '-b',
                repository_spec['branch_name'],
                '-m',
                repository_spec['manifest_xml'],
            ]
            if repository_spec['group']:
                init_cmd.extend(['-g', repository_spec['group']])
            logger.info(
                'DeepAudit project %s will initialize multi-repo workspace via git mm init + git mm sync: target=%s %s',
                _project_id(project),
                workspace,
                format_repository_spec_for_log(repository_spec),
            )
            _run_git_command(
                init_cmd,
                env=env,
                timeout=_git_clone_timeout(),
                project=project,
                branch_name=branch,
                operation='多仓初始化',
                cwd=workspace,
                repository_spec=repository_spec,
                log_context=log_context,
                event_callback=event_callback,
            )
            _run_git_command(
                ['git', 'mm', 'sync'],
                env=env,
                timeout=_git_clone_timeout(),
                project=project,
                branch_name=branch,
                operation='多仓同步',
                cwd=workspace,
                retry_count=1,
                repository_spec=repository_spec,
                log_context=log_context,
                event_callback=event_callback,
                soft_fail=True,
            )
            if clone_url != repository_spec['repository_url']:
                _scrub_origin_url(workspace, repository_spec['repository_url'], env)
        else:
            _guard_single_repo_path_for_multi_spec(
                operation='克隆',
                project=project,
                repository_spec=repository_spec,
                log_context=log_context,
                event_callback=event_callback,
            )
            logger.info(
                'DeepAudit project %s will initialize single-repo workspace via git clone: target=%s %s',
                _project_id(project),
                workspace,
                format_repository_spec_for_log(repository_spec),
            )
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
            _run_git_command(
                cmd,
                env=env,
                timeout=_git_clone_timeout(),
                project=project,
                branch_name=branch,
                operation='仓库克隆',
                repository_spec=repository_spec,
                log_context=log_context,
                event_callback=event_callback,
            )
            if clone_url != repository_spec['repository_url']:
                _scrub_origin_url(workspace, repository_spec['repository_url'], env)
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
    repository_spec: dict[str, Any] | None = None,
    log_context: dict[str, Any] | None = None,
    event_callback: GitEventCallback | None = None,
) -> None:
    _guard_single_repo_path_for_multi_spec(
        operation='缓存刷新',
        project=project,
        repository_spec=repository_spec or {},
        log_context=log_context,
        event_callback=event_callback,
    )
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
        repository_spec=repository_spec,
        log_context=log_context,
        event_callback=event_callback,
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
            repository_spec=repository_spec,
            log_context=log_context,
            event_callback=event_callback,
        )
    if clone_url != repository_url:
        _scrub_origin_url(cache_repo, repository_url, env)


def _update_multi_repository_cache(
    project,
    *,
    cache_repo: Path,
    branch_name: str,
    env: dict[str, str],
    repository_spec: dict[str, Any] | None = None,
    log_context: dict[str, Any] | None = None,
    event_callback: GitEventCallback | None = None,
) -> None:
    logger.info(
        'DeepAudit refreshing multi-repo cache via git mm sync: project=%s cache_repo=%s %s %s',
        _project_id(project),
        cache_repo,
        format_repository_spec_for_log(repository_spec or {}),
        _format_log_context(log_context),
    )
    _run_git_command(
        ['git', 'mm', 'sync'],
        env=env,
        timeout=_git_clone_timeout(),
        project=project,
        branch_name=branch_name,
        operation='多仓缓存同步',
        cwd=cache_repo,
        retry_count=1,
        repository_spec=repository_spec,
        log_context=log_context,
        event_callback=event_callback,
        soft_fail=True,
    )


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
    repository_spec: dict[str, Any] | None = None,
    repository_type: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
    allow_stale_on_failure: bool = False,
    force_refresh: bool = False,
    force_multi_sync: bool = False,
    event_callback: GitEventCallback | None = None,
    log_context: dict[str, Any] | None = None,
) -> Path:
    repository_spec = _validate_repository_spec(_resolved_repository_spec(
        project,
        repository_url,
        branch_name,
        repository_spec=repository_spec,
        repository_type=repository_type,
        manifest_xml=manifest_xml,
        group=group,
    ))
    branch = repository_spec['branch_name']
    repo_type = repository_spec['repository_type']
    spec_key = repository_spec_cache_key(repository_spec)
    cache_paths = _cache_paths(project, repository_spec)
    cache_repo = cache_paths['repo']
    cache_root = cache_paths['root']
    clone_url, env = build_clone_context(
        project,
        repository_spec['repository_url'],
        repository_spec['branch_name'],
        user_config,
        ssh_private_key,
        repository_type=repository_spec['repository_type'],
    )
    cache_repo = cache_paths['repo']
    cache_root = cache_paths['root']
    initial_state = _read_cache_state(cache_paths['state'])
    initial_cache_exists = _cache_exists(cache_repo, repository_type=repo_type)
    should_force_refresh = bool(force_refresh or (repo_type == 'multi' and force_multi_sync))
    logger.debug(
        'DeepAudit repository cache state before refresh: project=%s spec_key=%s repo_path=%s exists=%s fresh=%s matches=%s force_refresh=%s force_multi_sync=%s',
        _project_id(project),
        spec_key,
        cache_repo,
        initial_cache_exists,
        _cache_is_fresh(initial_state),
        _cache_state_matches(initial_state, repository_spec),
        force_refresh,
        force_multi_sync,
    )
    if (
        not should_force_refresh
        and initial_cache_exists
        and _cache_is_fresh(initial_state)
        and _cache_state_matches(initial_state, repository_spec)
    ):
        logger.info(
            'DeepAudit repository cache hit for project %s spec_key=%s repo_path=%s %s',
            _project_id(project),
            spec_key,
            cache_repo,
            format_repository_spec_for_log(repository_spec),
        )
        return cache_repo

    try:
        with _repository_cache_lock(cache_paths['lock']):
            state = _read_cache_state(cache_paths['state'])
            cache_exists = _cache_exists(cache_repo, repository_type=repo_type)
            if (
                not should_force_refresh
                and cache_exists
                and _cache_is_fresh(state)
                and _cache_state_matches(state, repository_spec)
            ):
                logger.info(
                    'DeepAudit repository cache hit after lock acquisition for project %s spec_key=%s repo_path=%s %s',
                    _project_id(project),
                    spec_key,
                    cache_repo,
                    format_repository_spec_for_log(repository_spec),
                )
                return cache_repo

            cache_root.mkdir(parents=True, exist_ok=True)
            logger.info(
                'DeepAudit refreshing repository cache for project %s spec_key=%s repo_path=%s %s',
                _project_id(project),
                spec_key,
                cache_repo,
                format_repository_spec_for_log(repository_spec),
            )
            if repo_type == 'multi':
                state_matches = _cache_state_matches(state, repository_spec)
                if cache_exists and state_matches:
                    _update_multi_repository_cache(
                        project,
                        cache_repo=cache_repo,
                        branch_name=repository_spec['branch_name'],
                        env=env,
                        repository_spec=repository_spec,
                        log_context=log_context,
                        event_callback=event_callback,
                    )
                else:
                    refresh_target = cache_repo if not cache_exists else cache_root / f'refresh-{os.getpid()}-{int(time.time() * 1000)}'
                    if refresh_target.exists():
                        shutil.rmtree(refresh_target, ignore_errors=True)
                    backup_repo = None
                    try:
                        clone_repository(
                            project,
                            repository_spec['repository_url'],
                            repository_spec['branch_name'],
                            user_config,
                            ssh_private_key=ssh_private_key,
                            target_path=refresh_target,
                            repository_spec=repository_spec,
                            repository_type=repo_type,
                            manifest_xml=repository_spec['manifest_xml'],
                            group=repository_spec['group'],
                            event_callback=event_callback,
                            log_context=log_context,
                        )
                        if refresh_target != cache_repo:
                            backup_repo = cache_root / f'backup-{os.getpid()}-{int(time.time() * 1000)}'
                            if backup_repo.exists():
                                shutil.rmtree(backup_repo, ignore_errors=True)
                            if cache_repo.exists():
                                cache_repo.rename(backup_repo)
                            try:
                                refresh_target.rename(cache_repo)
                            except Exception:
                                if backup_repo.exists():
                                    backup_repo.rename(cache_repo)
                                raise
                    except Exception:
                        if refresh_target != cache_repo:
                            shutil.rmtree(refresh_target, ignore_errors=True)
                        if backup_repo and backup_repo.exists() and not cache_repo.exists():
                            try:
                                backup_repo.rename(cache_repo)
                            except Exception:
                                logger.warning('DeepAudit failed to restore multi-repo cache backup for %s', cache_repo)
                        if backup_repo and backup_repo.exists():
                            shutil.rmtree(backup_repo, ignore_errors=True)
                        raise
                    if backup_repo and backup_repo.exists():
                        shutil.rmtree(backup_repo, ignore_errors=True)
            elif not cache_exists:
                clone_repository(
                    project,
                    repository_spec['repository_url'],
                    repository_spec['branch_name'],
                    user_config,
                    ssh_private_key=ssh_private_key,
                    target_path=cache_repo,
                    repository_spec=repository_spec,
                    repository_type=repo_type,
                    manifest_xml=repository_spec['manifest_xml'],
                    group=repository_spec['group'],
                    event_callback=event_callback,
                    log_context=log_context,
                )
            else:
                _update_repository_cache(
                    project,
                    cache_repo=cache_repo,
                    repository_url=repository_spec['repository_url'],
                    clone_url=clone_url,
                    branch_name=repository_spec['branch_name'],
                    env=env,
                    repository_spec=repository_spec,
                    log_context=log_context,
                    event_callback=event_callback,
                )
            _write_cache_state(
                cache_paths['state'],
                repository_spec=repository_spec,
                branch_name=repository_spec['branch_name'],
                repository_url=repository_spec['repository_url'],
            )
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
    repository_spec: dict[str, Any] | None = None,
    repository_type: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
    allow_stale_on_failure: bool = False,
    force_refresh: bool = False,
    force_multi_sync: bool = False,
    event_callback: GitEventCallback | None = None,
    log_context: dict[str, Any] | None = None,
) -> Path:
    repository_spec = _validate_repository_spec(_resolved_repository_spec(
        project,
        repository_url,
        branch_name,
        repository_spec=repository_spec,
        repository_type=repository_type,
        manifest_xml=manifest_xml,
        group=group,
    ))
    branch = repository_spec['branch_name']
    repo_type = repository_spec['repository_type']
    if not repository_cache_enabled():
        return clone_repository(
            project,
            repository_spec['repository_url'],
            branch,
            user_config,
            ssh_private_key=ssh_private_key,
            repository_spec=repository_spec,
            repository_type=repository_type,
            manifest_xml=manifest_xml,
            group=group,
            event_callback=event_callback,
            log_context=log_context,
        )

    cache_repo = ensure_repository_cache(
        project,
        repository_spec['repository_url'],
        branch,
        user_config,
        ssh_private_key=ssh_private_key,
        repository_spec=repository_spec,
        repository_type=repo_type,
        manifest_xml=manifest_xml,
        group=group,
        allow_stale_on_failure=allow_stale_on_failure,
        force_refresh=force_refresh,
        force_multi_sync=force_multi_sync,
        event_callback=event_callback,
        log_context=log_context,
    )
    cache_paths = _cache_paths(
        project,
        repository_spec,
    )
    _, env = build_clone_context(
        project,
        repository_spec['repository_url'],
        branch,
        user_config,
        ssh_private_key,
        repository_type=repo_type,
    )

    if repo_type == 'multi':
        workspace = deepaudit_storage.reserve_workspace_path(f'project-{project.id}')
        try:
            shutil.copytree(cache_repo, workspace, dirs_exist_ok=True)
            logger.info(
                'DeepAudit created workspace by copying multi-repo cache: project=%s cache_repo=%s workspace=%s %s',
                _project_id(project),
                cache_repo,
                workspace,
                format_repository_spec_for_log(repository_spec),
            )
            _emit_git_event(
                event_callback,
                'info',
                '代码工作区准备完成',
                {
                    'workspace': str(workspace),
                    'cache_repo': str(cache_repo),
                    'workspace_source': 'copied from multi-repo cache',
                    'repository_type': repo_type,
                },
            )
            return workspace
        except Exception:
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    try:
        _guard_single_repo_path_for_multi_spec(
            operation='工作区创建',
            project=project,
            repository_spec=repository_spec,
            log_context=log_context,
            event_callback=event_callback,
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
            logger.info(
                'DeepAudit creating git worktree workspace from single-repo cache: project=%s cache_repo=%s workspace=%s %s',
                _project_id(project),
                cache_repo,
                workspace,
                format_repository_spec_for_log(repository_spec),
            )
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
                repository_spec=repository_spec,
                log_context=log_context,
                event_callback=event_callback,
            )
            _emit_git_event(
                event_callback,
                'info',
                '代码工作区准备完成',
                {
                    'workspace': str(workspace),
                    'cache_repo': str(cache_repo),
                    'workspace_source': 'git worktree from single-repo cache',
                    'repository_type': repo_type,
                },
            )
            return workspace
        except Exception:
            shutil.rmtree(workspace, ignore_errors=True)
            raise
    except GitServiceError:
        if not cache_paths['repo'].exists():
            shutil.rmtree(cache_paths['root'], ignore_errors=True)
        raise


def list_repository_files(
    cache_repo: Path,
    *,
    exclude_patterns: list[str] | None = None,
    repository_type: str | None = None,
) -> list[dict]:
    rows: list[dict] = []
    repo_type = normalize_repository_type(repository_type or 'single')
    try:
        if repo_type != 'multi' and (cache_repo / '.git').exists():
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
                if should_exclude(relative_path, exclude_patterns):
                    continue
                try:
                    size = int(parts[3])
                except (TypeError, ValueError):
                    size = 0
                rows.append({'path': relative_path, 'size': size})
        else:
            for path in cache_repo.rglob('*'):
                if not path.is_file():
                    continue
                relative_path = str(path.relative_to(cache_repo)).replace('\\', '/')
                if should_exclude(relative_path, exclude_patterns):
                    continue
                rows.append({'path': relative_path, 'size': path.stat().st_size})
    except Exception as exc:
        logger.warning('DeepAudit falling back to filesystem file listing for %s: %s', cache_repo, exc)
        for path in cache_repo.rglob('*'):
            if not path.is_file():
                continue
            relative_path = str(path.relative_to(cache_repo)).replace('\\', '/')
            if should_exclude(relative_path, exclude_patterns):
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
