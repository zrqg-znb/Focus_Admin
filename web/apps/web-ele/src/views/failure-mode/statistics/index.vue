<script lang="ts" setup>
import type {
  FailureModeStatisticsSubsystemRow,
  FailureModeStatisticsSummary,
} from '#/api/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { ElCard, ElMessage, ElTabPane, ElTabs, ElTag } from 'element-plus';

import {
  getFailureModeDictOptionsApi,
  getFailureModeStatisticsSummaryApi,
  listFailureModeStatisticsSubsystemOptionsApi,
  listFailureModeStatisticsSubsystemsApi,
} from '#/api/failure_mode';
import { useZqTable } from '#/components/zq-table';

import { createEmptyDictOptions } from '../data';
import StatisticsBarChart from './components/StatisticsBarChart.vue';
import StatisticsPieChart from './components/StatisticsPieChart.vue';
import {
  buildStatisticsPieCards,
  createEmptyStatisticsSummary,
  formatPercent,
  resolveOrderedCategoryValues,
  resolveStatusLightMeta,
  statisticsTabs,
  useStatisticsSubsystemColumns,
} from './data';

defineOptions({ name: 'FailureModeStatisticsPage' });

type StatisticsTabKey = 'charts' | 'table';

interface GridQueryContext {
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const activeTab = ref<StatisticsTabKey>('charts');
const pageScrollTop = ref(0);
const summaryLoading = ref(false);
const subsystemOptionsLoading = ref(false);
const subsystemOptions = ref<string[]>([]);
const selectedSubsystems = ref<string[]>([]);
const dictOptions = ref(createEmptyDictOptions());
const summary = ref<FailureModeStatisticsSummary>(
  createEmptyStatisticsSummary(),
);
const handlingCategories = computed(() =>
  resolveOrderedCategoryValues(
    dictOptions.value.measure_category,
    Object.keys(summary.value.handling_status_map || {}),
  ),
);
const observationTypes = computed(() =>
  resolveOrderedCategoryValues(
    dictOptions.value.monitor_type,
    Object.keys(summary.value.observation_status_map || {}),
  ),
);
const statisticsPieCards = computed(() =>
  buildStatisticsPieCards({
    handlingCategories: handlingCategories.value,
    observationTypes: observationTypes.value,
  }),
);

const [SubsystemTable, subsystemTableApi] =
  useZqTable<FailureModeStatisticsSubsystemRow>({
    gridOptions: {
      border: true,
      columns: useStatisticsSubsystemColumns({
        handlingCategories: [],
        observationTypes: [],
      }) as ZqTableGridOptions<FailureModeStatisticsSubsystemRow>['columns'],
      proxyConfig: {
        autoLoad: true,
        ajax: {
          query: async ({ page }: GridQueryContext) => {
            return listFailureModeStatisticsSubsystemsApi({
              page: page.currentPage,
              pageSize: page.pageSize,
              subsystems: selectedSubsystems.value,
            });
          },
        },
      },
      rowKey: 'subsystem',
      stripe: true,
      toolbarConfig: {
        custom: true,
        refresh: true,
        search: false,
        zoom: true,
      },
      pagerConfig: {
        enabled: true,
        pageSize: 10,
        pageSizes: [10, 20, 50],
      },
    },
  });

const totalFailureModeCount = computed(() => {
  return (summary.value.subsystem_counts || []).reduce((sum, item) => {
    return sum + Number(item.value || 0);
  }, 0);
});

const selectedSubsystemCount = computed(() => {
  if (selectedSubsystems.value.length === 0) {
    return subsystemOptions.value.length;
  }
  return selectedSubsystems.value.length;
});

const subsystemScopeLabel = computed(() => {
  if (selectedSubsystems.value.length === 0) {
    return '全部子系统';
  }
  if (selectedSubsystems.value.length === 1) {
    return selectedSubsystems.value[0] || '全部子系统';
  }
  return `已选 ${selectedSubsystems.value.length} 个子系统`;
});

const waitingInterceptionCount = computed(() => {
  const item = (summary.value.interception_status || []).find(
    (entry) => entry.name === '待补充',
  );
  return Number(item?.value || 0);
});

const showSummaryBar = computed(() => pageScrollTop.value > 72);

watch(
  [handlingCategories, observationTypes],
  ([nextHandlingCategories, nextObservationTypes]) => {
    subsystemTableApi.setGridOptions({
      columns: useStatisticsSubsystemColumns({
        handlingCategories: nextHandlingCategories,
        observationTypes: nextObservationTypes,
      }) as ZqTableGridOptions<FailureModeStatisticsSubsystemRow>['columns'],
    });
  },
  { immediate: true },
);

async function loadDictOptions() {
  dictOptions.value = await getFailureModeDictOptionsApi();
}

async function loadSummary() {
  summaryLoading.value = true;
  try {
    summary.value = await getFailureModeStatisticsSummaryApi({
      subsystems: selectedSubsystems.value,
    });
  } finally {
    summaryLoading.value = false;
  }
}

async function loadSubsystemOptions() {
  subsystemOptionsLoading.value = true;
  try {
    const rows = await listFailureModeStatisticsSubsystemOptionsApi();
    subsystemOptions.value = rows || [];
    if (selectedSubsystems.value.length === 0) {
      return;
    }
    const optionSet = new Set(subsystemOptions.value);
    const nextSelected = selectedSubsystems.value.filter((item) =>
      optionSet.has(item),
    );
    selectedSubsystems.value = nextSelected.length > 0 ? nextSelected : [];
  } finally {
    subsystemOptionsLoading.value = false;
  }
}

async function reloadAnalysis() {
  await Promise.all([loadSummary(), subsystemTableApi.reload()]);
}

async function handleSubsystemFilterChange() {
  try {
    await reloadAnalysis();
  } catch (error) {
    console.error(error);
    ElMessage.error('切换子系统统计失败');
  }
}

async function resetSubsystemFilter() {
  selectedSubsystems.value = [];
  await handleSubsystemFilterChange();
}

function handlePageScroll(event: Event) {
  const target = event.target as HTMLElement | null;
  pageScrollTop.value = Number(target?.scrollTop || 0);
}

onMounted(async () => {
  try {
    await Promise.all([loadDictOptions(), loadSubsystemOptions()]);
    await reloadAnalysis();
  } catch (error) {
    console.error(error);
    ElMessage.error('加载故障管理统计失败');
  }
  await nextTick();
});
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div
      class="failure-statistics-page flex h-full min-h-0 flex-col gap-4"
      @scroll.passive="handlePageScroll"
    >
      <div class="failure-statistics-summary-anchor">
        <section
          class="failure-statistics-summary-bar"
          :class="{ 'is-visible': showSummaryBar }"
        >
          <div class="failure-statistics-summary-bar__title">
            <span class="failure-statistics-summary-bar__eyebrow">
              Failure Mode Analytics
            </span>
            <span class="failure-statistics-summary-bar__heading">
              故障管理统计
            </span>
          </div>
          <div class="failure-statistics-summary-bar__metrics">
            <div class="failure-statistics-summary-pill">
              <span>筛选范围</span>
              <strong>{{ subsystemScopeLabel }}</strong>
            </div>
            <div class="failure-statistics-summary-pill">
              <span>故障模式</span>
              <strong>{{ totalFailureModeCount }}</strong>
            </div>
            <div class="failure-statistics-summary-pill warning">
              <span>拦截待补充</span>
              <strong>{{ waitingInterceptionCount }}</strong>
            </div>
          </div>
        </section>
      </div>

      <section class="failure-statistics-hero">
        <div>
          <div class="failure-statistics-hero__eyebrow">
            Failure Mode Analytics
          </div>
          <h1 class="failure-statistics-hero__title">故障管理统计</h1>
          <p class="failure-statistics-hero__desc">
            统一聚合故障模式、拦截策略、诊断方案、处理措施与维测手段配置状态，快速识别待补充子系统。
          </p>
        </div>
        <div class="failure-statistics-hero__metrics">
          <div class="failure-statistics-metric-card">
            <div class="failure-statistics-metric-card__label">统计子系统</div>
            <div class="failure-statistics-metric-card__value">
              {{ selectedSubsystemCount }}
            </div>
            <div class="failure-statistics-metric-card__hint">
              当前筛选范围内的子系统数量
            </div>
          </div>
          <div class="failure-statistics-metric-card">
            <div class="failure-statistics-metric-card__label">
              故障模式总量
            </div>
            <div class="failure-statistics-metric-card__value">
              {{ totalFailureModeCount }}
            </div>
            <div class="failure-statistics-metric-card__hint">
              来自全部故障模式主数据
            </div>
          </div>
          <div class="failure-statistics-metric-card warning">
            <div class="failure-statistics-metric-card__label">拦截待补充</div>
            <div class="failure-statistics-metric-card__value">
              {{ waitingInterceptionCount }}
            </div>
            <div class="failure-statistics-metric-card__hint">
              必配但尚未配置产线拦截策略
            </div>
          </div>
        </div>
      </section>

      <section class="failure-statistics-filter-panel">
        <div class="failure-statistics-filter-panel__header">
          <div>
            <div class="failure-statistics-filter-panel__title">统计范围</div>
            <div class="failure-statistics-filter-panel__desc">
              默认统计全部子系统，也可以单选或多选后重新汇总图表与表格。
            </div>
          </div>
          <ElButton
            plain
            :disabled="selectedSubsystems.length === 0"
            @click="resetSubsystemFilter"
          >
            全选子系统
          </ElButton>
        </div>
        <div class="failure-statistics-filter-panel__controls">
          <ElSelect
            v-model="selectedSubsystems"
            class="failure-statistics-filter-panel__select"
            collapse-tags
            collapse-tags-tooltip
            filterable
            multiple
            clearable
            :loading="subsystemOptionsLoading"
            placeholder="全部子系统"
            @change="handleSubsystemFilterChange"
            @clear="handleSubsystemFilterChange"
          >
            <ElOption
              v-for="item in subsystemOptions"
              :key="item"
              :label="item"
              :value="item"
            />
          </ElSelect>
          <div class="failure-statistics-filter-panel__summary">
            当前范围：{{ subsystemScopeLabel }}
          </div>
        </div>
      </section>

      <ElTabs
        v-model="activeTab"
        class="failure-statistics-tabs border-border bg-card rounded-xl border p-4 shadow-sm"
      >
        <ElTabPane
          v-for="tab in statisticsTabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
        >
          <template v-if="tab.key === 'charts'">
            <div class="failure-statistics-chart-pane">
              <div
                class="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.75fr)]"
              >
                <ElCard
                  class="border-none !bg-transparent shadow-none"
                  v-loading="summaryLoading"
                >
                  <div class="failure-statistics-card-header">
                    <div>
                      <div class="failure-statistics-card-header__title">
                        子系统故障模式数量
                      </div>
                      <div class="failure-statistics-card-header__desc">
                        从子系统维度看当前故障模式沉淀规模。
                      </div>
                    </div>
                    <ElTag type="primary">柱状图</ElTag>
                  </div>
                  <StatisticsBarChart
                    :data="summary.subsystem_counts"
                    title="故障模式数量"
                  />
                </ElCard>

                <ElCard
                  class="border-none !bg-transparent shadow-none"
                  v-loading="summaryLoading"
                >
                  <div class="failure-statistics-card-header">
                    <div>
                      <div class="failure-statistics-card-header__title">
                        看板说明
                      </div>
                      <div class="failure-statistics-card-header__desc">
                        饼图统一使用“已配置 / 待补充 /
                        无需配置”三态，对比当前统计字段与主数据关联的完整度。
                      </div>
                    </div>
                    <ElTag type="success">三态规则</ElTag>
                  </div>
                  <div class="failure-statistics-note-grid">
                    <div class="failure-statistics-note-item">
                      <span class="dot configured"></span>
                      <div>
                        <div class="title">已配置</div>
                        <div class="desc">
                          当前维度为必配且至少存在 1 条匹配关联。
                        </div>
                      </div>
                    </div>
                    <div class="failure-statistics-note-item">
                      <span class="dot pending"></span>
                      <div>
                        <div class="title">待补充</div>
                        <div class="desc">
                          当前维度为必配，但尚未补齐对应关联关系。
                        </div>
                      </div>
                    </div>
                    <div class="failure-statistics-note-item">
                      <span class="dot skipped"></span>
                      <div>
                        <div class="title">无需配置</div>
                        <div class="desc">
                          当前维度未勾选必配，不纳入待补充统计。
                        </div>
                      </div>
                    </div>
                  </div>
                </ElCard>
              </div>

              <div class="mt-4 grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
                <ElCard
                  v-for="card in statisticsPieCards"
                  :key="card.key"
                  class="failure-statistics-pie-card border-none shadow-none"
                  v-loading="summaryLoading"
                >
                  <div class="failure-statistics-card-header mb-3">
                    <div>
                      <div class="failure-statistics-card-header__title">
                        {{ card.title }}
                      </div>
                      <div class="failure-statistics-card-header__desc">
                        {{ card.subtitle }}
                      </div>
                    </div>
                    <ElTag type="info">饼图</ElTag>
                  </div>
                  <StatisticsPieChart
                    :data="card.resolveData(summary)"
                    :title="card.title"
                  />
                </ElCard>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="failure-statistics-table-pane">
              <div class="failure-statistics-table-card">
                <SubsystemTable class="h-full min-h-0 flex-1">
                  <template #toolbar-actions>
                    <ElButton type="primary" @click="reloadAnalysis">
                      刷新统计摘要
                    </ElButton>
                  </template>
                  <template #cell-status_light="{ row }">
                    <div class="failure-statistics-status-cell">
                      <span
                        class="failure-statistics-status-light"
                        :style="{
                          backgroundColor: resolveStatusLightMeta(
                            row.status_light,
                          ).color,
                        }"
                      ></span>
                      <div>
                        <div class="failure-statistics-status-label">
                          {{ resolveStatusLightMeta(row.status_light).label }}
                        </div>
                        <div class="failure-statistics-status-hint">
                          待补充 {{ row.pending_failure_mode_count }} /
                          {{ row.failure_mode_count }} ·
                          {{ formatPercent(row.pending_rate) }}
                        </div>
                      </div>
                    </div>
                  </template>
                </SubsystemTable>
              </div>
            </div>
          </template>
        </ElTabPane>
      </ElTabs>
    </div>
  </Page>
</template>

<style scoped>
.failure-statistics-page {
  min-height: 100%;
  overflow-y: auto;
  padding-right: 4px;
  overscroll-behavior: contain;
}

.failure-statistics-tabs {
  flex: none;
}

.failure-statistics-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  padding: 18px 20px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.failure-statistics-filter-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.failure-statistics-filter-panel__title {
  color: #111827;
  font-size: 16px;
  font-weight: 700;
}

.failure-statistics-filter-panel__desc {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.failure-statistics-filter-panel__controls {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(0, 1fr) auto;
}

.failure-statistics-filter-panel__select {
  width: 100%;
}

.failure-statistics-filter-panel__summary {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--el-color-primary-light-9) 72%, white);
  padding: 0 14px;
  color: #475569;
  font-size: 13px;
  white-space: nowrap;
}

.failure-statistics-summary-anchor {
  position: sticky;
  top: 0;
  z-index: 14;
  height: 0;
}

.failure-statistics-summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 20%, transparent);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(14px);
  padding: 12px 14px;
  opacity: 0;
  pointer-events: none;
  transform: translateY(-10px) scale(0.98);
  transition:
    opacity 0.18s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.failure-statistics-summary-bar.is-visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0) scale(1);
}

.failure-statistics-summary-bar__title {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.failure-statistics-summary-bar__eyebrow {
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.failure-statistics-summary-bar__heading {
  color: #111827;
  font-size: 15px;
  font-weight: 700;
}

.failure-statistics-summary-bar__metrics {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  overflow-x: auto;
  white-space: nowrap;
}

.failure-statistics-summary-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 999px;
  background: color-mix(in srgb, var(--el-fill-color-light) 86%, white);
  padding: 6px 10px;
  color: #64748b;
  font-size: 12px;
  line-height: 1;
}

.failure-statistics-summary-pill strong {
  color: #111827;
  font-size: 14px;
  font-weight: 700;
}

.failure-statistics-summary-pill.warning {
  border-color: color-mix(in srgb, var(--el-color-primary) 22%, transparent);
  background: color-mix(in srgb, var(--el-color-primary-light-9) 76%, white);
}

.failure-statistics-hero {
  display: grid;
  flex: none;
  gap: 20px;
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 18%, transparent);
  border-radius: 20px;
  background:
    radial-gradient(
      circle at top right,
      color-mix(in srgb, var(--el-color-primary) 16%, transparent),
      transparent 32%
    ),
    linear-gradient(
      135deg,
      color-mix(in srgb, var(--el-color-primary-light-9) 88%, white) 0%,
      color-mix(in srgb, var(--el-color-primary-light-8) 52%, white) 48%,
      #ffffff 100%
    );
  padding: 24px;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
}

.failure-statistics-hero__eyebrow {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.failure-statistics-hero__title {
  margin-top: 10px;
  color: #1f2937;
  font-size: 32px;
  font-weight: 700;
  line-height: 1.15;
}

.failure-statistics-hero__desc {
  margin-top: 10px;
  max-width: 760px;
  color: #64748b;
  font-size: 14px;
  line-height: 1.7;
}

.failure-statistics-hero__metrics {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.failure-statistics-metric-card {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  padding: 18px;
  backdrop-filter: blur(8px);
}

.failure-statistics-metric-card.warning {
  border-color: color-mix(in srgb, var(--el-color-primary) 24%, transparent);
  background: color-mix(in srgb, var(--el-color-primary-light-9) 76%, white);
}

.failure-statistics-metric-card__label {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.failure-statistics-metric-card__value {
  margin-top: 10px;
  color: #111827;
  font-size: 34px;
  font-weight: 700;
  line-height: 1;
}

.failure-statistics-metric-card__hint {
  margin-top: 8px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.failure-statistics-tabs :deep(.el-tabs__content) {
  min-height: 0;
  overflow: visible;
}

.failure-statistics-tabs :deep(.el-tab-pane) {
  min-height: 0;
}

.failure-statistics-chart-pane {
  min-height: 320px;
}

.failure-statistics-table-pane {
  display: flex;
  min-height: 0;
  flex-direction: column;
}

.failure-statistics-table-card {
  height: clamp(520px, 68vh, 760px);
}

.failure-statistics-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.failure-statistics-card-header__title {
  color: #1f2937;
  font-size: 16px;
  font-weight: 700;
}

.failure-statistics-card-header__desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.failure-statistics-note-grid {
  display: grid;
  gap: 12px;
}

.failure-statistics-note-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  border: 1px solid var(--el-border-color-light);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  padding: 14px;
}

.failure-statistics-note-item .title {
  color: #1f2937;
  font-size: 14px;
  font-weight: 600;
}

.failure-statistics-note-item .desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.dot {
  display: inline-flex;
  width: 12px;
  height: 12px;
  margin-top: 4px;
  border-radius: 999px;
  flex: none;
}

.dot.configured {
  background: #2f9e44;
}

.dot.pending {
  background: #f59f00;
}

.dot.skipped {
  background: #94a3b8;
}

.failure-statistics-pie-card {
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.96),
    color-mix(in srgb, var(--el-color-primary-light-9) 38%, white)
  );
}

.failure-statistics-status-cell {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-align: left;
}

.failure-statistics-status-light {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  box-shadow: 0 0 0 4px rgba(15, 23, 42, 0.04);
}

.failure-statistics-status-label {
  color: #1f2937;
  font-size: 13px;
  font-weight: 700;
}

.failure-statistics-status-hint {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

@media (min-width: 1024px) {
  .failure-statistics-hero {
    grid-template-columns: minmax(0, 1.2fr) minmax(340px, 0.8fr);
    align-items: center;
  }
}

@media (max-width: 768px) {
  .failure-statistics-page {
    padding-right: 0;
  }

  .failure-statistics-summary-bar {
    flex-direction: column;
    align-items: flex-start;
    padding: 10px 12px;
  }

  .failure-statistics-summary-bar__metrics {
    width: 100%;
  }

  .failure-statistics-hero {
    padding: 18px;
  }

  .failure-statistics-table-card {
    height: 560px;
  }
}
</style>
