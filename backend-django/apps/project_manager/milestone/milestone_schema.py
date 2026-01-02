from ninja import Schema, ModelSchema, Field
from typing import Optional, List
from datetime import date
from .milestone_model import Milestone

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
