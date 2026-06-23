import { requestClient } from '#/api/request';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export interface ScanProjectItem {
  id: string;
  name: string;
  repo_url: string;
  branch: string;
  project_key: string;
  description?: null | string;
  caretaker?: null | string;
  caretaker_name?: null | string;
  path_shield_prefixes?: string[];
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface ScanProjectPayload {
  branch?: string;
  caretaker_id?: null | string;
  description?: null | string;
  name: string;
  path_shield_prefixes?: string[];
  repo_url: string;
}

export interface ScanProjectListParams {
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface ScanTaskListParams {
  page?: number;
  pageSize?: number;
  status?: string;
  tool_name?: string;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

export interface ProjectOverviewQueryParams {
  page?: number;
  pageSize?: number;
  project_id?: string;
  sub_modules?: string;
  sort_field?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ProjectOverviewItem {
  latest_time?: null | string;
  project_id: string;
  project_name: string;
  tool_counts: Record<string, number>;
  total?: null | number;
}

export interface ScanTaskItem {
  id: string;
  log?: null | string;
  processed_time?: null | string;
  project: string;
  report_file?: null | string;
  scan_time?: null | string;
  source: string;
  status: string;
  sub_module?: string;
  tool_name: string;
}

export type ShieldStatus = 'Normal' | 'Pending' | 'Rejected' | 'Shielded';

export interface LatestScanResultItem {
  code_snippet?: null | string;
  description: string;
  defect_type: string;
  file_path: string;
  fingerprint: string;
  help_info?: null | string;
  id: string;
  line_number: number;
  severity: string;
  shield_status: ShieldStatus;
  sub_module?: null | string;
  sys_create_datetime?: null | string;
  task_id: string;
  tool_name: string;
}

export interface ShieldApplicationItem {
  applicant_id: string;
  applicant_name?: null | string;
  approver_id?: null | string;
  approver_name?: null | string;
  audit_comment?: null | string;
  code_snippet?: null | string;
  defect_description?: null | string;
  file_path?: null | string;
  help_info?: null | string;
  id: string;
  reason: string;
  result_id: string;
  severity?: null | string;
  status: string;
  sys_create_datetime?: null | string;
  tool_name?: null | string;
}

export interface ShieldRecordItem {
  applicant_name?: null | string;
  approver_name?: null | string;
  audit_comment?: null | string;
  id: string;
  reason: string;
  result_id: string;
  status: string;
  sys_create_datetime?: null | string;
  sys_update_datetime?: null | string;
}

export interface ShieldApplyPayload {
  approver_id: string;
  reason: string;
  result_ids: string[];
}

export interface ShieldAuditPayload {
  application_id?: string;
  application_ids?: string[];
  audit_comment?: string;
  status: string;
}

export const listProjectsApi = (params?: ScanProjectListParams) => {
  return requestClient.get<PaginatedResponse<ScanProjectItem>>(
    '/api/code-scan/projects',
    { params },
  );
};

export const listProjectOverviewApi = (params?: ProjectOverviewQueryParams) => {
  return requestClient.get<PaginatedResponse<ProjectOverviewItem>>(
    '/api/code-scan/projects/overview',
    { params },
  );
};

export const createProjectApi = (data: ScanProjectPayload) => {
  return requestClient.post<ScanProjectItem>('/api/code-scan/projects', data);
};

export const updateProjectApi = (id: string, data: ScanProjectPayload) => {
  return requestClient.put<ScanProjectItem>(
    `/api/code-scan/projects/${id}`,
    data,
  );
};

export const deleteProjectApi = (id: string) => {
  return requestClient.delete<boolean>(`/api/code-scan/projects/${id}`);
};

export const listTasksApi = (
  projectId?: string,
  params?: ScanTaskListParams,
) => {
  return requestClient.get<PaginatedResponse<ScanTaskItem>>(
    '/api/code-scan/tasks',
    {
      params: {
        project_id: projectId,
        ...params,
      },
    },
  );
};

export const runScanTaskApi = (projectId: string) => {
  return requestClient.post(`/api/code-scan/tasks/${projectId}/run`);
};

export const listResultsApi = (taskId: string) => {
  return requestClient.get('/api/code-scan/results', {
    params: { task_id: taskId },
  });
};

export interface LatestResultsQueryParams {
  defect_type_keyword?: string;
  description_keyword?: string;
  file_path_keyword?: string;
  page?: number;
  pageSize?: number;
  severity_keyword?: string;
  shield_status?: ShieldStatus;
  sub_modules?: string;
  tool_name?: string;
}

export const listLatestResultsApi = (
  projectId: string,
  params?: LatestResultsQueryParams,
) => {
  return requestClient.get<PaginatedResponse<LatestScanResultItem>>(
    `/api/code-scan/projects/${projectId}/latest-results`,
    { params },
  );
};

export const exportLatestResultsApi = (
  projectId: string,
  params?: Omit<LatestResultsQueryParams, 'page' | 'pageSize' | 'tool_name'>,
) => {
  return requestClient.get(
    `/api/code-scan/projects/${projectId}/latest-results/export`,
    {
      params,
      responseType: 'blob',
    },
  );
};

export const applyShieldApi = (data: ShieldApplyPayload) => {
  return requestClient.post('/api/code-scan/shield/apply', data);
};

export const listApplicationsApi = (
  mode: 'my_apply' | 'my_audit',
  params?: PaginationParams,
) => {
  return requestClient.get<PaginatedResponse<ShieldApplicationItem>>(
    '/api/code-scan/shield/applications',
    {
      params: { mode, ...params },
    },
  );
};

export const auditShieldApi = (data: ShieldAuditPayload) => {
  return requestClient.post('/api/code-scan/shield/audit', data);
};

export const listResultShieldRecordsApi = (resultId: string) => {
  return requestClient.get<ShieldRecordItem[]>(
    `/api/code-scan/results/${resultId}/shield-records`,
  );
};
