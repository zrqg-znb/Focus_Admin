from __future__ import annotations

from ninja import File, Form, Router, UploadedFile

from .project_schemas import (
    AuditProjectCreateSchema,
    AuditProjectDetailSchema,
    ProjectStatsSchema,
    AuditProjectUpdateSchema,
    PaginatedProjectRecycleSchema,
    PaginatedProjectSchema,
    ProjectFileBrowserResponseSchema,
    ProjectMemberSchema,
    ProjectMemberSaveSchema,
    ProjectOwnerTransferSchema,
    ProjectZipMetaSchema,
)
from . import project_services

router = Router(tags=['DeepAudit-Projects'])


@router.get('', response=PaginatedProjectSchema, summary='获取项目列表')
def list_projects(request, keyword: str = '', source_type: str = '', page: int = 1, pageSize: int = 20):
    return project_services.list_projects(
        request.auth,
        keyword=keyword,
        source_type=source_type,
        page=page,
        page_size=pageSize,
    )


@router.get('/recycle-bin', response=PaginatedProjectRecycleSchema, summary='获取回收站项目列表')
def list_recycle_projects(request, keyword: str = '', page: int = 1, pageSize: int = 20):
    return project_services.list_projects(
        request.auth,
        keyword=keyword,
        page=page,
        page_size=pageSize,
        recycle=True,
    )


@router.get('/stats', response=ProjectStatsSchema, summary='获取项目统计')
def get_project_stats(request):
    return project_services.get_project_stats(request.auth)


@router.post('', response=AuditProjectDetailSchema, summary='创建项目')
def create_project(request, data: AuditProjectCreateSchema):
    project = project_services.create_project(request.auth, data.dict())
    return project_services.get_project_detail(request.auth, str(project.id))


@router.get('/{project_id}', response=AuditProjectDetailSchema, summary='获取项目详情')
def get_project(request, project_id: str):
    return project_services.get_project_detail(request.auth, project_id)


@router.put('/{project_id}', response=AuditProjectDetailSchema, summary='更新项目')
def update_project(request, project_id: str, data: AuditProjectUpdateSchema):
    project_services.update_project(request.auth, project_id, data.dict(exclude_unset=True))
    return project_services.get_project_detail(request.auth, project_id)


@router.delete('/{project_id}', response=bool, summary='删除项目')
def delete_project(request, project_id: str):
    return project_services.delete_project(request.auth, project_id)


@router.post('/{project_id}/restore', response=bool, summary='恢复项目')
def restore_project(request, project_id: str):
    return project_services.restore_project(request.auth, project_id)


@router.delete('/{project_id}/purge', response=bool, summary='彻底删除项目')
def purge_project(request, project_id: str):
    return project_services.purge_project(request.auth, project_id)


@router.get('/{project_id}/members', response=list[ProjectMemberSchema], summary='获取项目成员')
def list_members(request, project_id: str):
    return project_services.list_members(request.auth, project_id)


@router.post('/{project_id}/members', response=ProjectMemberSchema, summary='新增项目成员')
def create_member(request, project_id: str, data: ProjectMemberSaveSchema):
    return project_services.add_member(request.auth, project_id, data.dict())


@router.put('/{project_id}/members/{member_id}', response=ProjectMemberSchema, summary='更新项目成员')
def update_member(request, project_id: str, member_id: str, data: ProjectMemberSaveSchema):
    return project_services.update_member(request.auth, project_id, member_id, data.dict())


@router.delete('/{project_id}/members/{member_id}', response=bool, summary='移除项目成员')
def delete_member(request, project_id: str, member_id: str):
    return project_services.remove_member(request.auth, project_id, member_id)


@router.post('/{project_id}/transfer-owner', response=bool, summary='转移项目所有权')
def transfer_owner(request, project_id: str, data: ProjectOwnerTransferSchema):
    return project_services.transfer_owner(request.auth, project_id, data.user_id)


@router.post('/{project_id}/zip', response=ProjectZipMetaSchema, summary='上传项目 ZIP')
def upload_project_zip(request, project_id: str, file: UploadedFile = File(...)):
    return project_services.upload_project_zip(request.auth, project_id, file.name, file.read())


@router.get('/{project_id}/zip', response=ProjectZipMetaSchema, summary='获取项目 ZIP 信息')
def get_project_zip_meta(request, project_id: str):
    return project_services.get_project_zip_meta(request.auth, project_id)


@router.delete('/{project_id}/zip', response=bool, summary='删除项目 ZIP')
def delete_project_zip(request, project_id: str):
    return project_services.delete_zip_file(request.auth, project_id)


@router.get('/{project_id}/branches', response=list[str], summary='获取远端分支列表')
def list_project_branches(request, project_id: str):
    return project_services.list_branches(request.auth, project_id)


@router.get('/{project_id}/files', response=list[dict], summary='获取项目文件列表')
def list_project_files(
    request,
    project_id: str,
    branch_name: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
    exclude_patterns: str = '',
):
    patterns = [item.strip() for item in exclude_patterns.split(',') if item.strip()]
    return project_services.list_files(
        request.auth,
        project_id,
        branch_name=branch_name,
        manifest_xml=manifest_xml,
        group=group,
        exclude_patterns=patterns,
    )


@router.get('/{project_id}/file-browser', response=ProjectFileBrowserResponseSchema, summary='分页获取项目文件浏览数据')
def browse_project_files(
    request,
    project_id: str,
    repository_type: str | None = None,
    branch_name: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
    path: str = '',
    keyword: str = '',
    offset: int = 0,
    limit: int = 100,
    refresh: bool = False,
    exclude_patterns: str = '',
):
    patterns = [item.strip() for item in exclude_patterns.split(',') if item.strip()]
    return project_services.browse_files(
        request.auth,
        project_id,
        repository_type=repository_type,
        branch_name=branch_name,
        manifest_xml=manifest_xml,
        group=group,
        path=path,
        keyword=keyword,
        offset=offset,
        limit=limit,
        refresh=refresh,
        exclude_patterns=patterns,
    )
