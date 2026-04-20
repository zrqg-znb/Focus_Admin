import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterable

from django.conf import settings

from apps.deepaudit.serialization import normalize_json_payload


DEEPAUDIT_ROOT = Path(settings.BASE_DIR) / 'media' / 'deepaudit'
PROJECTS_DIR = DEEPAUDIT_ROOT / 'projects'
ZIP_DIR = DEEPAUDIT_ROOT / 'zip'
WORKSPACE_DIR = DEEPAUDIT_ROOT / 'workspaces'
REPORTS_DIR = DEEPAUDIT_ROOT / 'reports'
ARTIFACTS_DIR = DEEPAUDIT_ROOT / 'artifacts'
VECTOR_DB_DIR = DEEPAUDIT_ROOT / 'vector_db'
SSH_DIR = DEEPAUDIT_ROOT / 'ssh'
KNOWLEDGE_DIR = DEEPAUDIT_ROOT / 'knowledge'
REPO_CACHE_DIR = DEEPAUDIT_ROOT / 'repo_cache'



def ensure_storage_dirs() -> None:
    for directory in [
        DEEPAUDIT_ROOT,
        PROJECTS_DIR,
        ZIP_DIR,
        WORKSPACE_DIR,
        REPORTS_DIR,
        ARTIFACTS_DIR,
        VECTOR_DB_DIR,
        SSH_DIR,
        KNOWLEDGE_DIR,
        REPO_CACHE_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)



def save_project_zip(project_id: str, file_name: str, file_bytes: bytes) -> Path:
    ensure_storage_dirs()
    suffix = Path(file_name or 'upload.zip').suffix or '.zip'
    target = ZIP_DIR / f'{project_id}{suffix}'
    target.write_bytes(file_bytes)
    return target



def get_project_zip(project_id: str) -> Path | None:
    ensure_storage_dirs()
    for item in ZIP_DIR.glob(f'{project_id}.*'):
        if item.is_file():
            return item
    return None



def delete_project_zip(project_id: str) -> bool:
    target = get_project_zip(project_id)
    if target and target.exists():
        target.unlink()
        return True
    return False



def create_workspace(prefix: str) -> Path:
    ensure_storage_dirs()
    return Path(tempfile.mkdtemp(prefix=f'{prefix}-', dir=str(WORKSPACE_DIR)))



def reserve_workspace_path(prefix: str) -> Path:
    path = create_workspace(prefix)
    shutil.rmtree(path, ignore_errors=True)
    return path



def cleanup_workspace(path: Path | None) -> None:
    if path and path.exists():
        shutil.rmtree(path, ignore_errors=True)



def save_report_file(file_name: str, payload: bytes) -> Path:
    ensure_storage_dirs()
    target = REPORTS_DIR / file_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target



def save_json_artifact(file_name: str, data: dict) -> Path:
    ensure_storage_dirs()
    target = ARTIFACTS_DIR / file_name
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_json_payload(data)
    target.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding='utf-8')
    return target



def get_project_repo_cache_root(project_id: str) -> Path:
    ensure_storage_dirs()
    target = REPO_CACHE_DIR / str(project_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def delete_project_repo_cache(project_id: str) -> bool:
    target = REPO_CACHE_DIR / str(project_id)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
        return True
    return False



def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob('*'):
        if path.is_file():
            yield path
