import { requestClient } from '#/api/request';

export type RequirementTimeField =
  | 'accepted_time'
  | 'completed_time'
  | 'due_date'
  | 'planned_test_time';

export type RequirementScheduleState = 'A' | 'C' | 'D' | 'I' | 'P';

export interface RequirementBoardFilterPayload {
  project_ids: string[];
  sub_teams?: string[];
  categories?: string[];
  schedule_state?: RequirementScheduleState[];
  verification_policies?: string[];
  title_keyword?: string;
  develop_user?: string[];
  test_user?: string[];
  responsible_pl_group_ids?: string[];
  /**
   * @deprecated use develop_user (username list)
   */
  develop_users?: string[];
  /**
   * @deprecated use test_user (username list)
   */
  test_users?: string[];
  time_field?: RequirementTimeField;
  time_start?: string;
  time_end?: string;
  accepted_time_start?: string;
  accepted_time_end?: string;
}

export interface RequirementBoardQuery extends RequirementBoardFilterPayload {
  page_no: number;
  page_size: number;
}

export interface RequirementBoardProjectOption {
  id: string;
  name: string;
  code: string;
  domain: string;
  type: string;
  design_id?: null | string;
  sub_teams: string[];
  config_complete: boolean;
  is_favorited: boolean;
}

export interface RequirementBoardFilterOptions {
  projects: RequirementBoardProjectOption[];
  saved_filter: null | RequirementBoardFilterPayload;
}

export interface RequirementBoardQueryTask {
  id: string;
  fingerprint: string;
  status: 'failed' | 'pending' | 'running' | 'success';
  message: string;
  error_message: string;
  progress: number;
  scanned_pages: number;
  total_pages: number;
  matched_count: number;
  started_at?: null | string;
  finished_at?: null | string;
}

export interface RequirementBoardQueryPrepareResponse {
  mode: 'async' | 'ready';
  task: null | RequirementBoardQueryTask;
}

export interface RequirementBoardItem {
  requirement_id: string;
  title: string;
  category: string;
  verification_policy: string;
  verification_policy_label: string;
  status_code: string;
  status_label: string;
  raw_status?: string;
  project_id: string;
  project_name: string;
  design_id?: null | string;
  team_name: string;
  planned_test_time?: null | string;
  due_date?: null | string;
  completed_time?: null | string;
  accepted_time?: null | string;
  is_dev_delayed: boolean;
  is_test_delayed: boolean;
  workload_kloc: number;
  workload_man_day: number;
  develop_users: string[];
  test_users: string[];
  responsible_pl_group_id?: null | string;
  responsible_pl_group_name: string;
  develop_user_display: string;
  test_user_display: string;
  develop_user: string;
  test_user: string;
}

export interface RequirementBoardPage {
  items: RequirementBoardItem[];
  total: number;
  page_no: number;
  page_size: number;
  page_sum: number;
}

export interface RequirementStatusSummary {
  status_code: string;
  status_label: string;
  count: number;
  count_rate: number;
  workload_man_day: number;
  workload_kloc: number;
}

export interface RequirementTypeSummary {
  category: string;
  total_count: number;
  total_workload_man_day: number;
  total_workload_kloc: number;
}

export interface RequirementProjectSummary {
  project_id: string;
  project_name: string;
  total_count: number;
  total_workload_man_day: number;
  total_workload_kloc: number;
}

export interface RequirementCompletionSummary {
  count: number;
  workload_man_day: number;
  workload_kloc: number;
  count_rate: number;
  workload_man_day_rate: number;
  workload_kloc_rate: number;
}

export interface RequirementTeamSummary {
  team_name: string;
  total_count: number;
  total_workload_man_day: number;
  total_workload_kloc: number;
  i_count: number;
  d_count: number;
  p_count: number;
  c_count: number;
  a_count: number;
  dev_done: RequirementCompletionSummary;
  acceptance_done: RequirementCompletionSummary;
}

export interface RequirementUserSummaryItem {
  username: string;
  task_count: number;
  workload_man_day: number;
  workload_kloc: number;
}

export interface RequirementUserSummary {
  develop_users: RequirementUserSummaryItem[];
  test_users: RequirementUserSummaryItem[];
}

export interface RequirementDispatchRate {
  p_total: number;
  develop_owner_count: number;
  develop_owner_rate: number;
  test_owner_count: number;
  test_owner_rate: number;
}

export interface RequirementPlanRefreshRate {
  planned_test_time_count: number;
  planned_test_time_rate: number;
  due_date_count: number;
  due_date_rate: number;
}

export interface RequirementDelayBucketSummary {
  count: number;
  rate: number;
  preview_items: RequirementBoardItem[];
}

export interface RequirementDelaySummary {
  development: RequirementDelayBucketSummary;
  acceptance: RequirementDelayBucketSummary;
}

export interface RequirementDeliveryTrendItem {
  month: string;
  planned_count: number;
  actual_count: number;
}

export interface RequirementBoardSummary {
  total_count: number;
  total_workload_man_day: number;
  total_workload_kloc: number;
  status_summary: RequirementStatusSummary[];
  type_summary: RequirementTypeSummary[];
  project_summary: RequirementProjectSummary[];
  team_summary: RequirementTeamSummary[];
  user_summary: RequirementUserSummary;
  dispatch_rate: RequirementDispatchRate;
  plan_refresh_rate: RequirementPlanRefreshRate;
  delay_summary: RequirementDelaySummary;
  development_delivery_trend: RequirementDeliveryTrendItem[];
  acceptance_delivery_trend: RequirementDeliveryTrendItem[];
}

const base = '/api/project-manager/requirement-board';

export async function getRequirementBoardFilterOptionsApi() {
  return requestClient.get<RequirementBoardFilterOptions>(
    `${base}/filter-options`,
  );
}

export async function putRequirementBoardFilterPreferenceApi(
  data: RequirementBoardFilterPayload,
) {
  return requestClient.put<boolean>(`${base}/filter-preference`, data);
}

export async function deleteRequirementBoardFilterPreferenceApi() {
  return requestClient.delete<boolean>(`${base}/filter-preference`);
}

export async function prepareRequirementBoardQueryApi(
  data: RequirementBoardFilterPayload,
) {
  return requestClient.post<RequirementBoardQueryPrepareResponse>(
    `${base}/query-prepare`,
    data,
  );
}

export async function getRequirementBoardQueryTaskApi(taskId: string) {
  return requestClient.get<RequirementBoardQueryTask>(
    `${base}/query-task/${taskId}`,
  );
}

export async function getRequirementBoardDataApi(data: RequirementBoardQuery) {
  return requestClient.post<RequirementBoardPage>(`${base}/data`, data, {
    timeout: 60 * 1000,
  });
}

export async function getRequirementBoardSummaryApi(
  data: RequirementBoardFilterPayload,
) {
  return requestClient.post<RequirementBoardSummary>(`${base}/summary`, data, {
    timeout: 60 * 1000,
  });
}

export async function exportRequirementBoardApi(
  data: RequirementBoardFilterPayload,
) {
  return requestClient.post<Blob>(`${base}/export`, data, {
    responseType: 'blob',
  });
}
