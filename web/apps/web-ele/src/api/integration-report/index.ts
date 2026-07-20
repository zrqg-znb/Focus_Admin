import { requestClient } from '#/api/request';

export type MetricLevel = 'danger' | 'normal' | 'warning';

export interface MetricCell {
  key: string;
  name: string;
  value?: null | number;
  text?: null | string;
  unit?: null | string;
  url?: null | string;
  level: MetricLevel;
}

export interface ProjectConfigOut {
  id: string; // Config ID
  name: string; // Config Name
  project_id: string;
  project_name: string;
  project_domain: string;
  project_type: string;
  project_managers: string;
  managers: string;
  enabled: boolean;
  subscribed: boolean;
  latest_date?: null | string;
  dt_bin_task_id: string;
  cooddy_check_task_id: string;
  code_scan_project_key?: string;
  valgrind_sub_modules?: string[];
  enable_dt_fuzz: boolean;
  dt_fuzz_version_name: string;
  dt_fuzz_branches: string[];
  dt_fuzz_pbi_id: string;
  dt_fuzz_domain_id: string;
  dt_fuzz_project_id: string;
  code_metrics: MetricCell[];
  dt_metrics: MetricCell[];
}

export interface ProjectConfigManageRow {
  id: string; // Config ID
  name: string; // Config Name
  project_id: string;
  project_name: string;
  managers: string;
  manager_ids: string[];
  enabled: boolean;
  code_check_task_id: string;
  dt_bin_task_id: string;
  cooddy_check_task_id: string;
  bin_scope_task_id: string;
  build_check_task_id: string;
  compile_check_task_id: string;
  dt_project_id: string;
  code_scan_project_key: string;
  valgrind_sub_modules: string[];
  enable_dt_fuzz: boolean;
  dt_fuzz_version_name: string;
  dt_fuzz_branches: string[];
  dt_fuzz_pbi_id: string;
  dt_fuzz_domain_id: string;
  dt_fuzz_project_id: string;
}

export interface ProjectConfigUpsertIn {
  project_id?: null | string;
  name: string;
  managers: string[];
  enabled: boolean;
  code_check_task_id: string;
  dt_bin_task_id: string;
  cooddy_check_task_id: string;
  bin_scope_task_id: string;
  build_check_task_id: string;
  compile_check_task_id: string;
  dt_project_id: string;
  code_scan_project_key: string;
  valgrind_sub_modules: string[];
  enable_dt_fuzz: boolean;
  dt_fuzz_version_name: string;
  dt_fuzz_branches: string[];
  dt_fuzz_pbi_id: string;
  dt_fuzz_domain_id: string;
  dt_fuzz_project_id: string;
}

export interface HistoryRow {
  record_date: string;
  config_id: string;
  config_name: string;
  project_name: string;
  caretaker_names: string;
  code_metrics: MetricCell[];
  dt_metrics: MetricCell[];
}

export interface DtFuzzNode {
  node_key: string;
  name: string;
  type: string;
  highRiskApiCover: string;
  highRiskApiTotal: string;
  highRiskApiCoverage: string;
  secLineCover: string;
  secLineTotal: string;
  secLineCoverage: string;
  secReportUrl: string;
  lcovLineCover: string;
  lcovLineTotal: string;
  lcovLineCoverage: string;
  lcovReportUrl: string;
  defectNumber: string;
  casePass: string;
  casePassRate: string;
  caseActive: string;
  caseActiveRate: string;
  caseTotal: string;
  reportUrl: string;
  branch: string;
  owner: string;
  children: DtFuzzNode[];
}

export interface DtFuzzHistoryItem {
  record_date: string;
  config_id: string;
  config_name: string;
  project_name: string;
  branch: string;
  owner: string;
  source_due_date: string;
  nodes: DtFuzzNode[];
}

export interface HistoryQueryOut {
  items: HistoryRow[];
  dt_fuzz_items: DtFuzzHistoryItem[];
}

export async function listIntegrationProjectsApi(params?: ConfigFilterParams) {
  // Returns configs for subscription page
  return requestClient.get<PaginatedResponse<ProjectConfigOut>>(
    '/api/integration-report/projects',
    { params },
  );
}

export interface ConfigFilterParams {
  project_name?: string;
  page?: number;
  pageSize?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  count?: number;
  total?: number;
}

export async function listIntegrationConfigsApi(params?: ConfigFilterParams) {
  return requestClient.get<PaginatedResponse<ProjectConfigManageRow>>(
    '/api/integration-report/configs',
    { params },
  );
}

export async function createIntegrationConfigApi(
  payload: ProjectConfigUpsertIn,
) {
  return requestClient.post<string>('/api/integration-report/configs', payload);
}

export async function updateIntegrationConfigApi(
  configId: string,
  payload: ProjectConfigUpsertIn,
) {
  return requestClient.put<boolean>(
    `/api/integration-report/configs/${configId}`,
    payload,
  );
}

export async function deleteIntegrationConfigApi(configId: string) {
  return requestClient.delete<boolean>(
    `/api/integration-report/configs/${configId}`,
  );
}

export async function initIntegrationConfigsApi() {
  return requestClient.post<number>('/api/integration-report/configs/init');
}

export async function mockCollectIntegrationApi(
  recordDate?: string,
  configIds?: string[],
) {
  return requestClient.post<boolean>('/api/integration-report/mock/collect', {
    record_date: recordDate,
    config_ids: configIds,
  });
}

export async function mockSendIntegrationEmailsApi(recordDate?: string) {
  return requestClient.post<number>(
    '/api/integration-report/mock/send-emails',
    null,
    { params: recordDate ? { record_date: recordDate } : undefined },
  );
}

export async function toggleIntegrationSubscriptionApi(
  configId: string,
  enabled: boolean,
) {
  return requestClient.post<boolean>(
    `/api/integration-report/subscriptions/${configId}`,
    {
      enabled,
    },
  );
}

export async function queryIntegrationHistoryApi(params: {
  caretaker_keyword?: string;
  caretaker_keywords?: string[];
  config_ids?: string[];
  end: string;
  keyword?: string;
  keyword_match_mode?: 'all' | 'any';
  keywords?: string[];
  start: string;
}) {
  return requestClient.get<HistoryQueryOut>('/api/integration-report/history', {
    params,
    paramsSerializer: 'repeat',
  });
}

export interface EmailDeliveryRow {
  id: string;
  record_date: string;
  user_id: string;
  user_name?: null | string;
  to_email: string;
  subject: string;
  status: string; // pending|sent|failed
  error_message?: null | string;
  sys_create_datetime?: null | string;
}

export interface EmailDeliveryQueryParams {
  status?: string; // pending|sent|failed
  start_date?: string;
  end_date?: string;
  user_id?: string;
  to_email?: string;
  page?: number;
  pageSize?: number;
}

export async function listEmailDeliveriesApi(
  params?: EmailDeliveryQueryParams,
) {
  return requestClient.get<PaginatedResponse<EmailDeliveryRow>>(
    '/api/integration-report/email-deliveries',
    { params },
  );
}

export interface SubscriptionManagementProjectRow {
  id: string;
  name: string;
  project_id: string;
  project_name: string;
  managers: string;
  project_managers: string;
  enabled: boolean;
  subscriber_count: number;
  missing_email_count: number;
  sys_update_datetime?: null | string;
}

export interface SubscriptionManagementProjectQueryParams {
  keyword?: string;
  enabled?: boolean;
  has_subscribers?: boolean;
  has_missing_email?: boolean;
  page?: number;
  pageSize?: number;
  page_size?: number;
}

export interface SubscriptionSubscriberRow {
  id: string;
  user_id: string;
  username: string;
  name?: null | string;
  email?: null | string;
  enabled: boolean;
  sys_update_datetime?: null | string;
}

export interface SubscriptionSubscriberQueryParams {
  keyword?: string;
  enabled?: boolean;
  page?: number;
  pageSize?: number;
  page_size?: number;
}

export interface SubscriptionBatchResult {
  changed_count: number;
}

export async function listSubscriptionManagementProjectsApi(
  params?: SubscriptionManagementProjectQueryParams,
) {
  return requestClient.get<PaginatedResponse<SubscriptionManagementProjectRow>>(
    '/api/integration-report/subscription-management/projects',
    { params },
  );
}

export async function listSubscriptionManagementSubscribersApi(
  configId: string,
  params?: SubscriptionSubscriberQueryParams,
) {
  return requestClient.get<PaginatedResponse<SubscriptionSubscriberRow>>(
    `/api/integration-report/subscription-management/projects/${configId}/subscribers`,
    { params },
  );
}

export async function replaceSubscriptionManagementSubscribersApi(
  configId: string,
  userIds: string[],
) {
  return requestClient.put<SubscriptionBatchResult>(
    `/api/integration-report/subscription-management/projects/${configId}/subscribers`,
    { user_ids: userIds },
  );
}

export async function addSubscriptionManagementSubscribersApi(
  configId: string,
  userIds: string[],
) {
  return requestClient.post<SubscriptionBatchResult>(
    `/api/integration-report/subscription-management/projects/${configId}/subscribers/batch-add`,
    { user_ids: userIds },
  );
}

export async function batchAddSubscriptionManagementSubscribersApi(
  configIds: string[],
  userIds: string[],
) {
  return requestClient.post<SubscriptionBatchResult>(
    '/api/integration-report/subscription-management/projects/subscribers/batch-add',
    { config_ids: configIds, user_ids: userIds },
  );
}

export async function removeSubscriptionManagementSubscribersApi(
  configId: string,
  userIds: string[],
) {
  return requestClient.post<SubscriptionBatchResult>(
    `/api/integration-report/subscription-management/projects/${configId}/subscribers/batch-remove`,
    { user_ids: userIds },
  );
}
