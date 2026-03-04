from datetime import datetime
from typing import Dict, List, Optional

from django.utils import timezone
from ninja import Field, ModelSchema, Schema

from .requirement_model import (
    Requirement,
    RequirementComment,
    RequirementLog,
    RequirementStatus,
)


class UserBrief(Schema):
    id: str
    username: str
    name: Optional[str] = None
    email: Optional[str] = None


def _to_user_brief(user) -> Optional[Dict]:
    if not user:
        return None
    return {
        "id": str(user.id),
        "username": user.username,
        "name": user.name,
        "email": user.email,
    }


class RequirementCreateSchema(Schema):
    title: str = Field(..., description="需求标题")
    description: Optional[str] = Field("", description="需求描述")
    business_value: Optional[str] = Field("", description="业务价值")
    acceptance_criteria: Optional[str] = Field("", description="验收标准")
    type: str = Field("", description="需求类型")
    source: str = Field("", description="需求来源")
    priority: str = Field("medium", description="优先级")
    reviewer_id: Optional[str] = Field(None, description="评审人ID")
    owner_id: Optional[str] = Field(None, description="责任人ID")
    attachments: Optional[List[str]] = Field(default_factory=list, description="附件文件ID列表")
    review_due_at: Optional[datetime] = Field(None, description="评审截止时间")
    dev_due_at: Optional[datetime] = Field(None, description="开发截止时间")


class RequirementUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    business_value: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    type: Optional[str] = None
    source: Optional[str] = None
    priority: Optional[str] = None
    reviewer_id: Optional[str] = None
    owner_id: Optional[str] = None
    attachments: Optional[List[str]] = None
    review_due_at: Optional[datetime] = None
    dev_due_at: Optional[datetime] = None


class RequirementFilterSchema(Schema):
    keyword: Optional[str] = Field(None, description="关键字")
    status: Optional[str] = Field(None, description="状态")
    priority: Optional[str] = Field(None, description="优先级")
    type: Optional[str] = Field(None, description="需求类型")
    source: Optional[str] = Field(None, description="需求来源")
    reviewer_id: Optional[str] = Field(None, description="评审人ID")
    owner_id: Optional[str] = Field(None, description="责任人ID")
    overdue: Optional[bool] = Field(None, description="是否逾期")


class RequirementTreeQuerySchema(RequirementFilterSchema):
    root_id: Optional[str] = Field(None, description="根需求ID")


class RequirementSubmitSchema(Schema):
    note: Optional[str] = Field("", description="提交说明")


class RequirementReviewSchema(Schema):
    action: str = Field(..., description="accept/reject/need_info")
    note: Optional[str] = Field("", description="评审意见")


class TransferReviewerSchema(Schema):
    reviewer_id: str = Field(..., description="新评审人ID")
    note: Optional[str] = Field("", description="转审备注")


class AssignOwnerSchema(Schema):
    owner_id: str = Field(..., description="责任人ID")
    note: Optional[str] = Field("", description="分配备注")


class RequirementTransitionSchema(Schema):
    action: str = Field(..., description="planned/in_dev/in_acceptance/done/archive")
    note: Optional[str] = Field("", description="流转备注")


class RequirementCreateChildSchema(Schema):
    title: str = Field(..., description="子需求标题")
    description: Optional[str] = Field("", description="子需求描述")
    business_value: Optional[str] = Field("", description="业务价值")
    acceptance_criteria: Optional[str] = Field("", description="验收标准")
    type: Optional[str] = Field(None, description="需求类型（默认继承父需求）")
    source: Optional[str] = Field(None, description="需求来源（默认继承父需求）")
    priority: Optional[str] = Field(None, description="优先级（默认继承父需求）")
    reviewer_id: Optional[str] = Field(None, description="评审人ID（默认继承父需求）")
    owner_id: Optional[str] = Field(None, description="责任人ID（默认继承父需求）")
    attachments: Optional[List[str]] = Field(default_factory=list, description="附件文件ID列表")
    dev_due_at: Optional[datetime] = Field(None, description="开发截止时间")


class RequirementCommentCreateSchema(Schema):
    content: str = Field(..., description="评论内容")
    mention_ids: List[str] = Field(default_factory=list, description="@用户ID列表")


class RequirementBatchAssignReviewerSchema(Schema):
    requirement_ids: List[str] = Field(..., description="需求ID列表")
    reviewer_id: str = Field(..., description="评审人ID")
    note: Optional[str] = Field("", description="批量备注")


class RequirementBatchAssignOwnerSchema(Schema):
    requirement_ids: List[str] = Field(..., description="需求ID列表")
    owner_id: str = Field(..., description="责任人ID")
    note: Optional[str] = Field("", description="批量备注")


class RequirementBatchPrioritySchema(Schema):
    requirement_ids: List[str] = Field(..., description="需求ID列表")
    priority: str = Field(..., description="优先级")
    note: Optional[str] = Field("", description="批量备注")


class RequirementBatchArchiveSchema(Schema):
    requirement_ids: List[str] = Field(..., description="需求ID列表")
    note: Optional[str] = Field("", description="批量备注")


class BatchActionOut(Schema):
    msg: str
    count: int
    skipped_ids: List[str] = Field(default_factory=list)


class RequirementOut(ModelSchema):
    id: str
    parent_id: Optional[str] = None
    submitter_info: Optional[UserBrief] = None
    reviewer_info: Optional[UserBrief] = None
    owner_info: Optional[UserBrief] = None
    watcher_ids: List[str] = Field(default_factory=list)
    children: List["RequirementOut"] = Field(default_factory=list)

    class Meta:
        model = Requirement
        fields = "__all__"
        exclude = ["submitter", "reviewer", "owner", "parent"]

    @staticmethod
    def resolve_id(obj):
        return str(getattr(obj, "id", "") or "")

    @staticmethod
    def resolve_parent_id(obj):
        parent_id = getattr(obj, "parent_id", None)
        return str(parent_id) if parent_id else None

    @staticmethod
    def resolve_submitter_id(obj):
        submitter_id = getattr(obj, "submitter_id", None)
        return str(submitter_id) if submitter_id else None

    @staticmethod
    def resolve_reviewer_id(obj):
        reviewer_id = getattr(obj, "reviewer_id", None)
        return str(reviewer_id) if reviewer_id else None

    @staticmethod
    def resolve_owner_id(obj):
        owner_id = getattr(obj, "owner_id", None)
        return str(owner_id) if owner_id else None

    @staticmethod
    def resolve_sys_creator_id(obj):
        sys_creator_id = getattr(obj, "sys_creator_id", None)
        return str(sys_creator_id) if sys_creator_id else None

    @staticmethod
    def resolve_sys_modifier_id(obj):
        sys_modifier_id = getattr(obj, "sys_modifier_id", None)
        return str(sys_modifier_id) if sys_modifier_id else None

    @staticmethod
    def resolve_submitter_info(obj):
        return _to_user_brief(getattr(obj, "submitter", None))

    @staticmethod
    def resolve_reviewer_info(obj):
        return _to_user_brief(getattr(obj, "reviewer", None))

    @staticmethod
    def resolve_owner_info(obj):
        return _to_user_brief(getattr(obj, "owner", None))

    @staticmethod
    def resolve_watcher_ids(obj):
        return [str(item.user_id) for item in obj.watchers.filter(is_deleted=False).only("user_id")]

    @staticmethod
    def resolve_children(obj):
        if hasattr(obj, "children_items"):
            return getattr(obj, "children_items") or []
        return []

    @staticmethod
    def resolve_is_review_overdue(obj):
        if obj.status not in RequirementStatus.REVIEW_PENDING:
            return False
        if not obj.review_due_at:
            return False
        return obj.review_due_at < timezone.now()

    @staticmethod
    def resolve_is_dev_overdue(obj):
        if obj.status not in RequirementStatus.DEV_PENDING:
            return False
        if not obj.dev_due_at:
            return False
        return obj.dev_due_at < timezone.now()

    class Config:
        from_attributes = True


class RequirementCommentOut(ModelSchema):
    id: str
    commenter_info: Optional[UserBrief] = None

    class Meta:
        model = RequirementComment
        fields = "__all__"
        exclude = ["commenter"]

    @staticmethod
    def resolve_id(obj):
        return str(getattr(obj, "id", "") or "")

    @staticmethod
    def resolve_commenter_info(obj):
        return _to_user_brief(getattr(obj, "commenter", None))

    @staticmethod
    def resolve_requirement_id(obj):
        requirement_id = getattr(obj, "requirement_id", None)
        return str(requirement_id) if requirement_id else ""

    @staticmethod
    def resolve_commenter_id(obj):
        commenter_id = getattr(obj, "commenter_id", None)
        return str(commenter_id) if commenter_id else None

    @staticmethod
    def resolve_sys_creator_id(obj):
        sys_creator_id = getattr(obj, "sys_creator_id", None)
        return str(sys_creator_id) if sys_creator_id else None

    @staticmethod
    def resolve_sys_modifier_id(obj):
        sys_modifier_id = getattr(obj, "sys_modifier_id", None)
        return str(sys_modifier_id) if sys_modifier_id else None

    class Config:
        from_attributes = True


class RequirementLogOut(ModelSchema):
    id: str
    operator_info: Optional[UserBrief] = None

    class Meta:
        model = RequirementLog
        fields = "__all__"
        exclude = ["operator"]

    @staticmethod
    def resolve_id(obj):
        return str(getattr(obj, "id", "") or "")

    @staticmethod
    def resolve_operator_info(obj):
        return _to_user_brief(getattr(obj, "operator", None))

    @staticmethod
    def resolve_requirement_id(obj):
        requirement_id = getattr(obj, "requirement_id", None)
        return str(requirement_id) if requirement_id else ""

    @staticmethod
    def resolve_operator_id(obj):
        operator_id = getattr(obj, "operator_id", None)
        return str(operator_id) if operator_id else None

    @staticmethod
    def resolve_sys_creator_id(obj):
        sys_creator_id = getattr(obj, "sys_creator_id", None)
        return str(sys_creator_id) if sys_creator_id else None

    @staticmethod
    def resolve_sys_modifier_id(obj):
        sys_modifier_id = getattr(obj, "sys_modifier_id", None)
        return str(sys_modifier_id) if sys_modifier_id else None

    class Config:
        from_attributes = True


class DashboardCountItem(Schema):
    key: str
    label: str
    count: int


class RequirementDashboardSummary(Schema):
    total_count: int
    open_count: int
    closed_count: int
    overdue_count: int
    review_overdue_count: int
    dev_overdue_count: int
    status_stats: List[DashboardCountItem]
    priority_stats: List[DashboardCountItem]
    reviewer_stats: List[DashboardCountItem]
    owner_stats: List[DashboardCountItem]


RequirementOut.update_forward_refs()
