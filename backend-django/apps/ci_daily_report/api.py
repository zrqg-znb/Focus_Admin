from typing import List, Optional
from ninja import Router, Query
from ninja.pagination import paginate
from django.shortcuts import get_object_or_404
from django.db.models import Q, Exists, OuterRef
from datetime import date

from common.fu_auth import BearerAuth as GlobalAuth
from common.fu_pagination import MyPagination
from .models import ProjectConfig, ProjectDailyData, Subscription
from .schemas import (
    ProjectConfigSchema, 
    ProjectConfigCreateSchema, 
    ProjectDailyDataSchema, 
    SubscriptionSchema, 
    SubscribeInputSchema
)

router = Router(tags=["CI 每日集成报告"], auth=GlobalAuth())

# --- Project Configuration Endpoints ---

@router.post("/projects", response=ProjectConfigSchema, summary="创建项目配置")
def create_project(request, data: ProjectConfigCreateSchema):
    project = ProjectConfig.objects.create(**data.dict())
    return project

@router.put("/projects/{id}", response=ProjectConfigSchema, summary="更新项目配置")
def update_project(request, id: int, data: ProjectConfigCreateSchema):
    project = get_object_or_404(ProjectConfig, id=id)
    for attr, value in data.dict().items():
        setattr(project, attr, value)
    project.save()
    # 重新获取带订阅状态的对象
    return ProjectConfig.objects.annotate(
        is_subscribed=Exists(
            Subscription.objects.filter(project=OuterRef('pk'), user=request.auth, is_active=True)
        )
    ).get(id=project.id)

@router.delete("/projects/{id}", summary="删除项目配置")
def delete_project(request, id: int):
    project = get_object_or_404(ProjectConfig, id=id)
    project.delete()
    return {"success": True}

@router.get("/projects", response=List[ProjectConfigSchema], summary="获取项目配置列表")
@paginate(MyPagination)
def list_projects(request, keyword: str = None, category: str = None, owner: str = None):
    query = Q()
    if keyword:
        query &= Q(name__icontains=keyword) | Q(description__icontains=keyword)
    
    if category:
        query &= Q(project_category__icontains=category)
        
    if owner:
        query &= Q(project_owner__icontains=owner)
    
    return ProjectConfig.objects.filter(query).annotate(
        is_subscribed=Exists(
            Subscription.objects.filter(project=OuterRef('pk'), user=request.auth, is_active=True)
        )
    ).order_by('-created_at')

@router.get("/projects/{id}", response=ProjectConfigSchema, summary="获取项目配置详情")
def get_project(request, id: int):
    return get_object_or_404(ProjectConfig, id=id)

# --- Subscription Endpoints ---

@router.post("/subscriptions", response=SubscriptionSchema, summary="订阅项目")
def subscribe_project(request, data: SubscribeInputSchema):
    user = request.auth
    
    project = get_object_or_404(ProjectConfig, id=data.project_id)
    subscription, created = Subscription.objects.get_or_create(user=user, project=project)
    if not subscription.is_active:
        subscription.is_active = True
        subscription.save()
    return subscription

@router.delete("/subscriptions/{project_id}", summary="取消订阅项目")
def unsubscribe_project(request, project_id: int):
    user = request.auth
    project = get_object_or_404(ProjectConfig, id=project_id)
    subscription = get_object_or_404(Subscription, user=user, project=project)
    subscription.delete()
    return {"success": True}

@router.get("/subscriptions", response=List[SubscriptionSchema], summary="获取我的订阅列表")
@paginate(MyPagination)
def list_my_subscriptions(request):
    user = request.auth
    return Subscription.objects.filter(user=user, is_active=True).select_related('project')

# --- Data Endpoints ---

@router.get("/data", response=List[ProjectDailyDataSchema], summary="获取项目历史数据")
@paginate(MyPagination)
def list_project_data(
    request, 
    project_id: Optional[int] = None, 
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None
):
    query = Q()
    if project_id:
        query &= Q(project_id=project_id)
    
    if start_date:
        query &= Q(date__gte=start_date)
        
    if end_date:
        query &= Q(date__lte=end_date)
        
    # 如果用户只能看自己订阅的项目数据，可以在这里加权限控制
    # query &= Q(project__subscribers__user=request.user)
        
    return ProjectDailyData.objects.filter(query).order_by('-date')
