import { requestClient } from '#/api/request';

export interface UserBriefInfo {
  id: string;
  username: string;
  name?: null | string;
}

export interface RelationItem {
  id: string;
  label: string;
  subtitle?: null | string;
}

export interface DictOption {
  label: string;
  value: string;
}

export interface FailureModeDictOptions {
  subsystem: DictOption[];
  module: DictOption[];
  chip: DictOption[];
  fault_category: DictOption[];
  functional_safety_level: DictOption[];
  occurrence_frequency: DictOption[];
  detectability: DictOption[];
  severity: DictOption[];
  status: DictOption[];
  measure_category: DictOption[];
  monitor_type: DictOption[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  limit?: number;
}

export interface FailureModeItem {
  id: string;
  brief: string;
  subsystem?: null | string;
  module?: null | string;
  chips: string[];
  fault_categories: string[];
  symptoms: string[];
  effect_html: string;
  root_cause_html: string;
  functional_safety_level?: null | string;
  occurrence_frequency?: null | string;
  detectability?: null | string;
  severity?: null | string;
  author_ids: string[];
  author_info: UserBriefInfo[];
  related_dts_nos: string[];
  status?: null | string;
  interception_strategy_ids: string[];
  interception_strategy_items: RelationItem[];
  handling_measure_ids: string[];
  handling_measure_items: RelationItem[];
  observation_method_ids: string[];
  observation_method_items: RelationItem[];
  huatuo_diagnosis_ids: string[];
  huatuo_diagnosis_items: RelationItem[];
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface FailureModePayload {
  brief: string;
  subsystem?: null | string;
  module?: null | string;
  chips?: string[];
  fault_categories?: string[];
  symptoms?: string[];
  effect_html?: string;
  root_cause_html?: string;
  functional_safety_level?: null | string;
  occurrence_frequency?: null | string;
  detectability?: null | string;
  severity?: null | string;
  author_ids?: string[];
  related_dts_nos?: string[];
  status?: null | string;
  interception_strategy_ids?: string[];
  handling_measure_ids?: string[];
  observation_method_ids?: string[];
  huatuo_diagnosis_ids?: string[];
}

export interface FailureModeQuery {
  keyword?: string;
  subsystem?: string;
  module?: string;
  status?: string;
  author_id?: string;
  page?: number;
  pageSize?: number;
}

export interface InterceptionStrategyItem {
  id: string;
  interception_item: string;
  version_detection_html: string;
  station?: null | string;
  owner_ids: string[];
  owner_info: UserBriefInfo[];
  display_name: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface InterceptionStrategyPayload {
  interception_item: string;
  version_detection_html?: string;
  station?: null | string;
  owner_ids?: string[];
}

export interface HandlingMeasureItem {
  id: string;
  measure_category?: null | string;
  measure: string;
  measure_detail_html: string;
  measure_effect: string;
  owner_ids: string[];
  owner_info: UserBriefInfo[];
  test_case_ids: string[];
  test_case_items: RelationItem[];
  display_name: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface HandlingMeasurePayload {
  measure_category?: null | string;
  measure: string;
  measure_detail_html?: string;
  measure_effect?: null | string;
  owner_ids?: string[];
  test_case_ids?: string[];
}

export interface ObservationMethodItem {
  id: string;
  monitor_type?: null | string;
  log_id?: null | string;
  log_keyword?: null | string;
  log_path?: null | string;
  owner_ids: string[];
  owner_info: UserBriefInfo[];
  display_name: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface ObservationMethodPayload {
  monitor_type?: null | string;
  log_id?: null | string;
  log_keyword?: null | string;
  log_path?: null | string;
  owner_ids?: string[];
}

export interface HuatuoDiagnosisItem {
  id: string;
  description: string;
  owner_ids: string[];
  owner_info: UserBriefInfo[];
  display_name: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface HuatuoDiagnosisPayload {
  description: string;
  owner_ids?: string[];
}

export interface TestCaseItem {
  id: string;
  brief: string;
  detail_html: string;
  cida_link?: null | string;
  owner_ids: string[];
  owner_info: UserBriefInfo[];
  display_name: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface TestCasePayload {
  brief: string;
  detail_html?: string;
  cida_link?: null | string;
  owner_ids?: string[];
}

export interface KeywordQuery {
  keyword?: string;
  page?: number;
  pageSize?: number;
}

const base = '/api/project-manager/failure-mode';

export async function getFailureModeDictOptionsApi() {
  return requestClient.get<FailureModeDictOptions>(`${base}/dict-options`);
}

export async function listFailureModesApi(params?: FailureModeQuery) {
  return requestClient.get<PaginatedResponse<FailureModeItem>>(
    `${base}/failure-modes`,
    { params },
  );
}

export async function createFailureModeApi(data: FailureModePayload) {
  return requestClient.post<FailureModeItem>(`${base}/failure-modes`, data);
}

export async function updateFailureModeApi(
  id: string,
  data: Partial<FailureModePayload>,
) {
  return requestClient.put<FailureModeItem>(
    `${base}/failure-modes/${id}`,
    data,
  );
}

export async function getFailureModeDetailApi(id: string) {
  return requestClient.get<FailureModeItem>(`${base}/failure-modes/${id}`);
}

export async function deleteFailureModeApi(id: string) {
  return requestClient.delete<{ success: boolean }>(
    `${base}/failure-modes/${id}`,
  );
}

export async function listInterceptionStrategiesApi(params?: KeywordQuery) {
  return requestClient.get<PaginatedResponse<InterceptionStrategyItem>>(
    `${base}/interception-strategies`,
    { params },
  );
}

export async function createInterceptionStrategyApi(
  data: InterceptionStrategyPayload,
) {
  return requestClient.post<InterceptionStrategyItem>(
    `${base}/interception-strategies`,
    data,
  );
}

export async function updateInterceptionStrategyApi(
  id: string,
  data: Partial<InterceptionStrategyPayload>,
) {
  return requestClient.put<InterceptionStrategyItem>(
    `${base}/interception-strategies/${id}`,
    data,
  );
}

export async function getInterceptionStrategyDetailApi(id: string) {
  return requestClient.get<InterceptionStrategyItem>(
    `${base}/interception-strategies/${id}`,
  );
}

export async function deleteInterceptionStrategyApi(id: string) {
  return requestClient.delete<{ success: boolean }>(
    `${base}/interception-strategies/${id}`,
  );
}

export async function listHandlingMeasuresApi(params?: KeywordQuery) {
  return requestClient.get<PaginatedResponse<HandlingMeasureItem>>(
    `${base}/handling-measures`,
    { params },
  );
}

export async function createHandlingMeasureApi(data: HandlingMeasurePayload) {
  return requestClient.post<HandlingMeasureItem>(
    `${base}/handling-measures`,
    data,
  );
}

export async function updateHandlingMeasureApi(
  id: string,
  data: Partial<HandlingMeasurePayload>,
) {
  return requestClient.put<HandlingMeasureItem>(
    `${base}/handling-measures/${id}`,
    data,
  );
}

export async function getHandlingMeasureDetailApi(id: string) {
  return requestClient.get<HandlingMeasureItem>(
    `${base}/handling-measures/${id}`,
  );
}

export async function deleteHandlingMeasureApi(id: string) {
  return requestClient.delete<{ success: boolean }>(
    `${base}/handling-measures/${id}`,
  );
}

export async function listObservationMethodsApi(params?: KeywordQuery) {
  return requestClient.get<PaginatedResponse<ObservationMethodItem>>(
    `${base}/observation-methods`,
    { params },
  );
}

export async function createObservationMethodApi(
  data: ObservationMethodPayload,
) {
  return requestClient.post<ObservationMethodItem>(
    `${base}/observation-methods`,
    data,
  );
}

export async function updateObservationMethodApi(
  id: string,
  data: Partial<ObservationMethodPayload>,
) {
  return requestClient.put<ObservationMethodItem>(
    `${base}/observation-methods/${id}`,
    data,
  );
}

export async function getObservationMethodDetailApi(id: string) {
  return requestClient.get<ObservationMethodItem>(
    `${base}/observation-methods/${id}`,
  );
}

export async function deleteObservationMethodApi(id: string) {
  return requestClient.delete<{ success: boolean }>(
    `${base}/observation-methods/${id}`,
  );
}

export async function listHuatuoDiagnosesApi(params?: KeywordQuery) {
  return requestClient.get<PaginatedResponse<HuatuoDiagnosisItem>>(
    `${base}/huatuo-diagnoses`,
    { params },
  );
}

export async function createHuatuoDiagnosisApi(data: HuatuoDiagnosisPayload) {
  return requestClient.post<HuatuoDiagnosisItem>(
    `${base}/huatuo-diagnoses`,
    data,
  );
}

export async function updateHuatuoDiagnosisApi(
  id: string,
  data: Partial<HuatuoDiagnosisPayload>,
) {
  return requestClient.put<HuatuoDiagnosisItem>(
    `${base}/huatuo-diagnoses/${id}`,
    data,
  );
}

export async function getHuatuoDiagnosisDetailApi(id: string) {
  return requestClient.get<HuatuoDiagnosisItem>(
    `${base}/huatuo-diagnoses/${id}`,
  );
}

export async function deleteHuatuoDiagnosisApi(id: string) {
  return requestClient.delete<{ success: boolean }>(
    `${base}/huatuo-diagnoses/${id}`,
  );
}

export async function listTestCasesApi(params?: KeywordQuery) {
  return requestClient.get<PaginatedResponse<TestCaseItem>>(
    `${base}/test-cases`,
    { params },
  );
}

export async function createTestCaseApi(data: TestCasePayload) {
  return requestClient.post<TestCaseItem>(`${base}/test-cases`, data);
}

export async function updateTestCaseApi(
  id: string,
  data: Partial<TestCasePayload>,
) {
  return requestClient.put<TestCaseItem>(`${base}/test-cases/${id}`, data);
}

export async function getTestCaseDetailApi(id: string) {
  return requestClient.get<TestCaseItem>(`${base}/test-cases/${id}`);
}

export async function deleteTestCaseApi(id: string) {
  return requestClient.delete<{ success: boolean }>(`${base}/test-cases/${id}`);
}
