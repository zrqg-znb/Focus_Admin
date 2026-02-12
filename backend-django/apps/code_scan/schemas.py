from typing import Optional, List
from uuid import UUID
from ninja import Schema, ModelSchema
from apps.code_scan.models import ScanProject, ScanTask, ScanResult, ShieldApplication

class ScanProjectSchema(ModelSchema):
    # 显式覆盖自动生成的类型，确保序列化时兼容 UUID 对象
    id: UUID
    project_key: UUID
    caretaker_name: Optional[str] = None

    class Config:
        model = ScanProject
        model_fields = "__all__"
    
    @staticmethod
    def resolve_caretaker_name(obj):
        return obj.caretaker.name if obj.caretaker else None

class ScanProjectCreateSchema(Schema):
    name: str
    repo_url: str
    branch: str = "master"
    description: Optional[str] = None
    caretaker_id: Optional[str] = None

class ScanTaskSchema(ModelSchema):
    class Config:
        model = ScanTask
        model_fields = "__all__"

class ScanResultSchema(ModelSchema):
    class Config:
        model = ScanResult
        model_fields = "__all__"

class ShieldApplicationSchema(Schema):
    id: str
    result_id: str
    applicant_id: str
    approver_id: Optional[str] = None
    reason: str
    status: str
    audit_comment: Optional[str] = None
    applicant_name: Optional[str] = None
    approver_name: Optional[str] = None
    sys_create_datetime: Optional[str] = None
    # Context info
    file_path: Optional[str] = None
    defect_description: Optional[str] = None
    severity: Optional[str] = None
    tool_name: Optional[str] = None
    help_info: Optional[str] = None
    code_snippet: Optional[str] = None

class ShieldRecordSchema(Schema):
    id: str
    result_id: str
    status: str
    reason: str
    audit_comment: Optional[str] = None
    applicant_name: Optional[str] = None
    approver_name: Optional[str] = None
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None

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
    file_ext: Optional[str] = "xml" # File extension, default to xml

class ProjectOverviewSchema(Schema):
    project_id: str
    project_name: str
    tool_counts: dict[str, int]
    total: int
    latest_time: Optional[str] = None

class LatestScanResultSchema(Schema):
    id: str
    task_id: str
    tool_name: str
    file_path: str
    line_number: int
    defect_type: str
    severity: str
    description: str
    fingerprint: str
    shield_status: str
    help_info: Optional[str] = None
    code_snippet: Optional[str] = None
    sys_create_datetime: Optional[str] = None

class PaginatedScanResultSchema(Schema):
    items: List[LatestScanResultSchema]
    total: int

class PaginatedScanProjectSchema(Schema):
    items: List[ScanProjectSchema]
    total: int

class PaginatedScanTaskSchema(Schema):
    items: List[ScanTaskSchema]
    total: int

class PaginatedShieldApplicationSchema(Schema):
    items: List[ShieldApplicationSchema]
    total: int

class PaginatedProjectOverviewSchema(Schema):
    items: List[ProjectOverviewSchema]
    total: int
