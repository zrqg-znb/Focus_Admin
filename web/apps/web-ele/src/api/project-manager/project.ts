import { requestClient } from '#/api/request';

export interface ProjectOut {
  id: string;
  name: string;
  domain: string;
  type: string;
  code: string;
  managers_info: { id: string; name: string }[];
  is_closed: boolean;
  repo_url?: string;
  remark?: string;
  enable_milestone: boolean;
  enable_iteration: boolean;
  enable_quality: boolean;
  enable_dts: boolean;
  ws_id?: string;
  di_teams?: string[];
  sys_create_datetime?: string;
  is_favorited: boolean;
}

export interface ProjectCreatePayload {
  name: string;
  domain: string;
  type: string;
  code: string;
  manager_ids: string[];
  is_closed?: boolean;
  repo_url?: string;
  remark?: string;
  enable_milestone?: boolean;
  enable_iteration?: boolean;
  enable_quality?: boolean;
  enable_dts?: boolean;
  ws_id?: string;
  di_teams?: string[];
}

export interface ProjectUpdatePayload {
  name?: string;
  domain?: string;
  type?: string;
  code?: string;
  manager_ids?: string[];
  is_closed?: boolean;
  repo_url?: string;
  remark?: string;
  enable_milestone?: boolean;
  enable_iteration?: boolean;
  enable_quality?: boolean;
  enable_dts?: boolean;
  ws_id?: string;
  di_teams?: string[];
}

export interface ProjectFilterParams {
  keyword?: string;
  domain?: string;
  type?: string;
  manager_id?: string;
  is_closed?: boolean;
  enable_milestone?: boolean;
  enable_iteration?: boolean;
  enable_quality?: boolean;
  enable_dts?: boolean;
  page?: number;
  pageSize?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

const listEndpoint = '/api/project-manager/projects/';

export async function listProjectsApi(params?: ProjectFilterParams) {
  return requestClient.get<PaginatedResponse<ProjectOut>>(listEndpoint, { params });
}

export async function createProjectApi(data: ProjectCreatePayload) {
  return requestClient.post<ProjectOut>(listEndpoint, data);
}

export async function updateProjectApi(id: string, data: ProjectUpdatePayload) {
  return requestClient.put<ProjectOut>(`/api/project-manager/projects/${id}`, data);
}

export async function deleteProjectApi(id: string) {
  return requestClient.delete(`/api/project-manager/projects/${id}`);
}

export async function getProjectApi(id: string) {
  return requestClient.get<ProjectOut>(`/api/project-manager/projects/${id}`);
}

export async function favoriteProjectApi(id: string) {
  return requestClient.post<boolean>(`/api/project-manager/projects/${id}/favorite`);
}

export async function unfavoriteProjectApi(id: string) {
  return requestClient.delete<boolean>(`/api/project-manager/projects/${id}/favorite`);
}
