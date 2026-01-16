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
  risks?: Record<string, string>;
  [key: string]: any; // Allow dynamic access for QG keys
}

export interface QGConfig {
  id: string;
  milestone: string;
  qg_name: string;
  target_di: number | null;
  enabled: boolean;
}

export interface QGConfigPayload {
  qg_name: string;
  target_di?: number | null;
  enabled: boolean;
}

export interface RiskItem {
  id: string;
  config_id: string;
  qg_name: string;
  milestone_id: string;
  project_id: string;
  project_name: string;
  record_date: string;
  risk_type: 'dts' | 'di';
  description: string;
  status: 'pending' | 'confirmed' | 'closed';
  manager_confirm_note: string;
  manager_confirm_at: string | null;
  manager_name?: string | null;
}

export interface RiskConfirmPayload {
  note: string;
  action: 'confirm' | 'close';
}

export interface RiskLog {
  id: string;
  action: string;
  operator_name: string;
  note: string;
  create_time: string;
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

// QG Config
export async function getQGConfigsApi(milestoneId: string) {
  return requestClient.get<QGConfig[]>(`/api/project-manager/milestones/${milestoneId}/qg-configs`);
}

export async function saveQGConfigApi(milestoneId: string, data: QGConfigPayload) {
  return requestClient.post<QGConfig>(`/api/project-manager/milestones/${milestoneId}/qg-configs`, data);
}

// Risks
export async function getPendingRisksApi(scope: 'all' | 'favorites' = 'all') {
  return requestClient.get<RiskItem[]>('/api/project-manager/milestones/risks/pending', {
    params: { scope },
  });
}

export async function getProjectRisksApi(projectId: string) {
  return requestClient.get<RiskItem[]>(`/api/project-manager/milestones/project/${projectId}/risks`);
}

export async function getRiskLogsApi(riskId: string) {
  return requestClient.get<RiskLog[]>(`/api/project-manager/milestones/risks/${riskId}/logs`);
}

export async function confirmRiskApi(riskId: string, data: RiskConfirmPayload) {
  return requestClient.post<boolean>(`/api/project-manager/milestones/risks/${riskId}/confirm`, data);
}

// Mock
export async function mockDailyCheckApi() {
  return requestClient.post<boolean>('/api/project-manager/milestones/mock/daily-check');
}
