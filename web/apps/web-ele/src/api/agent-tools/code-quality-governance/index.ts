import { requestClient } from '#/api/request';

export interface PageResult<T> {
  items: T[];
  total: number;
}

export interface UserOption {
  id: string;
  name: string;
  username: string;
}

export interface GovernanceProject {
  id: string;
  name: string;
  code: string;
  repository: string;
  branch: string;
  description: string;
  is_active: boolean;
}

export interface GovernanceResponsibility {
  id: string;
  name: string;
  code: string;
  description: string;
  is_active: boolean;
  owner?: UserOption;
  approvers: UserOption[];
}

export interface GovernanceLink {
  id: string;
  project_id: string;
  project_name: string;
  responsibility_id: string;
  responsibility_name: string;
  is_active: boolean;
  remark: string;
}

export interface Finding {
  id: string;
  project_name: string;
  responsibility_name: string;
  identity_key: string;
  issue_key: string;
  fingerprint: string;
  rule_id: string;
  severity: string;
  shield_status: string;
  latest_tool_name: string;
  latest_file_path: string;
  latest_line: number;
  latest_message: string;
  last_seen_at?: string;
  occurrence_id?: string;
  file_path?: string;
  start_line?: number;
  end_line?: number;
  message?: string;
  evidence?: unknown[];
  identity?: Record<string, unknown>;
  raw_finding?: Record<string, unknown>;
  report_complete?: boolean;
}

export interface Application {
  id: string;
  finding_id: string;
  project_name: string;
  responsibility_name: string;
  applicant?: UserOption;
  approver?: UserOption;
  reason: string;
  status: string;
  audit_comment: string;
  severity: string;
  file_path: string;
  rule_id: string;
  message: string;
  created_at?: string;
}

export interface Summary {
  total: number;
  normal: number;
  pending: number;
  shielded: number;
  pending_applications: number;
  severity: Record<string, number>;
  project_rank: { count: number; name: string }[];
  responsibility_rank: { count: number; name: string }[];
  tool_rank: { count: number; name: string }[];
  latest_report?: Record<string, unknown>;
}

const base = '/api/agent-tools/code-quality-governance';

const pageParams = (params?: Record<string, unknown>) => ({
  page: 1,
  pageSize: 20,
  ...params,
});

export const listUsersApi = () =>
  requestClient.get<UserOption[]>(`${base}/users`);
export const listProjectsApi = (params?: Record<string, unknown>) =>
  requestClient.get<PageResult<GovernanceProject>>(`${base}/projects`, {
    params: pageParams(params),
  });
export const createProjectApi = (data: unknown) =>
  requestClient.post(`${base}/projects`, data);
export const updateProjectApi = (id: string, data: unknown) =>
  requestClient.put(`${base}/projects/${id}`, data);
export const deleteProjectApi = (id: string) =>
  requestClient.delete(`${base}/projects/${id}`);
export const listResponsibilitiesApi = (params?: Record<string, unknown>) =>
  requestClient.get<PageResult<GovernanceResponsibility>>(
    `${base}/responsibilities`,
    {
      params: pageParams(params),
    },
  );
export const createResponsibilityApi = (data: unknown) =>
  requestClient.post(`${base}/responsibilities`, data);
export const updateResponsibilityApi = (id: string, data: unknown) =>
  requestClient.put(`${base}/responsibilities/${id}`, data);
export const deleteResponsibilityApi = (id: string) =>
  requestClient.delete(`${base}/responsibilities/${id}`);
export const listLinksApi = (params?: Record<string, unknown>) =>
  requestClient.get<PageResult<GovernanceLink>>(
    `${base}/project-responsibilities`,
    {
      params: pageParams(params),
    },
  );
export const createLinkApi = (data: unknown) =>
  requestClient.post(`${base}/project-responsibilities`, data);
export const updateLinkApi = (id: string, data: unknown) =>
  requestClient.put(`${base}/project-responsibilities/${id}`, data);
export const deleteLinkApi = (id: string) =>
  requestClient.delete(`${base}/project-responsibilities/${id}`);
export const uploadReportApi = (data: FormData) =>
  requestClient.post(`${base}/reports/upload`, data);
export const listFindingsApi = (params?: Record<string, unknown>) =>
  requestClient.get<PageResult<Finding>>(`${base}/findings`, {
    params: pageParams(params),
  });
export const getFindingApi = (id: string) =>
  requestClient.get<Finding>(`${base}/findings/${id}`);
export const listApplicationsApi = (params?: Record<string, unknown>) =>
  requestClient.get<PageResult<Application>>(`${base}/shield-applications`, {
    params: pageParams(params),
  });
export const getApplicationLogsApi = (id: string) =>
  requestClient.get<Record<string, unknown>[]>(
    `${base}/shield-applications/${id}/logs`,
  );
export const createApplicationApi = (data: unknown) =>
  requestClient.post(`${base}/shield-applications`, data);
export const approveApplicationApi = (id: string, comment: string) =>
  requestClient.post(`${base}/shield-applications/${id}/approve`, { comment });
export const rejectApplicationApi = (id: string, comment: string) =>
  requestClient.post(`${base}/shield-applications/${id}/reject`, { comment });
export const getSummaryApi = (params?: Record<string, unknown>) =>
  requestClient.get<Summary>(`${base}/dashboard/summary`, { params });
export const getTrendApi = (params?: Record<string, unknown>) =>
  requestClient.get<{ count: number; date: string }[]>(
    `${base}/dashboard/trend`,
    {
      params,
    },
  );
