from typing import List, Optional

from ninja import File, Query, Router, UploadedFile

from . import base_services as services
from .base_schemas import (
    BatchBindBranchesIn,
    BatchBindRepositoriesIn,
    BindResultOut,
    BranchIn,
    BranchOut,
    BranchPatch,
    ImportResultOut,
    OrganizationIn,
    OrganizationOut,
    OrganizationPatch,
    PaginatedBranchOut,
    PaginatedRepositoryOut,
    RepositoryIn,
    RepositoryOut,
    RepositoryPatch,
)


router = Router()


@router.get("/organizations/tree", response=List[OrganizationOut], summary="获取代码库组织树")
def list_organizations(request):
    """返回代码库管理页左侧组织树。"""
    return services.list_organization_tree()


@router.get("/organizations/valid-parents", response=List[OrganizationOut], summary="获取可选父组织")
def list_valid_organization_parents(request, exclude_id: Optional[str] = Query(None)):
    """返回新增/编辑组织时可选择的父组织树。"""
    return services.list_organization_tree(exclude_id=exclude_id)


@router.post("/organizations", response=OrganizationOut, summary="创建代码库组织")
def create_organization(request, payload: OrganizationIn):
    """创建公司代码库系统组织主数据。"""
    return services.create_organization(request.auth, payload)


@router.get("/organizations/template", summary="下载组织导入模板")
def download_organization_template(request):
    """下载组织基础字段 Excel 导入模板。"""
    return services.build_organization_template_response()


@router.post("/organizations/import", response=ImportResultOut, summary="Excel导入组织")
def import_organizations(request, file: UploadedFile = File(...)):
    """导入组织基础字段，不处理代码库绑定。"""
    return services.import_organizations(request.auth, file)


@router.put("/organizations/{org_id}", response=OrganizationOut, summary="更新代码库组织")
def update_organization(request, org_id: str, payload: OrganizationPatch):
    """更新组织基础字段并校验父子关系。"""
    return services.update_organization(request.auth, org_id, payload)


@router.delete("/organizations/{org_id}", summary="删除代码库组织")
def delete_organization(request, org_id: str):
    """删除没有子组织和代码库的组织。"""
    return services.delete_organization(org_id)


@router.get("/repositories", response=PaginatedRepositoryOut, summary="获取代码库列表")
def list_repositories(
    request,
    page: int = Query(1),
    pageSize: int = Query(20),
    organization_id: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    repo_type: Optional[str] = Query(None),
):
    """分页查询代码库列表，支持按当前组织直接过滤。"""
    return services.list_repositories(
        page=page,
        page_size=pageSize,
        organization_id=organization_id,
        keyword=keyword,
        mode=mode,
        domain=domain,
        repo_type=repo_type,
    )


@router.post("/repositories", response=RepositoryOut, summary="创建代码库")
def create_repository(request, payload: RepositoryIn):
    """创建代码库主数据并绑定责任 PL 组。"""
    return services.create_repository(request.auth, payload)


@router.get("/repositories/template", summary="下载代码库导入模板")
def download_repository_template(request):
    """下载代码库基础字段 Excel 导入模板。"""
    return services.build_repository_template_response()


@router.post("/repositories/import", response=ImportResultOut, summary="Excel导入代码库")
def import_repositories(request, file: UploadedFile = File(...)):
    """导入代码库基础字段，不导入代码库-分支关系。"""
    return services.import_repositories(request.auth, file)


@router.post("/repositories/batch-bind-branches", response=BindResultOut, summary="批量绑定代码库分支")
def batch_bind_repository_branches(request, payload: BatchBindBranchesIn):
    """从代码库侧批量绑定分支，支持 append/replace。"""
    return services.bind_branches_to_repositories(
        payload.repository_ids,
        payload.branch_ids,
        payload.mode,
    )


@router.get("/repositories/{repo_id}", response=RepositoryOut, summary="获取代码库详情")
def get_repository(request, repo_id: str):
    """获取代码库详情和派生统计字段。"""
    return services.get_repository(repo_id)


@router.put("/repositories/{repo_id}", response=RepositoryOut, summary="更新代码库")
def update_repository(request, repo_id: str, payload: RepositoryPatch):
    """更新代码库基础字段和责任 PL 组。"""
    return services.update_repository(request.auth, repo_id, payload)


@router.delete("/repositories/{repo_id}", summary="删除代码库")
def delete_repository(request, repo_id: str):
    """软删除代码库并解除活跃分支绑定。"""
    return services.delete_repository(repo_id)


@router.get("/branches", response=PaginatedBranchOut, summary="获取分支列表")
def list_branches(
    request,
    page: int = Query(1),
    pageSize: int = Query(20),
    keyword: Optional[str] = Query(None),
    branch_type: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
):
    """分页查询分支主数据并返回关联代码库数量。"""
    return services.list_branches(
        page=page,
        page_size=pageSize,
        keyword=keyword,
        branch_type=branch_type,
        domain=domain,
    )


@router.post("/branches", response=BranchOut, summary="创建分支")
def create_branch(request, payload: BranchIn):
    """创建分支主数据。"""
    return services.create_branch(request.auth, payload)


@router.get("/branches/template", summary="下载分支导入模板")
def download_branch_template(request):
    """下载分支基础字段 Excel 导入模板。"""
    return services.build_branch_template_response()


@router.post("/branches/import", response=ImportResultOut, summary="Excel导入分支")
def import_branches(request, file: UploadedFile = File(...)):
    """导入分支基础字段，不导入绑定关系。"""
    return services.import_branches(request.auth, file)


@router.post("/branches/batch-bind-repositories", response=BindResultOut, summary="批量绑定分支代码库")
def batch_bind_branch_repositories(request, payload: BatchBindRepositoriesIn):
    """从分支侧批量绑定代码库，支持 append/replace。"""
    return services.bind_repositories_to_branches(
        payload.branch_ids,
        payload.repository_ids,
        payload.mode,
    )


@router.get("/branches/{branch_id}", response=BranchOut, summary="获取分支详情")
def get_branch(request, branch_id: str):
    """获取分支详情和关联代码库统计。"""
    return services.get_branch(branch_id)


@router.put("/branches/{branch_id}", response=BranchOut, summary="更新分支")
def update_branch(request, branch_id: str, payload: BranchPatch):
    """更新分支基础字段。"""
    return services.update_branch(request.auth, branch_id, payload)


@router.delete("/branches/{branch_id}", summary="删除分支")
def delete_branch(request, branch_id: str):
    """软删除分支并解除活跃代码库绑定。"""
    return services.delete_branch(branch_id)
