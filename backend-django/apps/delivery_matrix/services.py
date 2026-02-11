from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from common import fu_crud
from .models import OrganizationNode, PositionStaff
from .schemas import OrgNodeCreate, OrgNodeUpdate, PositionStaffCreate

@transaction.atomic
def create_node(request, data: OrgNodeCreate):
    data_dict = data.dict()
    positions_data = data_dict.pop('positions', [])
    
    # Handle parent
    if data_dict.get('parent_id') == "":
         data_dict['parent_id'] = None
    
    # Handle linked_project
    if data_dict.get('linked_project_id') == "":
        data_dict['linked_project_id'] = None
    
    node = fu_crud.create(request, data_dict, OrganizationNode)
    
    # Create positions
    for pos in positions_data:
        # pos is already a dict if data.dict() was called on parent
        if isinstance(pos, dict):
             p_dict = pos
        else:
             p_dict = pos.dict()
             
        user_ids = p_dict.pop('user_ids', [])
        position = PositionStaff.objects.create(node=node, **p_dict)
        if user_ids:
            position.users.set(user_ids)
            
    return node

@transaction.atomic
def update_node(request, node_id, data: OrgNodeUpdate):
    data_dict = data.dict(exclude_unset=True)
    if 'parent_id' in data_dict:
         if data_dict['parent_id'] == "":
             data_dict['parent_id'] = None
         elif str(data_dict['parent_id']) == str(node_id):
             from ninja.errors import HttpError
             raise HttpError(400, "不能将节点自身设为父节点")
    
    if 'linked_project_id' in data_dict and data_dict['linked_project_id'] == "":
        data_dict['linked_project_id'] = None
         
    node = get_object_or_404(OrganizationNode, id=node_id)
    fu_crud.update(request, node_id, data_dict, OrganizationNode)
    return node

def delete_node(request, node_id):
    """删除组织节点（软删除）"""
    node = get_object_or_404(OrganizationNode, id=node_id)
    
    # 检查是否有子节点
    if node.children.exists():
        from ninja.errors import HttpError
        raise HttpError(400, "该节点存在子节点，无法删除")
    
    result = fu_crud.delete(node_id, OrganizationNode)
    return {"id": str(node_id)}

@transaction.atomic
def update_node_positions(request, node_id, positions: list[PositionStaffCreate]):
    node = get_object_or_404(OrganizationNode, id=node_id)
    
    # Clear existing
    node.positions.all().delete()
    
    result = []
    for pos_data in positions:
        # pos_data might be dict or Schema depending on how ninja handles list input
        if isinstance(pos_data, dict):
            p_dict = pos_data
        else:
            p_dict = pos_data.dict()
            
        user_ids = p_dict.pop('user_ids', [])
        position = PositionStaff.objects.create(node=node, **p_dict)
        if user_ids:
            position.users.set(user_ids)
        result.append(position)
            
    return result

def get_tree_data():
    """获取组织架构树数据"""
    # 预取岗位与用户，保证根节点等场景返回最新岗位数据
    positions_qs = PositionStaff.objects.filter(is_deleted=False).prefetch_related('users').order_by('-sort')

    nodes = OrganizationNode.objects.prefetch_related(
        Prefetch('positions', queryset=positions_qs, to_attr='position_list'),
        'linked_project',
        'linked_project__milestone',
    ).order_by('-sort_order', 'sys_create_datetime')
    
    # Build tree in memory
    node_map = {n.id: n for n in nodes}
    roots = []
    
    # Initialize child_list for all nodes
    for node in nodes:
        node.child_list = []
        
    # Build parent-child relationships
    for node in nodes:
        if node.parent_id:
            parent = node_map.get(node.parent_id)
            if parent:
                parent.child_list.append(node)
            else:
                # Orphan node, treat as root
                roots.append(node)
        else:
            # Root node
            roots.append(node)
            
    return roots
