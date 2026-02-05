import { requestClient } from '#/api/request';

export const listProjectsApi = () => {
  return requestClient.get('/api/code-scan/projects');
};

export const listProjectOverviewApi = () => {
  return requestClient.get('/api/code-scan/projects/overview');
};

export const createProjectApi = (data: any) => {
  return requestClient.post('/api/code-scan/projects', data);
};

export const updateProjectApi = (id: string, data: any) => {
  return requestClient.put(`/api/code-scan/projects/${id}`, data);
};

export const listTasksApi = (projectId: string) => {
  return requestClient.get('/api/code-scan/tasks', { params: { project_id: projectId } });
};

export const runScanTaskApi = (projectId: string) => {
  return requestClient.post(`/api/code-scan/tasks/${projectId}/run`);
};

export const listResultsApi = (taskId: string) => {
  return requestClient.get('/api/code-scan/results', { params: { task_id: taskId } });
};

export const listLatestResultsApi = (projectId: string) => {
  return requestClient.get(`/api/code-scan/projects/${projectId}/latest-results`);
};

export const applyShieldApi = (data: { result_ids: string[]; approver_id: string; reason: string }) => {
  return requestClient.post('/api/code-scan/shield/apply', data);
};

export const listApplicationsApi = (mode: 'my_apply' | 'my_audit') => {
  return requestClient.get('/api/code-scan/shield/applications', { params: { mode } });
};

export const auditShieldApi = (data: { application_id: string; status: string; audit_comment?: string }) => {
  return requestClient.post('/api/code-scan/shield/audit', data);
};
