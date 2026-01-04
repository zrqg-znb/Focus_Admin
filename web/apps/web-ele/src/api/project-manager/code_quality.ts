import { requestClient } from '#/api/request';

export interface ProjectQualitySummary {
  project_id: string;
  project_name: string;
  total_loc: number;
  total_function_count: number;
  total_dangerous_func_count: number;
  avg_duplication_rate: number;
  module_count: number;
}

export interface CodeModuleOut {
  id: string;
  project_id: string;
  name: string;
  owner_id?: string | null;
  owner_name?: string | null;
}

export interface CodeMetricOut {
  id: string;
  module_id: string;
  record_date: string;
  loc: number;
  function_count: number;
  dangerous_func_count: number;
  duplication_rate: number;
}

export interface ModuleQualityDetail {
  module_info: CodeModuleOut;
  metrics_history: CodeMetricOut[];
}

export interface ModuleConfigPayload {
  project_id: string;
  name: string;
  owner_id?: string;
}

export interface CodeMetricPayload {
  record_date: string;
  loc: number;
  function_count: number;
  dangerous_func_count: number;
  duplication_rate: number;
}

const base = '/api/project-manager/code_quality';

export async function getQualityOverviewApi() {
  return requestClient.get<ProjectQualitySummary[]>(`${base}/overview`);
}

export async function configModuleApi(data: ModuleConfigPayload) {
  return requestClient.post<CodeModuleOut>(`${base}/modules`, data);
}

export async function getProjectQualityDetailsApi(projectId: string) {
  return requestClient.get<ModuleQualityDetail[]>(`${base}/project/${projectId}/details`);
}

export async function recordModuleMetricApi(moduleId: string, data: CodeMetricPayload) {
  return requestClient.post<CodeMetricOut>(`${base}/module/${moduleId}/metrics`, data);
}
