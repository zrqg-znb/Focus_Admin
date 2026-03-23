import os
import shutil
import stat
import subprocess
import time
import logging
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from .storage import SSH_DIR, create_workspace, ensure_storage_dirs

logger = logging.getLogger(__name__)


class GitServiceError(RuntimeError):
    pass



def _inject_token(repository_url: str, token: str) -> str:
    if not token or not repository_url.startswith(('http://', 'https://')):
        return repository_url
    parts = urlsplit(repository_url)
    safe_token = quote(token, safe='')
    netloc = f'oauth2:{safe_token}@{parts.hostname or ""}'
    if parts.port:
        netloc = f'{netloc}:{parts.port}'
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))



def build_clone_context(project, repository_url: str, branch_name: str, user_config: dict, ssh_private_key: str | None = None) -> tuple[str, dict[str, str]]:
    clone_url = repository_url
    env = os.environ.copy()
    env.setdefault('GIT_TERMINAL_PROMPT', '0')
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
        ensure_storage_dirs()
        key_file = SSH_DIR / f'{project.owner_id or project.id}_id_ed25519'
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
    )
    return any(marker in error_text for marker in retryable_markers)



def clone_repository(project, repository_url: str, branch_name: str, user_config: dict, ssh_private_key: str | None = None) -> Path:
    clone_url, env = build_clone_context(project, repository_url, branch_name, user_config, ssh_private_key)
    branch = branch_name or getattr(project, 'default_branch', 'main') or 'main'
    max_attempts = 3
    last_error = ''

    for attempt in range(1, max_attempts + 1):
        workspace = create_workspace(f'project-{project.id}')
        cmd = [
            'git',
            '-c',
            'http.version=HTTP/1.1',
            'clone',
            '--depth',
            '1',
            '--single-branch',
            '--branch',
            branch,
            clone_url,
            str(workspace),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300, env=env)
            return workspace
        except subprocess.CalledProcessError as exc:
            last_error = exc.stderr or exc.stdout or str(exc)
            shutil.rmtree(workspace, ignore_errors=True)
            if attempt < max_attempts and _is_retryable_git_error(last_error):
                logger.warning(
                    'DeepAudit git clone failed on attempt %s/%s for project %s, retrying: %s',
                    attempt,
                    max_attempts,
                    getattr(project, 'id', ''),
                    last_error.strip().splitlines()[-1] if last_error.strip() else last_error,
                )
                time.sleep(attempt)
                continue
            raise GitServiceError(last_error) from exc
        except Exception:
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    raise GitServiceError(last_error or 'git clone failed')



def list_remote_branches(project, repository_url: str, user_config: dict, ssh_private_key: str | None = None) -> list[str]:
    clone_url, env = build_clone_context(project, repository_url, getattr(project, 'default_branch', 'main') or 'main', user_config, ssh_private_key)
    cmd = ['git', 'ls-remote', '--heads', clone_url]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120, env=env)
    except subprocess.CalledProcessError as exc:
        raise GitServiceError(exc.stderr or exc.stdout or str(exc)) from exc
    branches: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip() or 'refs/heads/' not in line:
            continue
        branches.append(line.split('refs/heads/', 1)[1].strip())
    return branches
