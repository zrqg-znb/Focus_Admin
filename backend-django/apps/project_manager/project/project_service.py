from django.db import transaction
from django.shortcuts import get_object_or_404
from common import fu_crud
from .project_model import Project
from .project_schema import ProjectCreateSchema, ProjectUpdateSchema
from apps.project_manager.milestone.milestone_model import Milestone
from apps.project_manager.iteration.iteration_model import Iteration
from datetime import date

@transaction.atomic
def create_project(request, data: ProjectCreateSchema):
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

@transaction.atomic
def update_project(request, id: str, data: ProjectUpdateSchema):
    project = get_object_or_404(Project, id=id)
    old_enable_milestone = project.enable_milestone
    
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
            
    return project

def delete_project(request, id: str):
    return fu_crud.delete(id, Project)
