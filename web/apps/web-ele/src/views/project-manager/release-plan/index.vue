<script lang="ts" setup>
import type {
  ReleasePlanFilterParams,
  ReleasePlanItem,
  ReleasePlanProjectBoard,
  ReleasePlanProjectGroup,
  ReleasePlanVersionWeeklyTrend,
} from '#/api/project-manager/release-plan';
import type { EchartsUIType } from '@vben/plugins/echarts';

import { computed, nextTick, reactive, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { ElEmpty, ElSegmented, ElTable, ElTableColumn, ElTag } from 'element-plus';

import { getReleasePlanProjectBoardApi } from '#/api/project-manager/release-plan';
import { useZqTable } from '#/components/zq-table';

import ReleasePlanHeaderFilter from './components/ReleasePlanHeaderFilter.vue';
import { useReleasePlanColumns, VERSION_TYPE_OPTIONS } from './data';

defineOptions({ name: 'ProjectReleasePlanDashboard' });

type Scenario = 'cockpit' | 'vehicle';

interface ReleasePlanQueryParams {
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const scenario = ref<Scenario>('vehicle');
type HeaderFilterKey =
  | 'branch_name'
  | 'keyword'
  | 'platform_keyword'
  | 'vehicle_keyword'
  | 'version_type';

const filters = reactive<ReleasePlanFilterParams>({
  keyword: '',
  branch_name: '',
  version_type: '',
  platform_keyword: '',
  vehicle_keyword: '',
});
const dateRange = ref<string[]>([]);
const boardData = ref<ReleasePlanProjectBoard>({
  items: [],
  total: 0,
  version_weekly_trend: [],
  weekly_trend: [],
});

const releaseTrendChartRef = ref<EchartsUIType>();
const versionTrendChartRef = ref<EchartsUIType>();
const { renderEcharts: renderReleaseTrendChart } = useEcharts(releaseTrendChartRef);
const { renderEcharts: renderVersionTrendChart } = useEcharts(versionTrendChartRef);

const scenarioOptions = [
  { label: '车控域', value: 'vehicle' },
  { label: '座舱域', value: 'cockpit' },
];

const scenarioLabel = computed(() => (scenario.value === 'vehicle' ? '车控域' : '座舱域'));
const totalProjectCount = computed(() => boardData.value.total || 0);
const totalPlanCount = computed(() =>
  (boardData.value.items || []).reduce((sum, item) => sum + Number(item.plan_count || 0), 0),
);
const totalBranchCount = computed(() =>
  (boardData.value.items || []).reduce((sum, item) => sum + Number(item.branch_count || 0), 0),
);

function getQueryParams(page: { currentPage: number; pageSize: number }) {
  const [start, end] = dateRange.value || [];
  return {
    ...filters,
    page: page.currentPage,
    pageSize: page.pageSize,
    release_date_end: end || undefined,
    release_date_start: start || undefined,
    scenario: scenario.value,
  };
}

function reloadFromFirstPage() {
  gridApi.pagination.currentPage = 1;
  gridApi.reload();
}

function applyHeaderFilter() {
  reloadFromFirstPage();
}

function clearFilter(key: HeaderFilterKey) {
  filters[key] = undefined;
  reloadFromFirstPage();
}

function clearDateFilter() {
  dateRange.value = [];
  reloadFromFirstPage();
}

function formatList(values?: string[], limit = 3) {
  const list = (values || []).filter(Boolean);
  if (list.length === 0) {
    return { hidden: 0, shown: ['-'] };
  }
  return {
    hidden: Math.max(list.length - limit, 0),
    shown: list.slice(0, limit),
  };
}

function formatManagers(row: ReleasePlanProjectGroup) {
  return (row.manager_names || []).join('、') || '-';
}

function formatDomain(row: ReleasePlanProjectGroup) {
  return row.project_domain || (scenario.value === 'vehicle' ? '车控域' : '座舱域');
}

function formatVehicles(row: { release_vehicles?: string[] }) {
  return (row.release_vehicles || []).join('、') || '-';
}

function branchSpanMethod({ column, row, rowIndex }: any, plans: ReleasePlanItem[]) {
  const field = String(column.property || column.prop || '');
  if (field !== 'branch_name') {
    return { colspan: 1, rowspan: 1 };
  }
  const previous = plans[rowIndex - 1];
  if (previous && previous.branch_name === row.branch_name) {
    return { colspan: 0, rowspan: 0 };
  }
  let rowspan = 1;
  for (let index = rowIndex + 1; index < plans.length; index += 1) {
    if (plans[index]?.branch_name === row.branch_name) {
      rowspan += 1;
    } else {
      break;
    }
  }
  return { colspan: 1, rowspan };
}

function renderEmptyChart(render: (options: any) => void, title: string) {
  render({
    graphic: {
      left: 'center',
      style: {
        fill: '#94a3b8',
        fontSize: 12,
        text: '暂无匹配发布计划',
      },
      top: 'middle',
      type: 'text',
    },
    title: {
      left: 8,
      text: title,
      textStyle: { color: '#334155', fontSize: 13, fontWeight: 700 },
    },
  });
}

function renderCharts() {
  const weeklyTrend = boardData.value.weekly_trend || [];
  if (weeklyTrend.length === 0) {
    renderEmptyChart(renderReleaseTrendChart, '未来发布数量趋势');
  } else {
    renderReleaseTrendChart({
      color: ['#2563eb'],
      grid: { bottom: 26, containLabel: true, left: 10, right: 10, top: 34 },
      title: {
        left: 8,
        text: '未来发布数量趋势',
        textStyle: { color: '#334155', fontSize: 13, fontWeight: 700 },
      },
      tooltip: { trigger: 'axis' },
      xAxis: {
        axisLabel: { color: '#64748b', fontSize: 10 },
        axisTick: { show: false },
        data: weeklyTrend.map((item) => item.week),
        type: 'category',
      },
      yAxis: {
        axisLabel: { color: '#64748b', fontSize: 10 },
        splitLine: { lineStyle: { color: '#e2e8f0' } },
        type: 'value',
      },
      series: [
        {
          barMaxWidth: 18,
          data: weeklyTrend.map((item) => item.count),
          itemStyle: { borderRadius: [4, 4, 0, 0] },
          type: 'bar',
        },
      ],
    });
  }

  const versionTrend = boardData.value.version_weekly_trend || [];
  if (versionTrend.length === 0) {
    renderEmptyChart(renderVersionTrendChart, '版本类型周趋势');
    return;
  }
  const weeks = Array.from(new Set(versionTrend.map((item) => item.week)));
  const versionTypes = Array.from(new Set(versionTrend.map((item) => item.version_type)));
  const countMap = new Map(
    versionTrend.map((item: ReleasePlanVersionWeeklyTrend) => [
      `${item.week}__${item.version_type}`,
      item.count,
    ]),
  );
  renderVersionTrendChart({
    color: ['#0f766e', '#2563eb', '#f59e0b', '#dc2626', '#7c3aed', '#64748b'],
    grid: { bottom: 26, containLabel: true, left: 10, right: 10, top: 34 },
    legend: {
      itemHeight: 7,
      itemWidth: 8,
      right: 6,
      textStyle: { color: '#64748b', fontSize: 10 },
      top: 4,
    },
    title: {
      left: 8,
      text: '版本类型周趋势',
      textStyle: { color: '#334155', fontSize: 13, fontWeight: 700 },
    },
    tooltip: { trigger: 'axis' },
    xAxis: {
      axisLabel: { color: '#64748b', fontSize: 10 },
      axisTick: { show: false },
      data: weeks,
      type: 'category',
    },
    yAxis: {
      axisLabel: { color: '#64748b', fontSize: 10 },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      type: 'value',
    },
    series: versionTypes.map((versionType) => ({
      barMaxWidth: 16,
      data: weeks.map((week) => countMap.get(`${week}__${versionType}`) || 0),
      name: versionType,
      stack: 'version',
      type: 'bar',
    })),
  });
}

const [Grid, gridApi] = useZqTable<ReleasePlanProjectGroup>({
  showSearchForm: false,
  gridOptions: {
    border: true,
    columns: useReleasePlanColumns(),
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page }: ReleasePlanQueryParams) => {
          const response = await getReleasePlanProjectBoardApi(getQueryParams(page));
          boardData.value = response;
          await nextTick();
          renderCharts();
          return {
            items: response.items || [],
            total: response.total || 0,
          };
        },
      },
    },
    rowKey: 'project_id',
    stripe: true,
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  },
});

watch(scenario, () => {
  reloadFromFirstPage();
});
</script>

<template>
  <Page auto-content-height>
    <div class="release-board h-full min-h-0">
      <section class="release-board__analysis">
        <div class="release-board__domain">
          <div class="release-board__title">发布计划看板</div>
          <ElSegmented
            v-model="scenario"
            :options="scenarioOptions"
            size="small"
            class="release-board__segmented"
          />
          <div class="release-board__metrics">
            <div class="release-board__metric">
              <span>项目</span>
              <strong>{{ totalProjectCount }}</strong>
            </div>
            <div class="release-board__metric">
              <span>分支</span>
              <strong>{{ totalBranchCount }}</strong>
            </div>
            <div class="release-board__metric">
              <span>计划</span>
              <strong>{{ totalPlanCount }}</strong>
            </div>
          </div>
          <div class="release-board__hint">{{ scenarioLabel }} · 按项目分页</div>
        </div>
        <div class="release-board__chart">
          <EchartsUI ref="releaseTrendChartRef" height="128px" />
        </div>
        <div class="release-board__chart">
          <EchartsUI ref="versionTrendChartRef" height="128px" />
        </div>
      </section>

      <Grid class="release-board__grid">
        <template #header-project_name>
          <ReleasePlanHeaderFilter
            v-model="filters.keyword"
            label="项目/编码"
            placeholder="项目、编码、分支"
            @apply="applyHeaderFilter"
            @clear="clearFilter('keyword')"
          />
        </template>
        <template #header-branch_names>
          <ReleasePlanHeaderFilter
            v-model="filters.branch_name"
            label="分支数"
            placeholder="分支名"
            @apply="applyHeaderFilter"
            @clear="clearFilter('branch_name')"
          />
        </template>
        <template #header-next_release_date>
          <ReleasePlanHeaderFilter
            v-model="dateRange"
            label="最近发布"
            type="date-range"
            @apply="applyHeaderFilter"
            @clear="clearDateFilter"
          />
        </template>
        <template #header-version_type>
          <ReleasePlanHeaderFilter
            v-model="filters.version_type"
            label="版本类型"
            type="select-create"
            :options="VERSION_TYPE_OPTIONS"
            @apply="applyHeaderFilter"
            @clear="clearFilter('version_type')"
          />
        </template>
        <template #header-platform_name>
          <ReleasePlanHeaderFilter
            v-model="filters.platform_keyword"
            label="发布平台"
            placeholder="平台关键字"
            @apply="applyHeaderFilter"
            @clear="clearFilter('platform_keyword')"
          />
        </template>
        <template #header-release_vehicles>
          <ReleasePlanHeaderFilter
            v-model="filters.vehicle_keyword"
            label="车型摘要"
            placeholder="车型关键字"
            @apply="applyHeaderFilter"
            @clear="clearFilter('vehicle_keyword')"
          />
        </template>

        <template #cell-project_name="{ row }">
          <div class="project-cell">
            <div class="project-cell__name">{{ row.project_name || '-' }}</div>
            <div class="project-cell__meta">
              <span>{{ row.project_code || '-' }}</span>
              <ElTag size="small" effect="plain" type="info">{{ formatDomain(row) }}</ElTag>
            </div>
          </div>
        </template>
        <template #cell-manager_names="{ row }">
          <span class="muted-text">{{ formatManagers(row) }}</span>
        </template>
        <template #cell-branch_count="{ row }">
          <span class="count-pill">{{ row.branch_count }} 分支</span>
        </template>
        <template #cell-plan_count="{ row }">
          <span class="count-pill is-strong">{{ row.plan_count }} 计划</span>
        </template>
        <template #cell-next_release_date="{ row }">
          <div class="date-stack">
            <strong>{{ row.next_release_date || row.latest_release_date || '-' }}</strong>
            <span v-if="row.next_release_date">next</span>
            <span v-else-if="row.latest_release_date">latest</span>
          </div>
        </template>
        <template #cell-version_types="{ row }">
          <div class="tag-line">
            <ElTag
              v-for="item in formatList(row.version_types, 3).shown"
              :key="item"
              size="small"
              effect="plain"
            >
              {{ item }}
            </ElTag>
            <span v-if="formatList(row.version_types, 3).hidden" class="more-text">
              +{{ formatList(row.version_types, 3).hidden }}
            </span>
          </div>
        </template>
        <template #cell-platform_names="{ row }">
          <div class="summary-text">{{ formatList(row.platform_names, 2).shown.join('、') }}</div>
        </template>
        <template #cell-release_vehicles="{ row }">
          <div class="summary-text">
            {{ formatList(row.release_vehicles, 4).shown.join('、') }}
            <span v-if="formatList(row.release_vehicles, 4).hidden" class="more-text">
              +{{ formatList(row.release_vehicles, 4).hidden }}
            </span>
          </div>
        </template>

        <template #expand_content="{ row }">
          <div class="release-detail">
            <ElTable
              v-if="row.plans?.length"
              :data="row.plans"
              border
              size="small"
              :span-method="(scope: any) => branchSpanMethod(scope, row.plans)"
              class="release-detail__table"
            >
              <ElTableColumn prop="branch_name" label="分支名" min-width="180" />
              <ElTableColumn prop="release_date" label="发布日期" width="118" align="center" />
              <ElTableColumn
                prop="version_type_label"
                label="版本类型"
                width="118"
                align="center"
              />
              <ElTableColumn prop="platform_name" label="平台" min-width="160" />
              <ElTableColumn label="车型" min-width="260">
                <template #default="{ row: plan }">
                  {{ formatVehicles(plan) }}
                </template>
              </ElTableColumn>
            </ElTable>
            <ElEmpty v-else :image-size="44" description="暂无发布计划" />
          </div>
        </template>
      </Grid>
    </div>
  </Page>
</template>

<style scoped>
.release-board {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  padding: 0;
}

.release-board__analysis {
  display: grid;
  grid-template-columns: 240px minmax(280px, 1fr) minmax(280px, 1fr);
  gap: 8px;
  height: 160px;
  min-height: 160px;
  border: 1px solid #dbe4ef;
  border-radius: 6px;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
  overflow: hidden;
  padding: 8px;
}

.release-board__domain {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
  border-right: 1px solid #e2e8f0;
  padding: 4px 8px 4px 2px;
}

.release-board__title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 800;
  line-height: 20px;
}

.release-board__segmented {
  width: 172px;
}

.release-board__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.release-board__metric {
  min-width: 0;
  border: 1px solid #dbe4ef;
  border-radius: 6px;
  background: #fff;
  padding: 7px 6px;
}

.release-board__metric span {
  display: block;
  color: #64748b;
  font-size: 11px;
  line-height: 14px;
}

.release-board__metric strong {
  display: block;
  color: #0f172a;
  font-size: 18px;
  line-height: 22px;
}

.release-board__hint {
  color: #64748b;
  font-size: 12px;
}

.release-board__chart {
  min-width: 0;
  height: 144px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  overflow: hidden;
  padding: 4px;
}

.release-board__chart :deep(> div) {
  width: 100%;
  height: 128px;
}

.release-board__grid {
  min-height: 0;
  flex: 1;
}

.release-board__grid :deep(.zq-table-toolbar) {
  min-height: 34px;
  padding: 6px 12px;
}

.release-board__grid :deep(.zq-table-header th.el-table__cell) {
  background: #f8fafc;
}

.release-board__grid :deep(.zq-table-header .cell) {
  min-height: 30px;
  line-height: 18px;
}

.release-board__grid :deep(.el-table .cell) {
  line-height: 18px;
}

.release-board__grid :deep(.el-table__expanded-cell) {
  background: #f8fafc;
  padding: 8px 12px !important;
}

.project-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  min-width: 0;
}

.project-cell__name {
  overflow: hidden;
  max-width: 100%;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-cell__meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  color: #64748b;
  font-size: 11px;
}

.muted-text,
.summary-text {
  overflow: hidden;
  color: #475569;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.count-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  padding: 0 8px;
}

.count-pill.is-strong {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}

.date-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.date-stack strong {
  color: #0f172a;
  font-size: 12px;
}

.date-stack span {
  color: #94a3b8;
  font-size: 10px;
  text-transform: uppercase;
}

.tag-line {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  max-width: 100%;
}

.more-text {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.release-detail {
  border: 1px solid #dbe4ef;
  border-radius: 6px;
  background: #fff;
  padding: 6px;
}

.release-detail__table :deep(.el-table__cell) {
  padding: 5px 0;
}

.release-detail__table :deep(th.el-table__cell) {
  background: #eef2f7;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

@media (max-width: 1180px) {
  .release-board__analysis {
    grid-template-columns: 1fr;
  }

  .release-board__domain {
    border-right: 0;
    border-bottom: 1px solid #e2e8f0;
    gap: 8px;
    padding-bottom: 8px;
  }
}
</style>
