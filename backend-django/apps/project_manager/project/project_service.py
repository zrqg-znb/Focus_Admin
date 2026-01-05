from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from common import fu_crud
from .project_model import Project
from .project_schema import ProjectCreateSchema, ProjectUpdateSchema
from apps.project_manager.milestone.milestone_model import Milestone
from apps.project_manager.iteration.iteration_model import Iteration
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

        # 联动创建迭代（如果开启且配置了 design_id 和 sub_teams）
        if project.enable_iteration and project.design_id and project.sub_teams:
            # 模拟从数据中台获取迭代数据
            # 实际逻辑应调用数据中台 API
            # fetch_iterations_from_data_platform(project.design_id, project.sub_teams)
            
            # 这里仅作演示：自动创建一个初始迭代
            Iteration.objects.create(
                project=project,
                name="初始迭代-来自中台",
                code=f"{project.code}-IT01",
                start_date=date.today(),
                end_date=date.today(),
                is_current=True,
                is_healthy=True
            )
            
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
        if config_changed and project.design_id and project.sub_teams:
            # 模拟从数据中台获取迭代数据
            # 实际逻辑应调用数据中台 API
            # fetch_iterations_from_data_platform(project.design_id, project.sub_teams)
            
            # 简单演示：如果已存在同名迭代则更新，否则创建
            # 这里为了演示“变更生效”，我们更新或创建一个标记性的迭代记录
            Iteration.objects.update_or_create(
                project=project,
                code=f"{project.code}-IT01",
                defaults={
                    "name": f"迭代-配置变更-{project.design_id}",
                    "start_date": date.today(),
                    "end_date": date.today(),
                    "is_current": True,
                    "is_healthy": True
                }
            )

    return project

def delete_project(request, id: str):
    return fu_crud.delete(id, Project)
