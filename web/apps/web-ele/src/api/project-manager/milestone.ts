import { requestClient } from '#/api/request';

export interface RiskInfo {
  id: string;
  level: string;
  description: string;
  status: string;
}

export interface MilestoneBoardItem {
  project_id: string;
  project_name: string;
  project_domain: string;
  manager_names: string[];
  qg1_date: null | string;
  qg2_date: null | string;
  qg3_date: null | string;
  qg4_date: null | string;
  qg5_date: null | string;
  qg6_date: null | string;
  qg7_date: null | string;
  qg8_date: null | string;
  risks?: Record<string, RiskInfo>;
  next_qg?: string[];
  [key: string]: any; // Allow dynamic access for QG keys
}

export interface MilestoneOverviewQuery {
  keyword?: string;
  project_type?: string;
  manager_id?: string;
  qg_filters?: string[];
  sort_field?: 'qg3_date' | 'qg4_date' | 'qg5_date';
  sort_order?: 'asc' | 'desc';
}

export interface QGConfig {
  id: string;
  milestone: string;
  qg_name: string;
  target_di: null | number;
  enabled: boolean;
  is_delayed: boolean;
}

export interface QGConfigPayload {
  qg_name: string;
  target_di?: null | number;
  enabled: boolean;
  is_delayed?: boolean;
}

export interface RiskItem {
  id: string;
  config_id: string;
  qg_name: string;
  milestone_id: string;
  project_id: string;
  project_name: string;
  record_date: string;
  risk_type: 'di' | 'dts';
  description: string;
  status: 'closed' | 'confirmed' | 'pending';
  manager_confirm_note: string;
  manager_confirm_at: null | string;
  manager_name?: null | string;
}

export interface RiskConfirmPayload {
  note: string;
  action: 'close' | 'confirm';
}

export interface RiskLog {
  id: string;
  action: string;
  operator_name: string;
  note: string;
  create_time: string;
}

export async function getMilestoneOverviewApi(params?: MilestoneOverviewQuery) {
  // 手动处理数组参数，将其转换为 JSON 字符串
  const processedParams = { ...params };
  if (processedParams.qg_filters && Array.isArray(processedParams.qg_filters)) {
    processedParams.qg_filters = JSON.stringify(processedParams.qg_filters);
  }

  return requestClient.get<MilestoneBoardItem[]>(
    '/api/project-manager/milestones/overview',
    {
      params: processedParams,
    },
  );
}

// Alias for compatibility with form.vue
export const getMilestoneBoardApi = getMilestoneOverviewApi;

export async function updateMilestoneApi(projectId: string, data: any) {
  return requestClient.put(
    `/api/project-manager/milestones/project/${projectId}`,
    data,
  );
}

// QG Config
export async function getQGConfigsApi(milestoneId: string) {
  return requestClient.get<QGConfig[]>(
    `/api/project-manager/milestones/${milestoneId}/qg-configs`,
  );
}

export async function saveQGConfigApi(
  milestoneId: string,
  data: QGConfigPayload,
) {
  return requestClient.post<QGConfig>(
    `/api/project-manager/milestones/${milestoneId}/qg-configs`,
    data,
  );
}

// Risks
export async function getPendingRisksApi(scope: 'all' | 'favorites' = 'all') {
  return requestClient.get<RiskItem[]>(
    '/api/project-manager/milestones/risks/pending',
    {
      params: { scope },
    },
  );
}

export async function getProjectRisksApi(projectId: string) {
  return requestClient.get<RiskItem[]>(
    `/api/project-manager/milestones/project/${projectId}/risks`,
  );
}

export async function getRiskLogsApi(riskId: string) {
  return requestClient.get<RiskLog[]>(
    `/api/project-manager/milestones/risks/${riskId}/logs`,
  );
}

export async function confirmRiskApi(riskId: string, data: RiskConfirmPayload) {
  return requestClient.post<boolean>(
    `/api/project-manager/milestones/risks/${riskId}/confirm`,
    data,
  );
}

// Mock
export async function mockDailyCheckApi() {
  return requestClient.post<boolean>(
    '/api/project-manager/milestones/mock/daily-check',
  );
}
