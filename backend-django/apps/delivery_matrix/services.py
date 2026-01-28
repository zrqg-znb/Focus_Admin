from django.db import transaction
from django.shortcuts import get_object_or_404
from common import fu_crud
from .models import DeliveryDomain, ProjectGroup, ProjectComponent
from .schemas import (
    DeliveryDomainCreate, DeliveryDomainUpdate,
    ProjectGroupCreate, ProjectGroupUpdate,
    ProjectComponentCreate, ProjectComponentUpdate
)

# --- Domain ---
@transaction.atomic
def create_domain(request, data: DeliveryDomainCreate):
    data_dict = data.dict()
    interface_people_ids = data_dict.pop('interface_people_ids', [])
    domain = fu_crud.create(request, data_dict, DeliveryDomain)
    if interface_people_ids:
        domain.interface_people.set(interface_people_ids)
    return domain

@transaction.atomic
def update_domain(request, domain_id, data: DeliveryDomainUpdate):
    data_dict = data.dict(exclude_unset=True)
    interface_people_ids = data_dict.pop('interface_people_ids', None)
    domain = get_object_or_404(DeliveryDomain, id=domain_id)
    fu_crud.update(request, domain_id, data_dict, DeliveryDomain)
    if interface_people_ids is not None:
        domain.interface_people.set(interface_people_ids)
    return domain

def delete_domain(request, domain_id):
    return fu_crud.delete(request, domain_id, DeliveryDomain)

# --- Group ---
@transaction.atomic
def create_group(request, data: ProjectGroupCreate):
    data_dict = data.dict()
    manager_ids = data_dict.pop('manager_ids', [])
    group = fu_crud.create(request, data_dict, ProjectGroup)
    if manager_ids:
        group.managers.set(manager_ids)
    return group

@transaction.atomic
def update_group(request, group_id, data: ProjectGroupUpdate):
    data_dict = data.dict(exclude_unset=True)
    manager_ids = data_dict.pop('manager_ids', None)
    group = get_object_or_404(ProjectGroup, id=group_id)
    fu_crud.update(request, group_id, data_dict, ProjectGroup)
    if manager_ids is not None:
        group.managers.set(manager_ids)
    return group

def delete_group(request, group_id):
    return fu_crud.delete(request, group_id, ProjectGroup)

# --- Component ---
@transaction.atomic
def create_component(request, data: ProjectComponentCreate):
    data_dict = data.dict()
    manager_ids = data_dict.pop('manager_ids', [])
    component = fu_crud.create(request, data_dict, ProjectComponent)
    if manager_ids:
        component.managers.set(manager_ids)
    return component

@transaction.atomic
def update_component(request, component_id, data: ProjectComponentUpdate):
    data_dict = data.dict(exclude_unset=True)
    manager_ids = data_dict.pop('manager_ids', None)
    component = get_object_or_404(ProjectComponent, id=component_id)
    fu_crud.update(request, component_id, data_dict, ProjectComponent)
    if manager_ids is not None:
        component.managers.set(manager_ids)
    return component

def delete_component(request, component_id):
    return fu_crud.delete(request, component_id, ProjectComponent)

# --- Dashboard & Tree Data ---
def get_dashboard_data():
    domains = DeliveryDomain.objects.prefetch_related(
        'interface_people',
        'groups',
        'groups__managers',
        'groups__components',
        'groups__components__managers',
        'groups__components__linked_project',
        'groups__components__linked_project__milestone'
    ).all().order_by('id') # Ordered by ID or creation time

    result = []
    for domain in domains:
        groups_data = []
        for group in domain.groups.all().order_by('id'):
            components_data = []
            for comp in group.components.all().order_by('id'):
                milestone_info = None
                project_name = None
                if comp.linked_project:
                    project_name = comp.linked_project.name
                    if hasattr(comp.linked_project, 'milestone'):
                        ms = comp.linked_project.milestone
                        milestone_info = {
                            "qg1_date": ms.qg1_date,
                            "qg2_date": ms.qg2_date,
                            "qg3_date": ms.qg3_date,
                            "qg4_date": ms.qg4_date,
                            "qg5_date": ms.qg5_date,
                            "qg6_date": ms.qg6_date,
                            "qg7_date": ms.qg7_date,
                            "qg8_date": ms.qg8_date,
                        }
                
                components_data.append({
                    "id": comp.id,
                    "name": comp.name,
                    "managers": [u.name for u in comp.managers.all()],
                    "managers_info": [{"id": u.id, "name": u.name} for u in comp.managers.all()],
                    "project_name": project_name,
                    "milestone": milestone_info
                })
            
            groups_data.append({
                "id": group.id,
                "name": group.name,
                "managers": [u.name for u in group.managers.all()],
                "managers_info": [{"id": u.id, "name": u.name} for u in group.managers.all()],
                "components": components_data
            })
        
        result.append({
            "id": domain.id,
            "name": domain.name,
            "interface_people": [u.name for u in domain.interface_people.all()],
            "interface_people_info": [{"id": u.id, "name": u.name} for u in domain.interface_people.all()],
            "groups": groups_data
        })
    
    return result

def get_admin_tree_data():
    """
    Returns a unified tree structure for the admin sidebar.
    Structure:
    [
      {
        id: "domain_<id>",
        key: "domain_<id>",
        name: "Domain Name",
        type: "domain",
        real_id: <id>,
        children: [
          {
            id: "group_<id>",
            key: "group_<id>",
            name: "Group Name",
            type: "group",
            real_id: <id>,
            parent_id: "domain_<id>",
            children: [
               {
                 id: "component_<id>",
                 key: "component_<id>",
                 name: "Component Name",
                 type: "component",
                 real_id: <id>,
                 parent_id: "group_<id>"
               }
            ]
          }
        ]
      }
    ]
    """
    domains = DeliveryDomain.objects.prefetch_related(
        'interface_people',
        'groups',
        'groups__managers',
        'groups__components',
        'groups__components__managers',
        'groups__components__linked_project',
    ).all().order_by('id')

    tree = []
    for domain in domains:
        domain_node = {
            "id": f"domain_{domain.id}",
            "key": f"domain_{domain.id}",
            "name": domain.name,
            "type": "domain",
            "real_id": domain.id,
            "code": domain.code,
            "remark": domain.remark,
            "interface_people": [u.id for u in domain.interface_people.all()],
            "interface_people_info": [{"id": u.id, "name": u.name} for u in domain.interface_people.all()],
            "children": []
        }
        
        for group in domain.groups.all().order_by('id'):
            group_node = {
                "id": f"group_{group.id}",
                "key": f"group_{group.id}",
                "name": group.name,
                "type": "group",
                "real_id": group.id,
                "domain_id": domain.id,
                "remark": group.remark,
                "managers": [u.id for u in group.managers.all()],
                "managers_info": [{"id": u.id, "name": u.name} for u in group.managers.all()],
                "parent_id": f"domain_{domain.id}",
                "children": []
            }
            
            for comp in group.components.all().order_by('id'):
                comp_node = {
                    "id": f"component_{comp.id}",
                    "key": f"component_{comp.id}",
                    "name": comp.name,
                    "type": "component",
                    "real_id": comp.id,
                    "group_id": group.id,
                    "linked_project_id": comp.linked_project_id,
                    "linked_project_info": {"id": comp.linked_project.id, "name": comp.linked_project.name} if comp.linked_project else None,
                    "remark": comp.remark,
                    "managers": [u.id for u in comp.managers.all()],
                    "managers_info": [{"id": u.id, "name": u.name} for u in comp.managers.all()],
                    "parent_id": f"group_{group.id}"
                }
                group_node["children"].append(comp_node)
            
            domain_node["children"].append(group_node)
        
        tree.append(domain_node)
    
    return tree
