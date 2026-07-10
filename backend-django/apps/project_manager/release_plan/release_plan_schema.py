from datetime import date
from typing import List, Optional

from ninja import Field, Schema


class ReleasePlanFilterSchema(Schema):
    keyword: Optional[str] = Field(None, description="项目/编码/分支关键字")
    project_id: Optional[str] = Field(None, description="项目ID")
    branch_name: Optional[str] = Field(None, description="分支名")
    version_type: Optional[str] = Field(None, description="版本类型")
    scenario: Optional[str] = Field(None, description="发布场景")
    platform_keyword: Optional[str] = Field(None, description="平台关键字")
    vehicle_keyword: Optional[str] = Field(None, description="车型关键字")
    release_date_start: Optional[date] = Field(None, description="发布日期开始")
    release_date_end: Optional[date] = Field(None, description="发布日期结束")


class ReleasePlanOut(Schema):
    id: str
    project_id: str
    project_name: str
    project_code: str
    project_domain: str
    manager_names: List[str] = Field(default_factory=list)
    branch_name: str
    release_date: date
    version_type: str
    version_type_label: str
    scenario: str
    idvp_platform_id: Optional[str] = None
    idvp_platform_name: Optional[str] = None
    cdc_platform_id: Optional[str] = None
    cdc_platform_name: Optional[str] = None
    platform_name: str
    release_vehicles: List[str] = Field(default_factory=list)
    order: int


class ReleasePlanProjectGroupOut(Schema):
    project_id: str
    project_name: str
    project_code: str
    project_domain: str
    manager_names: List[str] = Field(default_factory=list)
    plan_count: int
    branch_count: int
    next_release_date: Optional[date] = None
    latest_release_date: Optional[date] = None
    branch_names: List[str] = Field(default_factory=list)
    version_types: List[str] = Field(default_factory=list)
    platform_names: List[str] = Field(default_factory=list)
    release_vehicles: List[str] = Field(default_factory=list)
    plans: List[ReleasePlanOut] = Field(default_factory=list)


class ReleasePlanWeeklyTrendOut(Schema):
    week: str
    week_start: date
    count: int


class ReleasePlanVersionWeeklyTrendOut(Schema):
    week: str
    week_start: date
    version_type: str
    count: int


class ReleasePlanProjectBoardOut(Schema):
    items: List[ReleasePlanProjectGroupOut] = Field(default_factory=list)
    total: int
    weekly_trend: List[ReleasePlanWeeklyTrendOut] = Field(default_factory=list)
    version_weekly_trend: List[ReleasePlanVersionWeeklyTrendOut] = Field(
        default_factory=list
    )
