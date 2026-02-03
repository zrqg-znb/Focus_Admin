from typing import Optional, List
from ninja import Schema, ModelSchema
from datetime import datetime
from apps.tscan.models import TScanProject, TScanTask, TScanResult, TScanShieldApplication

class TScanProjectSchema(ModelSchema):
    class Config:
        model = TScanProject
        model_fields = "__all__"

class TScanProjectCreateSchema(Schema):
    name: str
    repo_url: str
    branch: str = "master"
    build_cmd: str
    docker_image: str
    description: Optional[str] = None

class TScanTaskSchema(ModelSchema):
    class Config:
        model = TScanTask
        model_fields = "__all__"

class TScanResultSchema(ModelSchema):
    class Config:
        model = TScanResult
        model_fields = "__all__"

class TScanShieldApplicationSchema(ModelSchema):
    applicant_name: Optional[str] = None
    approver_name: Optional[str] = None

    class Config:
        model = TScanShieldApplication
        model_fields = "__all__"

class ShieldApplySchema(Schema):
    result_ids: List[str]
    approver_id: str
    reason: str

class ShieldAuditSchema(Schema):
    application_id: str
    status: str  # Approved or Rejected
    audit_comment: Optional[str] = None
