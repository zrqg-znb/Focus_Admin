import { requestClient } from '#/api/request';

/**
 * 项目配置接口
 */

export interface ProjectConfig {
  id: number;
  name: string;
  description?: string;
  project_category?: string;
  project_owner?: string;
  codecheck_id?: string;
  binscope_id?: string;
  cooddy_id?: string;
  compiletion_check_id?: string;
  build_check_id?: string;
  build_project_id?: string;
  codecov_id?: string;
  fossbot_id?: string;
  is_subscribed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectConfigCreate {
  name: string;
  description?: string;
  codecheck_id?: string;
  binscope_id?: string;
  cooddy_id?: string;
  compiletion_check_id?: string;
  build_check_id?: string;
  build_project_id?: string;
  codecov_id?: string;
  fossbot_id?: string;
}

export function getProjectList(params?: any) {
  return requestClient.get<ProjectConfig[]>('/api/ci-daily-report/projects', { params });
}

export function createProject(data: ProjectConfigCreate) {
  return requestClient.post<ProjectConfig>('/api/ci-daily-report/projects', data);
}

export function updateProject(id: number, data: ProjectConfigCreate) {
  return requestClient.put<ProjectConfig>(`/api/ci-daily-report/projects/${id}`, data);
}

export function getProject(id: number) {
  return requestClient.get<ProjectConfig>(`/api/ci-daily-report/projects/${id}`);
}

export function deleteProject(id: number) {
  return requestClient.delete(`/api/ci-daily-report/projects/${id}`);
}

/**
 * 订阅接口
 */

export interface Subscription {
  id: number;
  user_id: number;
  project: ProjectConfig;
  subscribed_at: string;
  is_active: boolean;
}

export function subscribeProject(projectId: number) {
  return requestClient.post<Subscription>('/api/ci-daily-report/subscriptions', { project_id: projectId });
}

export function unsubscribeProject(projectId: number) {
  return requestClient.delete(`/api/ci-daily-report/subscriptions/${projectId}`);
}

export function getMySubscriptions() {
  return requestClient.get<Subscription[]>('/api/ci-daily-report/subscriptions');
}

/**
 * 每日数据接口
 */

export interface ProjectDailyData {
  id: number;
  project_id: number;
  date: string;
  test_cases_count: number;
  test_cases_passed: number;
  compile_standard_options: any;
  build_standard_options: any;
  extra_data: any;
  created_at: string;
}

export function getProjectDailyData(params: {
  project_id?: number;
  start_date?: string;
  end_date?: string;
  page?: number;
  size?: number;
}) {
  return requestClient.get<ProjectDailyData[]>('/api/ci-daily-report/data', { params });
}
