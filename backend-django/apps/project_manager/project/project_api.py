from typing import List
from ninja import Router, Query
from ninja.pagination import paginate
from django.db.models import Q

from common.fu_auth import BearerAuth as GlobalAuth
from common.fu_pagination import MyPagination
from .project_model import Project
from .project_schema import ProjectCreateSchema, ProjectUpdateSchema, ProjectFilterSchema, ProjectOut
from . import project_service

router = Router(tags=["Project"], auth=GlobalAuth())

@router.post("/", response=ProjectOut, summary="创建项目")
def create_project(request, data: ProjectCreateSchema):
    return project_service.create_project(request, data)

@router.put("/{id}", response=ProjectOut, summary="更新项目")
def update_project(request, id: str, data: ProjectUpdateSchema):
    return project_service.update_project(request, id, data)

@router.delete("/{id}", response=ProjectOut, summary="删除项目")
def delete_project(request, id: str):
    return project_service.delete_project(request, id)

@router.get("/{id}", response=ProjectOut, summary="获取项目详情")
def get_project(request, id: str):
    return project_service.get_project(request, id)

@router.post("/{id}/favorite", response=bool, summary="收藏项目")
def favorite_project(request, id: str):
    return project_service.favorite_project(request, id)

@router.delete("/{id}/favorite", response=bool, summary="取消收藏项目")
def unfavorite_project(request, id: str):
    return project_service.unfavorite_project(request, id)

@router.get("/", response=List[ProjectOut], summary="获取项目列表")
@paginate(MyPagination)
def list_projects(request, filters: ProjectFilterSchema = Query(...)):
    query = Q(is_deleted=False)
    
    if filters.keyword:
        query &= (Q(name__icontains=filters.keyword) | Q(code__icontains=filters.keyword))
        
    if filters.domain:
        query &= Q(domain=filters.domain)
        
    if filters.type:
        query &= Q(type=filters.type)
        
    if filters.manager_id:
        query &= Q(managers__id=filters.manager_id)
        
    if filters.is_closed is not None:
        query &= Q(is_closed=filters.is_closed)
        
    if filters.enable_milestone is not None:
        query &= Q(enable_milestone=filters.enable_milestone)
        
    if filters.enable_iteration is not None:
        query &= Q(enable_iteration=filters.enable_iteration)
        
    if filters.enable_quality is not None:
        query &= Q(enable_quality=filters.enable_quality)
        
    return Project.objects.filter(query).distinct().order_by('-sort', '-sys_create_datetime')
