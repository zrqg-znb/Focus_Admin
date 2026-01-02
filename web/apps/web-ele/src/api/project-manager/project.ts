import { requestClient } from '../request';

export interface Project {
  id: string;
  name: string;
  domain: string;
  type: string;
  code: string;
  managers: { id: string; name: string }[];
  is_closed: boolean;
  repo_url?: string;
  remark?: string;
  enable_milestone: boolean;
  enable_iteration: boolean;
  enable_quality: boolean;
  sys_create_datetime: string;
  sys_update_datetime: string;
}

export interface ProjectCreate {
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
}

export interface ProjectUpdate extends Partial<ProjectCreate> {}

export interface ProjectFilter {
  page?: number;
  pageSize?: number;
  keyword?: string;
  domain?: string;
  type?: string;
  manager_id?: string;
  is_closed?: boolean;
  enable_milestone?: boolean;
  enable_iteration?: boolean;
  enable_quality?: boolean;
}

export interface ProjectListResult {
  items: Project[];
  total: number;
}

enum Api {
  Project = '/project-manager/projects',
}

export const getProjectList = (params?: ProjectFilter) => {
  return requestClient.get<ProjectListResult>(Api.Project, { params });
};

export const createProject = (data: ProjectCreate) => {
  return requestClient.post<Project>(Api.Project, data);
};

export const updateProject = (id: string, data: ProjectUpdate) => {
  return requestClient.put<Project>(`${Api.Project}/${id}`, data);
};

export const deleteProject = (id: string) => {
  return requestClient.delete(`${Api.Project}/${id}`);
};
