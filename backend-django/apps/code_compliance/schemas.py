from ninja import Schema, ModelSchema
from typing import List, Optional
from datetime import datetime
from .models import ComplianceRecord

class ComplianceRecordSchema(ModelSchema):
    class Config:
        model = ComplianceRecord
        model_fields = ['id', 'change_id', 'title', 'update_time', 'url', 'missing_branches', 'status', 'remark']

class ComplianceUpdateSchema(Schema):
    status: int
    remark: Optional[str] = None

class UserComplianceStatSchema(Schema):
    user_id: str
    user_name: str
    avatar: Optional[str]
    dept_name: Optional[str]
    total_count: int
    unresolved_count: int
    fixed_count: int
    no_risk_count: int

class DeptComplianceStatSchema(Schema):
    dept_id: str
    dept_name: str
    user_count: int
    total_risk_count: int
    unresolved_count: int

class OverviewSummarySchema(Schema):
    total_risks: int
    unresolved_risks: int
    affected_users: int
    affected_branches: int
    items: List[DeptComplianceStatSchema]

class DetailSummarySchema(Schema):
    total_risks: int
    unresolved_risks: int
    fixed_risks: int
    no_risk_risks: int
    items: List[UserComplianceStatSchema]
