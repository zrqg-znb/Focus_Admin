import { requestClient } from '#/api/request';

export interface IterationOut {
  id: string;
  project_id: string;
  name: string;
  code: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  is_healthy: boolean;
}

export interface IterationMetricOut {
  id: string;
  iteration_id: string;
  record_date: string;
  req_decomposition_rate: number;
  req_drift_rate: number;
  req_completion_rate: number;
  req_workload: number;
  completed_workload: number;
}

export interface IterationCreatePayload {
  project_id: string;
  name: string;
  code: string;
  start_date: string;
  end_date: string;
  is_current?: boolean;
  is_healthy?: boolean;
}

export interface IterationMetricPayload {
  record_date: string;
  req_decomposition_rate: number;
  req_drift_rate: number;
  req_completion_rate: number;
  req_workload: number;
  completed_workload: number;
}

export interface IterationOverviewItem {
  project_id: string;
  project_name: string;
  current_iteration?: IterationOut | null;
  latest_metric?: IterationMetricOut | null;
}

export interface IterationDetailItem extends IterationOut {
  latest_metric?: IterationMetricOut | null;
}

const base = '/api/project-manager/iterations';

export async function getIterationOverviewApi() {
  return requestClient.get<IterationOverviewItem[]>(`${base}/overview`);
}

export async function listProjectIterationsApi(projectId: string) {
  return requestClient.get<IterationDetailItem[]>(`${base}/project/${projectId}`);
}

export async function createIterationApi(data: IterationCreatePayload) {
  return requestClient.post<IterationOut>(`${base}/`, data);
}

export async function recordIterationMetricApi(iterationId: string, data: IterationMetricPayload) {
  return requestClient.post<IterationMetricOut>(`${base}/${iterationId}/metrics`, data);
}
