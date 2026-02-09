import { requestClient } from '#/api/request';

export type MetricLevel = 'normal' | 'warning' | 'danger';

export interface MetricCell {
  key: string;
  name: string;
  value?: number | null;
  text?: string | null;
  unit?: string | null;
  url?: string | null;
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
  latest_date?: string | null;
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
  bin_scope_task_id: string;
  build_check_task_id: string;
  compile_check_task_id: string;
  dt_project_id: string;
}

export interface ProjectConfigUpsertIn {
  project_id: string; // Required for create
  name: string;
  managers: string[];
  enabled: boolean;
  code_check_task_id: string;
  bin_scope_task_id: string;
  build_check_task_id: string;
  compile_check_task_id: string;
  dt_project_id: string;
}

export interface HistoryRow {
  record_date: string;
  config_id: string;
  config_name: string;
  project_name: string;
  code_metrics: MetricCell[];
  dt_metrics: MetricCell[];
}

export interface HistoryQueryOut {
  items: HistoryRow[];
}

export async function listIntegrationProjectsApi(params?: ConfigFilterParams) {
  // Returns configs for subscription page
  return requestClient.get<PaginatedResponse<ProjectConfigOut>>('/api/integration-report/projects', { params });
}

export interface ConfigFilterParams {
  project_name?: string;
  page?: number;
  pageSize?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  count: number;
}

export async function listIntegrationConfigsApi(params?: ConfigFilterParams) {
  return requestClient.get<PaginatedResponse<ProjectConfigManageRow>>(
    '/api/integration-report/configs',
    { params },
  );
}

export async function createIntegrationConfigApi(payload: ProjectConfigUpsertIn) {
  return requestClient.post<string>('/api/integration-report/configs', payload);
}

export async function updateIntegrationConfigApi(
  configId: string,
  payload: ProjectConfigUpsertIn,
) {
  return requestClient.put<boolean>(`/api/integration-report/configs/${configId}`, payload);
}

export async function initIntegrationConfigsApi() {
  return requestClient.post<number>('/api/integration-report/configs/init');
}

export async function mockCollectIntegrationApi(recordDate?: string, configIds?: string[]) {
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

export async function toggleIntegrationSubscriptionApi(configId: string, enabled: boolean) {
  return requestClient.post<boolean>(`/api/integration-report/subscriptions/${configId}`, {
    enabled,
  });
}

export async function queryIntegrationHistoryApi(params: {
  config_ids?: string[];
  start: string;
  end: string;
  keyword?: string;
}) {
  return requestClient.get<HistoryQueryOut>('/api/integration-report/history', { params });
}

export interface EmailDeliveryRow {
  id: string;
  record_date: string;
  user_id: string;
  user_name?: string | null;
  to_email: string;
  subject: string;
  status: string; // pending|sent|failed
  error_message?: string | null;
  sys_create_datetime?: string | null;
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

export async function listEmailDeliveriesApi(params?: EmailDeliveryQueryParams) {
  return requestClient.get<PaginatedResponse<EmailDeliveryRow>>(
    '/api/integration-report/email-deliveries',
    { params },
  );
}
