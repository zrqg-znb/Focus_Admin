from __future__ import annotations

import json
import logging
import subprocess
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.db.models import QuerySet
from ninja.errors import HttpError

from apps.deepaudit import storage as deepaudit_storage
from apps.deepaudit.git_service import GitServiceError, create_repository_workspace
from apps.deepaudit.heuristics import build_summary, is_text_file, scan_content, should_exclude
from apps.deepaudit.user_config.user_config_model import AuditSshCredential, AuditUserConfig
from apps.deepaudit.encryption import decrypt_value

logger = logging.getLogger(__name__)

TEST_PATH_MARKERS = ('/test/', '/tests/', '.spec.', '.test.', '/__tests__/')
DOC_PATH_MARKERS = ('/docs/', '/doc/', '/examples/')
DOC_SUFFIXES = {'.md', '.rst', '.txt'}


def _normalize_path(path: str) -> str:
    return str(path or '').replace('\\', '/').lstrip('./')


@lru_cache(maxsize=1)
def docker_available() -> bool:
    if not getattr(settings, 'DEEPAUDIT_DOCKER_ENABLED', True):
        return False
    try:
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False


def load_user_config_payload(user_id: str) -> dict:
    config = AuditUserConfig.objects.filter(user_id=user_id, is_deleted=False).first()
    payload = {
        'llm_config': {},
        'other_config': {},
    }
    if not config:
        return payload
    llm_config = dict(config.llm_config or {})
    other_config = dict(config.other_config or {})
    if llm_config.get('api_key'):
        llm_config['api_key'] = decrypt_value(llm_config['api_key'])
    for key in ('github_token', 'gitlab_token', 'gitea_token'):
        if other_config.get(key):
            other_config[key] = decrypt_value(other_config[key])
    embedding_config = dict(other_config.get('embedding_config') or {})
    if embedding_config.get('api_key'):
        embedding_config['api_key'] = decrypt_value(embedding_config['api_key'])
    other_config['embedding_config'] = embedding_config
    return {
        'llm_config': llm_config,
        'other_config': other_config,
    }


def load_ssh_private_key(user_id: str) -> str | None:
    credential = AuditSshCredential.objects.filter(user_id=user_id, is_deleted=False).first()
    if not credential or not credential.private_key_encrypted:
        return None
    return decrypt_value(credential.private_key_encrypted)


def prepare_workspace(
    project,
    *,
    branch_name: str | None = None,
    user_id: str | None = None,
    allow_stale_on_failure: bool = False,
) -> tuple[Path, dict]:
    user_payload = load_user_config_payload(user_id or getattr(project.owner, 'id', '') or '')
    if project.source_type == 'repository':
        try:
            workspace = create_repository_workspace(
                project,
                project.repository_url or '',
                branch_name or project.default_branch,
                user_payload,
                ssh_private_key=load_ssh_private_key(user_id or str(project.owner_id)),
                allow_stale_on_failure=allow_stale_on_failure,
            )
        except GitServiceError as exc:
            raise HttpError(400, str(exc)) from exc
        return workspace, user_payload

    zip_path = deepaudit_storage.get_project_zip(project.id)
    if not zip_path or not zip_path.exists():
        raise HttpError(400, '当前 ZIP 项目尚未上传压缩包')

    workspace = deepaudit_storage.create_workspace(f'zip-{project.id}')
    with zipfile.ZipFile(zip_path, 'r') as archive:
        archive.extractall(workspace)
    return workspace, user_payload


def list_project_files(
    workspace: Path,
    *,
    exclude_patterns: Iterable[str] | None = None,
    file_paths: Iterable[str] | None = None,
    include_tests: bool = False,
    include_docs: bool = False,
    max_file_size: int | None = None,
) -> list[dict]:
    normalized_targets = {
        _normalize_path(item)
        for item in (file_paths or [])
        if str(item or '').strip()
    }
    max_bytes = int(max_file_size or 0)
    items: list[dict] = []
    for file_path in deepaudit_storage.iter_text_files(workspace):
        relative_path = _normalize_path(str(file_path.relative_to(workspace)))
        if normalized_targets and relative_path not in normalized_targets:
            continue
        if not is_text_file(relative_path):
            continue
        if should_exclude(relative_path, exclude_patterns):
            continue
        if not include_tests and any(marker in f'/{relative_path.lower()}' for marker in TEST_PATH_MARKERS):
            continue
        suffix = file_path.suffix.lower()
        if not include_docs and (suffix in DOC_SUFFIXES or any(marker in f'/{relative_path.lower()}' for marker in DOC_PATH_MARKERS)):
            continue
        if max_bytes and file_path.stat().st_size > max_bytes:
            continue
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        items.append(
            {
                'path': relative_path,
                'size': file_path.stat().st_size,
                'content': content,
                'lines': max(1, content.count('\n') + 1),
            }
        )
    items.sort(key=lambda item: item['path'])
    return items


def run_heuristic_scan(
    workspace: Path,
    *,
    exclude_patterns: Iterable[str] | None = None,
    file_paths: Iterable[str] | None = None,
    include_tests: bool = False,
    include_docs: bool = False,
    max_file_size: int | None = None,
    target_vulnerabilities: Iterable[str] | None = None,
    rule_patterns=None,
    prompt_context: dict | None = None,
    analysis_depth: str = 'standard',
    severity_weights: dict | None = None,
) -> dict:
    files = list_project_files(
        workspace,
        exclude_patterns=exclude_patterns,
        file_paths=file_paths,
        include_tests=include_tests,
        include_docs=include_docs,
        max_file_size=max_file_size,
    )
    all_issues: list[dict] = []
    total_lines = 0
    for item in files:
        total_lines += item['lines']
        all_issues.extend(
            scan_content(
                item['content'],
                item['path'],
                target_vulnerabilities=target_vulnerabilities,
                rule_patterns=rule_patterns,
                prompt_context=prompt_context,
                analysis_depth=analysis_depth,
            )
        )
    summary = build_summary(
        all_issues,
        total_lines,
        len(files),
        severity_weights=severity_weights,
        analysis_depth=analysis_depth,
        prompt_context=prompt_context,
        rule_patterns=rule_patterns,
    )
    return {
        'files': files,
        'issues': all_issues,
        'summary': summary,
        'total_files': len(files),
        'total_lines': total_lines,
    }


def cleanup_runtime_workspace(workspace: Path | None) -> None:
    if not workspace or not workspace.exists():
        return

    git_metadata = workspace / '.git'
    if git_metadata.is_file():
        try:
            common_dir = subprocess.run(
                ['git', '-C', str(workspace), 'rev-parse', '--git-common-dir'],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout.strip()
            if common_dir:
                subprocess.run(
                    ['git', f'--git-dir={common_dir}', 'worktree', 'remove', '--force', str(workspace)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                subprocess.run(
                    ['git', f'--git-dir={common_dir}', 'worktree', 'prune'],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return
        except Exception as exc:
            logger.warning('DeepAudit failed to remove git worktree %s cleanly: %s', workspace, exc)

    deepaudit_storage.cleanup_workspace(workspace)


def load_rule_export(rule_set) -> dict:
    return {
        'id': str(rule_set.id),
        'name': rule_set.name,
        'description': rule_set.description,
        'language': rule_set.language,
        'rule_type': rule_set.rule_type,
        'severity_weights': rule_set.severity_weights or {},
        'is_default': rule_set.is_default,
        'is_system': rule_set.is_system,
        'is_active': rule_set.is_active,
        'rules': [
            {
                'id': str(rule.id),
                'rule_code': rule.rule_code,
                'name': rule.name,
                'description': rule.description,
                'category': rule.category,
                'severity': rule.severity,
                'custom_prompt': rule.custom_prompt,
                'fix_suggestion': rule.fix_suggestion,
                'reference_url': rule.reference_url,
                'enabled': rule.enabled,
            }
            for rule in rule_set.rules.filter(is_deleted=False).order_by('sort', 'rule_code')
        ],
    }
