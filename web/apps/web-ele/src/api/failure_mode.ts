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

export interface FailureModeScopeBinding {
  product_id: string;
  subsystem: string;
  product_name?: null | string;
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
  scope_bindings: FailureModeScopeBinding[];
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
  editable_in_task?: boolean;
  task_edit_mode?: 'direct_update' | 'draft' | null;
  landing_completed?: boolean;
  failure_mode_landing_status?: string;
  failure_mode_is_landed?: boolean;
  landing_resource_total?: number;
  landing_resource_selected_count?: number;
  landing_resource_landed_count?: number;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface FailureModeInsightProductRow {
  product_id: string;
  product_name: string;
  owner_info?: null | UserBriefInfo;
  subsystems: string[];
  failure_mode_status: string;
  interception_rows: FailureModeInsightResourceRow[];
  handling_rows: FailureModeInsightResourceRow[];
  observation_rows: FailureModeInsightResourceRow[];
  huatuo_rows: FailureModeInsightResourceRow[];
  landed_at?: null | string;
}

export interface FailureModeInsightResourceRow {
  id: string;
  label: string;
  subtitle?: null | string;
  status: string;
}

export interface FailureModeInsight {
  id: string;
  brief: string;
  subsystem?: null | string;
  status?: null | string;
  landed_product_count: number;
  related_product_count: number;
  total_product_count: number;
  product_rows: FailureModeInsightProductRow[];
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
  scope_bindings?: FailureModeScopeBinding[];
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

export interface InterceptionInsightFailureModeRow {
  failure_mode_id: string;
  failure_mode_brief: string;
  subsystem?: null | string;
  status?: null | string;
  product_names: string[];
  landed_product_count: number;
}

export interface InterceptionInsightProductRow {
  product_id: string;
  product_name: string;
  owner_info?: null | UserBriefInfo;
  failure_mode_briefs: string[];
}

export interface InterceptionInsight {
  id: string;
  interception_item: string;
  station?: null | string;
  related_failure_mode_count: number;
  landed_product_count: number;
  total_product_count: number;
  failure_mode_rows: InterceptionInsightFailureModeRow[];
  product_rows: InterceptionInsightProductRow[];
}

export interface HandlingMeasureInsight {
  id: string;
  measure: string;
  measure_category?: null | string;
  related_test_case_count: number;
  related_failure_mode_count: number;
  landed_product_count: number;
  total_product_count: number;
  failure_mode_rows: InterceptionInsightFailureModeRow[];
  product_rows: InterceptionInsightProductRow[];
}

export interface ObservationMethodInsight {
  id: string;
  display_name: string;
  monitor_type?: null | string;
  log_id?: null | string;
  log_keyword?: null | string;
  log_path?: null | string;
  related_failure_mode_count: number;
  landed_product_count: number;
  total_product_count: number;
  failure_mode_rows: InterceptionInsightFailureModeRow[];
  product_rows: InterceptionInsightProductRow[];
}

export interface HuatuoDiagnosisInsight {
  id: string;
  description: string;
  related_failure_mode_count: number;
  landed_product_count: number;
  total_product_count: number;
  failure_mode_rows: InterceptionInsightFailureModeRow[];
  product_rows: InterceptionInsightProductRow[];
}

export interface TestCaseInsight {
  id: string;
  brief: string;
  cida_link?: null | string;
  related_handling_measure_count: number;
  related_failure_mode_count: number;
  landed_product_count: number;
  total_product_count: number;
  failure_mode_rows: InterceptionInsightFailureModeRow[];
  product_rows: InterceptionInsightProductRow[];
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
  failure_mode_landing_status: FailureModeStatisticsChartDatum[];
  interception_status: FailureModeStatisticsChartDatum[];
  huatuo_status: FailureModeStatisticsChartDatum[];
  handling_detection_status: FailureModeStatisticsChartDatum[];
  handling_prevention_status: FailureModeStatisticsChartDatum[];
  handling_self_heal_status: FailureModeStatisticsChartDatum[];
  observation_pipeline_log_status: FailureModeStatisticsChartDatum[];
  observation_dmd_status: FailureModeStatisticsChartDatum[];
  observation_fmp_status: FailureModeStatisticsChartDatum[];
}

export interface FailureModeStatisticsSummaryQuery {
  subsystems?: string[];
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
  subsystems?: string[];
  page?: number;
  pageSize?: number;
}

function normalizeStringArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    const result: string[] = [];
    const seen = new Set<string>();
    value.forEach((item) => {
      if (typeof item === 'string') {
        const nested = item.trim();
        if (nested.startsWith('[') && nested.endsWith(']')) {
          try {
            const parsed = JSON.parse(nested);
            if (Array.isArray(parsed)) {
              normalizeStringArray(parsed).forEach((nestedItem) => {
                if (!nestedItem || seen.has(nestedItem)) {
                  return;
                }
                seen.add(nestedItem);
                result.push(nestedItem);
              });
              return;
            }
          } catch {}
        }
      }
      const text = String(item ?? '').trim();
      if (!text || seen.has(text)) {
        return;
      }
      seen.add(text);
      result.push(text);
    });
    return result;
  }

  if (typeof value === 'string') {
    const text = value.trim();
    if (!text) {
      return [];
    }
    if (text.startsWith('[') && text.endsWith(']')) {
      try {
        const parsed = JSON.parse(text);
        if (Array.isArray(parsed)) {
          return normalizeStringArray(parsed);
        }
      } catch {}
    }
    return [text];
  }

  if (value === null || value === undefined) {
    return [];
  }

  return normalizeStringArray([value]);
}

function normalizeScopeBindings(value: unknown): FailureModeScopeBinding[] {
  let items: unknown[] = [];
  if (Array.isArray(value)) {
    items = value;
  } else if (value) {
    items = [value];
  }
  const result: FailureModeScopeBinding[] = [];
  const seen = new Set<string>();

  items.forEach((item) => {
    const raw =
      item && typeof item === 'object'
        ? (item as Record<string, unknown>)
        : { product_id: item };
    const productId = String(raw.product_id ?? '').trim();
    const subsystem = String(raw.subsystem ?? '').trim();
    if (!productId || !subsystem) {
      return;
    }
    const key = `${productId}::${subsystem}`;
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    result.push({
      product_id: productId,
      subsystem,
      product_name: String(raw.product_name ?? '').trim() || null,
    });
  });

  return result;
}

export function normalizeFailureModeItem(
  item: FailureModeItem,
): FailureModeItem {
  return {
    ...item,
    chips: normalizeStringArray(item.chips),
    fault_categories: normalizeStringArray(item.fault_categories),
    symptoms: normalizeStringArray(item.symptoms),
    related_dts_nos: normalizeStringArray(item.related_dts_nos),
    required_handling_measure_categories: normalizeStringArray(
      item.required_handling_measure_categories,
    ),
    required_observation_method_types: normalizeStringArray(
      item.required_observation_method_types,
    ),
    scope_bindings: normalizeScopeBindings(item.scope_bindings),
    interception_strategy_ids: normalizeStringArray(
      item.interception_strategy_ids,
    ),
    handling_measure_ids: normalizeStringArray(item.handling_measure_ids),
    observation_method_ids: normalizeStringArray(item.observation_method_ids),
    huatuo_diagnosis_ids: normalizeStringArray(item.huatuo_diagnosis_ids),
    has_task_draft: Boolean(item.has_task_draft),
    editable_in_task: Boolean(item.editable_in_task),
    task_edit_mode: item.task_edit_mode || null,
    landing_completed: Boolean(item.landing_completed),
    failure_mode_landing_status:
      item.failure_mode_landing_status ||
      (item.failure_mode_is_landed ? '已落地' : '未落地'),
    failure_mode_is_landed: Boolean(item.failure_mode_is_landed),
    landing_resource_total: Number(item.landing_resource_total || 0),
    landing_resource_selected_count: Number(
      item.landing_resource_selected_count || 0,
    ),
    landing_resource_landed_count: Number(
      item.landing_resource_landed_count || 0,
    ),
  };
}

export interface TaskFailureModeLandingProductRow {
  product_id: string;
  product_name: string;
  subsystems: string[];
  landing_status?: null | string;
}

export interface TaskFailureModeLandingResourceRow {
  resource_id: string;
  label: string;
  subtitle?: null | string;
  group_key: string;
  landing_status?: null | string;
  product_rows: TaskFailureModeLandingProductRow[];
}

export interface TaskFailureModeLandingDetail {
  task_id: string;
  failure_mode_id: string;
  failure_mode_brief: string;
  failure_mode_landing_status: string;
  failure_mode_is_landed: boolean;
  landing_completed: boolean;
  landing_resource_total: number;
  landing_resource_selected_count: number;
  landing_resource_landed_count: number;
  products: TaskFailureModeLandingProductRow[];
  interception_rows: TaskFailureModeLandingResourceRow[];
  handling_rows: TaskFailureModeLandingResourceRow[];
  observation_rows: TaskFailureModeLandingResourceRow[];
  huatuo_rows: TaskFailureModeLandingResourceRow[];
}

export interface TaskFailureModeLandingPayload {
  products: TaskFailureModeLandingProductRow[];
  interception_rows: TaskFailureModeLandingResourceRow[];
  handling_rows: TaskFailureModeLandingResourceRow[];
  observation_rows: TaskFailureModeLandingResourceRow[];
  huatuo_rows: TaskFailureModeLandingResourceRow[];
}

const TRUTHY_LANDING_STATUS_VALUES = new Set(['1', 'on', 'true', 'yes']);
const FALSY_LANDING_STATUS_VALUES = new Set(['0', 'false', 'no', 'off']);

function normalizeLandingStatus(value: unknown): null | string {
  if (typeof value === 'boolean') {
    return value ? '已落地' : '未落地';
  }
  const text = String(value ?? '').trim();
  if (!text) {
    return null;
  }
  if (
    text === '已落地' ||
    text === '未落地' ||
    text === '不涉及' ||
    text === '部分落地'
  ) {
    return text;
  }
  const normalizedText = text.toLowerCase();
  if (TRUTHY_LANDING_STATUS_VALUES.has(normalizedText)) {
    return '已落地';
  }
  if (FALSY_LANDING_STATUS_VALUES.has(normalizedText)) {
    return '未落地';
  }
  return null;
}

export function normalizeTaskFailureModeLandingDetail(
  detail: TaskFailureModeLandingDetail,
): TaskFailureModeLandingDetail {
  const normalizeProductRows = (
    rows?: TaskFailureModeLandingProductRow[],
  ): TaskFailureModeLandingProductRow[] =>
    (rows || []).map((row) => ({
      ...row,
      landing_status: normalizeLandingStatus(row.landing_status),
      product_id: String(row.product_id || ''),
      product_name: String(row.product_name || ''),
      subsystems: normalizeStringArray(row.subsystems),
    }));
  const normalizeRows = (
    rows?: TaskFailureModeLandingResourceRow[],
  ): TaskFailureModeLandingResourceRow[] =>
    (rows || []).map((row) => ({
      ...row,
      group_key: String(row.group_key || ''),
      landing_status: normalizeLandingStatus(row.landing_status),
      label: String(row.label || ''),
      resource_id: String(row.resource_id || ''),
      subtitle: row.subtitle || null,
      product_rows: normalizeProductRows(row.product_rows),
    }));

  return {
    ...detail,
    failure_mode_landing_status:
      normalizeLandingStatus(detail.failure_mode_landing_status) ||
      (detail.failure_mode_is_landed ? '已落地' : '未落地'),
    failure_mode_is_landed: Boolean(detail.failure_mode_is_landed),
    landing_resource_total: Number(detail.landing_resource_total || 0),
    landing_resource_selected_count: Number(
      detail.landing_resource_selected_count || 0,
    ),
    landing_resource_landed_count: Number(
      detail.landing_resource_landed_count || 0,
    ),
    products: normalizeProductRows(detail.products),
    handling_rows: normalizeRows(detail.handling_rows),
    huatuo_rows: normalizeRows(detail.huatuo_rows),
    interception_rows: normalizeRows(detail.interception_rows),
    landing_completed: Boolean(detail.landing_completed),
    observation_rows: normalizeRows(detail.observation_rows),
  };
}

export interface FailureModeProductStatisticsOverviewItem {
  product_id: string;
  product_name: string;
  owner_info?: null | UserBriefInfo;
  baseline_failure_mode_count: number;
  landed_failure_mode_count: number;
  pending_failure_mode_count: number;
  pending_rate: number;
  status_light: 'green' | 'red' | 'yellow' | string;
}

export type FailureModeProductStatisticsSummary = FailureModeStatisticsSummary;

export interface FailureModeProductStatisticsSummaryQuery {
  product_ids?: string[];
  subsystems?: string[];
}

export interface FailureModeProductStatisticsSubsystemRow {
  subsystem: string;
  baseline_failure_mode_count: number;
  landed_failure_mode_count: number;
  pending_failure_mode_count: number;
  pending_rate: number;
  status_light: 'green' | 'red' | 'yellow' | string;
}

export interface FailureModeProductStatisticsSubsystemQuery
  extends FailureModeStatisticsSubsystemQuery {
  product_ids?: string[];
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

export async function listFailureModeStatisticsSubsystemOptionsApi() {
  return requestClient.get<string[]>(`${base}/statistics/subsystems/options`);
}

export async function getFailureModeStatisticsSummaryApi(
  data?: FailureModeStatisticsSummaryQuery,
) {
  return requestClient.post<FailureModeStatisticsSummary>(
    `${base}/statistics/summary`,
    data ?? {},
  );
}

export async function listFailureModeStatisticsSubsystemsApi(
  data?: FailureModeStatisticsSubsystemQuery,
) {
  return requestClient.post<
    PaginatedResponse<FailureModeStatisticsSubsystemRow>
  >(`${base}/statistics/subsystems/search`, data ?? {});
}

export async function listFailureModeProductStatisticsOverviewApi() {
  return requestClient.post<FailureModeProductStatisticsOverviewItem[]>(
    `${base}/statistics/products/overview`,
    {},
  );
}

export async function listFailureModeProductStatisticsSubsystemOptionsApi(
  data?: FailureModeProductStatisticsSummaryQuery,
) {
  return requestClient.post<string[]>(
    `${base}/statistics/products/subsystems/options`,
    data ?? {},
  );
}

export async function getFailureModeProductStatisticsSummaryApi(
  data: FailureModeProductStatisticsSummaryQuery,
) {
  return requestClient.post<FailureModeProductStatisticsSummary>(
    `${base}/statistics/products/summary`,
    data,
  );
}

export async function listFailureModeProductStatisticsSubsystemsApi(
  data: FailureModeProductStatisticsSubsystemQuery,
) {
  return requestClient.post<
    PaginatedResponse<FailureModeProductStatisticsSubsystemRow>
  >(`${base}/statistics/products/subsystems/search`, data);
}

export async function listFailureModesApi(data?: FailureModeQuery) {
  return requestClient
    .post<
      PaginatedResponse<FailureModeItem>
    >(`${base}/failure-modes/search`, data ?? {})
    .then((page) => ({
      ...page,
      items: (page.items || []).map((item) => normalizeFailureModeItem(item)),
    }));
}

export async function createFailureModeApi(data: FailureModePayload) {
  return requestClient
    .post<FailureModeItem>(`${base}/failure-modes`, data)
    .then(normalizeFailureModeItem);
}

export async function updateFailureModeApi(
  id: string,
  data: Partial<FailureModePayload>,
) {
  return requestClient
    .put<FailureModeItem>(`${base}/failure-modes/${id}`, data)
    .then(normalizeFailureModeItem);
}

export async function getFailureModeDetailApi(id: string) {
  return requestClient
    .get<FailureModeItem>(`${base}/failure-modes/${id}`)
    .then(normalizeFailureModeItem);
}

export async function getFailureModeInsightApi(id: string) {
  return requestClient.get<FailureModeInsight>(
    `${base}/failure-modes/${id}/insight`,
  );
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

export async function getInterceptionStrategyInsightApi(id: string) {
  return requestClient.get<InterceptionInsight>(
    `${base}/interception-strategies/${id}/insight`,
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

export async function getHandlingMeasureInsightApi(id: string) {
  return requestClient.get<HandlingMeasureInsight>(
    `${base}/handling-measures/${id}/insight`,
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

export async function getObservationMethodInsightApi(id: string) {
  return requestClient.get<ObservationMethodInsight>(
    `${base}/observation-methods/${id}/insight`,
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

export async function getHuatuoDiagnosisInsightApi(id: string) {
  return requestClient.get<HuatuoDiagnosisInsight>(
    `${base}/huatuo-diagnoses/${id}/insight`,
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

export async function getTestCaseInsightApi(id: string) {
  return requestClient.get<TestCaseInsight>(`${base}/test-cases/${id}/insight`);
}

export async function deleteTestCaseApi(id: string) {
  return requestClient.delete<{ success: boolean }>(`${base}/test-cases/${id}`);
}
