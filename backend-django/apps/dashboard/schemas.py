from ninja import Schema
from typing import List, Optional
from datetime import date

class CodeQualitySummary(Schema):
    total_projects: int
    total_modules: int
    total_loc: int
    total_issues: int  # 危险函数等问题总数
    avg_duplication_rate: float
    health_score: float # 模拟一个健康分

class IterationSummary(Schema):
    active_iterations: int
    delayed_iterations: int
    total_req_count: int
    completion_rate: float

class PerformanceSummary(Schema):
    total_indicators: int
    abnormal_count: int
    coverage_rate: float
    
class CoreMetricsSchema(Schema):
    code_quality: CodeQualitySummary
    iteration: IterationSummary
    performance: PerformanceSummary

class NameValue(Schema):
    name: str
    value: int

class ProjectDistribution(Schema):
    by_domain: List[NameValue]
    by_type: List[NameValue]

class UpcomingMilestone(Schema):
    project_name: str
    project_manager: str
    qg_name: str
    qg_date: date
    days_left: int

class QGNode(Schema):
    name: str
    date: date
    status: str # 'completed', 'pending', 'delayed'

class FavoriteProjectDetail(Schema):
    id: str
    name: str
    domain: str
    type: str
    managers: str
    loc: int
    health_score: float
    current_iteration: Optional[str]
    iteration_progress: float
    milestones: List[QGNode]
    
class DashboardSummarySchema(Schema):
    code_quality: CodeQualitySummary
    iteration: IterationSummary
    performance: PerformanceSummary
    project_distribution: ProjectDistribution
    upcoming_milestones: List[UpcomingMilestone]
    favorite_projects: List[FavoriteProjectDetail]
