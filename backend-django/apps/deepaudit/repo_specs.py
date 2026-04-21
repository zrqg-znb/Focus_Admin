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
    branch_name: Any = None,
    manifest_xml: Any = None,
    group: Any = None,
) -> dict[str, str]:
    default_branch = getattr(project, 'default_branch', 'main')
    default_manifest = getattr(project, 'manifest_xml', '')
    default_group = getattr(project, 'group', '')
    branch_override = normalize_repo_override(branch_name)
    manifest_override = normalize_repo_override(manifest_xml)
    group_override = normalize_repo_override(group)
    return build_repository_spec(
        getattr(project, 'repository_url', ''),
        branch_override if branch_override is not None else default_branch,
        repository_type=getattr(project, 'repository_type', REPOSITORY_TYPE_SINGLE),
        manifest_xml=manifest_override if manifest_override is not None else default_manifest,
        group=group_override if group_override is not None else default_group,
    )


def repository_spec_cache_key(spec: dict[str, Any]) -> str:
    payload = {
        'repository_type': normalize_repository_type(spec.get('repository_type')),
        'repository_url': normalize_repo_text(spec.get('repository_url')),
        'branch_name': normalize_repo_text(spec.get('branch_name'), default='main'),
        'manifest_xml': normalize_optional_repo_text(spec.get('manifest_xml')),
        'group': normalize_optional_repo_text(spec.get('group')),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(serialized.encode('utf-8')).hexdigest()[:16]


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
