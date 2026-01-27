from typing import List, Optional, Any
from ninja import ModelSchema, Schema, Field
from .models import DeliveryDomain, ProjectGroup, ProjectComponent
from apps.project_manager.project.project_model import Project

# --- Delivery Domain ---
class DeliveryDomainCreate(Schema):
    name: str
    code: str
    interface_people_ids: List[str] = Field([])
    remark: Optional[str] = None

class DeliveryDomainUpdate(Schema):
    name: Optional[str] = None
    code: Optional[str] = None
    interface_people_ids: Optional[List[str]] = Field(None)
    remark: Optional[str] = None

class DeliveryDomainOut(ModelSchema):
    interface_people_info: List[dict] = Field([])
    class Meta:
        model = DeliveryDomain
        fields = "__all__"
    
    @staticmethod
    def resolve_interface_people_info(obj):
        return [{"id": u.id, "name": u.name} for u in obj.interface_people.all()]

# --- Project Group ---
class ProjectGroupCreate(Schema):
    name: str
    domain_id: str
    manager_ids: List[str] = Field([])
    remark: Optional[str] = None

class ProjectGroupUpdate(Schema):
    name: Optional[str] = None
    domain_id: Optional[str] = None
    manager_ids: Optional[List[str]] = Field(None)
    remark: Optional[str] = None

class ProjectGroupOut(ModelSchema):
    domain_info: dict = Field(None)
    managers_info: List[dict] = Field([])
    class Meta:
        model = ProjectGroup
        fields = "__all__"

    @staticmethod
    def resolve_domain_info(obj):
        if obj.domain:
            return {"id": obj.domain.id, "name": obj.domain.name}
        return None

    @staticmethod
    def resolve_managers_info(obj):
        return [{"id": u.id, "name": u.name} for u in obj.managers.all()]

# --- Project Component ---
class ProjectComponentCreate(Schema):
    name: str
    group_id: str
    linked_project_id: Optional[str] = None
    manager_ids: List[str] = Field([])
    remark: Optional[str] = None

class ProjectComponentUpdate(Schema):
    name: Optional[str] = None
    group_id: Optional[str] = None
    linked_project_id: Optional[str] = None
    manager_ids: Optional[List[str]] = Field(None)
    remark: Optional[str] = None

class ProjectComponentOut(ModelSchema):
    group_info: dict = Field(None)
    managers_info: List[dict] = Field([])
    linked_project_info: Optional[dict] = Field(None)
    milestone_info: Optional[dict] = Field(None)

    class Meta:
        model = ProjectComponent
        fields = "__all__"

    @staticmethod
    def resolve_group_info(obj):
        if obj.group:
            return {"id": obj.group.id, "name": obj.group.name}
        return None

    @staticmethod
    def resolve_managers_info(obj):
        return [{"id": u.id, "name": u.name} for u in obj.managers.all()]

    @staticmethod
    def resolve_linked_project_info(obj):
        if obj.linked_project:
            return {"id": obj.linked_project.id, "name": obj.linked_project.name}
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

# --- Dashboard Schemas ---
class DashboardComponent(Schema):
    id: str
    name: str
    managers: List[str]
    project_name: Optional[str] = None
    milestone: Optional[dict] = None

class DashboardGroup(Schema):
    id: str
    name: str
    managers: List[str]
    components: List[DashboardComponent]

class DashboardDomain(Schema):
    id: str
    name: str
    interface_people: List[str]
    groups: List[DashboardGroup]
