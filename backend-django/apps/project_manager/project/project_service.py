from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from common import fu_crud
from .project_model import Project
from .project_schema import ProjectCreateSchema, ProjectUpdateSchema
from apps.project_manager.milestone.milestone_model import Milestone
from apps.project_manager.iteration.iteration_model import Iteration
from apps.project_manager.iteration.iteration_sync import sync_project_iterations
from datetime import date

@transaction.atomic
def create_project(request, data: ProjectCreateSchema):
    try:
        # 提取 M2M 字段
        data_dict = data.dict()
        manager_ids = data_dict.pop('manager_ids', [])
        
        # 使用 fu_crud 创建项目
        project = fu_crud.create(request, data_dict, Project)
        
        # 绑定经理
        if manager_ids:
            project.managers.set(manager_ids)
        
        # 联动创建里程碑
        if project.enable_milestone:
            Milestone.objects.create(project=project)

        # 联动同步迭代数据
        if project.enable_iteration and project.design_id and project.sub_teams:
            sync_project_iterations(project)
            
        return project
    except IntegrityError as e:
        if 'code' in str(e):
            raise HttpError(422, "项目编码已存在")
        raise e

@transaction.atomic
def update_project(request, id: str, data: ProjectUpdateSchema):
    project = get_object_or_404(Project, id=id)
    old_enable_milestone = project.enable_milestone
    old_design_id = project.design_id
    old_sub_teams = project.sub_teams
    
    # 提取 M2M 字段
    data_dict = data.dict(exclude_unset=True)
    manager_ids = data_dict.pop('manager_ids', None)
    
    # 使用 fu_crud 更新
    project = fu_crud.update(request, id, data_dict, Project)
    
    # 更新经理
    if manager_ids is not None:
        project.managers.set(manager_ids)
        
    # 检查是否开启了里程碑且需要补全
    if project.enable_milestone and not old_enable_milestone:
        if not hasattr(project, 'milestone'):
            Milestone.objects.create(project=project)
    
    # 检查是否需要同步迭代数据（当开启迭代且 design_id 或 sub_teams 发生变更时）
    if project.enable_iteration:
        config_changed = (
            project.design_id != old_design_id or 
            project.sub_teams != old_sub_teams
        )
        # 如果配置变更，或者之前没有迭代数据（初次开启），则触发同步
        if (config_changed or not project.iterations.exists()) and project.design_id and project.sub_teams:
            sync_project_iterations(project)

    return project

def delete_project(request, id: str):
    return fu_crud.delete(id, Project)

def get_project(request, id: str):
    return get_object_or_404(Project, id=id)

def favorite_project(request, id: str):
    project = get_object_or_404(Project, id=id)
    project.favorited_by.add(request.auth)
    return True

def unfavorite_project(request, id: str):
    project = get_object_or_404(Project, id=id)
    project.favorited_by.remove(request.auth)
    return True
