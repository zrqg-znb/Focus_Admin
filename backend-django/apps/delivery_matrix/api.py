from typing import List
from ninja import Router
from common.fu_auth import BearerAuth as GlobalAuth
from . import schemas, services

router = Router(auth=GlobalAuth())

@router.post("/nodes", response=schemas.OrgNodeOut, summary="创建组织节点")
def create_node(request, data: schemas.OrgNodeCreate):
    """创建沟通矩阵组织节点。"""
    return services.create_node(request, data)

@router.put("/nodes/{node_id}", response=schemas.OrgNodeOut, summary="更新组织节点")
def update_node(request, node_id: str, data: schemas.OrgNodeUpdate):
    """更新沟通矩阵组织节点，支持同时保存岗位人员配置。"""
    return services.update_node(request, node_id, data)

@router.delete("/nodes/{node_id}", response=schemas.DeleteOut, summary="删除组织节点")
def delete_node(request, node_id: str):
    """删除沟通矩阵组织节点。"""
    return services.delete_node(request, node_id)

@router.put("/nodes/{node_id}/positions", response=List[schemas.PositionStaffOut], summary="更新节点岗位")
def update_positions(request, node_id: str, data: List[schemas.PositionStaffCreate]):
    """独立更新组织节点的岗位人员配置。"""
    return services.update_node_positions(request, node_id, data)

@router.get("/export/markdown", summary="导出沟通矩阵 Markdown")
def export_markdown(request):
    """导出完整沟通矩阵 Markdown 文件。"""
    return services.export_delivery_matrix_markdown()

@router.get("/tree", response=List[schemas.OrgNodeOut], summary="获取组织架构树")
def get_tree(request):
    """获取沟通矩阵组织架构树。"""
    return services.get_tree_data()

@router.get("/nodes/{node_id}/valid-parents", response=List[schemas.OrgNodeOut], summary="获取可用父节点")
def get_valid_parents(request, node_id: str):
    """获取指定节点可选择的父节点树。"""
    return services.get_valid_parent_tree(node_id)
