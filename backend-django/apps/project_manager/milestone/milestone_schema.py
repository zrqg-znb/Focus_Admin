from ninja import Schema, ModelSchema, Field
from typing import Optional, List
from datetime import date, datetime
from .milestone_model import Milestone, MilestoneQGConfig, MilestoneRiskItem


class MilestoneUpdateSchema(Schema):
    qg1_date: Optional[date] = None
    qg2_date: Optional[date] = None
    qg3_date: Optional[date] = None
    qg4_date: Optional[date] = None
    qg5_date: Optional[date] = None
    qg6_date: Optional[date] = None
    qg7_date: Optional[date] = None
    qg8_date: Optional[date] = None


class MilestoneBoardSchema(Schema):
    id: str  # Milestone ID
    project_id: str
    project_name: str
    project_domain: str
    manager_names: List[str]
    qg1_date: Optional[date]
    qg2_date: Optional[date]
    qg3_date: Optional[date]
    qg4_date: Optional[date]
    qg5_date: Optional[date]
    qg6_date: Optional[date]
    qg7_date: Optional[date]
    qg8_date: Optional[date]
    
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


class QGConfigOut(ModelSchema):
    class Meta:
        model = MilestoneQGConfig
        fields = ["id", "milestone", "qg_name", "target_di", "enabled"]


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
