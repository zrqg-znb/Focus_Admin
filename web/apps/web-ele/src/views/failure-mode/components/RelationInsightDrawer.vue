<script lang="ts" setup>
import type {
  FailureModeInsight,
  FailureModeInsightResourceRow,
  FailureModeItem,
  HandlingMeasureInsight,
  HandlingMeasureItem,
  HuatuoDiagnosisInsight,
  HuatuoDiagnosisItem,
  InterceptionInsight,
  InterceptionStrategyItem,
  ObservationMethodInsight,
  ObservationMethodItem,
  TestCaseInsight,
  UserBriefInfo,
} from '#/api/failure_mode';

import { reactive, ref } from 'vue';

import {
  ElEmpty,
  ElMessage,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  getFailureModeDetailApi,
  getFailureModeInsightApi,
  getHandlingMeasureDetailApi,
  getHandlingMeasureInsightApi,
  getHuatuoDiagnosisDetailApi,
  getHuatuoDiagnosisInsightApi,
  getInterceptionStrategyDetailApi,
  getInterceptionStrategyInsightApi,
  getObservationMethodDetailApi,
  getObservationMethodInsightApi,
  getTestCaseInsightApi,
} from '#/api/failure_mode';
import { ZqDrawer } from '#/components/zq-drawer';

defineOptions({ name: 'RelationInsightDrawer' });

type InsightMode =
  | 'failure_mode'
  | 'handling_measure'
  | 'huatuo_diagnosis'
  | 'interception'
  | 'observation_method'
  | 'test_case';

type ResourceInsight =
  | HandlingMeasureInsight
  | HuatuoDiagnosisInsight
  | InterceptionInsight
  | ObservationMethodInsight
  | TestCaseInsight;

type FailureModeResourceLandingStatus =
  | '不涉及'
  | '已落地'
  | '未落地'
  | '部分落地';

interface SummaryMetric {
  label: string;
  value: number | string;
}

interface FailureModeResourceSummary {
  related_product_count: number;
  landed_product_count: number;
  summary_status: FailureModeResourceLandingStatus;
}

type FailureModeInterceptionRow = FailureModeResourceSummary &
  InterceptionStrategyItem;
type FailureModeHandlingRow = FailureModeResourceSummary & HandlingMeasureItem;
type FailureModeObservationRow = FailureModeResourceSummary &
  ObservationMethodItem;
type FailureModeHuatuoRow = FailureModeResourceSummary & HuatuoDiagnosisItem;

interface InsightFrame {
  key: string;
  resourceId: string;
  mode: InsightMode;
  visible: boolean;
  loading: boolean;
  failureModeDetail: FailureModeItem | null;
  failureModeInsight: FailureModeInsight | null;
  interceptionInsight: InterceptionInsight | null;
  handlingMeasureInsight: HandlingMeasureInsight | null;
  observationMethodInsight: null | ObservationMethodInsight;
  huatuoDiagnosisInsight: HuatuoDiagnosisInsight | null;
  testCaseInsight: null | TestCaseInsight;
  failureModeInterceptionRows: FailureModeInterceptionRow[];
  failureModeHandlingRows: FailureModeHandlingRow[];
  failureModeObservationRows: FailureModeObservationRow[];
  failureModeHuatuoRows: FailureModeHuatuoRow[];
}

let frameSequence = 0;
const frames = ref<InsightFrame[]>([]);
const failureModeDetailCache = new Map<
  string,
  FailureModeItem | Promise<FailureModeItem>
>();
const failureModeInsightCache = new Map<
  string,
  FailureModeInsight | Promise<FailureModeInsight>
>();
const interceptionDetailCache = new Map<
  string,
  InterceptionStrategyItem | Promise<InterceptionStrategyItem>
>();
const interceptionInsightCache = new Map<
  string,
  InterceptionInsight | Promise<InterceptionInsight>
>();
const handlingMeasureDetailCache = new Map<
  string,
  HandlingMeasureItem | Promise<HandlingMeasureItem>
>();
const handlingMeasureInsightCache = new Map<
  string,
  HandlingMeasureInsight | Promise<HandlingMeasureInsight>
>();
const observationMethodDetailCache = new Map<
  string,
  ObservationMethodItem | Promise<ObservationMethodItem>
>();
const observationMethodInsightCache = new Map<
  string,
  ObservationMethodInsight | Promise<ObservationMethodInsight>
>();
const huatuoDiagnosisDetailCache = new Map<
  string,
  HuatuoDiagnosisItem | Promise<HuatuoDiagnosisItem>
>();
const huatuoDiagnosisInsightCache = new Map<
  string,
  HuatuoDiagnosisInsight | Promise<HuatuoDiagnosisInsight>
>();
const testCaseInsightCache = new Map<
  string,
  Promise<TestCaseInsight> | TestCaseInsight
>();

function createFrame(mode: InsightMode, resourceId: string): InsightFrame {
  return reactive({
    key: `${mode}-${resourceId}-${++frameSequence}`,
    resourceId,
    mode,
    visible: true,
    loading: false,
    failureModeDetail: null,
    failureModeInsight: null,
    interceptionInsight: null,
    handlingMeasureInsight: null,
    observationMethodInsight: null,
    huatuoDiagnosisInsight: null,
    testCaseInsight: null,
    failureModeInterceptionRows: [],
    failureModeHandlingRows: [],
    failureModeObservationRows: [],
    failureModeHuatuoRows: [],
  }) as InsightFrame;
}

function removeFrame(frameKey: string) {
  const index = frames.value.findIndex((item) => item.key === frameKey);
  if (index === -1) {
    return;
  }
  frames.value.splice(index);
}

function getResourceInsight(frame: InsightFrame): null | ResourceInsight {
  switch (frame.mode) {
    case 'handling_measure': {
      return frame.handlingMeasureInsight;
    }
    case 'huatuo_diagnosis': {
      return frame.huatuoDiagnosisInsight;
    }
    case 'interception': {
      return frame.interceptionInsight;
    }
    case 'observation_method': {
      return frame.observationMethodInsight;
    }
    case 'test_case': {
      return frame.testCaseInsight;
    }
    default: {
      return null;
    }
  }
}

function getDrawerTitle(frame: InsightFrame) {
  switch (frame.mode) {
    case 'failure_mode': {
      return '故障模式关联洞察';
    }
    case 'handling_measure': {
      return '故障处理措施关联洞察';
    }
    case 'huatuo_diagnosis': {
      return '华佗诊断方案关联洞察';
    }
    case 'interception': {
      return '产线拦截策略关联洞察';
    }
    case 'observation_method': {
      return '维测手段关联洞察';
    }
    default: {
      return '测试用例关联洞察';
    }
  }
}

function getCurrentRate(frame: InsightFrame) {
  const resourceInsight = getResourceInsight(frame);
  const numerator =
    frame.mode === 'failure_mode'
      ? frame.failureModeInsight?.landed_product_count || 0
      : resourceInsight?.landed_product_count || 0;
  const denominator =
    frame.mode === 'failure_mode'
      ? frame.failureModeInsight?.related_product_count || 0
      : resourceInsight?.related_product_count || 0;
  return formatRate(numerator, denominator);
}

function getHeroTitle(frame: InsightFrame) {
  switch (frame.mode) {
    case 'failure_mode': {
      return frame.failureModeInsight?.brief || '';
    }
    case 'handling_measure': {
      return frame.handlingMeasureInsight?.measure || '';
    }
    case 'huatuo_diagnosis': {
      return frame.huatuoDiagnosisInsight?.description || '';
    }
    case 'interception': {
      return frame.interceptionInsight?.interception_item || '';
    }
    case 'observation_method': {
      return frame.observationMethodInsight?.display_name || '';
    }
    default: {
      return frame.testCaseInsight?.brief || '';
    }
  }
}

function getHeroMeta(frame: InsightFrame) {
  switch (frame.mode) {
    case 'failure_mode': {
      return [
        `子系统：${frame.failureModeInsight?.subsystem || '-'}`,
        `状态：${frame.failureModeInsight?.status || '-'}`,
      ];
    }
    case 'handling_measure': {
      return [
        `措施类别：${frame.handlingMeasureInsight?.measure_category || '-'}`,
      ];
    }
    case 'huatuo_diagnosis': {
      return [];
    }
    case 'interception': {
      return [`工位：${frame.interceptionInsight?.station || '-'}`];
    }
    case 'observation_method': {
      return [
        `维测类型：${frame.observationMethodInsight?.monitor_type || '-'}`,
        `日志 ID：${frame.observationMethodInsight?.log_id || '-'}`,
      ];
    }
    default: {
      return [`CIDA 链接：${frame.testCaseInsight?.cida_link || '-'}`];
    }
  }
}

function getSummaryMetrics(frame: InsightFrame): SummaryMetric[] {
  switch (frame.mode) {
    case 'failure_mode': {
      return [
        {
          label: '已落地产品数',
          value: frame.failureModeInsight?.landed_product_count || 0,
        },
        {
          label: '关联产品数',
          value: frame.failureModeInsight?.related_product_count || 0,
        },
        { label: '落地率', value: getCurrentRate(frame) },
      ];
    }
    case 'handling_measure': {
      return [
        {
          label: '关联测试用例数',
          value: frame.handlingMeasureInsight?.related_test_case_count || 0,
        },
        {
          label: '关联故障模式数',
          value: frame.handlingMeasureInsight?.related_failure_mode_count || 0,
        },
        {
          label: '关联产品数',
          value: frame.handlingMeasureInsight?.related_product_count || 0,
        },
        {
          label: '已落地产品数',
          value: frame.handlingMeasureInsight?.landed_product_count || 0,
        },
        { label: '落地率', value: getCurrentRate(frame) },
      ];
    }
    case 'huatuo_diagnosis': {
      return [
        {
          label: '关联故障模式数',
          value: frame.huatuoDiagnosisInsight?.related_failure_mode_count || 0,
        },
        {
          label: '关联产品数',
          value: frame.huatuoDiagnosisInsight?.related_product_count || 0,
        },
        {
          label: '已落地产品数',
          value: frame.huatuoDiagnosisInsight?.landed_product_count || 0,
        },
        { label: '落地率', value: getCurrentRate(frame) },
      ];
    }
    case 'interception': {
      return [
        {
          label: '关联故障模式数',
          value: frame.interceptionInsight?.related_failure_mode_count || 0,
        },
        {
          label: '关联产品数',
          value: frame.interceptionInsight?.related_product_count || 0,
        },
        {
          label: '已落地产品数',
          value: frame.interceptionInsight?.landed_product_count || 0,
        },
        { label: '落地率', value: getCurrentRate(frame) },
      ];
    }
    case 'observation_method': {
      return [
        {
          label: '关联故障模式数',
          value:
            frame.observationMethodInsight?.related_failure_mode_count || 0,
        },
        {
          label: '关联产品数',
          value: frame.observationMethodInsight?.related_product_count || 0,
        },
        {
          label: '已落地产品数',
          value: frame.observationMethodInsight?.landed_product_count || 0,
        },
        { label: '落地率', value: getCurrentRate(frame) },
      ];
    }
    default: {
      return [
        {
          label: '关联处理措施数',
          value: frame.testCaseInsight?.related_handling_measure_count || 0,
        },
        {
          label: '关联故障模式数',
          value: frame.testCaseInsight?.related_failure_mode_count || 0,
        },
        {
          label: '关联产品数',
          value: frame.testCaseInsight?.related_product_count || 0,
        },
        {
          label: '已落地产品数',
          value: frame.testCaseInsight?.landed_product_count || 0,
        },
        { label: '落地率', value: getCurrentRate(frame) },
      ];
    }
  }
}

function getCurrentFailureModeRows(frame: InsightFrame) {
  return getResourceInsight(frame)?.failure_mode_rows || [];
}

function getCurrentFailureModeProductRows(frame: InsightFrame) {
  return frame.failureModeInsight?.product_rows || [];
}

function getCurrentLandingProductRows(frame: InsightFrame) {
  return getResourceInsight(frame)?.product_rows || [];
}

function getProductEmptyText(frame: InsightFrame) {
  switch (frame.mode) {
    case 'failure_mode': {
      return '当前故障模式尚未关联到任何产品基线';
    }
    case 'handling_measure': {
      return '当前故障处理措施尚未关联到任何产品';
    }
    case 'huatuo_diagnosis': {
      return '当前华佗诊断方案尚未关联到任何产品';
    }
    case 'interception': {
      return '当前产线拦截策略尚未关联到任何产品';
    }
    case 'observation_method': {
      return '当前维测手段尚未关联到任何产品';
    }
    default: {
      return '当前测试用例尚未关联到任何产品';
    }
  }
}

function getFailureModeEmptyText(frame: InsightFrame) {
  switch (frame.mode) {
    case 'handling_measure': {
      return '当前故障处理措施尚未关联任何故障模式';
    }
    case 'huatuo_diagnosis': {
      return '当前华佗诊断方案尚未关联任何故障模式';
    }
    case 'interception': {
      return '当前产线拦截策略尚未关联任何故障模式';
    }
    case 'observation_method': {
      return '当前维测手段尚未关联任何故障模式';
    }
    default: {
      return '当前测试用例尚未通过处理措施关联到任何故障模式';
    }
  }
}

function getFrameZIndex(index: number) {
  return 2000 + index * 10;
}

function formatRate(numerator: number, denominator: number) {
  if (!denominator) {
    return '0%';
  }
  const value = ((numerator / denominator) * 100).toFixed(1);
  return value.endsWith('.0') ? `${Number(value)}%` : `${value}%`;
}

function formatUserName(user?: null | UserBriefInfo) {
  return user?.name || user?.username || '-';
}

function formatUserNames(users?: null | UserBriefInfo[]) {
  return (
    (users || [])
      .map((item) => item?.name || item?.username || item?.id || '')
      .filter(Boolean)
      .join(' / ') || '-'
  );
}

function formatTextList(items?: null | string[]) {
  return (items || []).filter(Boolean).join('、') || '-';
}

function formatRelationLabels(
  items?: Array<
    FailureModeInsightResourceRow | { label?: null | string }
  > | null,
) {
  return (
    (items || [])
      .map((item) => item.label || '')
      .filter(Boolean)
      .join('、') || '-'
  );
}

function stripHtmlText(value?: null | string) {
  const text = String(value || '')
    .replaceAll(/<\s*br\s*\/?>/gi, '\n')
    .replaceAll(/<\/p>/gi, '\n')
    .replaceAll(/<[^>]+>/g, ' ')
    .replaceAll(/\s+/g, ' ')
    .trim();
  return text || '-';
}

function truncateText(value: string, maxLength = 72) {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength)}...`;
}

function formatHtmlSnippet(value?: null | string) {
  return truncateText(stripHtmlText(value));
}

function loadCached<T>(
  cache: Map<string, Promise<T> | T>,
  key: string,
  loader: () => Promise<T>,
) {
  const cached = cache.get(key);
  if (cached) {
    return Promise.resolve(cached);
  }
  const promise = loader()
    .then((value) => {
      cache.set(key, value);
      return value;
    })
    .catch((error) => {
      cache.delete(key);
      throw error;
    });
  cache.set(key, promise);
  return promise;
}

async function loadDetailList<T extends { id: string }>(
  items: Array<{ id: string }>,
  loader: (id: string) => Promise<T>,
  cache: Map<string, Promise<T> | T>,
) {
  const results = await Promise.allSettled(
    items.map((item) => loadCached(cache, item.id, () => loader(item.id))),
  );
  return results.map((result) =>
    result.status === 'fulfilled' ? result.value : null,
  );
}

function normalizeLandingStatus(
  statuses: FailureModeResourceLandingStatus[],
): FailureModeResourceLandingStatus {
  const normalized = statuses.filter(Boolean);
  if (normalized.length === 0) {
    return '未落地';
  }
  if (normalized.every((item) => item === '不涉及')) {
    return '不涉及';
  }
  if (normalized.every((item) => item === '未落地')) {
    return '未落地';
  }
  if (normalized.every((item) => item === '已落地')) {
    return '已落地';
  }
  if (normalized.every((item) => item === '已落地' || item === '不涉及')) {
    return '已落地';
  }
  if (normalized.every((item) => item === '未落地' || item === '不涉及')) {
    return '未落地';
  }
  return '部分落地';
}

function buildResourceSummaryMap(
  productRows: FailureModeInsight['product_rows'],
  key:
    | 'handling_rows'
    | 'huatuo_rows'
    | 'interception_rows'
    | 'observation_rows',
  resourceIds: string[],
) {
  const buckets = new Map<
    string,
    {
      landedProductIds: Set<string>;
      relatedProductIds: Set<string>;
      statuses: FailureModeResourceLandingStatus[];
    }
  >();
  resourceIds.forEach((id) => {
    buckets.set(id, {
      relatedProductIds: new Set<string>(),
      landedProductIds: new Set<string>(),
      statuses: [],
    });
  });

  productRows.forEach((productRow) => {
    const seenResourceIds = new Set<string>();
    getFailureModeProductResourceRows(productRow, key).forEach((row) => {
      if (seenResourceIds.has(row.id)) {
        return;
      }
      seenResourceIds.add(row.id);
      const bucket = buckets.get(row.id);
      if (!bucket) {
        return;
      }
      const status =
        (row.status as FailureModeResourceLandingStatus) || '未落地';
      bucket.relatedProductIds.add(productRow.product_id);
      bucket.statuses.push(status);
      if (status === '已落地') {
        bucket.landedProductIds.add(productRow.product_id);
      }
    });
  });

  return new Map(
    resourceIds.map((id) => {
      const bucket = buckets.get(id) || {
        relatedProductIds: new Set<string>(),
        landedProductIds: new Set<string>(),
        statuses: [],
      };
      return [
        id,
        {
          related_product_count: bucket.relatedProductIds.size,
          landed_product_count: bucket.landedProductIds.size,
          summary_status: normalizeLandingStatus(bucket.statuses),
        },
      ] as const;
    }),
  );
}

function buildFailureModeInterceptionRows(
  relations: FailureModeItem['interception_strategy_items'],
  details: Array<InterceptionStrategyItem | null>,
  productRows: FailureModeInsight['product_rows'],
) {
  const summaryMap = buildResourceSummaryMap(
    productRows,
    'interception_rows',
    relations.map((item) => item.id),
  );
  return relations.map((relation, index) => {
    const detail = details[index];
    const summary = summaryMap.get(relation.id) || {
      related_product_count: 0,
      landed_product_count: 0,
      summary_status: '未落地' as const,
    };
    return {
      ...detail,
      id: detail?.id || relation.id,
      interception_item:
        detail?.interception_item || relation.label || '未命名产线拦截项',
      version_detection_html: detail?.version_detection_html || '',
      station: detail?.station || relation.subtitle || null,
      owner_ids: detail?.owner_ids || [],
      owner_info: detail?.owner_info || [],
      display_name: detail?.display_name || relation.label || '',
      sys_create_datetime: detail?.sys_create_datetime || '',
      sys_update_datetime: detail?.sys_update_datetime || '',
      ...summary,
    } satisfies FailureModeInterceptionRow;
  });
}

function buildFailureModeHandlingRows(
  relations: FailureModeItem['handling_measure_items'],
  details: Array<HandlingMeasureItem | null>,
  productRows: FailureModeInsight['product_rows'],
) {
  const summaryMap = buildResourceSummaryMap(
    productRows,
    'handling_rows',
    relations.map((item) => item.id),
  );
  return relations.map((relation, index) => {
    const detail = details[index];
    const summary = summaryMap.get(relation.id) || {
      related_product_count: 0,
      landed_product_count: 0,
      summary_status: '未落地' as const,
    };
    return {
      ...detail,
      id: detail?.id || relation.id,
      measure_category: detail?.measure_category || relation.subtitle || null,
      measure: detail?.measure || relation.label || '未命名故障处理措施',
      measure_detail_html: detail?.measure_detail_html || '',
      measure_effect: detail?.measure_effect || '',
      owner_ids: detail?.owner_ids || [],
      owner_info: detail?.owner_info || [],
      test_case_ids: detail?.test_case_ids || [],
      test_case_items: detail?.test_case_items || [],
      display_name: detail?.display_name || relation.label || '',
      sys_create_datetime: detail?.sys_create_datetime || '',
      sys_update_datetime: detail?.sys_update_datetime || '',
      ...summary,
    } satisfies FailureModeHandlingRow;
  });
}

function buildFailureModeObservationRows(
  relations: FailureModeItem['observation_method_items'],
  details: Array<null | ObservationMethodItem>,
  productRows: FailureModeInsight['product_rows'],
) {
  const summaryMap = buildResourceSummaryMap(
    productRows,
    'observation_rows',
    relations.map((item) => item.id),
  );
  return relations.map((relation, index) => {
    const detail = details[index];
    const summary = summaryMap.get(relation.id) || {
      related_product_count: 0,
      landed_product_count: 0,
      summary_status: '未落地' as const,
    };
    const displayName =
      detail?.display_name || relation.label || '未命名维测手段';
    return {
      ...detail,
      id: detail?.id || relation.id,
      monitor_type: detail?.monitor_type || relation.subtitle || null,
      log_id: detail?.log_id || '',
      log_keyword: detail?.log_keyword || '',
      log_path: detail?.log_path || '',
      display_name: displayName,
      owner_ids: detail?.owner_ids || [],
      owner_info: detail?.owner_info || [],
      sys_create_datetime: detail?.sys_create_datetime || '',
      sys_update_datetime: detail?.sys_update_datetime || '',
      ...summary,
    } satisfies FailureModeObservationRow;
  });
}

function buildFailureModeHuatuoRows(
  relations: FailureModeItem['huatuo_diagnosis_items'],
  details: Array<HuatuoDiagnosisItem | null>,
  productRows: FailureModeInsight['product_rows'],
) {
  const summaryMap = buildResourceSummaryMap(
    productRows,
    'huatuo_rows',
    relations.map((item) => item.id),
  );
  return relations.map((relation, index) => {
    const detail = details[index];
    const summary = summaryMap.get(relation.id) || {
      related_product_count: 0,
      landed_product_count: 0,
      summary_status: '未落地' as const,
    };
    return {
      ...detail,
      id: detail?.id || relation.id,
      description:
        detail?.description || relation.label || '未命名华佗诊断方案',
      owner_ids: detail?.owner_ids || [],
      owner_info: detail?.owner_info || [],
      display_name: detail?.display_name || relation.label || '',
      sys_create_datetime: detail?.sys_create_datetime || '',
      sys_update_datetime: detail?.sys_update_datetime || '',
      ...summary,
    } satisfies FailureModeHuatuoRow;
  });
}

function getLandingStatusTagType(status?: null | string) {
  if (status === '已落地') {
    return 'success';
  }
  if (status === '不涉及') {
    return 'info';
  }
  if (status === '部分落地') {
    return 'warning';
  }
  return 'info';
}

function getFailureModeProductResourceRows(
  row: FailureModeInsight['product_rows'][number],
  key:
    | 'handling_rows'
    | 'huatuo_rows'
    | 'interception_rows'
    | 'observation_rows',
) {
  return (row?.[key] || []) as FailureModeInsightResourceRow[];
}

function pushFrame(mode: InsightMode, resourceId: string) {
  const frame = createFrame(mode, resourceId);
  frames.value.push(frame);
  return frame;
}

function findFrame(frameKey: string) {
  return frames.value.find((item) => item.key === frameKey) || null;
}

async function loadFrame(
  frame: InsightFrame,
  loader: () => Promise<void>,
  errorMessage: string,
) {
  frame.loading = true;
  try {
    await loader();
  } catch (error) {
    removeFrame(frame.key);
    console.error(error);
    ElMessage.error(errorMessage);
  } finally {
    frame.loading = false;
  }
}

function handleFrameClosed(frameKey: string) {
  removeFrame(frameKey);
}

async function enrichFailureModeRelationRows(
  frameKey: string,
  detail: FailureModeItem,
  insight: FailureModeInsight,
) {
  try {
    const [
      interceptionDetails,
      handlingDetails,
      observationDetails,
      huatuoDetails,
    ] = await Promise.all([
      loadDetailList(
        detail.interception_strategy_items || [],
        getInterceptionStrategyDetailApi,
        interceptionDetailCache,
      ),
      loadDetailList(
        detail.handling_measure_items || [],
        getHandlingMeasureDetailApi,
        handlingMeasureDetailCache,
      ),
      loadDetailList(
        detail.observation_method_items || [],
        getObservationMethodDetailApi,
        observationMethodDetailCache,
      ),
      loadDetailList(
        detail.huatuo_diagnosis_items || [],
        getHuatuoDiagnosisDetailApi,
        huatuoDiagnosisDetailCache,
      ),
    ]);
    const frame = findFrame(frameKey);
    if (!frame) {
      return;
    }
    frame.failureModeInterceptionRows = buildFailureModeInterceptionRows(
      detail.interception_strategy_items || [],
      interceptionDetails,
      insight.product_rows || [],
    );
    frame.failureModeHandlingRows = buildFailureModeHandlingRows(
      detail.handling_measure_items || [],
      handlingDetails,
      insight.product_rows || [],
    );
    frame.failureModeObservationRows = buildFailureModeObservationRows(
      detail.observation_method_items || [],
      observationDetails,
      insight.product_rows || [],
    );
    frame.failureModeHuatuoRows = buildFailureModeHuatuoRows(
      detail.huatuo_diagnosis_items || [],
      huatuoDetails,
      insight.product_rows || [],
    );
  } catch (error) {
    console.error(error);
  }
}

async function openFailureMode(id: string) {
  const frame = pushFrame('failure_mode', id);
  await loadFrame(
    frame,
    async () => {
      const [detail, insight] = await Promise.all([
        loadCached(failureModeDetailCache, id, () =>
          getFailureModeDetailApi(id),
        ),
        loadCached(failureModeInsightCache, id, () =>
          getFailureModeInsightApi(id),
        ),
      ]);
      frame.failureModeDetail = detail;
      frame.failureModeInsight = insight;
      frame.failureModeInterceptionRows = buildFailureModeInterceptionRows(
        detail.interception_strategy_items || [],
        (detail.interception_strategy_items || []).map(() => null),
        insight.product_rows || [],
      );
      frame.failureModeHandlingRows = buildFailureModeHandlingRows(
        detail.handling_measure_items || [],
        (detail.handling_measure_items || []).map(() => null),
        insight.product_rows || [],
      );
      frame.failureModeObservationRows = buildFailureModeObservationRows(
        detail.observation_method_items || [],
        (detail.observation_method_items || []).map(() => null),
        insight.product_rows || [],
      );
      frame.failureModeHuatuoRows = buildFailureModeHuatuoRows(
        detail.huatuo_diagnosis_items || [],
        (detail.huatuo_diagnosis_items || []).map(() => null),
        insight.product_rows || [],
      );
      void enrichFailureModeRelationRows(frame.key, detail, insight);
    },
    '加载故障模式关联洞察失败',
  );
}

async function openInterception(id: string) {
  const frame = pushFrame('interception', id);
  await loadFrame(
    frame,
    async () => {
      frame.interceptionInsight = await loadCached(
        interceptionInsightCache,
        id,
        () => getInterceptionStrategyInsightApi(id),
      );
    },
    '加载产线拦截策略关联洞察失败',
  );
}

async function openHandlingMeasure(id: string) {
  const frame = pushFrame('handling_measure', id);
  await loadFrame(
    frame,
    async () => {
      frame.handlingMeasureInsight = await loadCached(
        handlingMeasureInsightCache,
        id,
        () => getHandlingMeasureInsightApi(id),
      );
    },
    '加载故障处理措施关联洞察失败',
  );
}

async function openObservationMethod(id: string) {
  const frame = pushFrame('observation_method', id);
  await loadFrame(
    frame,
    async () => {
      frame.observationMethodInsight = await loadCached(
        observationMethodInsightCache,
        id,
        () => getObservationMethodInsightApi(id),
      );
    },
    '加载维测手段关联洞察失败',
  );
}

async function openHuatuoDiagnosis(id: string) {
  const frame = pushFrame('huatuo_diagnosis', id);
  await loadFrame(
    frame,
    async () => {
      frame.huatuoDiagnosisInsight = await loadCached(
        huatuoDiagnosisInsightCache,
        id,
        () => getHuatuoDiagnosisInsightApi(id),
      );
    },
    '加载华佗诊断方案关联洞察失败',
  );
}

async function openTestCase(id: string) {
  const frame = pushFrame('test_case', id);
  await loadFrame(
    frame,
    async () => {
      frame.testCaseInsight = await loadCached(testCaseInsightCache, id, () =>
        getTestCaseInsightApi(id),
      );
    },
    '加载测试用例关联洞察失败',
  );
}

defineExpose({
  openFailureMode,
  openHandlingMeasure,
  openHuatuoDiagnosis,
  openInterception,
  openObservationMethod,
  openTestCase,
});
</script>

<template>
  <template v-for="(frame, index) in frames" :key="frame.key">
    <ZqDrawer
      v-model="frame.visible"
      :loading="frame.loading"
      :show-footer="false"
      :size="1180"
      :title="getDrawerTitle(frame)"
      :z-index="getFrameZIndex(index)"
      @closed="handleFrameClosed(frame.key)"
    >
      <div class="fm-relation-insight flex flex-col gap-4 pb-2">
        <div v-if="getHeroTitle(frame)" class="fm-relation-insight__hero">
          <div class="fm-relation-insight__hero-title">
            {{ getHeroTitle(frame) }}
          </div>
          <div
            v-if="getHeroMeta(frame).length > 0"
            class="fm-relation-insight__hero-meta"
          >
            <span v-for="item in getHeroMeta(frame)" :key="item">{{
              item
            }}</span>
          </div>
        </div>

        <div class="fm-relation-insight__summary-grid">
          <div
            v-for="item in getSummaryMetrics(frame)"
            :key="item.label"
            class="fm-relation-insight__summary-card"
          >
            <div class="fm-relation-insight__summary-label">
              {{ item.label }}
            </div>
            <div class="fm-relation-insight__summary-value">
              {{ item.value }}
            </div>
          </div>
        </div>

        <div v-if="frame.mode === 'failure_mode'" class="flex flex-col gap-4">
          <section class="fm-relation-insight__panel">
            <div class="fm-relation-insight__panel-title">产线拦截策略</div>
            <ElEmpty
              v-if="frame.failureModeInterceptionRows.length === 0"
              description="当前故障模式尚未关联任何产线拦截策略"
            />
            <ElTable
              v-else
              :data="frame.failureModeInterceptionRows"
              border
              stripe
            >
              <ElTableColumn label="产线拦截项" min-width="220">
                <template #default="{ row }">
                  <button
                    class="fm-relation-insight__drill-link"
                    type="button"
                    @click="openInterception(row.id)"
                  >
                    {{ row.interception_item }}
                  </button>
                </template>
              </ElTableColumn>
              <ElTableColumn label="工位" min-width="120">
                <template #default="{ row }">
                  {{ row.station || '-' }}
                </template>
              </ElTableColumn>
              <ElTableColumn label="版本检测内容" min-width="320">
                <template #default="{ row }">
                  {{ formatHtmlSnippet(row.version_detection_html) }}
                </template>
              </ElTableColumn>
              <ElTableColumn label="设计责任人" min-width="220">
                <template #default="{ row }">
                  {{ formatUserNames(row.owner_info) }}
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="关联产品数"
                min-width="110"
                prop="related_product_count"
              />
              <ElTableColumn
                label="已落地产品数"
                min-width="110"
                prop="landed_product_count"
              />
              <ElTableColumn label="汇总状态" min-width="120">
                <template #default="{ row }">
                  <ElTag
                    :type="getLandingStatusTagType(row.summary_status)"
                    effect="light"
                    round
                  >
                    {{ row.summary_status }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="创建时间"
                min-width="180"
                prop="sys_create_datetime"
              />
              <ElTableColumn
                label="更新时间"
                min-width="180"
                prop="sys_update_datetime"
              />
            </ElTable>
          </section>

          <section class="fm-relation-insight__panel">
            <div class="fm-relation-insight__panel-title">故障处理措施</div>
            <ElEmpty
              v-if="frame.failureModeHandlingRows.length === 0"
              description="当前故障模式尚未关联任何故障处理措施"
            />
            <ElTable v-else :data="frame.failureModeHandlingRows" border stripe>
              <ElTableColumn label="处理措施" min-width="220">
                <template #default="{ row }">
                  <button
                    class="fm-relation-insight__drill-link"
                    type="button"
                    @click="openHandlingMeasure(row.id)"
                  >
                    {{ row.measure }}
                  </button>
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="措施类别"
                min-width="120"
                prop="measure_category"
              />
              <ElTableColumn label="措施详情" min-width="280">
                <template #default="{ row }">
                  {{ formatHtmlSnippet(row.measure_detail_html) }}
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="措施效果"
                min-width="220"
                prop="measure_effect"
              />
              <ElTableColumn label="测试用例" min-width="260">
                <template #default="{ row }">
                  {{ formatRelationLabels(row.test_case_items) }}
                </template>
              </ElTableColumn>
              <ElTableColumn label="设计责任人" min-width="220">
                <template #default="{ row }">
                  {{ formatUserNames(row.owner_info) }}
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="关联产品数"
                min-width="110"
                prop="related_product_count"
              />
              <ElTableColumn
                label="已落地产品数"
                min-width="110"
                prop="landed_product_count"
              />
              <ElTableColumn label="汇总状态" min-width="120">
                <template #default="{ row }">
                  <ElTag
                    :type="getLandingStatusTagType(row.summary_status)"
                    effect="light"
                    round
                  >
                    {{ row.summary_status }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="创建时间"
                min-width="180"
                prop="sys_create_datetime"
              />
              <ElTableColumn
                label="更新时间"
                min-width="180"
                prop="sys_update_datetime"
              />
            </ElTable>
          </section>

          <section class="fm-relation-insight__panel">
            <div class="fm-relation-insight__panel-title">维测手段</div>
            <ElEmpty
              v-if="frame.failureModeObservationRows.length === 0"
              description="当前故障模式尚未关联任何维测手段"
            />
            <ElTable
              v-else
              :data="frame.failureModeObservationRows"
              border
              stripe
            >
              <ElTableColumn label="维测手段" min-width="220">
                <template #default="{ row }">
                  <button
                    class="fm-relation-insight__drill-link"
                    type="button"
                    @click="openObservationMethod(row.id)"
                  >
                    {{ row.display_name }}
                  </button>
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="维测类型"
                min-width="140"
                prop="monitor_type"
              />
              <ElTableColumn label="日志 ID" min-width="180" prop="log_id" />
              <ElTableColumn
                label="日志关键词"
                min-width="180"
                prop="log_keyword"
              />
              <ElTableColumn label="日志路径" min-width="240" prop="log_path" />
              <ElTableColumn label="设计责任人" min-width="220">
                <template #default="{ row }">
                  {{ formatUserNames(row.owner_info) }}
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="关联产品数"
                min-width="110"
                prop="related_product_count"
              />
              <ElTableColumn
                label="已落地产品数"
                min-width="110"
                prop="landed_product_count"
              />
              <ElTableColumn label="汇总状态" min-width="120">
                <template #default="{ row }">
                  <ElTag
                    :type="getLandingStatusTagType(row.summary_status)"
                    effect="light"
                    round
                  >
                    {{ row.summary_status }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="创建时间"
                min-width="180"
                prop="sys_create_datetime"
              />
              <ElTableColumn
                label="更新时间"
                min-width="180"
                prop="sys_update_datetime"
              />
            </ElTable>
          </section>

          <section class="fm-relation-insight__panel">
            <div class="fm-relation-insight__panel-title">华佗诊断方案</div>
            <ElEmpty
              v-if="frame.failureModeHuatuoRows.length === 0"
              description="当前故障模式尚未关联任何华佗诊断方案"
            />
            <ElTable v-else :data="frame.failureModeHuatuoRows" border stripe>
              <ElTableColumn label="诊断方案" min-width="320">
                <template #default="{ row }">
                  <button
                    class="fm-relation-insight__drill-link"
                    type="button"
                    @click="openHuatuoDiagnosis(row.id)"
                  >
                    {{ row.description }}
                  </button>
                </template>
              </ElTableColumn>
              <ElTableColumn label="设计责任人" min-width="220">
                <template #default="{ row }">
                  {{ formatUserNames(row.owner_info) }}
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="关联产品数"
                min-width="110"
                prop="related_product_count"
              />
              <ElTableColumn
                label="已落地产品数"
                min-width="110"
                prop="landed_product_count"
              />
              <ElTableColumn label="汇总状态" min-width="120">
                <template #default="{ row }">
                  <ElTag
                    :type="getLandingStatusTagType(row.summary_status)"
                    effect="light"
                    round
                  >
                    {{ row.summary_status }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="创建时间"
                min-width="180"
                prop="sys_create_datetime"
              />
              <ElTableColumn
                label="更新时间"
                min-width="180"
                prop="sys_update_datetime"
              />
            </ElTable>
          </section>

          <section class="fm-relation-insight__panel">
            <div class="fm-relation-insight__panel-title">落地产品</div>
            <ElEmpty
              v-if="getCurrentFailureModeProductRows(frame).length === 0"
              :description="getProductEmptyText(frame)"
            />
            <ElTable
              v-else
              :data="getCurrentFailureModeProductRows(frame)"
              border
              stripe
            >
              <ElTableColumn label="产品" min-width="220" prop="product_name" />
              <ElTableColumn label="主版本SE" min-width="160">
                <template #default="{ row }">
                  {{ formatUserName(row.owner_info) }}
                </template>
              </ElTableColumn>
              <ElTableColumn label="故障模式落地" min-width="150">
                <template #default="{ row }">
                  <ElTag
                    :type="getLandingStatusTagType(row.failure_mode_status)"
                    effect="light"
                    round
                  >
                    {{ row.failure_mode_status || '-' }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn label="落地子系统" min-width="220">
                <template #default="{ row }">
                  {{ formatTextList(row.subsystems) }}
                </template>
              </ElTableColumn>
              <ElTableColumn label="产线拦截策略" min-width="260">
                <template #default="{ row }">
                  <div
                    v-if="
                      getFailureModeProductResourceRows(
                        row,
                        'interception_rows',
                      ).length > 0
                    "
                    class="fm-relation-insight__tag-list"
                  >
                    <ElTag
                      v-for="item in getFailureModeProductResourceRows(
                        row,
                        'interception_rows',
                      )"
                      :key="item.id"
                      :type="getLandingStatusTagType(item.status)"
                      effect="light"
                      size="small"
                    >
                      {{ item.label }}
                      <span v-if="item.subtitle"> · {{ item.subtitle }}</span>
                      <span> · {{ item.status }}</span>
                    </ElTag>
                  </div>
                  <span v-else class="text-gray-400">未关联</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="故障处理措施" min-width="280">
                <template #default="{ row }">
                  <div
                    v-if="
                      getFailureModeProductResourceRows(row, 'handling_rows')
                        .length > 0
                    "
                    class="fm-relation-insight__tag-list"
                  >
                    <ElTag
                      v-for="item in getFailureModeProductResourceRows(
                        row,
                        'handling_rows',
                      )"
                      :key="item.id"
                      :type="getLandingStatusTagType(item.status)"
                      effect="light"
                      size="small"
                    >
                      {{ item.label }}
                      <span v-if="item.subtitle"> · {{ item.subtitle }}</span>
                      <span> · {{ item.status }}</span>
                    </ElTag>
                  </div>
                  <span v-else class="text-gray-400">未关联</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="维测手段" min-width="280">
                <template #default="{ row }">
                  <div
                    v-if="
                      getFailureModeProductResourceRows(row, 'observation_rows')
                        .length > 0
                    "
                    class="fm-relation-insight__tag-list"
                  >
                    <ElTag
                      v-for="item in getFailureModeProductResourceRows(
                        row,
                        'observation_rows',
                      )"
                      :key="item.id"
                      :type="getLandingStatusTagType(item.status)"
                      effect="light"
                      size="small"
                    >
                      {{ item.label }}
                      <span v-if="item.subtitle"> · {{ item.subtitle }}</span>
                      <span> · {{ item.status }}</span>
                    </ElTag>
                  </div>
                  <span v-else class="text-gray-400">未关联</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="华佗诊断方案" min-width="260">
                <template #default="{ row }">
                  <div
                    v-if="
                      getFailureModeProductResourceRows(row, 'huatuo_rows')
                        .length > 0
                    "
                    class="fm-relation-insight__tag-list"
                  >
                    <ElTag
                      v-for="item in getFailureModeProductResourceRows(
                        row,
                        'huatuo_rows',
                      )"
                      :key="item.id"
                      :type="getLandingStatusTagType(item.status)"
                      effect="light"
                      size="small"
                    >
                      {{ item.label }}
                      <span v-if="item.subtitle"> · {{ item.subtitle }}</span>
                      <span> · {{ item.status }}</span>
                    </ElTag>
                  </div>
                  <span v-else class="text-gray-400">未关联</span>
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="最近落地时间"
                min-width="180"
                prop="landed_at"
              />
            </ElTable>
          </section>
        </div>

        <div v-else class="flex flex-col gap-4">
          <section class="fm-relation-insight__panel">
            <div class="fm-relation-insight__panel-title">关联故障模式</div>
            <ElEmpty
              v-if="getCurrentFailureModeRows(frame).length === 0"
              :description="getFailureModeEmptyText(frame)"
            />
            <ElTable
              v-else
              :data="getCurrentFailureModeRows(frame)"
              border
              stripe
            >
              <ElTableColumn label="故障模式" min-width="240">
                <template #default="{ row }">
                  <button
                    class="fm-relation-insight__drill-link"
                    type="button"
                    @click="openFailureMode(row.failure_mode_id)"
                  >
                    {{ row.failure_mode_brief }}
                  </button>
                </template>
              </ElTableColumn>
              <ElTableColumn label="子系统" min-width="140" prop="subsystem" />
              <ElTableColumn label="状态" min-width="120" prop="status" />
              <ElTableColumn label="关联产品" min-width="220">
                <template #default="{ row }">
                  {{ formatTextList(row.product_names) }}
                </template>
              </ElTableColumn>
              <ElTableColumn
                label="关联产品数"
                min-width="90"
                prop="related_product_count"
              />
              <ElTableColumn
                label="已落地产品数"
                min-width="110"
                prop="landed_product_count"
              />
            </ElTable>
          </section>

          <section class="fm-relation-insight__panel">
            <div class="fm-relation-insight__panel-title">落地产品</div>
            <ElEmpty
              v-if="getCurrentLandingProductRows(frame).length === 0"
              :description="getProductEmptyText(frame)"
            />
            <ElTable
              v-else
              :data="getCurrentLandingProductRows(frame)"
              border
              stripe
            >
              <ElTableColumn label="产品" min-width="180" prop="product_name" />
              <ElTableColumn label="主版本SE" min-width="140">
                <template #default="{ row }">
                  {{ formatUserName(row.owner_info) }}
                </template>
              </ElTableColumn>
              <ElTableColumn label="通过哪些故障模式落地" min-width="260">
                <template #default="{ row }">
                  {{ formatTextList(row.failure_mode_briefs) }}
                </template>
              </ElTableColumn>
            </ElTable>
          </section>
        </div>
      </div>
    </ZqDrawer>
  </template>
</template>

<style scoped>
.fm-relation-insight__hero {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: linear-gradient(
    135deg,
    rgba(248, 250, 252, 0.96),
    rgba(239, 246, 255, 0.9)
  );
  padding: 18px 20px;
}

.fm-relation-insight__hero-title {
  color: #0f172a;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.5;
}

.fm-relation-insight__hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 8px;
  color: #475569;
  font-size: 13px;
}

.fm-relation-insight__summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.fm-relation-insight__summary-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  padding: 16px 18px;
}

.fm-relation-insight__summary-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.fm-relation-insight__summary-value {
  margin-top: 8px;
  color: #0f172a;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.fm-relation-insight__panel {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  padding: 16px;
}

.fm-relation-insight__panel-title {
  margin-bottom: 12px;
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
}

.fm-relation-insight__drill-link {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--el-color-primary);
  cursor: pointer;
  font: inherit;
  padding: 0;
  text-align: left;
}

.fm-relation-insight__drill-link:hover {
  text-decoration: underline;
}

.fm-relation-insight__tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
