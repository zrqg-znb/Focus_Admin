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

export interface IterationDashboardItem {
  project_id: string;
  project_name: string;
  project_domain: string;
  project_type: string;
  project_managers: string;
  current_iteration_name?: string;
  current_iteration_code?: string;
  start_date?: string;
  end_date?: string;
  is_healthy: boolean;
  req_decomposition_rate: number;
  req_drift_rate: number;
  req_completion_rate: number;
  req_workload: number;
  completed_workload: number;
}

export interface IterationDetailItem extends IterationOut {
  latest_metric?: IterationMetricOut | null;
}

const base = '/api/project-manager/iterations';

export async function getIterationOverviewApi(params?: any) {
  return requestClient.get<IterationDashboardItem[]>(`${base}/overview`, { params });
}

export async function listProjectIterationsApi(projectId: string) {
  return requestClient.get<IterationDetailItem[]>(`${base}/project/${projectId}`);
}

export async function refreshProjectIterationApi(projectId: string) {
  return requestClient.post<boolean>(`${base}/project/${projectId}/refresh`);
}
