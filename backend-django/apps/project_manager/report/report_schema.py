from ninja import Schema
from typing import List, Optional
from datetime import date
from apps.dashboard.schemas import (
    CodeQualitySummary, 
    IterationSummary, 
    DtsSummary,
    QGNode
)

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
    
    # 4. Modules Data
    code_quality: Optional[CodeQualitySummary]
    iteration: Optional[IterationSummary]
    dts_summary: Optional[DtsSummary]
