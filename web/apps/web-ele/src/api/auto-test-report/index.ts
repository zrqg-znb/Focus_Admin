import type { AutoTestReportDomain } from '#/views/auto-test-report/shared/domain';

import { requestClient } from '#/api/request';

export type ResultStatus =
  | 'failed'
  | 'missing'
  | 'skip'
  | 'success'
  | 'timeout';
export type FailureCategory = 'case' | 'environment' | 'version';

export interface McuPlatformItem {
  id: string;
  name: string;
  version_code: string;
  domain: AutoTestReportDomain;
  sort: number;
  is_active: boolean;
  remark?: string;
  vehicle_count: number;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface PlatformPayload {
  name: string;
  version_code: string;
  domain: AutoTestReportDomain;
  sort: number;
  is_active: boolean;
  remark?: string;
}

export interface VehicleItem {
  id: string;
  platform_id: string;
  platform_name: string;
  name: string;
  vehicle_code: string;
  cdc_platform: string;
  execution_machine: string;
  viu_codes: string[];
  sort: number;
  is_active: boolean;
  remark?: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface VehiclePayload {
  platform_id: string;
  name: string;
  vehicle_code: string;
  cdc_platform: string;
  execution_machine: string;
  viu_codes: string[];
  sort: number;
  is_active: boolean;
  remark?: string;
}

export interface VehicleOption {
  id: string;
  name: string;
  vehicle_code: string;
  platform_id: string;
  platform_name: string;
  viu_codes: string[];
}

export interface TestCaseItem {
  id: string;
  vehicle_id: string;
  vehicle_name: string;
  vehicle_code: string;
  platform_name: string;
  viu_code: string;
  case_no: string;
  case_name: string;
  remark?: string;
  sort: number;
  is_active: boolean;
  latest_execute_time?: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface TestCasePayload {
  vehicle_id: string;
  viu_code: string;
  case_no: string;
  case_name: string;
  remark?: string;
  sort: number;
  is_active: boolean;
}

export interface ImportCaseRow {
  viu_code?: string;
  case_no: string;
  case_name: string;
  remark?: string;
}

export interface TestCaseQueryParams {
  domain?: AutoTestReportDomain;
  is_active?: boolean;
  keyword?: string;
  platform_id?: string;
  vehicle_id?: string;
  viu_code?: string;
}

export interface ImportErrorRow {
  row_no: number;
  message: string;
}

export interface ImportResult {
  created_count: number;
  updated_count: number;
  ignored_count: number;
  errors: ImportErrorRow[];
}

export interface SummaryStat {
  key: ResultStatus;
  label: string;
  count: number;
  ratio: number;
}

export interface DailySummary {
  vehicle_id: string;
  vehicle_name: string;
  vehicle_code: string;
  execute_date: string;
  total_count: number;
  success_count: number;
  failed_count: number;
  timeout_count: number;
  skip_count: number;
  missing_result_count: number;
  total_duration_seconds: number;
  stats: SummaryStat[];
  last_report_at?: string;
}

export interface DailyOverviewRow {
  vehicle_id: string;
  vehicle_name: string;
  vehicle_code: string;
  platform_id: string;
  platform_name: string;
  total_count: number;
  success_count: number;
  failed_count: number;
  timeout_count: number;
  skip_count: number;
  non_version_failure_count: number;
  version_failure_count: number;
  uncategorized_failure_count: number;
  missing_result_count: number;
  total_duration_seconds: number;
  last_report_at?: string;
  is_abnormal: boolean;
}

export interface DailyOverviewSummary {
  execute_date: string;
  vehicle_count: number;
  abnormal_vehicle_count: number;
  total_case_count: number;
  success_count: number;
  failed_count: number;
  timeout_count: number;
  skip_count: number;
  non_version_failure_count: number;
  version_failure_count: number;
  uncategorized_failure_count: number;
  missing_result_count: number;
  downstream_trigger_enabled: boolean;
  downstream_trigger_block_reasons: string[];
  total_duration_seconds: number;
  stats: SummaryStat[];
  last_report_at?: string;
}

export interface DailyOverviewResponse {
  items: DailyOverviewRow[];
  summary: DailyOverviewSummary;
}

export interface DailyResultItem {
  result_id?: string;
  case_id: string;
  viu_code: string;
  case_no: string;
  case_name: string;
  remark?: string;
  status: ResultStatus;
  failure_reason?: string;
  failure_category?: FailureCategory;
  suggested_failure_reason?: string;
  start_time?: string;
  duration_seconds: number;
  log_url?: string;
  car_log_url?: string;
  reported_at?: string;
}

export interface TestCaseHistoryRow {
  id: string;
  execute_date: string;
  viu_code: string;
  status: ResultStatus;
  failure_reason?: string;
  failure_category?: FailureCategory;
  start_time?: string;
  duration_seconds: number;
  log_url?: string;
  car_log_url?: string;
  reported_at?: string;
}

export interface TestCaseHistoryPage {
  items: TestCaseHistoryRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface DownstreamTriggerResult {
  triggered: boolean;
  dry_run: boolean;
  message: string;
  execute_date: string;
  vehicle_count: number;
  total_case_count: number;
  success_count: number;
  failed_count: number;
  timeout_count: number;
  skip_count: number;
  non_version_failure_count: number;
  version_failure_count: number;
  uncategorized_failure_count: number;
  missing_result_count: number;
  block_reasons: string[];
}

const base = '/api/auto-test-report';

export async function listPlatformsApi(params?: {
  domain?: AutoTestReportDomain;
}) {
  return requestClient.get<McuPlatformItem[]>(`${base}/platforms`, { params });
}

export async function createPlatformApi(data: PlatformPayload) {
  return requestClient.post<McuPlatformItem>(`${base}/platforms`, data);
}

export async function updatePlatformApi(id: string, data: PlatformPayload) {
  return requestClient.put<McuPlatformItem>(`${base}/platforms/${id}`, data);
}

export async function deletePlatformApi(id: string) {
  return requestClient.delete<boolean>(`${base}/platforms/${id}`);
}

export async function listVehiclesApi(params?: {
  domain?: AutoTestReportDomain;
  keyword?: string;
  platform_id?: string;
}) {
  return requestClient.get<VehicleItem[]>(`${base}/vehicles`, { params });
}

export async function listVehicleOptionsApi(domain?: AutoTestReportDomain) {
  return requestClient.get<VehicleOption[]>(`${base}/vehicle-options`, {
    params: { domain },
  });
}

export async function createVehicleApi(data: VehiclePayload) {
  return requestClient.post<VehicleItem>(`${base}/vehicles`, data);
}

export async function updateVehicleApi(id: string, data: VehiclePayload) {
  return requestClient.put<VehicleItem>(`${base}/vehicles/${id}`, data);
}

export async function deleteVehicleApi(id: string) {
  return requestClient.delete<boolean>(`${base}/vehicles/${id}`);
}

export async function listTestCasesApi(params?: TestCaseQueryParams) {
  return requestClient.get<TestCaseItem[]>(`${base}/test-cases`, { params });
}

export async function createTestCaseApi(data: TestCasePayload) {
  return requestClient.post<TestCaseItem>(`${base}/test-cases`, data);
}

export async function updateTestCaseApi(id: string, data: TestCasePayload) {
  return requestClient.put<TestCaseItem>(`${base}/test-cases/${id}`, data);
}

export async function deleteTestCaseApi(id: string) {
  return requestClient.delete<boolean>(`${base}/test-cases/${id}`);
}

export async function batchDeleteTestCasesApi(ids: string[]) {
  return requestClient.post<number>(`${base}/test-cases/batch-delete`, { ids });
}

export async function importTestCasesApi(
  vehicle_id: string,
  rows: ImportCaseRow[],
) {
  return requestClient.post<ImportResult>(`${base}/test-cases/import`, {
    vehicle_id,
    rows,
  });
}

export async function importTestCasesExcelApi(vehicle_id: string, file: File) {
  const formData = new FormData();
  formData.append('vehicle_id', vehicle_id);
  formData.append('file', file);
  return requestClient.post<ImportResult>(
    `${base}/test-cases/import-excel`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
}

export async function downloadTestCaseTemplateApi(
  domain?: AutoTestReportDomain,
) {
  return requestClient.get(`${base}/test-cases/template`, {
    params: { domain },
    responseType: 'blob',
  });
}

export async function downloadTestCaseExportApi(params?: TestCaseQueryParams) {
  return requestClient.get(`${base}/test-cases/export`, {
    params,
    responseType: 'blob',
  });
}

export async function getDailySummaryApi(
  vehicle_id: string,
  execute_date: string,
  domain?: AutoTestReportDomain,
) {
  return requestClient.get<DailySummary>(`${base}/daily-results/summary`, {
    params: { vehicle_id, execute_date, domain },
  });
}

export async function getDailyOverviewApi(params: {
  abnormal_only?: boolean;
  domain?: AutoTestReportDomain;
  execute_date: string;
  platform_id?: string;
}) {
  return requestClient.get<DailyOverviewResponse>(
    `${base}/daily-results/overview`,
    {
      params,
    },
  );
}

export async function listDailyResultsApi(
  vehicle_id: string,
  execute_date: string,
  domain?: AutoTestReportDomain,
) {
  return requestClient.get<DailyResultItem[]>(`${base}/daily-results/list`, {
    params: { vehicle_id, execute_date, domain },
  });
}

export async function updateDailyResultFailureReasonApi(
  result_id: string,
  failure_reason?: string,
  failure_category?: FailureCategory,
) {
  return requestClient.request<boolean>(
    `${base}/daily-results/${result_id}/failure-reason`,
    {
      method: 'PATCH',
      data: { failure_category, failure_reason },
    },
  );
}

export async function triggerCockpitDownstreamApi(execute_date: string) {
  return requestClient.post<DownstreamTriggerResult>(
    `${base}/daily-results/downstream-trigger`,
    { execute_date },
  );
}

export async function getTestCaseHistoryApi(
  caseId: string,
  page: number,
  pageSize: number,
) {
  return requestClient.get<TestCaseHistoryPage>(
    `${base}/test-cases/${caseId}/history`,
    {
      params: { page, pageSize },
    },
  );
}
