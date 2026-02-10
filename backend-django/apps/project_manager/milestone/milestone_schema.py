from ninja import Schema, ModelSchema, Field
from typing import Optional, List, Dict
from datetime import date, datetime
from .milestone_model import Milestone, MilestoneQGConfig, MilestoneRiskItem, MilestoneRiskLog


class MilestoneUpdateSchema(Schema):
    qg1_date: Optional[date] = None
    qg2_date: Optional[date] = None
    qg3_date: Optional[date] = None
    qg4_date: Optional[date] = None
    qg5_date: Optional[date] = None
    qg6_date: Optional[date] = None
    qg7_date: Optional[date] = None
    qg8_date: Optional[date] = None


class RiskInfo(Schema):
    id: str
    level: str
    description: str
    status: str

class MilestoneBoardSchema(Schema):
    id: str  # Milestone ID
    project_id: str
    project_name: str
    project_domain: str
    manager_names: List[str]
    qg1_date: Optional[date] = None
    qg2_date: Optional[date] = None
    qg3_date: Optional[date] = None
    qg4_date: Optional[date] = None
    qg5_date: Optional[date] = None
    qg6_date: Optional[date] = None
    qg7_date: Optional[date] = None
    qg8_date: Optional[date] = None
    risks: Optional[Dict[str, RiskInfo]] = None # key: QG name, value: RiskInfo
    next_qg: Optional[List[str]] = None
    
    # 允许额外的字段以支持 ORM 映射
    class Config:
        from_attributes = True


class MilestoneOut(ModelSchema):
    class Meta:
        model = Milestone
        fields = "__all__"


class QGConfigIn(Schema):
    qg_name: str
    target_di: Optional[float] = None
    enabled: bool = True
    is_delayed: bool = False


class QGConfigOut(Schema):
    id: str
    milestone_id: str
    qg_name: str
    target_di: Optional[float] = None
    enabled: bool
    is_delayed: bool

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)
    
    @staticmethod
    def resolve_milestone_id(obj):
        return str(obj.milestone.id)


class RiskItemOut(Schema):
    id: str
    config_id: str
    qg_name: str
    milestone_id: str
    project_id: str
    project_name: str
    record_date: date
    risk_type: str
    description: str
    status: str
    manager_confirm_note: str
    manager_confirm_at: Optional[datetime]
    manager_name: Optional[str] = None


class RiskConfirmIn(Schema):
    note: str
    action: str = "confirm"  # confirm | close


class RiskLogOut(Schema):
    id: str
    action: str
    operator_name: str
    note: str
    create_time: datetime
