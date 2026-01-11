from ninja import Schema
from typing import List, Optional, Dict, Any
from datetime import date, datetime

class ProjectConfigSchema(Schema):
    id: int
    name: str
    description: Optional[str] = None
    project_category: Optional[str] = None
    project_owner: Optional[str] = None
    codecheck_id: Optional[str] = None
    binscope_id: Optional[str] = None
    cooddy_id: Optional[str] = None
    compiletion_check_id: Optional[str] = None
    build_check_id: Optional[str] = None
    build_project_id: Optional[str] = None
    codecov_id: Optional[str] = None
    fossbot_id: Optional[str] = None
    is_subscribed: bool = False
    created_at: datetime
    updated_at: datetime

class ProjectConfigCreateSchema(Schema):
    name: str
    description: Optional[str] = None
    project_category: Optional[str] = None
    project_owner: Optional[str] = None
    codecheck_id: Optional[str] = None
    binscope_id: Optional[str] = None
    cooddy_id: Optional[str] = None
    compiletion_check_id: Optional[str] = None
    build_check_id: Optional[str] = None
    build_project_id: Optional[str] = None
    codecov_id: Optional[str] = None
    fossbot_id: Optional[str] = None

class ProjectDailyDataSchema(Schema):
    id: int
    project_id: int
    date: date
    test_cases_count: int
    test_cases_passed: int
    compile_standard_options: Dict[str, Any]
    build_standard_options: Dict[str, Any]
    extra_data: Dict[str, Any]
    created_at: datetime

class SubscriptionSchema(Schema):
    id: int
    user_id: int
    project: ProjectConfigSchema
    subscribed_at: datetime
    is_active: bool

class SubscribeInputSchema(Schema):
    project_id: int
