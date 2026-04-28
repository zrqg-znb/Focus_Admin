from __future__ import annotations

import hashlib
import json
from typing import Any

from apps.deepaudit.constants import (
    REPOSITORY_TYPE_MULTI,
    REPOSITORY_TYPE_SINGLE,
)


LEGACY_REPOSITORY_TYPES = {'github', 'gitlab', 'gitea', 'other'}


def normalize_repository_type(value: Any) -> str:
    raw = str(value or REPOSITORY_TYPE_SINGLE).strip().lower()
    if raw in {REPOSITORY_TYPE_SINGLE, REPOSITORY_TYPE_MULTI}:
        return raw
    if raw in LEGACY_REPOSITORY_TYPES:
        return REPOSITORY_TYPE_SINGLE
    return REPOSITORY_TYPE_SINGLE


def is_multi_repository_type(value: Any) -> bool:
    return normalize_repository_type(value) == REPOSITORY_TYPE_MULTI


def normalize_repo_text(value: Any, *, default: str = '') -> str:
    return str(value or '').strip() or default


def normalize_optional_repo_text(value: Any) -> str:
    return str(value or '').strip()


def normalize_repo_override(value: Any) -> str | None:
    text = str(value or '').strip()
    return text or None


def build_repository_spec(
    repository_url: Any,
    branch_name: Any,
    *,
    repository_type: Any = REPOSITORY_TYPE_SINGLE,
    manifest_xml: Any = '',
    group: Any = '',
) -> dict[str, str]:
    return {
        'repository_type': normalize_repository_type(repository_type),
        'repository_url': normalize_repo_text(repository_url),
        'branch_name': normalize_repo_text(branch_name, default='main'),
        'manifest_xml': normalize_optional_repo_text(manifest_xml),
        'group': normalize_optional_repo_text(group),
    }


def build_effective_project_repository_spec(
    project,
    *,
    repository_url: Any = None,
    repository_type: Any = None,
    branch_name: Any = None,
    manifest_xml: Any = None,
    group: Any = None,
) -> dict[str, str]:
    default_repository_url = getattr(project, 'repository_url', '')
    default_repository_type = getattr(project, 'repository_type', REPOSITORY_TYPE_SINGLE)
    default_branch = getattr(project, 'default_branch', 'main')
    default_manifest = getattr(project, 'manifest_xml', '')
    default_group = getattr(project, 'group', '')
    repository_url_override = normalize_repo_override(repository_url)
    branch_override = normalize_repo_override(branch_name)
    manifest_override = normalize_repo_override(manifest_xml)
    group_override = normalize_repo_override(group)
    return build_repository_spec(
        repository_url_override if repository_url_override is not None else default_repository_url,
        branch_override if branch_override is not None else default_branch,
        repository_type=repository_type if repository_type is not None else default_repository_type,
        manifest_xml=manifest_override if manifest_override is not None else default_manifest,
        group=group_override if group_override is not None else default_group,
    )


def build_locked_project_repository_spec(
    project,
    *,
    branch_name: Any = None,
    manifest_xml: Any = None,
    group: Any = None,
) -> dict[str, str]:
    current_project_spec = build_effective_project_repository_spec(project)
    return build_effective_project_repository_spec(
        project,
        repository_url=current_project_spec['repository_url'],
        repository_type=current_project_spec['repository_type'],
        branch_name=branch_name,
        manifest_xml=manifest_xml,
        group=group,
    )


def build_project_repository_binding(
    project,
    *,
    branch_name: Any = None,
    manifest_xml: Any = None,
    group: Any = None,
) -> dict[str, dict[str, str] | str]:
    project_repository_spec = build_effective_project_repository_spec(project)
    repository_spec = build_locked_project_repository_spec(
        project,
        branch_name=branch_name,
        manifest_xml=manifest_xml,
        group=group,
    )
    return {
        'project_repository_spec': project_repository_spec,
        'repository_spec': repository_spec,
        'project_repository_signature': repository_spec_signature(project_repository_spec),
        'repository_signature': repository_spec_signature(repository_spec),
    }


def build_task_repository_spec(task, *, fallback_project=None) -> dict[str, str]:
    project = fallback_project or getattr(task, 'project', None)
    if project is not None:
        return build_effective_project_repository_spec(
            project,
            repository_url=getattr(task, 'repository_url', None),
            repository_type=getattr(task, 'repository_type', None),
            branch_name=getattr(task, 'branch_name', None),
            manifest_xml=getattr(task, 'manifest_xml', None),
            group=getattr(task, 'group', None),
        )
    return build_repository_spec(
        getattr(task, 'repository_url', ''),
        getattr(task, 'branch_name', ''),
        repository_type=getattr(task, 'repository_type', REPOSITORY_TYPE_SINGLE),
        manifest_xml=getattr(task, 'manifest_xml', ''),
        group=getattr(task, 'group', ''),
    )


def build_task_repository_binding(task, *, fallback_project=None) -> dict[str, dict[str, str] | str]:
    project = fallback_project or getattr(task, 'project', None)
    repository_spec = build_task_repository_spec(task, fallback_project=project)
    project_repository_spec = (
        build_effective_project_repository_spec(project)
        if project is not None
        else repository_spec
    )
    return {
        'project_repository_spec': project_repository_spec,
        'repository_spec': repository_spec,
        'project_repository_signature': repository_spec_signature(project_repository_spec),
        'repository_signature': repository_spec_signature(repository_spec),
    }


def format_repository_spec_for_log(spec: dict[str, Any]) -> str:
    normalized = repository_spec_state(spec)
    return ' '.join(
        [
            f"repository_type={normalized.get('repository_type') or REPOSITORY_TYPE_SINGLE}",
            f"repository_url={normalized.get('repository_url') or '-'}",
            f"branch={normalized.get('branch_name') or 'main'}",
            f"manifest_xml={normalized.get('manifest_xml') or '-'}",
            f"group={normalized.get('group') or '-'}",
            f"repository_signature={repository_spec_signature(normalized)}",
        ]
    )


def validate_repository_spec_for_execution(spec: dict[str, Any]) -> dict[str, str]:
    normalized = repository_spec_state(spec)
    if not normalized['repository_url']:
        raise ValueError('任务仓库快照缺少 repository_url，无法初始化代码工作区')
    if is_multi_repository_type(normalized['repository_type']) and not normalized['manifest_xml']:
        raise ValueError('多仓任务快照缺少 manifest_xml，无法执行 git mm init')
    return normalized


def repository_spec_signature(spec: dict[str, Any]) -> str:
    payload = {
        'repository_type': normalize_repository_type(spec.get('repository_type')),
        'repository_url': normalize_repo_text(spec.get('repository_url')),
        'branch_name': normalize_repo_text(spec.get('branch_name'), default='main'),
        'manifest_xml': normalize_optional_repo_text(spec.get('manifest_xml')),
        'group': normalize_optional_repo_text(spec.get('group')),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(serialized.encode('utf-8')).hexdigest()[:16]


def repository_spec_cache_key(spec: dict[str, Any]) -> str:
    return repository_spec_signature(spec)


def repository_spec_state(spec: dict[str, Any]) -> dict[str, str]:
    normalized = {
        'repository_type': normalize_repository_type(spec.get('repository_type')),
        'repository_url': normalize_repo_text(spec.get('repository_url')),
        'branch_name': normalize_repo_text(spec.get('branch_name'), default='main'),
        'manifest_xml': normalize_optional_repo_text(spec.get('manifest_xml')),
        'group': normalize_optional_repo_text(spec.get('group')),
    }
    return normalized


def repository_spec_state_matches(current: dict[str, Any], expected: dict[str, Any]) -> bool:
    current_state = repository_spec_state(current)
    expected_state = repository_spec_state(expected)
    return all(current_state.get(key) == expected_state.get(key) for key in expected_state)
