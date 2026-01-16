from ninja import Schema
from typing import List, Optional
from datetime import date
from apps.dashboard.schemas import (
    CodeQualitySummary, 
    IterationSummary, 
    DtsSummary,
)
from apps.project_manager.code_quality.code_quality_schema import ModuleQualityDetailSchema

class RadarIndicator(Schema):
    name: str
    value: float
    max: float = 100.0

class DtsTrendItem(Schema):
    date: str
    critical: int
    major: int
    minor: int
    suggestion: int
    solve_rate: float
    critical_solve_rate: float

class DtsTeamDiItem(Schema):
    team_name: str
    di: float
    target_di: Optional[float] = None

class DtsTeamDiSeries(Schema):
    team_name: str
    values: List[Optional[float]]

class DtsTeamDiTrend(Schema):
    dates: List[str]
    series: List[DtsTeamDiSeries]

class IterationDetailMetrics(Schema):
    sr_num: int = 0
    dr_num: int = 0
    ar_num: int = 0
    sr_breakdown_rate: float = 0.0
    dr_breakdown_rate: float = 0.0
    ar_set_a_rate: float = 0.0
    dr_set_a_rate: float = 0.0
    ar_set_c_rate: float = 0.0
    dr_set_c_rate: float = 0.0

class QGNode(Schema):
    name: str
    date: date
    status: str # 'completed', 'pending', 'delayed'
    has_risk: bool = False
    risk_status: Optional[str] = None # 'pending', 'confirmed', 'normal'

class ProjectReportSchema(Schema):
    project_id: str
    project_name: str
    manager: str
    health_score: float
    health_level: str # 'healthy', 'warning', 'error'
    
    # 1. Radar Data
    radar_data: List[RadarIndicator]
    
    # 2. Milestones (Fishbone)
    milestones: List[QGNode]
    
    # 3. DTS Trend (Last 7 days)
    dts_trend: List[DtsTrendItem]
    dts_team_di: Optional[List[DtsTeamDiItem]] = None
    dts_team_di_trend: Optional[DtsTeamDiTrend] = None
    
    # 4. Modules Data
    code_quality: Optional[CodeQualitySummary]
    code_quality_details: Optional[List[ModuleQualityDetailSchema]] = None
    iteration: Optional[IterationSummary]
    iteration_detail: Optional[IterationDetailMetrics] = None
    dts_summary: Optional[DtsSummary]
