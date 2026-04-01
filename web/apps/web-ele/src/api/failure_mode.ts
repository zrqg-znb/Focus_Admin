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
  symptom: DictOption[];
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

export interface FailureModeSubsystemLinkedOption {
  subsystem: string;
  module_options: string[];
  chip_options: string[];
}

export interface FailureModeSubsystemConfigOptions {
  subsystem_options: DictOption[];
  module_options: DictOption[];
  chip_options: DictOption[];
  items: FailureModeSubsystemLinkedOption[];
}

export interface FailureModeSubsystemConfigItem {
  id: string;
  subsystem: string;
  module_options: string[];
  chip_options: string[];
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface FailureModeSubsystemConfigPayload {
  subsystem: string;
  module_options?: string[];
  chip_options?: string[];
}

export interface FailureModeSubsystemConfigQuery {
  keyword?: string;
  page?: number;
  pageSize?: number;
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
  source_type: 'manual' | 'task_quick_create';
  source_task_id?: null | string;
  source_task_no?: null | string;
  interception_required: boolean;
  huatuo_required: boolean;
  required_handling_measure_categories: string[];
  required_observation_method_types: string[];
  interception_strategy_ids: string[];
  interception_strategy_items: RelationItem[];
  handling_measure_ids: string[];
  handling_measure_items: RelationItem[];
  observation_method_ids: string[];
  observation_method_items: RelationItem[];
  huatuo_diagnosis_ids: string[];
  huatuo_diagnosis_items: RelationItem[];
  task_change_type?: 'baseline' | 'delete_candidate' | 'edited' | 'new' | null;
  has_task_draft?: boolean;
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
  interception_required?: boolean;
  huatuo_required?: boolean;
  required_handling_measure_categories?: string[];
  required_observation_method_types?: string[];
  interception_strategy_ids?: string[];
  handling_measure_ids?: string[];
  observation_method_ids?: string[];
  huatuo_diagnosis_ids?: string[];
}

export interface FailureModeQuery {
  keyword?: string;
  subsystem?: string[];
  module?: string[];
  status?: string[];
  author_id?: string;
  author_keyword?: string;
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
  owner_keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface HandlingMeasureQuery extends KeywordQuery {
  measure_category?: string[];
}

export interface ObservationMethodQuery extends KeywordQuery {
  monitor_type?: string[];
}

export interface FailureModeStatisticsChartDatum {
  name: string;
  value: number;
}

export interface FailureModeStatisticsSummary {
  subsystem_counts: FailureModeStatisticsChartDatum[];
  interception_status: FailureModeStatisticsChartDatum[];
  huatuo_status: FailureModeStatisticsChartDatum[];
  handling_detection_status: FailureModeStatisticsChartDatum[];
  handling_prevention_status: FailureModeStatisticsChartDatum[];
  handling_self_heal_status: FailureModeStatisticsChartDatum[];
  observation_pipeline_log_status: FailureModeStatisticsChartDatum[];
  observation_dmd_status: FailureModeStatisticsChartDatum[];
  observation_fmp_status: FailureModeStatisticsChartDatum[];
}

export interface FailureModeStatisticsSubsystemRow {
  subsystem: string;
  failure_mode_count: number;
  interception_relation_count: number;
  handling_detection_relation_count: number;
  handling_prevention_relation_count: number;
  handling_self_heal_relation_count: number;
  observation_pipeline_log_relation_count: number;
  observation_dmd_relation_count: number;
  observation_fmp_relation_count: number;
  huatuo_relation_count: number;
  pending_failure_mode_count: number;
  pending_rate: number;
  status_light: 'green' | 'red' | 'yellow' | string;
}

export interface FailureModeStatisticsSubsystemQuery {
  keyword?: string;
  page?: number;
  pageSize?: number;
}

const base = '/api/failure-mode';

export async function getFailureModeDictOptionsApi() {
  return requestClient.get<FailureModeDictOptions>(`${base}/dict-options`);
}

export async function getFailureModeSubsystemConfigOptionsApi() {
  return requestClient.get<FailureModeSubsystemConfigOptions>(
    `${base}/subsystem-configs/options`,
  );
}

export async function listFailureModeSubsystemConfigsApi(
  data?: FailureModeSubsystemConfigQuery,
) {
  return requestClient.post<PaginatedResponse<FailureModeSubsystemConfigItem>>(
    `${base}/subsystem-configs/search`,
    data ?? {},
  );
}

export async function createFailureModeSubsystemConfigApi(
  data: FailureModeSubsystemConfigPayload,
) {
  return requestClient.post<FailureModeSubsystemConfigItem>(
    `${base}/subsystem-configs`,
    data,
  );
}

export async function getFailureModeSubsystemConfigDetailApi(id: string) {
  return requestClient.get<FailureModeSubsystemConfigItem>(
    `${base}/subsystem-configs/${id}`,
  );
}

export async function updateFailureModeSubsystemConfigApi(
  id: string,
  data: Partial<FailureModeSubsystemConfigPayload>,
) {
  return requestClient.put<FailureModeSubsystemConfigItem>(
    `${base}/subsystem-configs/${id}`,
    data,
  );
}

export async function deleteFailureModeSubsystemConfigApi(id: string) {
  return requestClient.delete<{ success: boolean }>(
    `${base}/subsystem-configs/${id}`,
  );
}

export async function getFailureModeStatisticsSummaryApi() {
  return requestClient.post<FailureModeStatisticsSummary>(
    `${base}/statistics/summary`,
    {},
  );
}

export async function listFailureModeStatisticsSubsystemsApi(
  data?: FailureModeStatisticsSubsystemQuery,
) {
  return requestClient.post<
    PaginatedResponse<FailureModeStatisticsSubsystemRow>
  >(`${base}/statistics/subsystems/search`, data ?? {});
}

export async function listFailureModesApi(data?: FailureModeQuery) {
  return requestClient.post<PaginatedResponse<FailureModeItem>>(
    `${base}/failure-modes/search`,
    data ?? {},
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

export async function listInterceptionStrategiesApi(data?: KeywordQuery) {
  return requestClient.post<PaginatedResponse<InterceptionStrategyItem>>(
    `${base}/interception-strategies/search`,
    data ?? {},
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

export async function listHandlingMeasuresApi(data?: HandlingMeasureQuery) {
  return requestClient.post<PaginatedResponse<HandlingMeasureItem>>(
    `${base}/handling-measures/search`,
    data ?? {},
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

export async function listObservationMethodsApi(data?: ObservationMethodQuery) {
  return requestClient.post<PaginatedResponse<ObservationMethodItem>>(
    `${base}/observation-methods/search`,
    data ?? {},
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

export async function listHuatuoDiagnosesApi(data?: KeywordQuery) {
  return requestClient.post<PaginatedResponse<HuatuoDiagnosisItem>>(
    `${base}/huatuo-diagnoses/search`,
    data ?? {},
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

export async function listTestCasesApi(data?: KeywordQuery) {
  return requestClient.post<PaginatedResponse<TestCaseItem>>(
    `${base}/test-cases/search`,
    data ?? {},
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
