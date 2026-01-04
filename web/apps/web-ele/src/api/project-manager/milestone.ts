import { requestClient } from '#/api/request';

export interface MilestoneUpdatePayload {
  qg1_date?: string;
  qg2_date?: string;
  qg3_date?: string;
  qg4_date?: string;
  qg5_date?: string;
  qg6_date?: string;
  qg7_date?: string;
  qg8_date?: string;
}

export interface MilestoneBoardItem {
  project_id: string;
  project_name: string;
  project_domain: string;
  manager_names: string[];
  qg1_date?: string;
  qg2_date?: string;
  qg3_date?: string;
  qg4_date?: string;
  qg5_date?: string;
  qg6_date?: string;
  qg7_date?: string;
  qg8_date?: string;
}

const base = '/api/project-manager/milestones';

export async function getMilestoneBoardApi(params?: {
  keyword?: string;
  project_type?: string;
  manager_id?: string;
}) {
  return requestClient.get<MilestoneBoardItem[]>(`${base}/overview`, { params });
}

export async function updateMilestoneApi(projectId: string, data: MilestoneUpdatePayload) {
  return requestClient.put(`${base}/project/${projectId}`, data);
}
