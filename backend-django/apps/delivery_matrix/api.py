from typing import List, Optional
from ninja import Router
from ninja.pagination import paginate
from common.fu_auth import BearerAuth as GlobalAuth
from common.fu_pagination import MyPagination
from .models import DeliveryDomain, ProjectGroup, ProjectComponent
from . import schemas, services

router = Router(auth=GlobalAuth())

# --- Domain ---
@router.post("/domains", response=schemas.DeliveryDomainOut, summary="创建交付领域")
def create_domain(request, data: schemas.DeliveryDomainCreate):
    return services.create_domain(request, data)

@router.delete("/domains/{domain_id}", summary="删除交付领域")
def delete_domain(request, domain_id: str):
    return services.delete_domain(request, domain_id)

@router.put("/domains/{domain_id}", response=schemas.DeliveryDomainOut, summary="更新交付领域")
def update_domain(request, domain_id: str, data: schemas.DeliveryDomainUpdate):
    return services.update_domain(request, domain_id, data)

@router.get("/domains", response=List[schemas.DeliveryDomainOut], summary="获取交付领域列表")
@paginate(MyPagination)
def list_domains(request):
    return DeliveryDomain.objects.all().order_by('-id')

@router.get("/domains/all", response=List[schemas.DeliveryDomainOut], summary="获取所有交付领域(不分页)")
def list_all_domains(request):
    return DeliveryDomain.objects.all().order_by('-id')

# --- Group ---
@router.post("/groups", response=schemas.ProjectGroupOut, summary="创建项目群")
def create_group(request, data: schemas.ProjectGroupCreate):
    return services.create_group(request, data)

@router.delete("/groups/{group_id}", summary="删除项目群")
def delete_group(request, group_id: str):
    return services.delete_group(request, group_id)

@router.put("/groups/{group_id}", response=schemas.ProjectGroupOut, summary="更新项目群")
def update_group(request, group_id: str, data: schemas.ProjectGroupUpdate):
    return services.update_group(request, group_id, data)

@router.get("/groups", response=List[schemas.ProjectGroupOut], summary="获取项目群列表")
@paginate(MyPagination)
def list_groups(request, domain_id: str = None):
    qs = ProjectGroup.objects.all().order_by('-id')
    if domain_id:
        qs = qs.filter(domain_id=domain_id)
    return qs

# --- Component ---
@router.post("/components", response=schemas.ProjectComponentOut, summary="创建项目组件")
def create_component(request, data: schemas.ProjectComponentCreate):
    return services.create_component(request, data)

@router.delete("/components/{component_id}", summary="删除项目组件")
def delete_component(request, component_id: str):
    return services.delete_component(request, component_id)

@router.put("/components/{component_id}", response=schemas.ProjectComponentOut, summary="更新项目组件")
def update_component(request, component_id: str, data: schemas.ProjectComponentUpdate):
    return services.update_component(request, component_id, data)

@router.get("/components", response=List[schemas.ProjectComponentOut], summary="获取项目组件列表")
@paginate(MyPagination)
def list_components(request, group_id: str = None):
    qs = ProjectComponent.objects.all().order_by('-id')
    if group_id:
        qs = qs.filter(group_id=group_id)
    return qs

# --- Dashboard ---
@router.get("/dashboard/matrix", response=List[schemas.DashboardDomain], summary="获取交付矩阵看板数据")
def get_dashboard_matrix(request):
    return services.get_dashboard_data()

@router.get("/admin/tree", response=List[dict], summary="获取管理端树形数据")
def get_admin_tree(request):
    return services.get_admin_tree_data()
