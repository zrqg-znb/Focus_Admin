import { requestClient } from '#/api/request';

export interface RequirementUserBrief {
  id: string;
  username: string;
  name?: null | string;
  email?: null | string;
}

export interface RequirementItem {
  id: string;
  title: string;
  description?: string;
  business_value?: string;
  acceptance_criteria?: string;
  type: string;
  source: string;
  priority: string;
  status: RequirementStatus;
  attachments: string[];
  reviewer_id?: null | string;
  owner_id?: null | string;
  submitter_id?: null | string;
  review_due_at?: null | string;
  dev_due_at?: null | string;
  is_review_overdue: boolean;
  is_dev_overdue: boolean;
  submitted_at?: null | string;
  accepted_at?: null | string;
  planned_at?: null | string;
  dev_started_at?: null | string;
  done_at?: null | string;
  sys_create_datetime?: string;
  submitter_info?: null | RequirementUserBrief;
  reviewer_info?: null | RequirementUserBrief;
  owner_info?: null | RequirementUserBrief;
  watcher_ids?: string[];
  parent_id?: null | string;
  root_id?: string;
  level?: number;
  tree_path?: string;
  child_count?: number;
  is_leaf?: boolean;
  children?: RequirementItem[];
}

export interface RequirementCreatePayload {
  title: string;
  description?: string;
  business_value?: string;
  acceptance_criteria?: string;
  type: string;
  source: string;
  priority: string;
  reviewer_id?: string;
  owner_id?: string;
  attachments?: string[];
  review_due_at?: string;
  dev_due_at?: string;
}

export interface RequirementUpdatePayload {
  title?: string;
  description?: string;
  business_value?: string;
  acceptance_criteria?: string;
  type?: string;
  source?: string;
  priority?: string;
  reviewer_id?: string;
  owner_id?: string;
  attachments?: string[];
  review_due_at?: string;
  dev_due_at?: string;
}

export interface RequirementCreateChildPayload {
  title: string;
  description?: string;
  business_value?: string;
  acceptance_criteria?: string;
  type?: string;
  source?: string;
  priority?: string;
  reviewer_id?: string;
  owner_id?: string;
  attachments?: string[];
  dev_due_at?: string;
}

export interface RequirementReviewPayload {
  action: 'accept' | 'need_info' | 'reject';
  note?: string;
}

export interface RequirementTransitionPayload {
  action: 'archive' | 'done' | 'in_acceptance' | 'in_dev' | 'planned';
  note?: string;
}

export interface RequirementComment {
  id: string;
  content: string;
  mentions: string[];
  commenter_info?: null | RequirementUserBrief;
  sys_create_datetime?: string;
}

export interface RequirementLogItem {
  id: string;
  action: string;
  from_status: string;
  note: string;
  operator_info?: null | RequirementUserBrief;
  to_status: string;
  sys_create_datetime?: string;
}

export interface RequirementFilterParams {
  keyword?: string;
  overdue?: boolean;
  owner_id?: string;
  page?: number;
  pageSize?: number;
  priority?: string;
  reviewer_id?: string;
  source?: string;
  status?: RequirementStatus;
  type?: string;
}

export interface RequirementTreeFilterParams extends RequirementFilterParams {
  root_id?: string;
}

export interface RequirementBatchPayload {
  note?: string;
  requirement_ids: string[];
}

export interface RequirementBatchAssignOwnerPayload
  extends RequirementBatchPayload {
  owner_id: string;
}

export interface RequirementBatchAssignReviewerPayload
  extends RequirementBatchPayload {
  reviewer_id: string;
}

export interface RequirementBatchPriorityPayload
  extends RequirementBatchPayload {
  priority: string;
}

export interface BatchActionOut {
  count: number;
  msg: string;
  skipped_ids: string[];
}

export interface DashboardCountItem {
  count: number;
  key: string;
  label: string;
}

export interface RequirementDashboardSummary {
  closed_count: number;
  dev_overdue_count: number;
  open_count: number;
  overdue_count: number;
  owner_stats: DashboardCountItem[];
  priority_stats: DashboardCountItem[];
  review_overdue_count: number;
  reviewer_stats: DashboardCountItem[];
  status_stats: DashboardCountItem[];
  total_count: number;
}

export type RequirementStatus =
  | 'accepted'
  | 'archived'
  | 'done'
  | 'draft'
  | 'in_acceptance'
  | 'in_dev'
  | 'need_info'
  | 'planned'
  | 'rejected'
  | 'submitted';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

const base = '/api/requirement-center/requirements';
const baseCollection = `${base}/`;

export async function listRequirementsApi(params?: RequirementFilterParams) {
  return requestClient.get<PaginatedResponse<RequirementItem>>(baseCollection, {
    params,
  });
}

export async function listRequirementTreeApi(
  params?: RequirementTreeFilterParams,
) {
  return requestClient.get<RequirementItem[]>(`${base}/tree`, {
    params,
  });
}

export async function createRequirementApi(data: RequirementCreatePayload) {
  return requestClient.post<RequirementItem>(baseCollection, data);
}

export async function updateRequirementApi(
  id: string,
  data: RequirementUpdatePayload,
) {
  return requestClient.put<RequirementItem>(`${base}/${id}`, data);
}

export async function getRequirementApi(id: string) {
  return requestClient.get<RequirementItem>(`${base}/${id}`);
}

export async function listRequirementChildrenApi(parentId: string) {
  return requestClient.get<RequirementItem[]>(`${base}/${parentId}/children`);
}

export async function createRequirementChildApi(
  parentId: string,
  data: RequirementCreateChildPayload,
) {
  return requestClient.post<RequirementItem>(`${base}/${parentId}/children`, data);
}

export async function submitRequirementApi(id: string, note = '') {
  return requestClient.post<RequirementItem>(`${base}/${id}/submit`, { note });
}

export async function reviewRequirementApi(
  id: string,
  data: RequirementReviewPayload,
) {
  return requestClient.post<RequirementItem>(`${base}/${id}/review`, data);
}

export async function transferReviewerApi(
  id: string,
  reviewerId: string,
  note = '',
) {
  return requestClient.post<RequirementItem>(
    `${base}/${id}/transfer-reviewer`,
    {
      note,
      reviewer_id: reviewerId,
    },
  );
}

export async function assignOwnerApi(id: string, ownerId: string, note = '') {
  return requestClient.post<RequirementItem>(`${base}/${id}/assign-owner`, {
    note,
    owner_id: ownerId,
  });
}

export async function transitionRequirementApi(
  id: string,
  data: RequirementTransitionPayload,
) {
  return requestClient.post<RequirementItem>(`${base}/${id}/transition`, data);
}

export async function listRequirementCommentsApi(id: string) {
  return requestClient.get<RequirementComment[]>(`${base}/${id}/comments`);
}

export async function createRequirementCommentApi(
  id: string,
  content: string,
  mentionIds: string[] = [],
) {
  return requestClient.post<RequirementComment>(`${base}/${id}/comments`, {
    content,
    mention_ids: mentionIds,
  });
}

export async function listRequirementLogsApi(id: string) {
  return requestClient.get<RequirementLogItem[]>(`${base}/${id}/logs`);
}

export async function batchAssignReviewerApi(
  data: RequirementBatchAssignReviewerPayload,
) {
  return requestClient.post<BatchActionOut>(
    `${base}/batch/assign-reviewer`,
    data,
  );
}

export async function batchAssignOwnerApi(
  data: RequirementBatchAssignOwnerPayload,
) {
  return requestClient.post<BatchActionOut>(`${base}/batch/assign-owner`, data);
}

export async function batchPriorityApi(data: RequirementBatchPriorityPayload) {
  return requestClient.post<BatchActionOut>(`${base}/batch/priority`, data);
}

export async function batchArchiveApi(data: RequirementBatchPayload) {
  return requestClient.post<BatchActionOut>(`${base}/batch/archive`, data);
}

export async function getRequirementDashboardSummaryApi() {
  return requestClient.get<RequirementDashboardSummary>(
    `${base}/dashboard/summary`,
  );
}
