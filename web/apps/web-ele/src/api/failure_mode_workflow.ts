import type {
  FailureModeItem,
  FailureModePayload,
  UserBriefInfo,
} from './failure_mode';

import { requestClient } from '#/api/request';

export interface FailureModeProductItem {
  id: string;
  project_id: string;
  project_name: string;
  owner_id?: null | string;
  owner_info?: null | UserBriefInfo;
  owner_assignment_id?: null | string;
  can_manage_roles: boolean;
  role_preview: FailureModeRolePreviewItem[];
  sys_create_datetime?: null | string;
  sys_update_datetime?: null | string;
}

export interface FailureModeRolePreviewItem {
  subsystem: string;
  feature_se_info: UserBriefInfo[];
  member_info: UserBriefInfo[];
}

export interface ProductFailureModeItem {
  id: string;
  product_id: string;
  subsystem: string;
  failure_mode_id: string;
  failure_mode_brief: string;
  sys_create_datetime?: null | string;
}

export interface VisibleSubsystemItem {
  label: string;
  value: string;
}

export interface FailureModeRoleAssignmentItem {
  id: string;
  user_id: string;
  user_info: UserBriefInfo;
  role: 'feature_se' | 'fm_admin' | 'member' | 'version_se';
  product_id?: null | string;
  subsystem: string;
  is_active: boolean;
  sys_create_datetime?: null | string;
  sys_update_datetime?: null | string;
}

export interface ProductRoleAssignmentSaveItem {
  user_id: string;
  role: 'feature_se' | 'member';
  subsystem: string;
}

export interface FailureModeTaskItem {
  id: string;
  task_no: string;
  name: string;
  task_type: 'CREATE' | 'DELETE' | 'REVISE';
  status: 'CLOSED' | 'CREATED' | 'PROCESSING' | 'REVIEWING';
  product_id: string;
  product_name: string;
  subsystem: string;
  creator_id?: null | string;
  creator_info?: null | UserBriefInfo;
  assignee_id?: null | string;
  assignee_info?: null | UserBriefInfo;
  review_result: string;
  review_minutes_html: string;
  review_attachment_ids: string[];
  accepted_at?: null | string;
  submitted_at?: null | string;
  reviewed_at?: null | string;
  closed_at?: null | string;
  sys_create_datetime?: null | string;
  sys_update_datetime?: null | string;
}

export interface FailureModeTaskLogItem {
  id: string;
  action: string;
  from_status: string;
  to_status: string;
  note: string;
  operator_id?: null | string;
  operator_info?: null | UserBriefInfo;
  extra_data: Record<string, any>;
  sys_create_datetime?: null | string;
}

export interface FailureModeTaskCreatePayload {
  name: string;
  task_type: 'CREATE' | 'DELETE' | 'REVISE';
  product_id: string;
  subsystem: string;
  assignee_id: string;
}

export interface TaskClosePayload {
  review_result?: string;
  review_minutes_html: string;
  review_attachment_ids?: string[];
}

export function listProductsApi(params?: { owner_id?: string }) {
  return requestClient.get<FailureModeProductItem[]>(
    '/api/failure-mode/workflow/products',
    { params },
  );
}

export function updateProductOwnerApi(productId: string, owner_id?: string) {
  return requestClient.put<FailureModeProductItem>(
    `/api/failure-mode/workflow/products/${productId}/owner`,
    { owner_id },
  );
}

export function listProductFailureModesApi(
  productId: string,
  params?: { subsystem?: string },
) {
  return requestClient.get<ProductFailureModeItem[]>(
    `/api/failure-mode/workflow/products/${productId}/failure-modes`,
    { params },
  );
}

export function listProductRoleAssignmentsApi(productId: string) {
  return requestClient.get<FailureModeRoleAssignmentItem[]>(
    `/api/failure-mode/workflow/products/${productId}/roles`,
  );
}

export function saveProductRoleAssignmentsApi(
  productId: string,
  assignments: ProductRoleAssignmentSaveItem[],
) {
  return requestClient.put<FailureModeRoleAssignmentItem[]>(
    `/api/failure-mode/workflow/products/${productId}/roles`,
    { assignments },
  );
}

export function listVisibleSubsystemsApi(productId: string) {
  return requestClient.get<VisibleSubsystemItem[]>(
    `/api/failure-mode/workflow/products/${productId}/visible-subsystems`,
  );
}

export function listTasksApi(params?: {
  product_id?: string;
  status?: string;
}) {
  return requestClient.get<FailureModeTaskItem[]>(
    '/api/failure-mode/workflow/tasks',
    { params },
  );
}

export function getTaskApi(taskId: string) {
  return requestClient.get<FailureModeTaskItem>(
    `/api/failure-mode/workflow/tasks/${taskId}`,
  );
}

export function createTaskApi(data: FailureModeTaskCreatePayload) {
  return requestClient.post<FailureModeTaskItem>(
    '/api/failure-mode/workflow/tasks',
    data,
  );
}

export function acceptTaskApi(taskId: string) {
  return requestClient.post<FailureModeTaskItem>(
    `/api/failure-mode/workflow/tasks/${taskId}/accept`,
  );
}

export function getTaskFailureModesApi(taskId: string) {
  return requestClient.get<FailureModeItem[]>(
    `/api/failure-mode/workflow/tasks/${taskId}/failure-modes`,
  );
}

export function bindTaskFailureModesApi(
  taskId: string,
  failure_mode_ids: string[],
) {
  return requestClient.post<{ success: boolean }>(
    `/api/failure-mode/workflow/tasks/${taskId}/failure-modes/bind`,
    { failure_mode_ids },
  );
}

export function saveTaskFailureModeDraftApi(
  taskId: string,
  failureModeId: string,
  data: Partial<FailureModePayload>,
) {
  return requestClient.post<FailureModeItem>(
    `/api/failure-mode/workflow/tasks/${taskId}/failure-modes/${failureModeId}/draft`,
    data,
  );
}

export function deleteTaskFailureModeDraftApi(
  taskId: string,
  failureModeId: string,
) {
  return requestClient.delete<{ success: boolean }>(
    `/api/failure-mode/workflow/tasks/${taskId}/failure-modes/${failureModeId}/draft`,
  );
}

export function quickCreateTaskFailureModeApi(
  taskId: string,
  data: FailureModePayload,
) {
  return requestClient.post<FailureModeItem>(
    `/api/failure-mode/workflow/tasks/${taskId}/failure-modes/quick-create`,
    data,
  );
}

export function submitTaskApi(taskId: string) {
  return requestClient.post<FailureModeTaskItem>(
    `/api/failure-mode/workflow/tasks/${taskId}/submit`,
  );
}

export function closeTaskApi(taskId: string, data: TaskClosePayload) {
  return requestClient.post<FailureModeTaskItem>(
    `/api/failure-mode/workflow/tasks/${taskId}/close`,
    data,
  );
}

export function reassignTaskApi(taskId: string, assignee_id: string) {
  return requestClient.post<FailureModeTaskItem>(
    `/api/failure-mode/workflow/tasks/${taskId}/reassign`,
    { assignee_id },
  );
}

export function listTaskLogsApi(taskId: string) {
  return requestClient.get<FailureModeTaskLogItem[]>(
    `/api/failure-mode/workflow/tasks/${taskId}/logs`,
  );
}
