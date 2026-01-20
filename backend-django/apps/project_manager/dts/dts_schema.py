from ninja import Schema
from typing import List, Optional
from datetime import date

class DtsDataSchema(Schema):
    di: float
    target_di: float
    today_in_di: float
    today_out_di: float
    solve_rate: str
    critical_solve_rate: str
    suggestion_num: int
    minor_num: int
    major_num: int
    fatal_num: int

class DtsTeamSchema(Schema):
    id: str
    team_name: str
    latest_data: Optional[DtsDataSchema] = None
    children: List['DtsTeamSchema'] = []

class DtsDashboardSchema(Schema):
    project_id: str
    root_teams: List[DtsTeamSchema]

class DtsProjectOverviewSchema(Schema):
    project_id: str
    project_name: str
    project_domain: str
    project_type: str
    project_managers: str
    ws_id: str
    root_teams_count: int
    # We don't have sync time in model yet, use today's date if data exists
    has_data_today: bool

class DtsSyncResponse(Schema):
    success: bool
    message: str

class DtsPageResultSchema(Schema):
    pageNo: int
    pageSize: int
    total: int
    currentPageNo: int
    npage: bool

class DtsDefectSchema(Schema):
    defectNo: str
    brief: str
    severity: str
    currentTeam: str
    currentHandler: str
    currentStageStayDay: int
    progress: str

class DtsDefectListResponseSchema(Schema):
    pageResult: DtsPageResultSchema
    dataList: List[DtsDefectSchema]
