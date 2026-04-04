import { requestClient } from '#/api/request';

export interface DtsStatisticsFilters {
  productId: string;
  flowStates: string[];
  severityNos: string[];
  updateTimeBegin: number;
  updateTimeEnd: number;
}

export interface DtsStatisticsQuery extends DtsStatisticsFilters {
  pageIndex: number;
  pageSize: number;
}

export interface DtsMergedDefect {
  defectNo: string;
  dtsBizNo?: null | string;
  brief?: string;
  briefDesc?: null | string;
  severity?: string;
  serverityNo?: null | string;
  serverityNoName?: null | string;
  weight?: null | string;
  submitTime?: null | string;
  createAt?: null | string;
  dCloseTime?: null | string;
  submitterId?: null | string;
  submitTeam?: null | string;
  currentHandler?: null | string;
  currentTeam?: null | string;
  currentStatus?: null | string;
  dtsStatus?: null | string;
  dtsStatusName?: null | string;
  flowState?: null | string;
  currentStage?: null | string;
  closeType?: null | string;
  process_days?: null | string;
  parentNo?: null | string;
  sDeptOneNoName?: null | string;
  creator?: null | string;
  sSubmitUserName?: null | string;
  sSubmitsystemNoName?: null | string;
  sTestorTestReport?: null | string;
  productId?: null | string;
  productName?: null | string;

  project_ids: string[];
  project_names: string[];
  team_names: string[];
  project_name?: null | string;
  team_name?: null | string;

  qa_category?: null | string;
  pl_group_id?: null | string;
  pl_group_name?: null | string;
  is_downstream?: null | string;
  process_quality_type?: null | string;
  need_dev_analyze?: null | string;
  need_test_analyze?: null | string;
  dev_owner_id?: null | string;
  dev_owner_name?: null | string;
  test_owner_id?: null | string;
  test_owner_name?: null | string;
  is_dev_analyzed?: null | string;
  is_test_analyzed?: null | string;
  qa_remark?: null | string;

  dev_sub_category: string[];
  dev_reason?: null | string;
  dev_intro_reason?: null | string;
  dev_improvements: string[];
  dev_non_base_desc: string[];
  dev_asset_link?: null | string;
  dev_status?: null | string;

  test_feature?: null | string;
  test_miss_reason: string[];
  test_standard_desc?: null | string;
  test_improvements: string[];
  test_non_test_desc?: null | string;
  test_asset_link?: null | string;
  test_status?: null | string;
}

export interface DtsListResponse {
  total: number;
  items: DtsMergedDefect[];
}

export interface DtsExtensionSavePayload {
  project_ids?: string[];
  qa_category?: null | string;
  pl_group_id?: null | string;
  is_downstream?: null | string;
  process_quality_type?: null | string;
  need_dev_analyze?: null | string;
  need_test_analyze?: null | string;
  dev_owner_id?: null | string;
  test_owner_id?: null | string;
  is_dev_analyzed?: null | string;
  is_test_analyzed?: null | string;
  qa_remark?: null | string;

  dev_sub_category?: string[];
  dev_reason?: null | string;
  dev_intro_reason?: null | string;
  dev_improvements?: string[];
  dev_non_base_desc?: string[];
  dev_asset_link?: null | string;
  dev_status?: null | string;

  test_feature?: null | string;
  test_miss_reason?: string[];
  test_standard_desc?: null | string;
  test_improvements?: string[];
  test_non_test_desc?: null | string;
  test_asset_link?: null | string;
  test_status?: null | string;
}

export interface DtsSaveResponse {
  success: boolean;
}

export interface DtsDistributionItem {
  label: string;
  value: number;
}

export interface DtsSummary {
  total_count: number;
  open_count: number;
  closed_count: number;
  avg_process_days: number;

  qa_filled_count: number;
  qa_completion_rate: number;
  dev_analyzed_count: number;
  dev_analysis_completion_rate: number;
  test_analyzed_count: number;
  test_analysis_completion_rate: number;

  severity_dist: DtsDistributionItem[];
  status_dist: DtsDistributionItem[];
  team_dist: DtsDistributionItem[];
  stage_dist: DtsDistributionItem[];
  close_type_dist: DtsDistributionItem[];
  handler_dist: DtsDistributionItem[];
  qa_category_dist: DtsDistributionItem[];
  dev_sub_category_dist: DtsDistributionItem[];
  test_miss_reason_dist: DtsDistributionItem[];
  pl_group_dist: DtsDistributionItem[];
  project_dist: DtsDistributionItem[];
  action_status_dist: DtsDistributionItem[];
}

export interface DtsDictOption {
  label: string;
  value: string;
}

export interface DtsDictOptions {
  yes_no: DtsDictOption[];
  qa_category: DtsDictOption[];
  process_quality_type: DtsDictOption[];
  dev_sub_category: DtsDictOption[];
  dev_non_base_desc: DtsDictOption[];
  test_miss_reason: DtsDictOption[];
  action_status: DtsDictOption[];
}

const base = '/api/project-manager/dts-statistics';

export async function getDtsList(data: DtsStatisticsQuery) {
  return requestClient.post<DtsListResponse>(`${base}/list`, data);
}

export async function saveDtsExtension(
  defectNo: string,
  data: DtsExtensionSavePayload,
) {
  return requestClient.post<DtsSaveResponse>(
    `${base}/save-extension/${defectNo}`,
    data,
  );
}

export async function getDtsSummary(data: DtsStatisticsFilters) {
  return requestClient.post<DtsSummary>(`${base}/summary`, data);
}

export async function exportDtsStatistics(data: DtsStatisticsFilters) {
  return requestClient.post<Blob>(`${base}/export`, data, {
    responseType: 'blob',
  });
}

export async function getDtsDictOptions() {
  return requestClient.get<DtsDictOptions>(`${base}/dict-options`);
}
