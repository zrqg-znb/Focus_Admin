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
  project_id: string;
  project_name: string;
  project_domain: string;
  project_type: string;
  project_managers: string;
  enabled: boolean;
  subscribed: boolean;
  latest_date?: string | null;
  code_metrics: MetricCell[];
  dt_metrics: MetricCell[];
}

export interface ProjectConfigManageRow {
  project_id: string;
  project_name: string;
  enabled: boolean;
  code_check_task_id: string;
  bin_scope_task_id: string;
  build_check_task_id: string;
  compile_check_task_id: string;
  dt_project_id: string;
}

export interface ProjectConfigUpsertIn {
  enabled: boolean;
  code_check_task_id: string;
  bin_scope_task_id: string;
  build_check_task_id: string;
  compile_check_task_id: string;
  dt_project_id: string;
}

export interface HistoryRow {
  record_date: string;
  project_id: string;
  project_name: string;
  code_metrics: MetricCell[];
  dt_metrics: MetricCell[];
}

export interface HistoryQueryOut {
  items: HistoryRow[];
}

export async function listIntegrationProjectsApi() {
  return requestClient.get<ProjectConfigOut[]>('/api/integration-report/projects');
}

export async function listIntegrationConfigsApi() {
  return requestClient.get<ProjectConfigManageRow[]>(
    '/api/integration-report/configs',
  );
}

export async function upsertIntegrationConfigApi(
  projectId: string,
  payload: ProjectConfigUpsertIn,
) {
  return requestClient.post<boolean>(
    `/api/integration-report/configs/${projectId}`,
    payload,
  );
}

export async function initIntegrationConfigsApi() {
  return requestClient.post<number>('/api/integration-report/configs/init');
}

export async function mockCollectIntegrationApi(recordDate?: string) {
  return requestClient.post<boolean>('/api/integration-report/mock/collect', null, {
    params: recordDate ? { record_date: recordDate } : undefined,
  });
}

export async function mockSendIntegrationEmailsApi(recordDate?: string) {
  return requestClient.post<number>(
    '/api/integration-report/mock/send-emails',
    null,
    { params: recordDate ? { record_date: recordDate } : undefined },
  );
}

export async function toggleIntegrationSubscriptionApi(projectId: string, enabled: boolean) {
  return requestClient.post<boolean>(`/api/integration-report/subscriptions/${projectId}`, {
    enabled,
  });
}

export async function queryIntegrationHistoryApi(params: {
  project_ids?: string[];
  start: string;
  end: string;
}) {
  return requestClient.get<HistoryQueryOut>('/api/integration-report/history', { params });
}
