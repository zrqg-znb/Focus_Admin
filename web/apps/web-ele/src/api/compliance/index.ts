import { requestClient } from '#/api/request';

// Schemas
export interface ComplianceBranch {
  id: string;
  branch_name: string;
  status: number;
  remark: null | string;
}

export interface ComplianceRecord {
  id: string;
  change_id: string;
  title: string;
  update_time: string;
  url: string;
  branches: ComplianceBranch[];
  status: number; // 0: 待处理, 1: 无风险, 2: 已修复
  remark: null | string;
}

export interface PostComplianceStat {
  post_id: string;
  post_name: string;
  user_count: number;
  // Record counts
  total_risk_count: number;
  unresolved_count: number;
  // Branch counts
  total_branch_count: number;
  unresolved_branch_count: number;
}

export interface UserComplianceStat {
  user_id: string;
  user_name: string;
  avatar: null | string;
  post_name: string;
  // Record counts
  total_count: number;
  unresolved_count: number;
  fixed_count: number;
  no_risk_count: number;
  // Branch counts
  total_branch_count: number;
  unresolved_branch_count: number;
  fixed_branch_count: number;
  no_risk_branch_count: number;
}

export interface OverviewSummary {
  total_risks: number;
  unresolved_risks: number;
  total_branch_risks: number;
  unresolved_branch_risks: number;
  affected_users: number;
  items: PostComplianceStat[];
}

export interface DetailSummary {
  total_risks: number;
  unresolved_risks: number;
  fixed_risks: number;
  no_risk_risks: number;
  // Branch summaries
  total_branch_risks: number;
  unresolved_branch_risks: number;
  fixed_branch_risks: number;
  no_risk_branch_risks: number;
  items: UserComplianceStat[];
}

export interface UpdateStatusParams {
  status: number;
  remark?: string;
}

// APIs
export function getPostStats() {
  return requestClient.get<OverviewSummary>('/api/code-compliance/stats/post');
}

export function getPostUsersStats(
  postId: string,
  params?: { end_date?: string; start_date?: string },
) {
  return requestClient.get<DetailSummary>(
    `/api/code-compliance/stats/post/${postId}/users`,
    { params },
  );
}

export function getUserRecords(userId: string) {
  return requestClient.get<ComplianceRecord[]>(
    `/api/code-compliance/user/${userId}/records`,
  );
}

export function updateBranchStatus(branchId: string, data: UpdateStatusParams) {
  return requestClient.put(`/api/code-compliance/branch/${branchId}`, data);
}

export function uploadComplianceData(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return requestClient.post('/api/code-compliance/upload', formData);
}

export function getUploadTemplate() {
  return requestClient.get('/api/code-compliance/template', { responseType: 'blob' });
}
