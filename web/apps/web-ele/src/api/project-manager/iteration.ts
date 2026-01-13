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
  
  // Calculated Rates
  sr_breakdown_rate: number;
  dr_breakdown_rate: number;
  ar_set_a_rate: number;
  dr_set_a_rate: number;
  ar_set_c_rate: number;
  dr_set_c_rate: number;
  
  // Raw data (optional, but good to have)
  sr_num: number;
  dr_num: number;
  ar_num: number;
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
  
  // Calculated Rates
  sr_breakdown_rate: number;
  dr_breakdown_rate: number;
  ar_set_a_rate: number;
  dr_set_a_rate: number;
  ar_set_c_rate: number;
  dr_set_c_rate: number;
  
  // Raw counts
  sr_num: number;
  dr_num: number;
  ar_num: number;
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
