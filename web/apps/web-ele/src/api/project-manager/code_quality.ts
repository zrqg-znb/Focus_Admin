import { requestClient } from '#/api/request';

export interface ProjectQualitySummary {
  project_id: string;
  project_name: string;
  project_domain: string;
  project_type: string;
  project_managers: string;
  record_date?: string;
  oem_name?: string;
  total_loc: number;
  total_function_count: number;
  total_dangerous_func_count: number;
  avg_duplication_rate: number;
  module_count: number;
  clean_code_achieve_rate: number;
  clean_code_pass_modules: number;
  total_node_count: number;
  warning_node_count: number;
  warning_count?: number;
  warning_metrics?: string[];
  unachieved_clean_code?: string[];
  metric_values?: QualityMetricValue[];
}

export interface CodeModuleOut {
  id: string;
  project_id: string;
  oem_name: string;
  module: string;
  owner_names?: null | string[];
  owner_ids?: null | string[];
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

export interface QualityMetricValue {
  key: string;
  label: string;
  display: string;
  num?: null | number;
  is_warning: boolean;
  raw?: any;
}

export interface QualityTreeNode {
  id: string;
  node_key: string;
  version_name: string;
  owner_names?: string[];
  owner_ids?: string[];
  depth: number;
  clean_code_rate: number;
  is_clean_code: boolean;
  unachieved_clean_code: string[];
  warning_count: number;
  warning_metrics: string[];
  metric_values: QualityMetricValue[];
  children: QualityTreeNode[];
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
  clean_code_rate: number;
  clean_code_total: number;
  unachieved_clean_code: string[];
  warning_count: number;
  warning_metrics: string[];
  total_node_count: number;
  warning_node_count: number;
  root_version_name: string;
  metric_values: QualityMetricValue[];
  nodes: QualityTreeNode[];
}

export interface ModuleConfigPayload {
  id?: string;
  project_id: string;
  oem_name: string;
  module: string;
  owner_ids?: string[];
}

export interface NodeOwnerUpdatePayload {
  module_id: string;
  node_key: string;
  owner_ids: string[];
}

const base = '/api/project-manager/code_quality';

export async function getQualityOverviewApi(params?: any) {
  return requestClient.get<ProjectQualitySummary[]>(`${base}/overview`, {
    params,
  });
}

export async function configModuleApi(data: ModuleConfigPayload) {
  return requestClient.post<CodeModuleOut>(`${base}/modules`, data);
}

export async function getProjectQualityDetailsApi(
  projectId: string,
  params?: {
    record_date?: string;
  },
) {
  return requestClient.get<ModuleQualityDetail[]>(
    `${base}/project/${projectId}/details`,
    {
      params,
    },
  );
}

export async function getProjectQualityDetailsLiteApi(projectId: string) {
  return requestClient.get<ModuleQualityDetail[]>(
    `${base}/project/${projectId}/details`,
    { params: { lite: true } },
  );
}

export async function refreshProjectQualityApi(projectId: string) {
  return requestClient.post<boolean>(`${base}/project/${projectId}/refresh`);
}

export async function updateNodeOwnerApi(data: NodeOwnerUpdatePayload) {
  return requestClient.put<boolean>(`${base}/node-owner`, data);
}
