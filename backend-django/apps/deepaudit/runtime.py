from __future__ import annotations

import json
import logging
import subprocess
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from django.conf import settings
from django.db.models import QuerySet
from ninja.errors import HttpError

from apps.deepaudit import storage as deepaudit_storage
from apps.deepaudit.git_service import GitEventCallback, GitServiceError, create_repository_workspace
from apps.deepaudit.heuristics import build_summary, is_text_file, scan_content, should_exclude
from apps.deepaudit.repo_specs import build_effective_project_repository_spec, format_repository_spec_for_log
from apps.deepaudit.user_config.user_config_model import AuditSshCredential, AuditUserConfig
from apps.deepaudit.encryption import decrypt_value

logger = logging.getLogger(__name__)

TEST_PATH_MARKERS = ('/test/', '/tests/', '.spec.', '.test.', '/__tests__/')
DOC_PATH_MARKERS = ('/docs/', '/doc/', '/examples/')
DOC_SUFFIXES = {'.md', '.rst', '.txt'}


def _normalize_path(path: str) -> str:
    return str(path or '').replace('\\', '/').lstrip('./')


def _normalize_selection_target(path: str) -> str:
    normalized = _normalize_path(path)
    return normalized.rstrip('/')


def _matches_selection_target(relative_path: str, target_files: set[str], target_directories: set[str]) -> bool:
    if relative_path in target_files:
        return True
    return any(relative_path.startswith(f'{directory}/') for directory in target_directories)


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
    for key in ('codehub_token', 'github_token', 'gitlab_token', 'gitea_token'):
        if other_config.get(key):
            other_config[key] = decrypt_value(other_config[key])
    if not other_config.get('codehub_token'):
        for legacy_key in ('github_token', 'gitlab_token', 'gitea_token'):
            if other_config.get(legacy_key):
                other_config['codehub_token'] = other_config[legacy_key]
                break
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


def prepare_repository_workspace(
    project,
    *,
    repository_spec: dict[str, str],
    user_id: str | None = None,
    user_payload: dict | None = None,
    ssh_private_key: str | None = None,
    allow_stale_on_failure: bool = False,
    force_refresh: bool = False,
    force_multi_sync: bool = False,
    event_callback: GitEventCallback | None = None,
    log_context: dict[str, Any] | None = None,
) -> tuple[Path, dict]:
    resolved_user_id = str(user_id or getattr(getattr(project, 'owner', None), 'id', '') or getattr(project, 'owner_id', '') or '')
    payload = user_payload or load_user_config_payload(resolved_user_id)
    resolved_ssh_key = ssh_private_key
    if resolved_ssh_key is None:
        resolved_ssh_key = load_ssh_private_key(resolved_user_id or str(project.owner_id))

    logger.info(
        'DeepAudit preparing repository workspace for project %s: %s %s',
        getattr(project, 'id', ''),
        format_repository_spec_for_log(repository_spec),
        ' '.join(
            [
                f'{key}={value}'
                for key, value in (log_context or {}).items()
                if str(value or '').strip()
            ]
        ),
    )
    if event_callback is not None:
        event_callback(
            'info',
            '开始准备代码工作区',
            {
                'repository_type': repository_spec.get('repository_type'),
                'repository_url': repository_spec.get('repository_url'),
                'branch_name': repository_spec.get('branch_name'),
                'manifest_xml': repository_spec.get('manifest_xml'),
                'group': repository_spec.get('group'),
            },
        )
    try:
        workspace = create_repository_workspace(
            project,
            repository_spec['repository_url'] or '',
            repository_spec['branch_name'],
            payload,
            ssh_private_key=resolved_ssh_key,
            allow_stale_on_failure=allow_stale_on_failure,
            manifest_xml=repository_spec['manifest_xml'],
            group=repository_spec['group'],
            repository_type=repository_spec['repository_type'],
            repository_spec=repository_spec,
            force_refresh=force_refresh,
            force_multi_sync=force_multi_sync,
            event_callback=event_callback,
            log_context=log_context,
        )
    except GitServiceError as exc:
        raise HttpError(400, str(exc)) from exc
    if event_callback is not None:
        event_callback(
            'info',
            '仓库工作区已准备完成',
            {
                'workspace': str(workspace),
                'repository_type': repository_spec.get('repository_type'),
                'repository_url': repository_spec.get('repository_url'),
                'branch_name': repository_spec.get('branch_name'),
            },
        )
    return workspace, payload


def prepare_workspace(
    project,
    *,
    branch_name: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
    user_id: str | None = None,
    allow_stale_on_failure: bool = False,
) -> tuple[Path, dict]:
    if project.source_type == 'repository':
        repository_spec = build_effective_project_repository_spec(
            project,
            branch_name=branch_name,
            manifest_xml=manifest_xml,
            group=group,
        )
        return prepare_repository_workspace(
            project,
            repository_spec=repository_spec,
            user_id=user_id,
            allow_stale_on_failure=allow_stale_on_failure,
        )

    zip_path = deepaudit_storage.get_project_zip(project.id)
    if not zip_path or not zip_path.exists():
        raise HttpError(400, '当前 ZIP 项目尚未上传压缩包')

    user_payload = load_user_config_payload(user_id or getattr(project.owner, 'id', '') or '')
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
        _normalize_selection_target(str(item or ''))
        for item in (file_paths or [])
        if str(item or '').strip()
    }
    target_files: set[str] = set()
    target_directories: set[str] = set()
    for target in normalized_targets:
        if not target:
            continue
        resolved_target = workspace / target
        if resolved_target.exists() and resolved_target.is_dir():
            target_directories.add(target)
        else:
            target_files.add(target)
    max_bytes = int(max_file_size or 0)
    items: list[dict] = []
    for file_path in deepaudit_storage.iter_text_files(workspace):
        relative_path = _normalize_path(str(file_path.relative_to(workspace)))
        if normalized_targets and not _matches_selection_target(relative_path, target_files, target_directories):
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


def validate_selected_file_paths(
    workspace: Path,
    *,
    file_paths: Iterable[str] | None = None,
) -> dict[str, list[str]]:
    normalized_targets: list[str] = []
    seen: set[str] = set()
    for item in (file_paths or []):
        normalized = _normalize_selection_target(str(item or ''))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_targets.append(normalized)

    if not normalized_targets:
        return {'existing': [], 'missing': []}

    existing: list[str] = []
    missing: list[str] = []
    for relative_path in normalized_targets:
        target = workspace / relative_path
        if target.exists() and (target.is_file() or target.is_dir()):
            existing.append(relative_path)
        else:
            missing.append(relative_path)
    return {'existing': existing, 'missing': missing}


def resolve_selected_file_paths(
    workspace: Path,
    *,
    exclude_patterns: Iterable[str] | None = None,
    file_paths: Iterable[str] | None = None,
    include_tests: bool = False,
    include_docs: bool = False,
    max_file_size: int | None = None,
) -> list[str]:
    normalized_targets = {
        _normalize_selection_target(str(item or ''))
        for item in (file_paths or [])
        if str(item or '').strip()
    }
    if not normalized_targets:
        return []

    target_files: set[str] = set()
    target_directories: set[str] = set()
    for target in normalized_targets:
        if not target:
            continue
        resolved_target = workspace / target
        if resolved_target.exists() and resolved_target.is_dir():
            target_directories.add(target)
        else:
            target_files.add(target)

    max_bytes = int(max_file_size or 0)
    matched_paths: list[str] = []
    for file_path in deepaudit_storage.iter_text_files(workspace):
        relative_path = _normalize_path(str(file_path.relative_to(workspace)))
        if not _matches_selection_target(relative_path, target_files, target_directories):
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
        matched_paths.append(relative_path)

    matched_paths.sort()
    return matched_paths


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
