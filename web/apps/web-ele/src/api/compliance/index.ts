import { requestClient } from '#/api/request';

// Schemas
export interface ComplianceRecord {
  id: string;
  change_id: string;
  title: string;
  update_time: string;
  url: string;
  missing_branches: string[];
  status: number; // 0: 待处理, 1: 无风险, 2: 已修复
  remark: null | string;
}

export interface DeptComplianceStat {
  dept_id: string;
  dept_name: string;
  user_count: number;
  total_risk_count: number;
  unresolved_count: number;
}

export interface UserComplianceStat {
  user_id: string;
  user_name: string;
  avatar: null | string;
  dept_name: string;
  total_count: number;
  unresolved_count: number;
  fixed_count: number;
  no_risk_count: number;
}

export interface OverviewSummary {
  total_risks: number;
  unresolved_risks: number;
  affected_users: number;
  affected_branches: number;
  items: DeptComplianceStat[];
}

export interface DetailSummary {
  total_risks: number;
  unresolved_risks: number;
  fixed_risks: number;
  no_risk_risks: number;
  items: UserComplianceStat[];
}

export interface UpdateRecordParams {
  status: number;
  remark?: string;
}

// APIs
export function getDeptStats() {
  return requestClient.get<OverviewSummary>('/api/code-compliance/stats/dept');
}

export function getDeptUsersStats(
  deptId: string,
  params?: { end_date?: string; start_date?: string },
) {
  return requestClient.get<DetailSummary>(
    `/api/code-compliance/stats/dept/${deptId}/users`,
    { params },
  );
}

export function getUserRecords(userId: string) {
  return requestClient.get<ComplianceRecord[]>(
    `/api/code-compliance/user/${userId}/records`,
  );
}

export function updateRecordStatus(recordId: string, data: UpdateRecordParams) {
  return requestClient.put(`/api/code-compliance/record/${recordId}`, data);
}
