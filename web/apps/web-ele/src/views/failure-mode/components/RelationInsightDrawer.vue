<script lang="ts" setup>
import type {
  FailureModeInsight,
  FailureModeInsightResourceRow,
  HandlingMeasureInsight,
  HuatuoDiagnosisInsight,
  InterceptionInsight,
  InterceptionInsightFailureModeRow,
  InterceptionInsightProductRow,
  ObservationMethodInsight,
  TestCaseInsight,
  UserBriefInfo,
} from '#/api/failure_mode';

import { computed, ref } from 'vue';

import {
  ElEmpty,
  ElMessage,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  getFailureModeInsightApi,
  getHandlingMeasureInsightApi,
  getHuatuoDiagnosisInsightApi,
  getInterceptionStrategyInsightApi,
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

interface SummaryMetric {
  label: string;
  value: number | string;
}

const visible = ref(false);
const loading = ref(false);
const mode = ref<InsightMode>('failure_mode');

const failureModeInsight = ref<FailureModeInsight | null>(null);
const interceptionInsight = ref<InterceptionInsight | null>(null);
const handlingMeasureInsight = ref<HandlingMeasureInsight | null>(null);
const observationMethodInsight = ref<null | ObservationMethodInsight>(null);
const huatuoDiagnosisInsight = ref<HuatuoDiagnosisInsight | null>(null);
const testCaseInsight = ref<null | TestCaseInsight>(null);

const drawerTitle = computed(() => {
  switch (mode.value) {
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
});

const currentResourceInsight = computed<null | ResourceInsight>(() => {
  switch (mode.value) {
    case 'handling_measure': {
      return handlingMeasureInsight.value;
    }
    case 'huatuo_diagnosis': {
      return huatuoDiagnosisInsight.value;
    }
    case 'interception': {
      return interceptionInsight.value;
    }
    case 'observation_method': {
      return observationMethodInsight.value;
    }
    case 'test_case': {
      return testCaseInsight.value;
    }
    default: {
      return null;
    }
  }
});

const currentRate = computed(() => {
  const numerator =
    mode.value === 'failure_mode'
      ? failureModeInsight.value?.landed_product_count || 0
      : currentResourceInsight.value?.landed_product_count || 0;
  const denominator =
    mode.value === 'failure_mode'
      ? failureModeInsight.value?.related_product_count || 0
      : currentResourceInsight.value?.total_product_count || 0;
  return formatRate(numerator, denominator);
});

const heroTitle = computed(() => {
  switch (mode.value) {
    case 'failure_mode': {
      return failureModeInsight.value?.brief || '';
    }
    case 'handling_measure': {
      return handlingMeasureInsight.value?.measure || '';
    }
    case 'huatuo_diagnosis': {
      return huatuoDiagnosisInsight.value?.description || '';
    }
    case 'interception': {
      return interceptionInsight.value?.interception_item || '';
    }
    case 'observation_method': {
      return observationMethodInsight.value?.display_name || '';
    }
    default: {
      return testCaseInsight.value?.brief || '';
    }
  }
});

const heroMeta = computed(() => {
  switch (mode.value) {
    case 'failure_mode': {
      return [
        `子系统：${failureModeInsight.value?.subsystem || '-'}`,
        `状态：${failureModeInsight.value?.status || '-'}`,
      ];
    }
    case 'handling_measure': {
      return [
        `措施类别：${handlingMeasureInsight.value?.measure_category || '-'}`,
      ];
    }
    case 'huatuo_diagnosis': {
      return [];
    }
    case 'interception': {
      return [`工位：${interceptionInsight.value?.station || '-'}`];
    }
    case 'observation_method': {
      return [
        `维测类型：${observationMethodInsight.value?.monitor_type || '-'}`,
        `日志 ID：${observationMethodInsight.value?.log_id || '-'}`,
      ];
    }
    default: {
      return [`CIDA 链接：${testCaseInsight.value?.cida_link || '-'}`];
    }
  }
});

const summaryMetrics = computed<SummaryMetric[]>(() => {
  switch (mode.value) {
    case 'failure_mode': {
      return [
        {
          label: '已落地产品数',
          value: failureModeInsight.value?.landed_product_count || 0,
        },
        {
          label: '关联产品数',
          value: failureModeInsight.value?.related_product_count || 0,
        },
        { label: '落地率', value: currentRate.value },
      ];
    }
    case 'handling_measure': {
      return [
        {
          label: '关联测试用例数',
          value: handlingMeasureInsight.value?.related_test_case_count || 0,
        },
        {
          label: '关联故障模式数',
          value: handlingMeasureInsight.value?.related_failure_mode_count || 0,
        },
        {
          label: '已落地产品数',
          value: handlingMeasureInsight.value?.landed_product_count || 0,
        },
        { label: '落地率', value: currentRate.value },
      ];
    }
    case 'huatuo_diagnosis': {
      return [
        {
          label: '关联故障模式数',
          value: huatuoDiagnosisInsight.value?.related_failure_mode_count || 0,
        },
        {
          label: '已落地产品数',
          value: huatuoDiagnosisInsight.value?.landed_product_count || 0,
        },
        { label: '落地率', value: currentRate.value },
      ];
    }
    case 'interception': {
      return [
        {
          label: '关联故障模式数',
          value: interceptionInsight.value?.related_failure_mode_count || 0,
        },
        {
          label: '已落地产品数',
          value: interceptionInsight.value?.landed_product_count || 0,
        },
        { label: '落地率', value: currentRate.value },
      ];
    }
    case 'observation_method': {
      return [
        {
          label: '关联故障模式数',
          value:
            observationMethodInsight.value?.related_failure_mode_count || 0,
        },
        {
          label: '已落地产品数',
          value: observationMethodInsight.value?.landed_product_count || 0,
        },
        { label: '落地率', value: currentRate.value },
      ];
    }
    default: {
      return [
        {
          label: '关联处理措施数',
          value: testCaseInsight.value?.related_handling_measure_count || 0,
        },
        {
          label: '关联故障模式数',
          value: testCaseInsight.value?.related_failure_mode_count || 0,
        },
        {
          label: '已落地产品数',
          value: testCaseInsight.value?.landed_product_count || 0,
        },
        { label: '落地率', value: currentRate.value },
      ];
    }
  }
});

const currentFailureModeRows = computed<InterceptionInsightFailureModeRow[]>(
  () => currentResourceInsight.value?.failure_mode_rows || [],
);

const currentFailureModeProductRows = computed(
  () => failureModeInsight.value?.product_rows || [],
);

const currentLandingProductRows = computed<InterceptionInsightProductRow[]>(
  () => currentResourceInsight.value?.product_rows || [],
);

const productEmptyText = computed(() => {
  switch (mode.value) {
    case 'failure_mode': {
      return '当前故障模式尚未落地到任何产品基线';
    }
    case 'handling_measure': {
      return '当前故障处理措施尚未通过故障模式落地到任何产品';
    }
    case 'huatuo_diagnosis': {
      return '当前华佗诊断方案尚未通过故障模式落地到任何产品';
    }
    case 'interception': {
      return '当前产线拦截策略尚未通过故障模式落地到任何产品';
    }
    case 'observation_method': {
      return '当前维测手段尚未通过故障模式落地到任何产品';
    }
    default: {
      return '当前测试用例尚未通过处理措施与故障模式落地到任何产品';
    }
  }
});

const failureModeEmptyText = computed(() => {
  switch (mode.value) {
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
});

function resetInsights() {
  failureModeInsight.value = null;
  interceptionInsight.value = null;
  handlingMeasureInsight.value = null;
  observationMethodInsight.value = null;
  huatuoDiagnosisInsight.value = null;
  testCaseInsight.value = null;
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

function formatTextList(items?: null | string[]) {
  return (items || []).filter(Boolean).join('、') || '-';
}

function getLandingStatusTagType(status?: null | string) {
  if (status === '已落地') {
    return 'success';
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

async function openInsight(
  nextMode: InsightMode,
  loader: () => Promise<void>,
  errorMessage: string,
) {
  mode.value = nextMode;
  resetInsights();
  visible.value = true;
  loading.value = true;
  try {
    await loader();
  } catch (error) {
    visible.value = false;
    console.error(error);
    ElMessage.error(errorMessage);
  } finally {
    loading.value = false;
  }
}

async function openFailureMode(id: string) {
  await openInsight(
    'failure_mode',
    async () => {
      failureModeInsight.value = await getFailureModeInsightApi(id);
    },
    '加载故障模式关联洞察失败',
  );
}

async function openInterception(id: string) {
  await openInsight(
    'interception',
    async () => {
      interceptionInsight.value = await getInterceptionStrategyInsightApi(id);
    },
    '加载产线拦截策略关联洞察失败',
  );
}

async function openHandlingMeasure(id: string) {
  await openInsight(
    'handling_measure',
    async () => {
      handlingMeasureInsight.value = await getHandlingMeasureInsightApi(id);
    },
    '加载故障处理措施关联洞察失败',
  );
}

async function openObservationMethod(id: string) {
  await openInsight(
    'observation_method',
    async () => {
      observationMethodInsight.value = await getObservationMethodInsightApi(id);
    },
    '加载维测手段关联洞察失败',
  );
}

async function openHuatuoDiagnosis(id: string) {
  await openInsight(
    'huatuo_diagnosis',
    async () => {
      huatuoDiagnosisInsight.value = await getHuatuoDiagnosisInsightApi(id);
    },
    '加载华佗诊断方案关联洞察失败',
  );
}

async function openTestCase(id: string) {
  await openInsight(
    'test_case',
    async () => {
      testCaseInsight.value = await getTestCaseInsightApi(id);
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
  <ZqDrawer
    v-model="visible"
    :loading="loading"
    :show-footer="false"
    :size="1180"
    :title="drawerTitle"
  >
    <div class="fm-relation-insight flex flex-col gap-4 pb-2">
      <div v-if="heroTitle" class="fm-relation-insight__hero">
        <div class="fm-relation-insight__hero-title">
          {{ heroTitle }}
        </div>
        <div v-if="heroMeta.length > 0" class="fm-relation-insight__hero-meta">
          <span v-for="item in heroMeta" :key="item">{{ item }}</span>
        </div>
      </div>

      <div class="fm-relation-insight__summary-grid">
        <div
          v-for="item in summaryMetrics"
          :key="item.label"
          class="fm-relation-insight__summary-card"
        >
          <div class="fm-relation-insight__summary-label">{{ item.label }}</div>
          <div class="fm-relation-insight__summary-value">{{ item.value }}</div>
        </div>
      </div>

      <section
        v-if="mode === 'failure_mode'"
        class="fm-relation-insight__panel"
      >
        <div class="fm-relation-insight__panel-title">落地产品</div>
        <ElEmpty
          v-if="currentFailureModeProductRows.length === 0"
          :description="productEmptyText"
        />
        <ElTable v-else :data="currentFailureModeProductRows" border stripe>
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
                  getFailureModeProductResourceRows(row, 'interception_rows')
                    .length > 0
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
                  getFailureModeProductResourceRows(row, 'huatuo_rows').length >
                  0
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

      <div
        v-else
        class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]"
      >
        <section class="fm-relation-insight__panel">
          <div class="fm-relation-insight__panel-title">关联故障模式</div>
          <ElEmpty
            v-if="currentFailureModeRows.length === 0"
            :description="failureModeEmptyText"
          />
          <ElTable v-else :data="currentFailureModeRows" border stripe>
            <ElTableColumn
              label="故障模式"
              min-width="240"
              prop="failure_mode_brief"
            />
            <ElTableColumn label="子系统" min-width="140" prop="subsystem" />
            <ElTableColumn label="状态" min-width="120" prop="status" />
            <ElTableColumn label="已落地产品" min-width="220">
              <template #default="{ row }">
                {{ formatTextList(row.product_names) }}
              </template>
            </ElTableColumn>
            <ElTableColumn
              label="产品数"
              min-width="90"
              prop="landed_product_count"
            />
          </ElTable>
        </section>

        <section class="fm-relation-insight__panel">
          <div class="fm-relation-insight__panel-title">落地产品</div>
          <ElEmpty
            v-if="currentLandingProductRows.length === 0"
            :description="productEmptyText"
          />
          <ElTable v-else :data="currentLandingProductRows" border stripe>
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

.fm-relation-insight__tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
