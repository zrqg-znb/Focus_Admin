import { requestClient } from '../request';

export interface MilestoneBoard {
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

export interface MilestoneUpdate {
  qg1_date?: string;
  qg2_date?: string;
  qg3_date?: string;
  qg4_date?: string;
  qg5_date?: string;
  qg6_date?: string;
  qg7_date?: string;
  qg8_date?: string;
}

export interface MilestoneFilter {
  keyword?: string;
  project_type?: string;
  manager_id?: string;
}

enum Api {
  Overview = '/project-manager/milestones/overview',
  Update = '/project-manager/milestones/project',
}

export const getMilestoneOverview = (params?: MilestoneFilter) => {
  return requestClient.get<MilestoneBoard[]>(Api.Overview, { params });
};

export const updateMilestone = (projectId: string, data: MilestoneUpdate) => {
  return requestClient.put(`${Api.Update}/${projectId}`, data);
};
