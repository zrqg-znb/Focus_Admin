import { requestClient } from '#/api/request';

export interface DtsStatisticsFilters {
  productId: string;
  flowStates: string[];
  severityNos: string[];
  updateTimeBegin: number;
  updateTimeEnd: number;
  dtsBizNoKeyword: string;
  parentNoKeyword: string;
  projectNames: string[];
  briefDescKeyword: string;
  iTestBackCountKeyword: string;
  iNumOfCloseDaysKeyword: string;
  iNumOfFirmDaysKeyword: string;
  iNumOfLocateDaysKeyword: string;
  iNumofModifyDaysKeyword: string;
  iNumofTestDaysKeyword: string;
  currentHandlerKeywords: string[];
  creatorKeywords: string[];
  sSubmitUserNameKeywords: string[];
  last_dts009_handlerKeywords: string[];
  last_dts010_handlerKeywords: string[];
  last_dts013_handlerKeywords: string[];
  createAtBegin: number;
  createAtEnd: number;
  dCloseTimeBegin: number;
  dCloseTimeEnd: number;
  uQbiCloseTypeNames: string[];
  sDeptOneNoNames: string[];
  sSubsystemNoNames: string[];
  sConfigFlowTypes: string[];
  auto_source_types: string[];
  auto_pl_group_names: string[];
  is_downstream_values: string[];
  need_aar_values: string[];
  need_dev_analyze_values: string[];
  need_test_analyze_values: string[];
  process_quality_type_keyword: string;
  qa_remark_keyword: string;
  dev_owner_name_keyword: string[];
  issue_intro_stage_values: string[];
  dev_feature_keyword: string;
  dev_sub_category_values: string[];
  dev_reason_keyword: string;
  dev_intro_reason_keyword: string;
  dev_issue_intro_point_values: string[];
  dev_issue_probability_values: string[];
  dev_common_issue_type_values: string[];
  is_base_soft_issue_values: string[];
  is_duplicate_issue_values: string[];
  duplicate_issue_no_keyword: string;
  dev_control_points_values: string[];
  dev_intro_point_analysis_keyword: string;
  dev_improvements_keyword: string;
  dev_non_base_desc_values: string[];
  dev_aar_link_keyword: string;
  dev_asset_link_keyword: string;
  dev_asset_type_values: string[];
  dev_status_values: string[];
  dev_remark_keyword: string;
  test_owner_name_keyword: string[];
  test_miss_reason_values: string[];
  test_standard_desc_keyword: string;
  test_improvements_keyword: string;
  test_non_test_desc_keyword: string;
  test_asset_link_keyword: string;
  test_status_values: string[];
  test_remark_keyword: string;
}

export interface DtsStatisticsQuery extends DtsStatisticsFilters {
  pageIndex: number;
  pageSize: number;
}

export interface DtsMergedDefect {
  dtsBizNo: string;
  briefDesc?: null | string;
  dtsStatusName?: null | string;
  serverityNoName?: null | string;
  updateAt?: null | string;
  parentNo?: null | string;
  createAt?: null | string;
  dCloseTime?: null | string;
  uQbiCloseTypeName?: null | string;
  sDeptOneNoName?: null | string;
  currentHandler?: null | string;
  creator?: null | string;
  sSubmitUserName?: null | string;
  sSubsystemNoName?: null | string;
  sConfigFlowType?: null | string;
  sProdCName?: null | string;
  sProdFamilyNoName?: null | string;
  sProdXtdNoName?: null | string;
  iTestBackCount?: null | string;
  sSuggestByReviewer?: null | string;
  sTestReport?: null | string;
  sTestSuggest?: null | string;
  sModifyDocument?: null | string;
  sTestorTestReport?: null | string;
  last_dts009_handler?: null | string;
  last_dts010_handler?: null | string;
  last_dts013_handler?: null | string;
  iNumOfCloseDays?: null | string;
  iNumOfFirmDays?: null | string;
  iNumOfLocateDays?: null | string;
  iNumofModifyDays?: null | string;
  iNumofTestDays?: null | string;
  dts009ReasonAnalysis?: null | string;
  serverityNo?: null | string;
  productId?: null | string;
  productName?: null | string;
  projectName?: null | string;
  auto_source_type?: null | string;
  auto_pl_group_id?: null | string;
  auto_pl_group_name?: null | string;

  is_downstream?: null | string;
  process_quality_type?: null | string;
  issue_intro_stage?: null | string;
  need_aar?: null | string;
  need_dev_analyze?: null | string;
  need_test_analyze?: null | string;
  dev_owner_id?: null | string;
  dev_owner_name?: null | string;
  test_owner_id?: null | string;
  test_owner_name?: null | string;
  qa_remark?: null | string;

  dev_sub_category: string[];
  dev_feature?: null | string;
  dev_reason?: null | string;
  dev_intro_reason?: null | string;
  dev_issue_intro_point?: null | string;
  dev_issue_probability?: null | string;
  dev_common_issue_type?: null | string;
  is_base_soft_issue?: null | string;
  is_duplicate_issue?: null | string;
  duplicate_issue_no?: null | string;
  dev_control_points: string[];
  dev_intro_point_analysis?: null | string;
  dev_improvements: string[];
  dev_non_base_desc: string[];
  dev_aar_link?: null | string;
  dev_asset_link?: null | string;
  dev_asset_type: string[];
  dev_status?: null | string;
  dev_remark?: null | string;

  test_miss_reason: string[];
  test_standard_desc?: null | string;
  test_improvements: string[];
  test_non_test_desc?: null | string;
  test_asset_link?: null | string;
  test_status?: null | string;
  test_remark?: null | string;
}

export interface DtsSnapshotMeta {
  productId: string;
  productName: string;
  version: string;
  generatedAt?: null | string;
  windowBegin: number;
  windowEnd: number;
  rowCount: number;
  isStale: boolean;
}

export interface DtsListResponse {
  total: number;
  items: DtsMergedDefect[];
  snapshot?: DtsSnapshotMeta | null;
}

export interface DtsExtensionSavePayload {
  is_downstream?: null | string;
  process_quality_type?: null | string;
  issue_intro_stage?: null | string;
  need_aar?: null | string;
  need_dev_analyze?: null | string;
  need_test_analyze?: null | string;
  dev_owner_id?: null | string;
  test_owner_id?: null | string;
  qa_remark?: null | string;

  dev_sub_category?: string[];
  dev_feature?: null | string;
  dev_reason?: null | string;
  dev_intro_reason?: null | string;
  dev_issue_intro_point?: null | string;
  dev_issue_probability?: null | string;
  dev_common_issue_type?: null | string;
  is_base_soft_issue?: null | string;
  is_duplicate_issue?: null | string;
  duplicate_issue_no?: null | string;
  dev_control_points?: string[];
  dev_intro_point_analysis?: null | string;
  dev_improvements?: string[];
  dev_non_base_desc?: string[];
  dev_aar_link?: null | string;
  dev_asset_link?: null | string;
  dev_asset_type?: string[];
  dev_status?: null | string;
  dev_remark?: null | string;

  test_miss_reason?: string[];
  test_standard_desc?: null | string;
  test_improvements?: string[];
  test_non_test_desc?: null | string;
  test_asset_link?: null | string;
  test_status?: null | string;
  test_remark?: null | string;
}

export interface DtsSaveResponse {
  success: boolean;
}

export interface DtsBatchExtensionPatchPayload {
  is_downstream?: null | string;
  process_quality_type?: null | string;
  issue_intro_stage?: null | string;
  need_aar?: null | string;
  need_dev_analyze?: null | string;
  need_test_analyze?: null | string;
  dev_owner_id?: null | string;
  test_owner_id?: null | string;
  qa_remark?: null | string;

  dev_sub_category?: null | string[];
  dev_feature?: null | string;
  dev_reason?: null | string;
  dev_intro_reason?: null | string;
  dev_issue_intro_point?: null | string;
  dev_issue_probability?: null | string;
  dev_common_issue_type?: null | string;
  is_base_soft_issue?: null | string;
  is_duplicate_issue?: null | string;
  duplicate_issue_no?: null | string;
  dev_control_points?: null | string[];
  dev_intro_point_analysis?: null | string;
  dev_improvements?: null | string[];
  dev_non_base_desc?: null | string[];
  dev_aar_link?: null | string;
  dev_asset_link?: null | string;
  dev_asset_type?: null | string[];
  dev_status?: null | string;
  dev_remark?: null | string;

  test_miss_reason?: null | string[];
  test_standard_desc?: null | string;
  test_improvements?: null | string[];
  test_non_test_desc?: null | string;
  test_asset_link?: null | string;
  test_status?: null | string;
  test_remark?: null | string;
}

export interface DtsBatchExtensionSavePayload {
  defectNos: string[];
  fieldMask: string[];
  data: DtsBatchExtensionPatchPayload;
}

export interface DtsBatchSaveFailedItem {
  defectNo: string;
  errorMessage: string;
}

export interface DtsBatchSaveResponse {
  successCount: number;
  failedCount: number;
  failedItems: DtsBatchSaveFailedItem[];
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
  dev_filled_count: number;
  dev_completion_rate: number;
  test_filled_count: number;
  test_completion_rate: number;

  severity_dist: DtsDistributionItem[];
  status_dist: DtsDistributionItem[];
  team_dist: DtsDistributionItem[];
  stage_dist: DtsDistributionItem[];
  close_type_dist: DtsDistributionItem[];
  source_dist: DtsDistributionItem[];
  auto_pl_group_dist: DtsDistributionItem[];
  handler_dist: DtsDistributionItem[];
  dev_sub_category_dist: DtsDistributionItem[];
  test_miss_reason_dist: DtsDistributionItem[];
  project_dist: DtsDistributionItem[];
  action_status_dist: DtsDistributionItem[];
  snapshot?: DtsSnapshotMeta | null;
}

export type DtsTaskStatus = 'failed' | 'pending' | 'running' | 'success';

export interface DtsQueryTask {
  id: string;
  fingerprint: string;
  status: DtsTaskStatus;
  message: string;
  error_message: string;
  progress: number;
  scanned_pages: number;
  total_pages: number;
  matched_count: number;
  started_at?: null | string;
  finished_at?: null | string;
}

export interface DtsQueryPrepareResponse {
  mode: 'async' | 'ready';
  task: DtsQueryTask | null;
}

export interface DtsExportTask {
  id: string;
  fingerprint: string;
  status: DtsTaskStatus;
  message: string;
  error_message: string;
  progress: number;
  file_name?: null | string;
  file_size: number;
  started_at?: null | string;
  finished_at?: null | string;
}

export interface DtsExportPrepareResponse {
  mode: 'async' | 'ready';
  task: DtsExportTask | null;
}

export interface DtsDictOption {
  label: string;
  value: string;
}

export interface DtsDictOptions {
  yes_no: DtsDictOption[];
  issue_intro_stage: DtsDictOption[];
  dev_sub_category: DtsDictOption[];
  dev_issue_intro_point: DtsDictOption[];
  dev_issue_probability: DtsDictOption[];
  dev_common_issue_type: DtsDictOption[];
  dev_control_points: DtsDictOption[];
  dev_non_base_desc: DtsDictOption[];
  dev_asset_type: DtsDictOption[];
  test_miss_reason: DtsDictOption[];
  action_status: DtsDictOption[];
}

export interface DtsFieldSetRequest extends DtsStatisticsFilters {
  fields: string[];
}

export interface DtsFieldSetResponse {
  fieldSets: Record<string, string[]>;
}

const base = '/api/project-manager/dts-statistics';

export async function getDtsList(data: DtsStatisticsQuery) {
  return requestClient.post<DtsListResponse>(`${base}/list`, data);
}

export async function saveDtsExtension(
  dtsBizNo: string,
  data: DtsExtensionSavePayload,
) {
  return requestClient.post<DtsSaveResponse>(
    `${base}/save-extension/${dtsBizNo}`,
    data,
  );
}

export async function batchSaveDtsExtension(
  data: DtsBatchExtensionSavePayload,
) {
  return requestClient.post<DtsBatchSaveResponse>(
    `${base}/batch-save-extension`,
    data,
  );
}

export async function getDtsSummary(data: DtsStatisticsFilters) {
  return requestClient.post<DtsSummary>(`${base}/summary`, data);
}

export async function getDtsFieldSets(data: DtsFieldSetRequest) {
  return requestClient.post<DtsFieldSetResponse>(`${base}/field-sets`, data);
}

export async function prepareDtsQuery(data: DtsStatisticsFilters) {
  return requestClient.post<DtsQueryPrepareResponse>(
    `${base}/query-prepare`,
    data,
  );
}

export async function getDtsQueryTask(taskId: string) {
  return requestClient.get<DtsQueryTask>(`${base}/query-task/${taskId}`);
}

export async function exportDtsStatistics(data: DtsStatisticsFilters) {
  return requestClient.post<Blob>(`${base}/export`, data, {
    responseType: 'blob',
  });
}

export async function prepareDtsExport(data: DtsStatisticsFilters) {
  return requestClient.post<DtsExportPrepareResponse>(
    `${base}/export-prepare`,
    data,
  );
}

export async function getDtsExportTask(taskId: string) {
  return requestClient.get<DtsExportTask>(`${base}/export-task/${taskId}`);
}

export async function downloadDtsExportTask(taskId: string) {
  return requestClient.get<Blob>(`${base}/export-task/${taskId}/download`, {
    responseType: 'blob',
    timeout: 3 * 60 * 1000,
  });
}

export async function getDtsDictOptions() {
  return requestClient.get<DtsDictOptions>(`${base}/dict-options`);
}
