from typing import Any

from ninja import Schema


class ProjectIn(Schema):
    """项目维护请求。"""

    name: str
    code: str
    description: str = ''
    is_active: bool = True
    initial_responsibility_ids: list[str] = []


class ResponsibilityIn(Schema):
    """责任田维护请求。"""

    name: str
    code: str
    caretaker_ids: list[str] = []
    description: str = ''
    is_active: bool = True


class ProjectResponsibilityIn(Schema):
    """项目责任田关联请求。"""

    project_id: str
    responsibility_id: str
    is_active: bool = True
    remark: str = ''


class BatchProjectResponsibilityIn(Schema):
    """矩阵批量建立项目责任田关系请求。"""

    project_ids: list[str]
    responsibility_ids: list[str]
    remark: str = ''


class CaretakerIn(Schema):
    """新增责任田看护人请求。"""

    user_id: str
    comment: str = ''


class ReportIn(Schema):
    """机器接入扫描报告请求。"""

    project_id: str
    responsibility_id: str
    tool_name: str
    report: dict[str, Any]


class ShieldApplicationIn(Schema):
    """屏蔽申请请求。"""

    finding_ids: list[str]
    approver_id: str
    reason: str


class AuditIn(Schema):
    """屏蔽申请审批请求。"""

    comment: str = ''
