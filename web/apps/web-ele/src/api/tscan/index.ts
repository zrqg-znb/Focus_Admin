import { requestClient } from '#/api/request';

export const listProjectsApi = () => {
  return requestClient.get('/tscan/projects');
};

export const createProjectApi = (data: any) => {
  return requestClient.post('/tscan/projects', data);
};

export const listTasksApi = (projectId: string) => {
  return requestClient.get('/tscan/tasks', { params: { project_id: projectId } });
};

export const runScanTaskApi = (projectId: string) => {
  return requestClient.post(`/tscan/tasks/${projectId}/run`);
};

export const listResultsApi = (taskId: string) => {
  return requestClient.get('/tscan/results', { params: { task_id: taskId } });
};

export const applyShieldApi = (data: { result_ids: string[]; approver_id: string; reason: string }) => {
  return requestClient.post('/tscan/shield/apply', data);
};

export const listApplicationsApi = (mode: 'my_apply' | 'my_audit') => {
  return requestClient.get('/tscan/shield/applications', { params: { mode } });
};

export const auditShieldApi = (data: { application_id: string; status: string; audit_comment?: string }) => {
  return requestClient.post('/tscan/shield/audit', data);
};
