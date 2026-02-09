from typing import List, Optional
from ninja import ModelSchema, Schema, Field
from .models import OrganizationNode, PositionStaff

class DeleteOut(Schema):
    id: str

# --- Position Staff ---
class PositionStaffCreate(Schema):
    name: str
    sort: Optional[int] = 0
    user_ids: List[str] = Field([])

class PositionStaffOut(ModelSchema):
    id: str  # 明确指定为 str 类型
    users_info: List[dict] = Field([])
    
    class Meta:
        model = PositionStaff
        fields = ['id', 'name', 'sort']
    
    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_users_info(obj):
        return [{"id": str(u.id), "name": u.name, "avatar": u.avatar if hasattr(u, 'avatar') else None} for u in obj.users.all()]

# --- Organization Node ---
class OrgNodeCreate(Schema):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    linked_project_id: Optional[str] = None
    positions: List[PositionStaffCreate] = Field(default_factory=list)

class OrgNodeUpdate(Schema):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    linked_project_id: Optional[str] = None
    sort_order: Optional[int] = None

class OrgNodeOut(ModelSchema):
    id: str  # 明确指定为 str 类型
    children: List['OrgNodeOut'] = Field([])
    positions: List[PositionStaffOut] = Field([])
    linked_project_info: Optional[dict] = Field(None)
    milestone_info: Optional[dict] = Field(None)
    
    parent_id: Optional[str] = None
    linked_project_id: Optional[str] = None

    class Meta:
        model = OrganizationNode
        fields = ['id', 'name', 'code', 'description', 'sort_order', 'sys_create_datetime']
    
    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_children(obj):
        return getattr(obj, 'child_list', [])

    @staticmethod
    def resolve_parent_id(obj):
        return str(obj.parent_id) if obj.parent_id else None

    @staticmethod
    def resolve_linked_project_id(obj):
        return str(obj.linked_project_id) if obj.linked_project_id else None

    @staticmethod
    def resolve_positions(obj):
        """获取节点的所有岗位配置"""
        # 直接从数据库查询，避免使用可能被覆盖的属性
        from .models import PositionStaff
        return PositionStaff.objects.filter(node=obj).prefetch_related('users').order_by('-sort')

    @staticmethod
    def resolve_linked_project_info(obj):
        if obj.linked_project:
            return {"id": str(obj.linked_project.id), "name": obj.linked_project.name}
        return None
    
    @staticmethod
    def resolve_milestone_info(obj):
        if obj.linked_project and hasattr(obj.linked_project, 'milestone'):
            ms = obj.linked_project.milestone
            return {
                "qg1_date": ms.qg1_date,
                "qg2_date": ms.qg2_date,
                "qg3_date": ms.qg3_date,
                "qg4_date": ms.qg4_date,
                "qg5_date": ms.qg5_date,
                "qg6_date": ms.qg6_date,
                "qg7_date": ms.qg7_date,
                "qg8_date": ms.qg8_date,
            }
        return None

OrgNodeOut.update_forward_refs()
