from ninja import Schema, ModelSchema
from typing import List, Optional
from datetime import datetime
from .models import ComplianceRecord, ComplianceBranch

class ComplianceBranchSchema(ModelSchema):
    class Config:
        model = ComplianceBranch
        model_fields = ['id', 'branch_name', 'status', 'remark']

class ComplianceRecordSchema(ModelSchema):
    branches: List[ComplianceBranchSchema] = []
    
    class Config:
        model = ComplianceRecord
        model_fields = ['id', 'change_id', 'title', 'update_time', 'url', 'status', 'remark']

class ComplianceUpdateSchema(Schema):
    status: int
    remark: Optional[str] = None

class UserComplianceStatSchema(Schema):
    user_id: str
    user_name: str
    avatar: Optional[str]
    post_name: Optional[str]
    # Change/Record counts
    total_count: int
    unresolved_count: int
    fixed_count: int
    no_risk_count: int
    # Branch counts
    total_branch_count: int
    unresolved_branch_count: int
    fixed_branch_count: int
    no_risk_branch_count: int

class PostComplianceStatSchema(Schema):
    post_id: str
    post_name: str
    user_count: int
    # Change/Record counts
    total_risk_count: int
    unresolved_count: int
    # Branch counts
    total_branch_count: int
    unresolved_branch_count: int

class OverviewSummarySchema(Schema):
    total_risks: int # Total changes
    unresolved_risks: int # Unresolved changes
    total_branch_risks: int # Total branches
    unresolved_branch_risks: int # Unresolved branches
    affected_users: int
    items: List[PostComplianceStatSchema]

class DetailSummarySchema(Schema):
    total_risks: int
    unresolved_risks: int
    fixed_risks: int
    no_risk_risks: int
    # Branch summaries
    total_branch_risks: int
    unresolved_branch_risks: int
    fixed_branch_risks: int
    no_risk_branch_risks: int
    items: List[UserComplianceStatSchema]
