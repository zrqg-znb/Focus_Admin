from django.db.models import Q
from django.shortcuts import get_object_or_404
from common import fu_crud
from .milestone_model import Milestone
from .milestone_schema import MilestoneUpdateSchema, MilestoneBoardSchema

def get_milestone_board(filters: dict):
    queryset = Milestone.objects.select_related('project').prefetch_related('project__managers').filter(
        project__is_deleted=False,
        project__enable_milestone=True
    )
    
    # 模糊搜索
    keyword = filters.get('keyword')
    if keyword:
        queryset = queryset.filter(
            Q(project__name__icontains=keyword) | 
            Q(project__code__icontains=keyword)
        )
        
    project_type = filters.get('project_type')
    if project_type:
        queryset = queryset.filter(project__type=project_type)
        
    manager_id = filters.get('manager_id')
    if manager_id:
        queryset = queryset.filter(project__managers__id=manager_id)

    # 构造扁平化数据
    result = []
    for m in queryset:
        result.append(MilestoneBoardSchema(
            project_id=m.project.id,
            project_name=m.project.name,
            project_domain=m.project.domain,
            manager_names=[u.name or u.username for u in m.project.managers.all()],
            qg1_date=m.qg1_date,
            qg2_date=m.qg2_date,
            qg3_date=m.qg3_date,
            qg4_date=m.qg4_date,
            qg5_date=m.qg5_date,
            qg6_date=m.qg6_date,
            qg7_date=m.qg7_date,
            qg8_date=m.qg8_date,
        ))
    return result

def update_milestone(request, project_id: str, data: MilestoneUpdateSchema):
    milestone = get_object_or_404(Milestone, project_id=project_id)
    # 使用 fu_crud 更新，虽然是通过 project_id 查找的，但 fu_crud.update 需要主键
    # 这里我们直接用 ORM 更新更方便，或者先获取 ID 再调 fu_crud
    # 为了保持一致性，我们手动处理数据然后 save，或者复用 fu_crud.update
    return fu_crud.update(request, milestone.id, data.dict(exclude_unset=True), Milestone)
