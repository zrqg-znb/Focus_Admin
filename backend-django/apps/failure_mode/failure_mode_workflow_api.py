from typing import List

from ninja import Router

from common.fu_auth import BearerAuth as GlobalAuth

from apps.failure_mode.failure_mode_schemas import (
    FailureModeCreateSchema,
    FailureModeOutSchema,
    FailureModeProductOutSchema,
    FailureModeProductUpdateSchema,
    FailureModeRoleAssignmentOutSchema,
    FailureModeTaskLogOutSchema,
    FailureModeTaskOutSchema,
    FailureModeTaskCreateSchema,
    FailureModeTaskScopeUpdateSchema,
    FailureModeUpdateSchema,
    ProductFailureModeOutSchema,
    ProductFailureModePageSchema,
    ProductFailureModeSearchSchema,
    ProductRoleAssignmentBatchSaveSchema,
    SaveSuccessSchema,
    TaskCloseSchema,
    TaskFailureModeBindSchema,
    TaskFailureModeLandingOutSchema,
    TaskFailureModeLandingSaveSchema,
    TaskRecallSchema,
    TaskReassignSchema,
    TaskRejectSchema,
    VisibleSubsystemOutSchema,
)
from apps.failure_mode.failure_mode_workflow_services import ProductWorkflowService, TaskWorkflowService

router = Router(tags=['FailureModeWorkflow'], auth=GlobalAuth())


@router.get('/products', response=List[FailureModeProductOutSchema], summary='获取产品(项目)列表')
def list_products(
    request,
    owner_id: str = None,
    project_type: str = None,
    compact: bool = False,
):
    return ProductWorkflowService.list_products(
        request.auth,
        owner_id=owner_id,
        project_type=project_type,
        compact=compact,
    )


@router.post('/product-failure-modes/search', response=ProductFailureModePageSchema, summary='分页搜索产品故障模式基线')
def search_product_failure_modes(request, data: ProductFailureModeSearchSchema):
    return ProductWorkflowService.search_product_failure_modes(request.auth, data)


@router.put('/products/{product_id}/owner', response=FailureModeProductOutSchema, summary='更新产品主版本SE')
def update_product_owner(request, product_id: str, data: FailureModeProductUpdateSchema):
    return ProductWorkflowService.update_product_owner(request.auth, product_id, data.owner_id)


@router.get('/products/{product_id}/failure-modes', response=List[ProductFailureModeOutSchema], summary='获取产品的故障模式基线')
def list_product_failure_modes(request, product_id: str, subsystem: str = None):
    return ProductWorkflowService.list_product_failure_modes(request.auth, product_id, subsystem=subsystem)


@router.get('/products/{product_id}/roles', response=List[FailureModeRoleAssignmentOutSchema], summary='获取产品角色配置')
def list_product_role_assignments(request, product_id: str):
    return ProductWorkflowService.list_product_role_assignments(request.auth, product_id)


@router.put('/products/{product_id}/roles', response=List[FailureModeRoleAssignmentOutSchema], summary='批量保存产品角色配置')
def save_product_role_assignments(request, product_id: str, data: ProductRoleAssignmentBatchSaveSchema):
    return ProductWorkflowService.save_product_role_assignments(
        request.auth,
        product_id,
        [item.dict() for item in data.assignments],
    )


@router.get('/products/{product_id}/visible-subsystems', response=List[VisibleSubsystemOutSchema], summary='获取当前用户对产品可见的子系统')
def list_visible_subsystems(request, product_id: str):
    return ProductWorkflowService.list_visible_subsystems(request.auth, product_id)


@router.get('/tasks', response=List[FailureModeTaskOutSchema], summary='获取工作流任务列表')
def list_tasks(request, status: str = None, product_id: str = None):
    return TaskWorkflowService.list_tasks(request.auth, status=status, product_id=product_id)


@router.get('/tasks/{task_id}', response=FailureModeTaskOutSchema, summary='获取任务详情')
def get_task_detail(request, task_id: str):
    return TaskWorkflowService.get_task_detail(request.auth, task_id)


@router.post('/tasks', response=FailureModeTaskOutSchema, summary='发起梳理任务')
def create_task(request, data: FailureModeTaskCreateSchema):
    return TaskWorkflowService.create_task(request.auth, data.dict())


@router.put('/tasks/{task_id}/scope', response=FailureModeTaskOutSchema, summary='补齐任务工作范围')
def update_task_scope(request, task_id: str, data: FailureModeTaskScopeUpdateSchema):
    return TaskWorkflowService.update_task_scope(
        request.auth,
        task_id,
        product_id=data.product_id,
        subsystem=data.subsystem,
    )


@router.post('/tasks/{task_id}/accept', response=FailureModeTaskOutSchema, summary='接收任务')
def accept_task(request, task_id: str):
    return TaskWorkflowService.accept_task(request.auth, task_id)


@router.get('/tasks/{task_id}/failure-modes', response=List[FailureModeOutSchema], summary='获取任务绑定的故障模式')
def get_task_failure_modes(request, task_id: str):
    return TaskWorkflowService.get_task_failure_modes(request.auth, task_id)


@router.post('/tasks/{task_id}/failure-modes/bind', response=SaveSuccessSchema, summary='绑定故障模式到任务')
def bind_task_failure_modes(request, task_id: str, data: TaskFailureModeBindSchema):
    TaskWorkflowService.bind_failure_modes(request.auth, task_id, data.failure_mode_ids)
    return {'success': True}


@router.get(
    '/tasks/{task_id}/failure-modes/{failure_mode_id}/landing',
    response=TaskFailureModeLandingOutSchema,
    summary='获取任务内故障模式落地配置',
)
def get_task_failure_mode_landing(request, task_id: str, failure_mode_id: str):
    return TaskWorkflowService.get_task_failure_mode_landing(
        request.auth,
        task_id,
        failure_mode_id,
    )


@router.put(
    '/tasks/{task_id}/failure-modes/{failure_mode_id}/landing',
    response=TaskFailureModeLandingOutSchema,
    summary='保存任务内故障模式落地配置',
)
def save_task_failure_mode_landing(
    request,
    task_id: str,
    failure_mode_id: str,
    data: TaskFailureModeLandingSaveSchema,
):
    return TaskWorkflowService.save_task_failure_mode_landing(
        request.auth,
        task_id,
        failure_mode_id,
        data.dict(),
    )


@router.post('/tasks/{task_id}/failure-modes/{failure_mode_id}/draft', response=FailureModeOutSchema, summary='保存修订任务中的故障模式草稿')
def save_task_failure_mode_draft(request, task_id: str, failure_mode_id: str, data: FailureModeUpdateSchema):
    return TaskWorkflowService.save_failure_mode_draft(
        request.auth,
        task_id,
        failure_mode_id,
        data.dict(exclude_unset=True),
    )


@router.post('/tasks/{task_id}/failure-modes/quick-create', response=FailureModeOutSchema, summary='在任务中快速新增并绑定故障模式')
def quick_create_task_failure_mode(request, task_id: str, data: FailureModeCreateSchema):
    return TaskWorkflowService.quick_create_failure_mode(request, task_id, data)


@router.put('/tasks/{task_id}/failure-modes/{failure_mode_id}', response=FailureModeOutSchema, summary='编辑创建任务中的任务新增故障模式')
def update_task_failure_mode(request, task_id: str, failure_mode_id: str, data: FailureModeUpdateSchema):
    return TaskWorkflowService.update_task_created_failure_mode(
        request.auth,
        task_id,
        failure_mode_id,
        data.dict(exclude_unset=True),
    )


@router.delete('/tasks/{task_id}/failure-modes/{failure_mode_id}/draft', response=SaveSuccessSchema, summary='撤销修订任务中的故障模式草稿')
def delete_task_failure_mode_draft(request, task_id: str, failure_mode_id: str):
    TaskWorkflowService.delete_failure_mode_draft(request.auth, task_id, failure_mode_id)
    return {'success': True}


@router.post('/tasks/{task_id}/submit', response=FailureModeTaskOutSchema, summary='提交任务评审')
def submit_task(request, task_id: str):
    return TaskWorkflowService.submit_task(request.auth, task_id)


@router.post('/tasks/{task_id}/recall', response=FailureModeTaskOutSchema, summary='撤回评审中的任务')
def recall_task(request, task_id: str, data: TaskRecallSchema):
    return TaskWorkflowService.recall_task(request.auth, task_id, data.reason)


@router.post('/tasks/{task_id}/reject', response=FailureModeTaskOutSchema, summary='驳回评审中的任务')
def reject_task(request, task_id: str, data: TaskRejectSchema):
    return TaskWorkflowService.reject_task(request.auth, task_id, data.reason)


@router.post('/tasks/{task_id}/close', response=FailureModeTaskOutSchema, summary='评审并关闭任务')
def close_task(request, task_id: str, data: TaskCloseSchema):
    return TaskWorkflowService.close_task(
        request.auth,
        task_id,
        review_result=data.review_result,
        review_minutes_html=data.review_minutes_html,
        review_attachment_ids=data.review_attachment_ids,
    )


@router.post('/tasks/{task_id}/reassign', response=FailureModeTaskOutSchema, summary='改派责任人')
def reassign_task(request, task_id: str, data: TaskReassignSchema):
    return TaskWorkflowService.reassign_task(request.auth, task_id, data.assignee_id)


@router.get('/tasks/{task_id}/logs', response=List[FailureModeTaskLogOutSchema], summary='获取任务日志')
def list_task_logs(request, task_id: str):
    return TaskWorkflowService.list_task_logs(request.auth, task_id)
