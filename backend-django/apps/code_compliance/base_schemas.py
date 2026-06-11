from datetime import date, datetime
from typing import List, Optional

from ninja import Schema
from pydantic import Field


class ImportErrorRow(Schema):
    row_no: int
    message: str


class ImportResultOut(Schema):
    created_count: int
    updated_count: int
    ignored_count: int
    errors: List[ImportErrorRow] = Field(default_factory=list)


class BindResultOut(Schema):
    created_count: int
    restored_count: int
    removed_count: int
    ignored_count: int


class OrganizationIn(Schema):
    group_id: str
    name: str
    parent_id: Optional[str] = None
    mode: str = "CR"
    domain: str = "cockpit"
    remark: Optional[str] = None
    sort: int = 0


class OrganizationPatch(Schema):
    group_id: Optional[str] = None
    name: Optional[str] = None
    parent_id: Optional[str] = None
    mode: Optional[str] = None
    domain: Optional[str] = None
    remark: Optional[str] = None
    sort: Optional[int] = None


class OrganizationOut(Schema):
    id: str
    group_id: str
    name: str
    parent_id: Optional[str] = None
    parent_name: Optional[str] = None
    mode: str
    mode_label: str
    domain: str
    domain_label: str
    remark: Optional[str] = None
    sort: int
    repository_count: int
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None
    children: List["OrganizationOut"] = Field(default_factory=list)


class RepositoryIn(Schema):
    project_id: str
    project_name: str
    project_url: str = ""
    organization_id: str
    mode: str = "CR"
    responsibility_group_ids: List[str] = Field(default_factory=list)
    repo_type: str = ""
    domain: str = "cockpit"
    remark: Optional[str] = None
    sort: int = 0


class RepositoryPatch(Schema):
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    project_url: Optional[str] = None
    organization_id: Optional[str] = None
    mode: Optional[str] = None
    responsibility_group_ids: Optional[List[str]] = None
    repo_type: Optional[str] = None
    domain: Optional[str] = None
    remark: Optional[str] = None
    sort: Optional[int] = None


class RepositoryOut(Schema):
    id: str
    project_id: str
    project_name: str
    project_url: str
    organization_id: str
    organization_name: str
    organization_group_id: str
    mode: str
    mode_label: str
    responsibility_group_ids: List[str] = Field(default_factory=list)
    responsibility_group_names: List[str] = Field(default_factory=list)
    repo_type: str
    repo_type_label: str
    domain: str
    domain_label: str
    remark: Optional[str] = None
    sort: int
    branch_count: int
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class PaginatedRepositoryOut(Schema):
    items: List[RepositoryOut] = Field(default_factory=list)
    total: int


class BranchIn(Schema):
    branch_name: str
    created_date: Optional[date] = None
    branch_type: str = "other"
    alias: str = ""
    purpose: str = ""
    remark: Optional[str] = None
    is_active: bool = True
    domain: str = "cockpit"
    sort: int = 0


class BranchPatch(Schema):
    branch_name: Optional[str] = None
    created_date: Optional[date] = None
    branch_type: Optional[str] = None
    alias: Optional[str] = None
    purpose: Optional[str] = None
    remark: Optional[str] = None
    is_active: Optional[bool] = None
    domain: Optional[str] = None
    sort: Optional[int] = None


class BranchOut(Schema):
    id: str
    branch_name: str
    created_date: Optional[date] = None
    branch_type: str
    branch_type_label: str
    alias: str
    purpose: str
    remark: Optional[str] = None
    is_active: bool
    domain: str
    domain_label: str
    sort: int
    repository_count: int
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class PaginatedBranchOut(Schema):
    items: List[BranchOut] = Field(default_factory=list)
    total: int


class BranchRepositoryOrganizationOut(Schema):
    id: str
    group_id: str
    name: str
    parent_id: Optional[str] = None
    parent_name: Optional[str] = None
    mode: str
    mode_label: str
    domain: str
    domain_label: str
    remark: Optional[str] = None
    sort: int
    repository_count: int
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None
    repositories: List[RepositoryOut] = Field(default_factory=list)
    children: List["BranchRepositoryOrganizationOut"] = Field(default_factory=list)


class BranchRepositoryRelationOut(Schema):
    branch: BranchOut
    organizations: List[BranchRepositoryOrganizationOut] = Field(default_factory=list)


class RepositoryBranchRelationOut(Schema):
    repository: RepositoryOut
    branches: List[BranchOut] = Field(default_factory=list)


class BatchBindBranchesIn(Schema):
    repository_ids: List[str] = Field(default_factory=list)
    branch_ids: List[str] = Field(default_factory=list)
    mode: str = "append"


class BatchBindRepositoriesIn(Schema):
    branch_ids: List[str] = Field(default_factory=list)
    repository_ids: List[str] = Field(default_factory=list)
    mode: str = "append"


OrganizationOut.update_forward_refs()
BranchRepositoryOrganizationOut.update_forward_refs()
