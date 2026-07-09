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


class ReleasePlanCalendarDay(Schema):
    date: date
    items: List[ReleasePlanOut] = Field(default_factory=list)


class ReleasePlanVersionStat(Schema):
    version_type: str
    version_type_label: str
    count: int


class ReleasePlanCalendarOut(Schema):
    total: int
    upcoming_count: int
    active_project_count: int
    start_date: date
    end_date: date
    version_stats: List[ReleasePlanVersionStat] = Field(default_factory=list)
    days: List[ReleasePlanCalendarDay] = Field(default_factory=list)
