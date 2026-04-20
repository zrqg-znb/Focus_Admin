from __future__ import annotations

import asyncio
import hashlib
import json
import re
from pathlib import Path

from asgiref.sync import async_to_sync
from ninja.errors import HttpError

from apps.deepaudit.config_resolver import resolve_embedding_config
from apps.deepaudit.agent_engine.knowledge import knowledge_loader, security_knowledge_rag
from apps.deepaudit.agent_engine.knowledge.base import KnowledgeCategory
from apps.deepaudit.permissions import get_user_id, require_project_role
from apps.deepaudit.rag.embeddings import EmbeddingService
from apps.deepaudit.rag.indexer import CodeIndexer
from apps.deepaudit.rag.project_retriever import ProjectCodeRetriever
from apps.deepaudit.rag.retriever import CodeRetriever
from apps.deepaudit.runtime import cleanup_runtime_workspace, prepare_workspace
from apps.deepaudit.storage import VECTOR_DB_DIR, ensure_storage_dirs


ALLOWED_KNOWLEDGE_UPLOAD_SUFFIXES = {'.json', '.md', '.markdown', '.txt'}
CUSTOM_KNOWLEDGE_ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_-]*$')
RESERVED_KNOWLEDGE_PREFIXES = ('vuln_', 'vuln-', 'framework_', 'framework-')


def _normalize_scope(payload: dict | None = None) -> dict:
    data = dict(payload or {})
    return {
        'branch_name': str(data.get('branch_name') or '').strip() or None,
        'exclude_patterns': [str(item).strip() for item in (data.get('exclude_patterns') or []) if str(item).strip()],
        'target_files': [str(item).strip() for item in (data.get('target_files') or []) if str(item).strip()],
    }


def _build_collection_name(project_id: str, project_name: str, *, exclude_patterns: list[str], target_files: list[str]) -> str:
    base = str(project_id or project_name or 'workspace').strip() or 'workspace'
    base = re.sub(r'[^a-zA-Z0-9_]+', '_', base).strip('_').lower() or 'workspace'
    scope_seed = '||'.join(sorted(target_files)) or '__all__'
    exclude_seed = '||'.join(sorted(exclude_patterns))
    scope_hash = hashlib.sha1(f'{scope_seed}::{exclude_seed}'.encode('utf-8')).hexdigest()[:12]
    return f'deepaudit_{base}_{scope_hash}'


def _build_embedding_service(user_payload: dict) -> tuple[EmbeddingService, dict]:
    embedding_config = resolve_embedding_config(user_payload)
    return (
        EmbeddingService(
            provider=embedding_config.get('provider'),
            model=embedding_config.get('model'),
            api_key=embedding_config.get('api_key'),
            base_url=embedding_config.get('base_url'),
            dimension=embedding_config.get('dimensions'),
            user_config=user_payload,
        ),
        embedding_config,
    )


def _normalize_knowledge_category(value: str | None, *, default: str = KnowledgeCategory.BEST_PRACTICE.value) -> str:
    category_text = str(value or '').strip().lower()
    if not category_text:
        return default
    try:
        return KnowledgeCategory(category_text).value
    except ValueError as exc:
        raise HttpError(422, f'不支持的 category: {category_text}') from exc


def _normalize_text_list(values: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_items = values.replace('\n', ',').split(',')
    else:
        raw_items = values
    return [str(item).strip() for item in raw_items if str(item).strip()]


def _normalize_custom_knowledge_id(value: str | None) -> str:
    document_id = str(value or '').strip()
    if not document_id:
        raise HttpError(422, '知识条目必须显式填写模块 ID，不能再依赖标题自动生成')
    if not CUSTOM_KNOWLEDGE_ID_PATTERN.fullmatch(document_id):
        raise HttpError(422, '模块 ID 仅支持小写字母、数字、下划线和连字符，且必须以字母或数字开头')
    if document_id.startswith(RESERVED_KNOWLEDGE_PREFIXES):
        reserved = '、'.join(sorted(set(RESERVED_KNOWLEDGE_PREFIXES)))
        raise HttpError(422, f'模块 ID 不能使用内置知识前缀：{reserved}')
    return document_id


def _require_custom_knowledge_tags(tags: list[str]) -> list[str]:
    normalized_tags = _normalize_text_list(tags)
    if not normalized_tags:
        raise HttpError(422, '知识条目至少需要一个标签，便于筛选、检索和模块复用')
    return normalized_tags


def _infer_knowledge_maintenance_scope(document_id: str) -> str:
    lowered = str(document_id or '').strip().lower()
    if lowered.startswith('custom_'):
        return 'personal'
    if lowered.startswith('team_'):
        return 'team'
    if lowered.startswith('proj_'):
        return 'project'
    return 'custom'


def _ensure_custom_document_writable(user, document_id: str) -> dict | None:
    existing_document = security_knowledge_rag.get_document(document_id)
    if not existing_document:
        return None

    metadata = dict(existing_document.get('metadata') or {})
    source = str(metadata.get('source') or '').strip().lower() or 'builtin'
    if source != 'custom':
        raise HttpError(422, f'模块 ID `{document_id}` 已被内置知识占用，请更换 ID')

    current_user_id = str(get_user_id(user) or '').strip()
    owner_id = str(metadata.get('created_by_id') or '').strip()
    if owner_id and current_user_id and owner_id != current_user_id:
        raise HttpError(403, f'模块 ID `{document_id}` 已被其他用户占用，不能覆盖对方的自定义知识条目')
    return existing_document


def _require_rag_ready(embedding_config: dict) -> None:
    provider = str(embedding_config.get('provider') or 'openai').strip().lower()
    api_key = str(embedding_config.get('api_key') or '').strip()
    if provider != 'ollama' and not api_key:
        raise HttpError(
            400,
            f'当前未配置可用的 embedding API Key（provider={provider}, model={embedding_config.get("model") or "default"}）',
        )


async def _inspect_indexer(indexer: CodeIndexer) -> dict:
    await indexer.vector_store.initialize(force_recreate=False)
    metadata = indexer.vector_store.get_collection_metadata()
    embedding_config = indexer.vector_store.get_embedding_config()
    chunk_count = await indexer.vector_store.get_count()
    file_paths = await indexer.vector_store.get_all_file_paths()
    needs_rebuild, rebuild_reason = await indexer._check_rebuild_needed()
    return {
        'exists': chunk_count > 0,
        'index_version': metadata.get('index_version', ''),
        'chunk_count': chunk_count,
        'file_count': len(file_paths),
        'created_at': metadata.get('created_at', 0),
        'updated_at': metadata.get('updated_at', 0),
        'embedding_provider': embedding_config.get('provider', ''),
        'embedding_model': embedding_config.get('model', ''),
        'embedding_dimension': embedding_config.get('dimension', 0),
        'project_hash': metadata.get('project_hash', ''),
        'needs_rebuild': bool(needs_rebuild),
        'rebuild_reason': rebuild_reason or None,
    }


def get_project_rag_status(user, project_id: str, payload: dict | None = None) -> dict:
    access = require_project_role(user, project_id, min_role='viewer')
    scope = _normalize_scope(payload)
    collection_name = _build_collection_name(
        str(access.project.id),
        access.project.name,
        exclude_patterns=scope['exclude_patterns'],
        target_files=scope['target_files'],
    )
    ensure_storage_dirs()
    workspace = None
    try:
        workspace, user_payload = prepare_workspace(
            access.project,
            branch_name=scope['branch_name'] or access.project.default_branch,
            user_id=str(getattr(user, 'id', '') or ''),
            allow_stale_on_failure=True,
        )
        retriever = ProjectCodeRetriever(
            project_root=str(workspace),
            user_config=user_payload,
            project_id=str(access.project.id),
            project_name=access.project.name,
            exclude_patterns=scope['exclude_patterns'],
            target_files=scope['target_files'],
        )
        embedding_service, _embedding_config = _build_embedding_service(user_payload)
        indexer = CodeIndexer(
            collection_name=collection_name,
            embedding_service=embedding_service,
            persist_directory=str(VECTOR_DB_DIR),
        )
        status = async_to_sync(_inspect_indexer)(indexer)
        return {
            'collection_name': collection_name,
            **status,
            'unavailable_reason': retriever._embedding_unavailable_reason(),
        }
    finally:
        cleanup_runtime_workspace(workspace)


def rebuild_project_rag_index(user, project_id: str, payload: dict | None = None) -> dict:
    access = require_project_role(user, project_id, min_role='member')
    scope = _normalize_scope(payload)
    workspace = None
    try:
        workspace, user_payload = prepare_workspace(
            access.project,
            branch_name=scope['branch_name'] or access.project.default_branch,
            user_id=str(getattr(user, 'id', '') or ''),
        )
        embedding_service, embedding_config = _build_embedding_service(user_payload)
        _require_rag_ready(embedding_config)
        collection_name = _build_collection_name(
            str(access.project.id),
            access.project.name,
            exclude_patterns=scope['exclude_patterns'],
            target_files=scope['target_files'],
        )
        indexer = CodeIndexer(
            collection_name=collection_name,
            embedding_service=embedding_service,
            persist_directory=str(VECTOR_DB_DIR),
        )
        final_progress = None

        async def _rebuild():
            nonlocal final_progress
            async for progress in indexer.rebuild(
                directory=str(workspace),
                exclude_patterns=scope['exclude_patterns'],
                include_patterns=scope['target_files'] or None,
            ):
                final_progress = progress

        async_to_sync(_rebuild)()
        if final_progress is None:
            raise HttpError(500, 'RAG 索引未返回任何进度结果')
        return {
            'collection_name': collection_name,
            'update_mode': getattr(final_progress.update_mode, 'value', str(final_progress.update_mode)),
            'processed_files': final_progress.processed_files,
            'total_files': final_progress.total_files,
            'indexed_chunks': final_progress.indexed_chunks,
            'added_files': final_progress.added_files,
            'updated_files': final_progress.updated_files,
            'deleted_files': final_progress.deleted_files,
            'embedding_provider': embedding_config.get('provider'),
            'embedding_model': embedding_config.get('model'),
        }
    finally:
        cleanup_runtime_workspace(workspace)


def query_project_rag(user, project_id: str, payload: dict) -> dict:
    access = require_project_role(user, project_id, min_role='viewer')
    scope = _normalize_scope(payload)
    query = str(payload.get('query') or '').strip()
    if not query:
        raise HttpError(422, 'query 不能为空')
    top_k = max(1, min(int(payload.get('top_k') or 10), 50))
    workspace = None
    try:
        workspace, user_payload = prepare_workspace(
            access.project,
            branch_name=scope['branch_name'] or access.project.default_branch,
            user_id=str(getattr(user, 'id', '') or ''),
            allow_stale_on_failure=True,
        )
        retriever = ProjectCodeRetriever(
            project_root=str(workspace),
            user_config=user_payload,
            project_id=str(access.project.id),
            project_name=access.project.name,
            exclude_patterns=scope['exclude_patterns'],
            target_files=scope['target_files'],
        )
        unavailable_reason = retriever.get_unavailable_reason() or retriever._embedding_unavailable_reason()
        if unavailable_reason:
            return {
                'collection_name': retriever.collection_name,
                'count': 0,
                'results': [],
                'unavailable_reason': unavailable_reason,
            }
        results = async_to_sync(retriever.retrieve)(
            query=query,
            top_k=top_k,
            filter_file_path=str(payload.get('filter_file_path') or '').strip() or None,
            filter_language=str(payload.get('filter_language') or '').strip() or None,
        )
        return {
            'collection_name': retriever.collection_name,
            'count': len(results),
            'results': [item.to_dict() for item in results],
            'unavailable_reason': None,
        }
    finally:
        cleanup_runtime_workspace(workspace)


def get_knowledge_status(_user) -> dict:
    status = async_to_sync(security_knowledge_rag.get_index_status)()
    return {
        **status,
        'stats': security_knowledge_rag.get_knowledge_stats(),
    }


def list_knowledge_documents(_user, *, category: str = '', keyword: str = '', tag: str = '') -> dict:
    items = security_knowledge_rag.list_documents(
        category=category or None,
        keyword=keyword or None,
        tag=tag or None,
    )
    return {
        'total': len(items),
        'items': items,
    }


def get_knowledge_document(_user, document_id: str) -> dict:
    document = security_knowledge_rag.get_document(document_id)
    if not document:
        raise HttpError(404, '知识条目不存在')
    return document


def search_knowledge_documents(_user, payload: dict) -> dict:
    query = str(payload.get('query') or '').strip()
    if not query:
        raise HttpError(422, 'query 不能为空')
    top_k = max(1, min(int(payload.get('top_k') or 5), 20))
    category_text = str(payload.get('category') or '').strip().lower()
    category = None
    if category_text:
        try:
            category = KnowledgeCategory(category_text)
        except ValueError as exc:
            raise HttpError(422, f'不支持的 category: {category_text}') from exc
    raw_items = async_to_sync(security_knowledge_rag.search)(query=query, category=category, top_k=top_k)
    items = []
    for item in raw_items:
        item_payload = dict(item or {})
        document = security_knowledge_rag.get_document(str(item_payload.get('id') or ''))
        if document:
            items.append({
                **document,
                'score': item_payload.get('score'),
                'file_path': item_payload.get('file_path'),
            })
        else:
            items.append({
                'id': str(item_payload.get('id') or ''),
                'title': item_payload.get('title'),
                'content': str(item_payload.get('content') or ''),
                'category': item_payload.get('category'),
                'tags': list(item_payload.get('tags') or []),
                'severity': item_payload.get('severity'),
                'cwe_ids': list(item_payload.get('cwe_ids') or []),
                'owasp_ids': list(item_payload.get('owasp_ids') or []),
                'metadata': {'file_path': item_payload.get('file_path')},
                'score': item_payload.get('score'),
                'file_path': item_payload.get('file_path'),
            })
    return {
        'total': len(items),
        'items': items,
    }


def rebuild_knowledge_index(_user) -> dict:
    status = async_to_sync(security_knowledge_rag.rebuild_index)()
    return {
        **status,
        'stats': security_knowledge_rag.get_knowledge_stats(),
    }


def save_knowledge_document(user, payload: dict) -> dict:
    document_id = _normalize_custom_knowledge_id(payload.get('id'))
    _ensure_custom_document_writable(user, document_id)
    tags = _require_custom_knowledge_tags(payload.get('tags') or [])
    category = _normalize_knowledge_category(payload.get('category'))
    metadata = {
        **dict(payload.get('metadata') or {}),
        'maintenance_scope': _infer_knowledge_maintenance_scope(document_id),
        'created_by_id': str(get_user_id(user) or ''),
    }
    try:
        document = security_knowledge_rag.save_custom_document({
            **dict(payload or {}),
            'id': document_id,
            'category': category,
            'tags': tags,
            'cwe_ids': _normalize_text_list(payload.get('cwe_ids')),
            'owasp_ids': _normalize_text_list(payload.get('owasp_ids')),
            'metadata': metadata,
        })
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc
    async_to_sync(security_knowledge_rag.rebuild_index)()
    return {
        'document': document,
        'rebuilt': True,
    }


def upload_knowledge_document(
    user,
    *,
    file_name: str,
    file_bytes: bytes,
    document_id: str = '',
    title: str = '',
    category: str = '',
    tags: list[str] | None = None,
    severity: str = '',
    cwe_ids: list[str] | None = None,
    owasp_ids: list[str] | None = None,
) -> dict:
    suffix = Path(file_name or 'knowledge.txt').suffix.lower()
    if suffix not in ALLOWED_KNOWLEDGE_UPLOAD_SUFFIXES:
        allowed = ', '.join(sorted(ALLOWED_KNOWLEDGE_UPLOAD_SUFFIXES))
        raise HttpError(422, f'仅支持上传以下知识文件类型: {allowed}')

    try:
        raw_text = file_bytes.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise HttpError(422, '知识文件必须是 UTF-8 编码文本') from exc

    if suffix == '.json':
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise HttpError(422, '知识 JSON 文件格式错误') from exc
        if not isinstance(parsed, dict):
            raise HttpError(422, '知识 JSON 文件必须是对象结构')
        payload = dict(parsed)
    else:
        payload = {
            'title': title or Path(file_name or 'knowledge').stem,
            'content': raw_text,
            'category': category or 'best_practice',
            'tags': _normalize_text_list(tags),
        }

    if document_id:
        payload['id'] = document_id
    if title:
        payload['title'] = title
    if category:
        payload['category'] = _normalize_knowledge_category(category)
    if tags is not None:
        payload['tags'] = _normalize_text_list(tags)
    if severity:
        payload['severity'] = str(severity).strip()
    if cwe_ids is not None:
        payload['cwe_ids'] = _normalize_text_list(cwe_ids)
    if owasp_ids is not None:
        payload['owasp_ids'] = _normalize_text_list(owasp_ids)
    payload.setdefault('title', Path(file_name or 'knowledge').stem)
    payload.setdefault('category', KnowledgeCategory.BEST_PRACTICE.value)
    payload.setdefault('content', raw_text)
    payload['category'] = _normalize_knowledge_category(payload.get('category'))
    payload['metadata'] = {
        **dict(payload.get('metadata') or {}),
        'uploaded_file_name': file_name,
        'import_mode': 'upload',
    }
    return save_knowledge_document(user, payload)


def delete_knowledge_document(user, document_id: str) -> dict:
    document = security_knowledge_rag.get_document(document_id)
    if not document:
        raise HttpError(404, '自定义知识条目不存在')
    owner_id = str((document.get('metadata') or {}).get('created_by_id') or '').strip()
    current_user_id = str(get_user_id(user) or '').strip()
    if owner_id and current_user_id and owner_id != current_user_id:
        raise HttpError(403, '只能删除自己创建的自定义知识条目')
    if not security_knowledge_rag.delete_custom_document(document_id):
        raise HttpError(404, '自定义知识条目不存在')
    async_to_sync(security_knowledge_rag.rebuild_index)()
    return {
        'success': True,
        'rebuilt': True,
    }


def validate_knowledge_modules(_user, payload: dict) -> dict:
    modules = [str(item).strip() for item in (payload.get('modules') or []) if str(item).strip()]
    return knowledge_loader.validate_modules(modules)
