import { requestClient } from '../request';

export interface ProjectQualitySummary {
  project_id: string;
  project_name: string;
  total_loc: number;
  total_function_count: number;
  total_dangerous_func_count: number;
  avg_duplication_rate: number;
  module_count: number;
}

export interface CodeModule {
  id: string;
  project_id: string;
  name: string;
  owner_id?: string;
  owner_name?: string;
}

export interface CodeMetric {
  id: string;
  module_id: string;
  record_date: string;
  loc: number;
  function_count: number;
  dangerous_func_count: number;
  duplication_rate: number;
}

export interface ModuleQualityDetail {
  module_info: CodeModule;
  metrics_history: CodeMetric[];
}

export interface ModuleConfig {
  project_id: string;
  name: string;
  owner_id?: string;
}

export interface CodeMetricCreate {
  module_id: string;
  record_date: string;
  loc: number;
  function_count: number;
  dangerous_func_count: number;
  duplication_rate: number;
}

enum Api {
  Overview = '/project-manager/code_quality/overview',
  Modules = '/project-manager/code_quality/modules',
  Details = '/project-manager/code_quality/project',
  Metrics = '/project-manager/code_quality/module',
}

export const getQualityOverview = () => {
  return requestClient.get<ProjectQualitySummary[]>(Api.Overview);
};

export const configModule = (data: ModuleConfig) => {
  return requestClient.post<CodeModule>(Api.Modules, data);
};

export const getProjectQualityDetails = (projectId: string) => {
  return requestClient.get<ModuleQualityDetail[]>(`${Api.Details}/${projectId}/details`);
};

export const recordModuleMetric = (moduleId: string, data: CodeMetricCreate) => {
  return requestClient.post<CodeMetric>(`${Api.Metrics}/${moduleId}/metrics`, data);
};
