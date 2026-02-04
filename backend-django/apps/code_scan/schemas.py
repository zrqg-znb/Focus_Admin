from typing import Optional, List
from ninja import Schema, ModelSchema
from apps.code_scan.models import ScanProject, ScanTask, ScanResult, ShieldApplication

class ScanProjectSchema(ModelSchema):
    class Config:
        model = ScanProject
        model_fields = "__all__"

class ScanProjectCreateSchema(Schema):
    name: str
    repo_url: str
    branch: str = "master"
    description: Optional[str] = None

class ScanTaskSchema(ModelSchema):
    class Config:
        model = ScanTask
        model_fields = "__all__"

class ScanResultSchema(ModelSchema):
    class Config:
        model = ScanResult
        model_fields = "__all__"

class ShieldApplicationSchema(ModelSchema):
    applicant_name: Optional[str] = None
    approver_name: Optional[str] = None

    class Config:
        model = ShieldApplication
        model_fields = "__all__"

class ShieldApplySchema(Schema):
    result_ids: List[str]
    approver_id: str
    reason: str

class ShieldAuditSchema(Schema):
    application_id: str
    status: str  # Approved or Rejected
    audit_comment: Optional[str] = None

class ChunkUploadSchema(Schema):
    project_key: str
    tool_name: str
    chunk_index: int
    total_chunks: int
    chunk_content: str  # Base64 or plain text content of the chunk
    file_id: str # Unique ID for the file session
