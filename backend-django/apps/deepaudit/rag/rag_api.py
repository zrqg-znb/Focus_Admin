from __future__ import annotations

from ninja import File, Form, Router, UploadedFile

from . import rag_services
from .rag_schemas import (
    KnowledgeDeleteResultSchema,
    KnowledgeDocumentSchema,
    KnowledgeListSchema,
    KnowledgeSaveResultSchema,
    KnowledgeSaveSchema,
    KnowledgeSearchResultSchema,
    KnowledgeSearchSchema,
    KnowledgeStatusSchema,
    KnowledgeValidateResultSchema,
    KnowledgeValidateSchema,
    RagQueryResultSchema,
    RagQuerySchema,
    RagRebuildResultSchema,
    RagRebuildSchema,
    RagStatusSchema,
)

router = Router(tags=['DeepAudit-RAG'])


@router.get('/projects/{project_id}/status', response=RagStatusSchema, summary='获取项目 RAG 索引状态')
def get_project_rag_status(
    request,
    project_id: str,
    branch_name: str = '',
    repository_type: str = '',
    manifest_xml: str = '',
    group: str = '',
    exclude_patterns: str = '',
    target_files: str = '',
):
    return rag_services.get_project_rag_status(
        request.auth,
        project_id,
        {
            'branch_name': branch_name,
            'repository_type': repository_type,
            'manifest_xml': manifest_xml,
            'group': group,
            'exclude_patterns': [item.strip() for item in exclude_patterns.split(',') if item.strip()],
            'target_files': [item.strip() for item in target_files.split(',') if item.strip()],
        },
    )


@router.post('/projects/{project_id}/rebuild', response=RagRebuildResultSchema, summary='重建项目 RAG 索引')
def rebuild_project_rag(request, project_id: str, data: RagRebuildSchema):
    return rag_services.rebuild_project_rag_index(request.auth, project_id, data.dict())


@router.post('/projects/{project_id}/query', response=RagQueryResultSchema, summary='查询项目 RAG 索引')
def query_project_rag(request, project_id: str, data: RagQuerySchema):
    return rag_services.query_project_rag(request.auth, project_id, data.dict())


@router.get('/knowledge/status', response=KnowledgeStatusSchema, summary='获取安全知识库状态')
def get_knowledge_status(request):
    return rag_services.get_knowledge_status(request.auth)


@router.get('/knowledge/modules', response=KnowledgeListSchema, summary='获取安全知识库条目列表')
def list_knowledge_modules(request, category: str = '', keyword: str = '', tag: str = ''):
    return rag_services.list_knowledge_documents(request.auth, category=category, keyword=keyword, tag=tag)


@router.get('/knowledge/modules/{document_id}', response=KnowledgeDocumentSchema, summary='获取安全知识条目详情')
def get_knowledge_module(request, document_id: str):
    return rag_services.get_knowledge_document(request.auth, document_id)


@router.post('/knowledge/search', response=KnowledgeSearchResultSchema, summary='搜索安全知识库')
def search_knowledge(request, data: KnowledgeSearchSchema):
    return rag_services.search_knowledge_documents(request.auth, data.dict())


@router.post('/knowledge/rebuild', response=KnowledgeStatusSchema, summary='重建安全知识库索引')
def rebuild_knowledge(request):
    return rag_services.rebuild_knowledge_index(request.auth)


@router.post('/knowledge/modules', response=KnowledgeSaveResultSchema, summary='创建或更新自定义安全知识条目')
def save_knowledge_module(request, data: KnowledgeSaveSchema):
    return rag_services.save_knowledge_document(request.auth, data.dict())


@router.post('/knowledge/upload', response=KnowledgeSaveResultSchema, summary='上传安全知识文件')
def upload_knowledge_module(
    request,
    file: UploadedFile = File(...),
    document_id: str = Form(''),
    title: str = Form(''),
    category: str = Form(''),
    tags: str = Form(''),
    severity: str = Form(''),
    cwe_ids: str = Form(''),
    owasp_ids: str = Form(''),
):
    return rag_services.upload_knowledge_document(
        request.auth,
        file_name=file.name,
        file_bytes=file.read(),
        document_id=document_id,
        title=title,
        category=category,
        tags=[item.strip() for item in tags.replace('\n', ',').split(',') if item.strip()],
        severity=severity,
        cwe_ids=[item.strip() for item in cwe_ids.replace('\n', ',').split(',') if item.strip()],
        owasp_ids=[item.strip() for item in owasp_ids.replace('\n', ',').split(',') if item.strip()],
    )


@router.delete('/knowledge/modules/{document_id}', response=KnowledgeDeleteResultSchema, summary='删除自定义安全知识条目')
def delete_knowledge_module(request, document_id: str):
    return rag_services.delete_knowledge_document(request.auth, document_id)


@router.post('/knowledge/validate', response=KnowledgeValidateResultSchema, summary='校验知识模块名称')
def validate_knowledge_modules(request, data: KnowledgeValidateSchema):
    return rag_services.validate_knowledge_modules(request.auth, data.dict())
