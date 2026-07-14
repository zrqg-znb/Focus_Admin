import { requestClient } from '#/api/request';

export interface ContributionFilters {
  author_username?: string;
  branch_ids?: string[];
  branch_type?: string;
  domain?: string;
  keyword?: string;
  merged_after?: string;
  merged_before?: string;
  organization_ids?: string[];
  pl_group_ids?: string[];
  repo_type?: string;
  repository_ids?: string[];
}

export interface ContributionMetric {
  active_branch_count: number;
  active_repository_count: number;
  added_lines: number;
  baseline_branch_count: number;
  baseline_repository_count: number;
  changed_lines: number;
  contributor_count: number;
  cr_count: number;
  missing_baseline_count: number;
  net_lines: number;
  removed_lines: number;
  stock_lines: number;
}

export interface ContributionTrendPoint {
  added_lines: number;
  changed_lines: number;
  cr_count: number;
  date: string;
  net_lines: number;
  removed_lines: number;
}

export interface ContributionPlGroupTrendPoint {
  added_lines: number;
  changed_lines: number;
  cr_count: number;
  date: string;
  pl_group_name: string;
  removed_lines: number;
}

export interface ContributionRankingItem {
  added_lines: number;
  branch_name: string;
  baseline_at?: null | string;
  baseline_id?: null | string;
  baseline_lines: number;
  changed_lines: number;
  contributor_count: number;
  cr_count: number;
  has_baseline: boolean;
  id: string;
  name: string;
  net_lines: number;
  project_id: string;
  removed_lines: number;
  repository_name: string;
  stock_lines: number;
}

export interface ContributionPersonRankingItem {
  added_lines: number;
  author_display_name: string;
  author_pl_group_id?: null | string;
  author_pl_group_name: string;
  author_user_id?: null | string;
  author_user_name: string;
  author_username: string;
  branch_count: number;
  changed_lines: number;
  cr_count: number;
  net_lines: number;
  removed_lines: number;
  repository_count: number;
}

export interface ContributionCategoryItem {
  added_lines: number;
  category: string;
  category_label: string;
  changed_lines: number;
  count: number;
  cr_count: number;
  net_lines: number;
  removed_lines: number;
}

export interface ContributionCategoryDistribution {
  domains: ContributionCategoryItem[];
  pl_groups: ContributionCategoryItem[];
  repo_types: ContributionCategoryItem[];
}

export interface ContributionRecordItem {
  added_lines: number;
  author_display_name: string;
  author_pl_group_id?: null | string;
  author_pl_group_name: string;
  author_user_id?: null | string;
  author_user_name: string;
  author_username: string;
  branch_id?: null | string;
  branch_name: string;
  branch_type: string;
  branch_type_label: string;
  changed_lines: number;
  change_key: string;
  change_request_iid: string;
  contribution_date: string;
  domain: string;
  domain_label: string;
  id: string;
  merged_at?: null | string;
  net_lines: number;
  organization_group_id: string;
  organization_id?: null | string;
  organization_name: string;
  removed_lines: number;
  repository_id?: null | string;
  repository_name: string;
  repository_project_id: string;
  repo_type: string;
  repo_type_label: string;
  target_branch: string;
  title: string;
  web_url: string;
}

export interface ContributionCollectTask {
  aggregate_count: number;
  collect_diagnostics: Record<string, any>;
  created_count: number;
  error_message: string;
  fetched_count: number;
  filter_payload: Record<string, any>;
  finished_at?: null | string;
  id: string;
  merged_after: string;
  merged_before: string;
  scanned_branch_count: number;
  scanned_organization_count: number;
  scanned_repository_count: number;
  skipped_count: number;
  started_at?: null | string;
  status: string;
  status_label: string;
  sys_create_datetime?: null | string;
  trigger_type: string;
  trigger_type_label: string;
  updated_count: number;
}

export interface ContributionExportTask {
  error_message: string;
  file_name: string;
  file_size: number;
  finished_at?: null | string;
  fingerprint: string;
  id: string;
  message: string;
  progress: number;
  scope: string;
  started_at?: null | string;
  status: string;
  sys_create_datetime?: null | string;
}

export interface ContributionCodeBaseline {
  baseline_at: string;
  baseline_lines: number;
  branch_id?: null | string;
  branch_name: string;
  branch_type: string;
  id: string;
  is_current: boolean;
  operator_name: string;
  organization_group_id: string;
  organization_id?: null | string;
  organization_name: string;
  remark: string;
  repository_id: string;
  repository_name: string;
  repository_project_id: string;
  source: string;
  source_label: string;
  sys_create_datetime?: null | string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

const base = '/api/code-compliance/contributions';

function normalizeParams(params?: ContributionFilters) {
  return {
    ...params,
    branch_ids: params?.branch_ids?.length
      ? params.branch_ids.join(',')
      : undefined,
    organization_ids: params?.organization_ids?.length
      ? params.organization_ids.join(',')
      : undefined,
    pl_group_ids: params?.pl_group_ids?.length
      ? params.pl_group_ids.join(',')
      : undefined,
    repository_ids: params?.repository_ids?.length
      ? params.repository_ids.join(',')
      : undefined,
  };
}

export function getContributionSummaryApi(params?: ContributionFilters) {
  return requestClient.get<ContributionMetric>(`${base}/dashboard/summary`, {
    params: normalizeParams(params),
  });
}

export function getContributionTrendApi(params?: ContributionFilters) {
  return requestClient.get<ContributionTrendPoint[]>(`${base}/dashboard/trend`, {
    params: normalizeParams(params),
  });
}

export function getContributionPlGroupTrendApi(params?: ContributionFilters) {
  return requestClient.get<ContributionPlGroupTrendPoint[]>(
    `${base}/dashboard/pl-group-trend`,
    { params: normalizeParams(params) },
  );
}

export function getContributionRepositoryRankingApi(params?: ContributionFilters) {
  return requestClient.get<ContributionRankingItem[]>(
    `${base}/dashboard/repository-ranking`,
    { params: normalizeParams(params) },
  );
}

export function getContributionPersonRankingApi(params?: ContributionFilters) {
  return requestClient.get<ContributionPersonRankingItem[]>(
    `${base}/dashboard/person-ranking`,
    { params: normalizeParams(params) },
  );
}

export function getContributionCategoryDistributionApi(
  params?: ContributionFilters,
) {
  return requestClient.get<ContributionCategoryDistribution>(
    `${base}/dashboard/category-distribution`,
    { params: normalizeParams(params) },
  );
}

export function listContributionRecordsApi(
  params?: ContributionFilters & { page?: number; pageSize?: number },
) {
  return requestClient.get<PaginatedResponse<ContributionRecordItem>>(
    `${base}/records`,
    { params: normalizeParams(params) },
  );
}

export function runContributionCollectTaskApi(data: {
  branch_ids?: string[];
  merged_after: string;
  merged_before: string;
  organization_ids?: string[];
  repository_ids?: string[];
}) {
  return requestClient.post<{
    accepted: boolean;
    message: string;
    task: ContributionCollectTask;
  }>(`${base}/collect-tasks/run`, data);
}

export function prepareContributionExportTaskApi(data: {
  filters: ContributionFilters;
  scope: 'records' | 'summary';
}) {
  return requestClient.post<{ mode: string; task: ContributionExportTask }>(
    `${base}/export-tasks`,
    data,
  );
}

export function getContributionExportTaskApi(id: string) {
  return requestClient.get<ContributionExportTask>(`${base}/export-tasks/${id}`);
}

export function downloadContributionExportTaskApi(id: string) {
  return requestClient.get(`${base}/export-tasks/${id}/download`, {
    responseType: 'blob',
  });
}

export function listContributionCodeBaselinesApi(
  params?: ContributionFilters & {
    current_only?: boolean;
    page?: number;
    pageSize?: number;
  },
) {
  return requestClient.get<PaginatedResponse<ContributionCodeBaseline>>(
    `${base}/code-baselines`,
    { params: normalizeParams(params) },
  );
}

export function createContributionCodeBaselineApi(data: {
  baseline_at: string;
  baseline_lines: number;
  branch_id: string;
  remark?: string;
  repository_id: string;
}) {
  return requestClient.post<ContributionCodeBaseline>(
    `${base}/code-baselines`,
    data,
  );
}

export function downloadContributionBaselineTemplateApi() {
  return requestClient.get(`${base}/code-baselines/template`, {
    responseType: 'blob',
  });
}

export function importContributionBaselinesApi(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return requestClient.post(
    `${base}/code-baselines/import`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
}
