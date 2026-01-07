import { requestClient } from '#/api/request';

export interface ProjectQualitySummary {
  project_id: string;
  project_name: string;
  project_domain: string;
  project_type: string;
  project_managers: string;
  record_date?: string;
  total_loc: number;
  total_function_count: number;
  total_dangerous_func_count: number;
  avg_duplication_rate: number;
  module_count: number;
}

export interface CodeModuleOut {
  id: string;
  project_id: string;
  oem_name: string;
  module: string;
  owner_names?: string[] | null;
  owner_ids?: string[] | null;
}

export interface CodeMetricOut {
  id: string;
  module_id: string;
  record_date: string;
  loc: number;
  function_count: number;
  dangerous_func_count: number;
  duplication_rate: number;
  is_clean_code: boolean;
}

export interface ModuleQualityDetail {
  id: string;
  oem_name: string;
  module: string;
  owner_names: string[];
  owner_ids?: string[];
  record_date?: string;
  loc: number;
  function_count: number;
  dangerous_func_count: number;
  duplication_rate: number;
  is_clean_code: boolean;
}

export interface ModuleConfigPayload {
  id?: string;
  project_id: string;
  oem_name: string;
  module: string;
  owner_ids?: string[];
}

const base = '/api/project-manager/code_quality';

export async function getQualityOverviewApi(params?: any) {
  return requestClient.get<ProjectQualitySummary[]>(`${base}/overview`, { params });
}

export async function configModuleApi(data: ModuleConfigPayload) {
  return requestClient.post<CodeModuleOut>(`${base}/modules`, data);
}

export async function getProjectQualityDetailsApi(projectId: string) {
  return requestClient.get<ModuleQualityDetail[]>(`${base}/project/${projectId}/details`);
}

export async function refreshProjectQualityApi(projectId: string) {
  return requestClient.post<boolean>(`${base}/project/${projectId}/refresh`);
}
