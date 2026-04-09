<script lang="ts" setup>
import type { ProductStatisticsTabKey } from './data';

import type {
  FailureModeProductStatisticsOverviewItem,
  FailureModeProductStatisticsSubsystemRow,
  FailureModeProductStatisticsSummary,
} from '#/api/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, nextTick, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElCard,
  ElEmpty,
  ElMessage,
  ElOption,
  ElSelect,
  ElTabPane,
  ElTabs,
} from 'element-plus';

import {
  getFailureModeProductStatisticsSummaryApi,
  listFailureModeProductStatisticsOverviewApi,
  listFailureModeProductStatisticsSubsystemOptionsApi,
  listFailureModeProductStatisticsSubsystemsApi,
} from '#/api/failure_mode';
import { useZqTable } from '#/components/zq-table';

import StatisticsBarChart from '../statistics/components/StatisticsBarChart.vue';
import StatisticsPieChart from '../statistics/components/StatisticsPieChart.vue';
import {
  createEmptyProductStatisticsSummary,
  formatPercent,
  productStatisticsPieCards,
  productStatisticsTabs,
  resolveStatusLightMeta,
  useProductStatisticsSubsystemColumns,
} from './data';

defineOptions({ name: 'FailureModeProductStatisticsPage' });

interface GridQueryContext {
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const activeTab = ref<ProductStatisticsTabKey>('charts');
const pageScrollTop = ref(0);
const overviewLoading = ref(false);
const summaryLoading = ref(false);
const subsystemOptionsLoading = ref(false);
const selectedProductIds = ref<string[]>([]);
const selectedSubsystems = ref<string[]>([]);
const overviewItems = ref<FailureModeProductStatisticsOverviewItem[]>([]);
const subsystemOptions = ref<string[]>([]);
const summary = ref<FailureModeProductStatisticsSummary>(
  createEmptyProductStatisticsSummary(),
);

const [SubsystemTable, subsystemTableApi] =
  useZqTable<FailureModeProductStatisticsSubsystemRow>({
    gridOptions: {
      border: true,
      columns:
        useProductStatisticsSubsystemColumns() as ZqTableGridOptions<FailureModeProductStatisticsSubsystemRow>['columns'],
      proxyConfig: {
        autoLoad: false,
        ajax: {
          query: async ({ page }: GridQueryContext) => {
            return listFailureModeProductStatisticsSubsystemsApi({
              page: page.currentPage,
              pageSize: page.pageSize,
              product_ids: selectedProductIds.value,
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

const visibleProductCount = computed(() => overviewItems.value.length);

const selectedProductItems = computed(() => {
  if (selectedProductIds.value.length === 0) {
    return overviewItems.value;
  }
  const selectedSet = new Set(selectedProductIds.value);
  return overviewItems.value.filter((item) => selectedSet.has(item.product_id));
});

const selectedProductCount = computed(() => selectedProductItems.value.length);

const selectionLabel = computed(() => {
  if (selectedProductIds.value.length === 0) {
    return '全部平台项目';
  }
  if (selectedProductIds.value.length === 1) {
    return selectedProductItems.value[0]?.product_name || '全部平台项目';
  }
  return `已选 ${selectedProductIds.value.length} 个平台项目`;
});

const selectedBaselineCount = computed(() => {
  return selectedProductItems.value.reduce((sum, item) => {
    return sum + Number(item.baseline_failure_mode_count || 0);
  }, 0);
});

const selectedLandedCount = computed(() => {
  return selectedProductItems.value.reduce((sum, item) => {
    return sum + Number(item.landed_failure_mode_count || 0);
  }, 0);
});

const selectedPendingCount = computed(() => {
  return selectedProductItems.value.reduce((sum, item) => {
    return sum + Number(item.pending_failure_mode_count || 0);
  }, 0);
});

const selectedPendingRate = computed(() => {
  if (selectedBaselineCount.value <= 0) {
    return 0;
  }
  return Number(
    ((selectedPendingCount.value / selectedBaselineCount.value) * 100).toFixed(
      2,
    ),
  );
});

const totalSubsystemCount = computed(() => {
  return (summary.value.subsystem_counts || []).length;
});

const showSummaryBar = computed(() => pageScrollTop.value > 96);

function handlePageScroll(event: Event) {
  const target = event.target as HTMLElement | null;
  pageScrollTop.value = Number(target?.scrollTop || 0);
}

function normalizeSelection(values: string[], allValues: string[]) {
  const allValueSet = new Set(allValues);
  const normalized: string[] = [];
  const seen = new Set<string>();
  values.forEach((item) => {
    const text = String(item || '').trim();
    if (!text || seen.has(text) || !allValueSet.has(text)) {
      return;
    }
    seen.add(text);
    normalized.push(text);
  });
  if (normalized.length === 0 || normalized.length === allValues.length) {
    return [];
  }
  return normalized;
}

async function loadOverview() {
  overviewLoading.value = true;
  try {
    overviewItems.value = await listFailureModeProductStatisticsOverviewApi();
    selectedProductIds.value = normalizeSelection(
      selectedProductIds.value,
      overviewItems.value.map((item) => item.product_id),
    );
  } finally {
    overviewLoading.value = false;
  }
}

async function loadSubsystemOptions() {
  subsystemOptionsLoading.value = true;
  try {
    subsystemOptions.value =
      await listFailureModeProductStatisticsSubsystemOptionsApi({
        product_ids: selectedProductIds.value,
      });
    selectedSubsystems.value = normalizeSelection(
      selectedSubsystems.value,
      subsystemOptions.value,
    );
  } finally {
    subsystemOptionsLoading.value = false;
  }
}

async function loadSummary() {
  summaryLoading.value = true;
  try {
    summary.value = await getFailureModeProductStatisticsSummaryApi({
      product_ids: selectedProductIds.value,
      subsystems: selectedSubsystems.value,
    });
  } finally {
    summaryLoading.value = false;
  }
}

async function reloadAnalysis() {
  if (overviewItems.value.length === 0) {
    summary.value = createEmptyProductStatisticsSummary();
    await subsystemTableApi.reload();
    return;
  }
  await Promise.all([loadSummary(), subsystemTableApi.reload()]);
}

async function handleProductSelectionChange(
  nextProductIds = selectedProductIds.value,
) {
  selectedProductIds.value = normalizeSelection(
    nextProductIds,
    overviewItems.value.map((item) => item.product_id),
  );
  try {
    await loadSubsystemOptions();
    await reloadAnalysis();
  } catch (error) {
    console.error(error);
    ElMessage.error('切换产品统计失败');
  }
}

async function handleSelectAllProducts() {
  await handleProductSelectionChange([]);
}

async function handleProductRowClick(productId: string) {
  await handleProductSelectionChange([productId]);
}

async function handleSubsystemChange(
  nextSubsystems = selectedSubsystems.value,
) {
  selectedSubsystems.value = normalizeSelection(
    nextSubsystems,
    subsystemOptions.value,
  );
  try {
    await reloadAnalysis();
  } catch (error) {
    console.error(error);
    ElMessage.error('切换子系统统计失败');
  }
}

async function initializePage() {
  await loadOverview();
  await loadSubsystemOptions();
  await reloadAnalysis();
}

onMounted(async () => {
  try {
    await initializePage();
  } catch (error) {
    console.error(error);
    ElMessage.error('加载产品故障统计失败');
  }
  await nextTick();
});
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div
      class="product-statistics-page flex h-full min-h-0 flex-col gap-4"
      @scroll.passive="handlePageScroll"
    >
      <div class="product-statistics-summary-anchor">
        <section
          class="product-statistics-summary-bar"
          :class="{ 'is-visible': showSummaryBar }"
        >
          <div class="product-statistics-summary-bar__title">
            <span class="product-statistics-summary-bar__eyebrow">
              Product Failure Analytics
            </span>
            <span class="product-statistics-summary-bar__heading">
              {{ selectionLabel }}
            </span>
          </div>
          <div class="product-statistics-summary-bar__metrics">
            <div class="product-statistics-summary-pill">
              <span>平台项目</span>
              <strong>{{ selectedProductCount }}</strong>
            </div>
            <div class="product-statistics-summary-pill">
              <span>当前基线</span>
              <strong>{{ selectedBaselineCount }}</strong>
            </div>
            <div class="product-statistics-summary-pill">
              <span>已落地故障</span>
              <strong>{{ selectedLandedCount }}</strong>
            </div>
            <div class="product-statistics-summary-pill warning">
              <span>待开展故障</span>
              <strong>{{ selectedPendingCount }}</strong>
            </div>
          </div>
        </section>
      </div>

      <section class="product-statistics-hero">
        <div>
          <div class="product-statistics-hero__eyebrow">
            Product Failure Analytics
          </div>
          <h1 class="product-statistics-hero__title">产品故障统计</h1>
          <p class="product-statistics-hero__desc">
            从产品视角追踪当前生效基线的显式落地成熟度，先看全产品概览，再下钻到子系统维度的待开展缺口。
          </p>
        </div>
        <div class="product-statistics-hero__metrics">
          <div class="product-statistics-metric-card">
            <div class="product-statistics-metric-card__label">可见产品</div>
            <div class="product-statistics-metric-card__value">
              {{ visibleProductCount }}
            </div>
            <div class="product-statistics-metric-card__hint">
              当前权限范围内可见的平台项目数量
            </div>
          </div>
          <div class="product-statistics-metric-card">
            <div class="product-statistics-metric-card__label">
              当前选中项目
            </div>
            <div class="product-statistics-metric-card__value">
              {{ selectedProductCount }}
            </div>
            <div class="product-statistics-metric-card__hint">
              默认全量展示，也支持单选和多选平台项目
            </div>
          </div>
          <div class="product-statistics-metric-card warning">
            <div class="product-statistics-metric-card__label">待开展率</div>
            <div class="product-statistics-metric-card__value">
              {{ formatPercent(selectedPendingRate) }}
            </div>
            <div class="product-statistics-metric-card__hint">
              按当前选中平台项目集合的基线故障模式加权计算
            </div>
          </div>
        </div>
      </section>

      <section class="product-overview-panel">
        <div class="product-overview-panel__header">
          <div>
            <div class="product-overview-panel__title">产品概览区</div>
            <div class="product-overview-panel__desc">
              仅展示平台项目。默认按全部平台项目聚合分析，也可以单选或多选切换到不同产品集合视角。
            </div>
          </div>
          <ElButton :loading="overviewLoading" @click="initializePage">
            刷新概览
          </ElButton>
        </div>

        <div class="product-overview-panel__controls">
          <ElButton
            plain
            :disabled="selectedProductIds.length === 0"
            @click="handleSelectAllProducts"
          >
            全选平台项目
          </ElButton>
          <ElSelect
            v-model="selectedProductIds"
            class="product-overview-panel__select"
            collapse-tags
            collapse-tags-tooltip
            filterable
            multiple
            clearable
            placeholder="全部平台项目"
            @change="handleProductSelectionChange"
            @clear="handleProductSelectionChange([])"
          >
            <ElOption
              v-for="item in overviewItems"
              :key="item.product_id"
              :label="item.product_name"
              :value="item.product_id"
            />
          </ElSelect>
          <div class="product-overview-panel__summary">
            当前视角：{{ selectionLabel }}
          </div>
        </div>

        <ElEmpty
          v-if="!overviewLoading && overviewItems.length === 0"
          description="当前权限范围内暂无产品统计数据"
        />

        <div
          v-else
          v-loading="overviewLoading"
          class="product-overview-table-wrap"
        >
          <div class="product-overview-table">
            <div class="product-overview-table__head">
              <span>产品</span>
              <span>主版本SE</span>
              <span>基线故障模式数</span>
              <span>已落地故障数</span>
              <span>待开展故障数</span>
              <span>待开展率</span>
              <span>状态灯</span>
            </div>
            <button
              v-for="item in overviewItems"
              :key="item.product_id"
              class="product-overview-table__row"
              :class="{
                'is-active': selectedProductIds.includes(item.product_id),
              }"
              type="button"
              @click="handleProductRowClick(item.product_id)"
            >
              <span class="product-overview-table__product">
                {{ item.product_name }}
              </span>
              <span>
                {{
                  item.owner_info?.name || item.owner_info?.username || '未配置'
                }}
              </span>
              <span>{{ item.baseline_failure_mode_count }}</span>
              <span>{{ item.landed_failure_mode_count }}</span>
              <span>{{ item.pending_failure_mode_count }}</span>
              <span>{{ formatPercent(item.pending_rate) }}</span>
              <span class="product-overview-table__lamp">
                <i
                  class="product-overview-table__lamp-dot"
                  :style="{
                    backgroundColor: resolveStatusLightMeta(item.status_light)
                      .color,
                  }"
                ></i>
                {{ resolveStatusLightMeta(item.status_light).label }}
              </span>
            </button>
          </div>
        </div>
      </section>

      <section class="product-analysis-panel">
        <div class="product-analysis-panel__header">
          <div>
            <div class="product-analysis-panel__title">产品分析区</div>
            <div class="product-analysis-panel__desc">
              图表与子系统表统一按当前选中的平台项目集合聚合，并支持对子系统再做单选或多选。
            </div>
          </div>
          <div class="product-analysis-panel__filters">
            <ElSelect
              v-model="selectedSubsystems"
              class="product-analysis-panel__select"
              collapse-tags
              collapse-tags-tooltip
              filterable
              multiple
              clearable
              :loading="subsystemOptionsLoading"
              placeholder="全部子系统"
              @change="handleSubsystemChange"
              @clear="handleSubsystemChange([])"
            >
              <ElOption
                v-for="item in subsystemOptions"
                :key="item"
                :label="item"
                :value="item"
              />
            </ElSelect>
            <ElButton plain @click="handleSubsystemChange([])">
              全选子系统
            </ElButton>
          </div>
        </div>

        <ElEmpty
          v-if="overviewItems.length === 0"
          description="暂无可分析的平台项目数据"
        />

        <template v-else>
          <div class="product-analysis-summary">
            <div class="product-analysis-summary__item">
              <span>分析视角</span>
              <strong>{{ selectionLabel }}</strong>
            </div>
            <div class="product-analysis-summary__item">
              <span>已选项目</span>
              <strong>{{ selectedProductCount }}</strong>
            </div>
            <div class="product-analysis-summary__item">
              <span>当前基线故障模式数</span>
              <strong>{{ selectedBaselineCount }}</strong>
            </div>
            <div class="product-analysis-summary__item">
              <span>已落地故障数</span>
              <strong>{{ selectedLandedCount }}</strong>
            </div>
            <div class="product-analysis-summary__item warning">
              <span>待开展率</span>
              <strong>{{ formatPercent(selectedPendingRate) }}</strong>
            </div>
            <div class="product-analysis-summary__item">
              <span>子系统维度</span>
              <strong>{{ totalSubsystemCount }}</strong>
            </div>
          </div>

          <ElTabs
            v-model="activeTab"
            class="border-border bg-card rounded-xl border p-4 shadow-sm"
          >
            <ElTabPane
              v-for="tab in productStatisticsTabs"
              :key="tab.key"
              :label="tab.label"
              :name="tab.key"
            >
              <template v-if="tab.key === 'charts'">
                <div class="product-statistics-chart-pane">
                  <div
                    class="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.75fr)]"
                  >
                    <ElCard
                      class="border-none !bg-transparent shadow-none"
                      v-loading="summaryLoading"
                    >
                      <div class="product-statistics-card-header">
                        <div>
                          <div class="product-statistics-card-header__title">
                            子系统故障模式数量
                          </div>
                          <div class="product-statistics-card-header__desc">
                            当前选中平台项目集合下，各子系统的基线故障模式数量分布。
                          </div>
                        </div>
                      </div>
                      <StatisticsBarChart
                        :data="summary.subsystem_counts"
                        title="基线故障模式数"
                      />
                    </ElCard>

                    <ElCard
                      class="border-none !bg-transparent shadow-none"
                      v-loading="summaryLoading"
                    >
                      <div class="product-statistics-card-header">
                        <div>
                          <div class="product-statistics-card-header__title">
                            看板说明
                          </div>
                          <div class="product-statistics-card-header__desc">
                            当前页面只看产品级显式落地结果。故障模式本身是二态，其余能力按“已落地
                            / 待开展 / 不涉及”三态推导。
                          </div>
                        </div>
                      </div>
                      <div class="product-statistics-note-grid">
                        <div class="product-statistics-note-item">
                          <span class="dot configured"></span>
                          <div>
                            <div class="title">已落地</div>
                            <div class="desc">
                              当前维度为必配，且当前绑定的全部资源都显式标记为已落地。
                            </div>
                          </div>
                        </div>
                        <div class="product-statistics-note-item">
                          <span class="dot pending"></span>
                          <div>
                            <div class="title">待开展</div>
                            <div class="desc">
                              当前维度为必配，但存在未落地资源，或当前还没有补齐对应资源。
                            </div>
                          </div>
                        </div>
                        <div class="product-statistics-note-item">
                          <span class="dot skipped"></span>
                          <div>
                            <div class="title">不涉及</div>
                            <div class="desc">
                              当前维度未勾选必配，因此不纳入待开展统计。
                            </div>
                          </div>
                        </div>
                      </div>
                    </ElCard>
                  </div>

                  <div class="mt-4 grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
                    <ElCard
                      v-for="card in productStatisticsPieCards"
                      :key="card.key"
                      class="product-statistics-pie-card border-none shadow-none"
                      v-loading="summaryLoading"
                    >
                      <div class="product-statistics-card-header mb-3">
                        <div>
                          <div class="product-statistics-card-header__title">
                            {{ card.title }}
                          </div>
                          <div class="product-statistics-card-header__desc">
                            {{ card.subtitle }}
                          </div>
                        </div>
                      </div>
                      <StatisticsPieChart
                        :data="summary[card.key]"
                        :title="card.title"
                      />
                    </ElCard>
                  </div>
                </div>
              </template>

              <template v-else>
                <div class="product-statistics-table-pane">
                  <div class="product-statistics-table-card">
                    <SubsystemTable class="h-full min-h-0 flex-1">
                      <template #toolbar-actions>
                        <ElButton type="primary" @click="reloadAnalysis">
                          刷新分析
                        </ElButton>
                      </template>
                      <template #cell-status_light="{ row }">
                        <div class="product-statistics-status-cell">
                          <span
                            class="product-statistics-status-light"
                            :style="{
                              backgroundColor: resolveStatusLightMeta(
                                row.status_light,
                              ).color,
                            }"
                          ></span>
                          <div>
                            <div class="product-statistics-status-label">
                              {{
                                resolveStatusLightMeta(row.status_light).label
                              }}
                            </div>
                            <div class="product-statistics-status-hint">
                              待开展 {{ row.pending_failure_mode_count }} /
                              {{ row.baseline_failure_mode_count }} ·
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
        </template>
      </section>
    </div>
  </Page>
</template>

<style scoped>
.product-statistics-page {
  min-height: 100%;
  overflow-y: auto;
  padding-right: 4px;
  overscroll-behavior: contain;
}

.product-statistics-summary-anchor {
  position: sticky;
  top: 0;
  z-index: 14;
  height: 0;
}

.product-statistics-summary-bar {
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

.product-statistics-summary-bar.is-visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0) scale(1);
}

.product-statistics-summary-bar__title {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.product-statistics-summary-bar__eyebrow {
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.product-statistics-summary-bar__heading {
  color: #111827;
  font-size: 15px;
  font-weight: 700;
}

.product-statistics-summary-bar__metrics {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  overflow-x: auto;
  white-space: nowrap;
}

.product-statistics-summary-pill {
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

.product-statistics-summary-pill strong {
  color: #111827;
  font-size: 14px;
  font-weight: 700;
}

.product-statistics-summary-pill.warning {
  border-color: color-mix(in srgb, var(--el-color-primary) 22%, transparent);
  background: color-mix(in srgb, var(--el-color-primary-light-9) 76%, white);
}

.product-statistics-hero {
  display: grid;
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

.product-statistics-hero__eyebrow {
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.product-statistics-hero__title {
  margin-top: 10px;
  color: #1f2937;
  font-size: 32px;
  font-weight: 700;
  line-height: 1.15;
}

.product-statistics-hero__desc {
  margin-top: 10px;
  max-width: 760px;
  color: #64748b;
  font-size: 14px;
  line-height: 1.7;
}

.product-statistics-hero__metrics {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.product-statistics-metric-card {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  padding: 18px;
  backdrop-filter: blur(8px);
}

.product-statistics-metric-card.warning {
  border-color: color-mix(in srgb, var(--el-color-primary) 24%, transparent);
  background: color-mix(in srgb, var(--el-color-primary-light-9) 76%, white);
}

.product-statistics-metric-card__label {
  color: #64748b;
  font-size: 12px;
}

.product-statistics-metric-card__value {
  margin-top: 10px;
  color: #0f172a;
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
}

.product-statistics-metric-card__hint {
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.product-overview-panel,
.product-analysis-panel {
  border: 1px solid var(--el-border-color-light);
  border-radius: 20px;
  background: var(--el-bg-color);
  padding: 18px;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.product-overview-panel__header,
.product-analysis-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.product-overview-panel__controls {
  display: grid;
  gap: 12px;
  margin-top: 16px;
  grid-template-columns: auto minmax(0, 1fr) auto;
}

.product-overview-panel__select {
  width: 100%;
}

.product-overview-panel__summary {
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

.product-overview-panel__title,
.product-analysis-panel__title {
  color: #111827;
  font-size: 18px;
  font-weight: 700;
}

.product-overview-panel__desc,
.product-analysis-panel__desc {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.product-overview-grid {
  display: grid;
  gap: 14px;
  margin-top: 16px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.product-overview-table-wrap {
  margin-top: 16px;
}

.product-overview-table {
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
}

.product-overview-table__head,
.product-overview-table__row {
  display: grid;
  align-items: center;
  gap: 12px;
  grid-template-columns:
    minmax(180px, 1.4fr)
    140px 140px 140px 140px 120px 100px;
}

.product-overview-table__head {
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(248, 250, 252, 0.88);
  padding: 14px 18px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.product-overview-table__row {
  width: 100%;
  border: 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  background: transparent;
  padding: 14px 18px;
  color: #334155;
  font-size: 13px;
  text-align: left;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease;
}

.product-overview-table__row:last-child {
  border-bottom: none;
}

.product-overview-table__row:hover,
.product-overview-table__row.is-active {
  background: color-mix(in srgb, var(--el-color-primary-light-9) 70%, white);
}

.product-overview-table__product {
  color: #111827;
  font-weight: 700;
}

.product-overview-table__lamp {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.product-overview-table__lamp-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.product-overview-card {
  appearance: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 18px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.98),
    rgba(248, 250, 252, 0.96)
  );
  padding: 18px;
  text-align: left;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.product-overview-card:hover,
.product-overview-card.is-active {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--el-color-primary) 40%, transparent);
  box-shadow: 0 18px 32px rgba(37, 99, 235, 0.1);
}

.product-overview-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.product-overview-card__title {
  color: #111827;
  font-size: 18px;
  font-weight: 700;
}

.product-overview-card__owner {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.product-overview-card__lamp {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 12px;
  white-space: nowrap;
}

.product-overview-card__lamp-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.7);
}

.product-overview-card__metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.product-overview-card__metric {
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.92);
  padding: 12px;
}

.product-overview-card__metric.warning {
  background: color-mix(in srgb, var(--el-color-primary-light-9) 70%, white);
}

.product-overview-card__metric span {
  display: block;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.product-overview-card__metric strong {
  display: block;
  margin-top: 8px;
  color: #0f172a;
  font-size: 22px;
  font-weight: 700;
}

.product-analysis-panel {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 16px;
}

.product-analysis-panel__filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.product-analysis-panel__select {
  width: 220px;
}

.product-analysis-panel__select--product {
  width: 280px;
}

.product-analysis-summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.product-analysis-summary__item {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.82);
  padding: 14px 16px;
}

.product-analysis-summary__item.warning {
  border-color: color-mix(in srgb, var(--el-color-primary) 20%, transparent);
  background: color-mix(in srgb, var(--el-color-primary-light-9) 72%, white);
}

.product-analysis-summary__item span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.product-analysis-summary__item strong {
  display: block;
  margin-top: 8px;
  color: #111827;
  font-size: 18px;
  font-weight: 700;
}

.product-statistics-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.product-statistics-card-header__title {
  color: #111827;
  font-size: 16px;
  font-weight: 700;
}

.product-statistics-card-header__desc {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.product-statistics-note-grid {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}

.product-statistics-note-item {
  display: flex;
  gap: 12px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.82);
  padding: 14px;
}

.product-statistics-note-item .dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  margin-top: 4px;
  flex: none;
}

.product-statistics-note-item .dot.configured {
  background: #16a34a;
}

.product-statistics-note-item .dot.pending {
  background: #d97706;
}

.product-statistics-note-item .dot.skipped {
  background: #94a3b8;
}

.product-statistics-note-item .title {
  color: #111827;
  font-size: 14px;
  font-weight: 700;
}

.product-statistics-note-item .desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.product-statistics-table-pane,
.product-statistics-table-card {
  min-height: 0;
}

.product-statistics-table-card {
  display: flex;
  min-height: 520px;
  flex: 1;
}

.product-statistics-status-cell {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.product-statistics-status-light {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.08);
}

.product-statistics-status-label {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.product-statistics-status-hint {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 1024px) {
  .product-statistics-summary-bar,
  .product-overview-panel__header,
  .product-analysis-panel__header {
    flex-direction: column;
    align-items: stretch;
  }

  .product-overview-card__metrics {
    grid-template-columns: 1fr;
  }
}
</style>
