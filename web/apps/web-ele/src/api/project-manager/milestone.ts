import { requestClient } from '#/api/request';

export interface MilestoneBoardItem {
  project_id: string;
  project_name: string;
  project_domain: string;
  manager_names: string[];
  qg1_date: string | null;
  qg2_date: string | null;
  qg3_date: string | null;
  qg4_date: string | null;
  qg5_date: string | null;
  qg6_date: string | null;
  qg7_date: string | null;
  qg8_date: string | null;
  [key: string]: any; // Allow dynamic access for QG keys
}

export async function getMilestoneOverviewApi(params?: any) {
  return requestClient.get<MilestoneBoardItem[]>('/api/project-manager/milestones/overview', {
    params,
  });
}

// Alias for compatibility with form.vue
export const getMilestoneBoardApi = getMilestoneOverviewApi;

export async function updateMilestoneApi(projectId: string, data: any) {
  return requestClient.put(`/api/project-manager/milestones/project/${projectId}`, data);
}
