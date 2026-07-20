"""CMC 贡献看板 API Schema。"""

from datetime import date, datetime
from typing import List

from ninja import Schema
from pydantic import Field


class CmcDateRangeQuery(Schema):
    """看板和表格共用的日期范围。"""

    startDate: date
    endDate: date


class CmcSummaryOut(Schema):
    """CMC 看板汇总指标。"""

    cnt_total: int = 0
    zero_comment_mr_count: int = 0
    zero_comment_rate: float = 0
    effective_comment_count: int = 0
    effective_comment_density: float | None = None
    checked_mr_lines: int = 0
    cmt_lines: int = 0
    contributor_count: int = 0
    major_comments_cnt: int = 0
    fatal_comments_cnt: int = 0
    minor_comments_cnt: int = 0
    sugge_comments_cnt: int = 0
    cmt_issue: int = 0


class CmcPersonRecordOut(Schema):
    """按人员聚合后的表格行。"""

    user: str
    cnt_total: int
    zero_comment_mr_count: int
    zero_comment_rate: float
    major_comments_cnt: int
    fatal_comments_cnt: int
    minor_comments_cnt: int
    sugge_comments_cnt: int
    cmt_issue: int
    effective_comment_count: int
    effective_comment_density: float | None = None
    checked_mr_lines: int
    cmt_lines: int


class CmcPersonPageOut(Schema):
    """人员汇总分页响应。"""

    items: List[CmcPersonRecordOut] = Field(default_factory=list)
    total: int = 0


class CmcSyncRunIn(Schema):
    """管理员手动补数请求。"""

    startDate: date
    endDate: date


class CmcSyncTaskOut(Schema):
    """同步任务状态。"""

    id: str
    trigger_type: str
    status: str
    start_date: date
    end_date: date
    requested_dates: list[str] = Field(default_factory=list)
    synced_dates: list[str] = Field(default_factory=list)
    fetched_pages: int
    fetched_rows: int
    error_message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
