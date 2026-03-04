from typing import List

from ninja import Query, Router
from ninja.pagination import paginate

from common.fu_auth import BearerAuth as GlobalAuth
from common.fu_pagination import MyPagination

from . import requirement_services as requirement_service
from .requirement_schemas import (
    AssignOwnerSchema,
    BatchActionOut,
    RequirementBatchArchiveSchema,
    RequirementBatchAssignOwnerSchema,
    RequirementBatchAssignReviewerSchema,
    RequirementBatchPrioritySchema,
    RequirementCommentCreateSchema,
    RequirementCommentOut,
    RequirementCreateChildSchema,
    RequirementCreateSchema,
    RequirementDashboardSummary,
    RequirementFilterSchema,
    RequirementLogOut,
    RequirementOut,
    RequirementReviewSchema,
    RequirementSubmitSchema,
    RequirementTransitionSchema,
    RequirementTreeQuerySchema,
    RequirementUpdateSchema,
    TransferReviewerSchema,
)

router = Router(tags=["RequirementCenter"], auth=GlobalAuth())


@router.post("/", response=RequirementOut, summary="创建需求")
def create_requirement(request, data: RequirementCreateSchema):
    return requirement_service.create_requirement(request, data)


@router.get("/", response=List[RequirementOut], summary="需求分页列表")
@paginate(MyPagination)
def list_requirements(request, filters: RequirementFilterSchema = Query(...)):
    return requirement_service.list_requirements(filters)


@router.get("/tree", response=List[RequirementOut], summary="需求树列表")
def list_requirements_tree(request, filters: RequirementTreeQuerySchema = Query(...)):
    return requirement_service.query_requirement_tree(filters)


@router.get("/dashboard/summary", response=RequirementDashboardSummary, summary="需求统计概览")
def get_dashboard_summary(request):
    return requirement_service.get_dashboard_summary()


@router.post("/batch/assign-reviewer", response=BatchActionOut, summary="批量分配评审人")
def batch_assign_reviewer(request, data: RequirementBatchAssignReviewerSchema):
    return requirement_service.batch_assign_reviewer(
        request,
        data.requirement_ids,
        data.reviewer_id,
        data.note or "",
    )


@router.post("/batch/assign-owner", response=BatchActionOut, summary="批量分配责任人")
def batch_assign_owner(request, data: RequirementBatchAssignOwnerSchema):
    return requirement_service.batch_assign_owner(
        request,
        data.requirement_ids,
        data.owner_id,
        data.note or "",
    )


@router.post("/batch/priority", response=BatchActionOut, summary="批量调整优先级")
def batch_update_priority(request, data: RequirementBatchPrioritySchema):
    return requirement_service.batch_update_priority(
        request,
        data.requirement_ids,
        data.priority,
        data.note or "",
    )


@router.post("/batch/archive", response=BatchActionOut, summary="批量归档")
def batch_archive(request, data: RequirementBatchArchiveSchema):
    return requirement_service.batch_archive(
        request,
        data.requirement_ids,
        data.note or "",
    )


@router.get("/{requirement_id}", response=RequirementOut, summary="需求详情")
def get_requirement(request, requirement_id: str):
    return requirement_service.get_requirement(requirement_id)


@router.put("/{requirement_id}", response=RequirementOut, summary="更新需求")
def update_requirement(request, requirement_id: str, data: RequirementUpdateSchema):
    return requirement_service.update_requirement(request, requirement_id, data)


@router.post("/{requirement_id}/children", response=RequirementOut, summary="拆解创建子需求")
def create_requirement_child(request, requirement_id: str, data: RequirementCreateChildSchema):
    return requirement_service.create_child_requirement(request, requirement_id, data)


@router.get("/{requirement_id}/children", response=List[RequirementOut], summary="子需求列表")
def list_requirement_children(request, requirement_id: str):
    return requirement_service.list_requirement_children(requirement_id)


@router.post("/{requirement_id}/submit", response=RequirementOut, summary="提交需求")
def submit_requirement(request, requirement_id: str, data: RequirementSubmitSchema):
    return requirement_service.submit_requirement(request, requirement_id, data.note or "")


@router.post("/{requirement_id}/review", response=RequirementOut, summary="评审需求")
def review_requirement(request, requirement_id: str, data: RequirementReviewSchema):
    return requirement_service.review_requirement(
        request,
        requirement_id,
        data.action,
        data.note or "",
    )


@router.post("/{requirement_id}/transfer-reviewer", response=RequirementOut, summary="转交评审人")
def transfer_reviewer(request, requirement_id: str, data: TransferReviewerSchema):
    return requirement_service.transfer_reviewer(
        request,
        requirement_id,
        data.reviewer_id,
        data.note or "",
    )


@router.post("/{requirement_id}/assign-owner", response=RequirementOut, summary="分配责任人")
def assign_owner(request, requirement_id: str, data: AssignOwnerSchema):
    return requirement_service.assign_owner(
        request,
        requirement_id,
        data.owner_id,
        data.note or "",
    )


@router.post("/{requirement_id}/transition", response=RequirementOut, summary="状态流转")
def transition_requirement(request, requirement_id: str, data: RequirementTransitionSchema):
    return requirement_service.transition_requirement(
        request,
        requirement_id,
        data.action,
        data.note or "",
    )


@router.post("/{requirement_id}/comments", response=RequirementCommentOut, summary="新增评论")
def create_comment(request, requirement_id: str, data: RequirementCommentCreateSchema):
    return requirement_service.create_comment(
        request,
        requirement_id,
        data.content,
        data.mention_ids,
    )


@router.get("/{requirement_id}/comments", response=List[RequirementCommentOut], summary="评论列表")
def list_comments(request, requirement_id: str):
    return requirement_service.list_comments(requirement_id)


@router.get("/{requirement_id}/logs", response=List[RequirementLogOut], summary="操作日志列表")
def list_logs(request, requirement_id: str):
    return requirement_service.list_logs(requirement_id)
