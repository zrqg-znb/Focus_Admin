<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  ContributionFilters,
  ContributionMetric,
  ContributionRankingItem,
  ContributionRecordItem,
  ContributionTrendPoint,
} from '#/api/compliance/contribution';

import { computed, nextTick, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';
import dayjs from 'dayjs';
import {
  ElButton,
  ElDrawer,
  ElEmpty,
  ElRadioButton,
  ElRadioGroup,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  getContributionRepositoryRankingApi,
  getContributionSummaryApi,
  getContributionTrendApi,
  listContributionRecordsApi,
} from '#/api/compliance/contribution';
import { useZqTable } from '#/components/zq-table';

type HistoryEntity =
  | { id: string; label: string; type: 'person' }
  | { id: string; label: string; type: 'pl_group' }
  | { branchId?: string; id: string; label: string; type: 'repository' };

const props = defineProps<{
  baseFilters: ContributionFilters;
  entity?: HistoryEntity;
  modelValue: boolean;
}>();

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>();

const summary = ref<ContributionMetric>();
const trendRows = ref<ContributionTrendPoint[]>([]);
const repositoryRows = ref<ContributionRankingItem[]>([]);
const overviewLoading = ref(false);
const sourceMode = ref<'' | 'CR' | 'MR'>('');
const trendChartRef = ref<EchartsUIType>();
const drawerOpened = ref(false);
let overviewRequestId = 0;
const { renderEcharts: renderTrendChart, resize: resizeTrendChart } = useEcharts(trendChartRef);

const title = computed(() => `${props.entity?.label || '-'} · 贡献历史`);

function getFilters(): ContributionFilters {
  const filters: ContributionFilters = {
    ...props.baseFilters,
    source_mode: sourceMode.value,
  };
  if (props.entity?.type === 'person') filters.author_username = props.entity.id;
  if (props.entity?.type === 'pl_group') filters.pl_group_ids = [props.entity.id];
  if (props.entity?.type === 'repository') {
    filters.repository_ids = [props.entity.id];
    filters.branch_ids = props.entity.branchId ? [props.entity.branchId] : [];
  }
  return filters;
}

function formatNumber(value?: number) {
  return Number(value || 0).toLocaleString();
}

function formatTime(value?: string | null) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-';
}

function renderTrend() {
  return renderTrendChart({
    color: ['#2563eb', '#dc2626', '#64748b'],
    grid: { bottom: 28, containLabel: true, left: 14, right: 16, top: 32 },
    legend: { top: 0 },
    series: [
      { data: trendRows.value.map((item) => item.added_lines), name: '新增行数', smooth: true, type: 'line' },
      { data: trendRows.value.map((item) => item.removed_lines), name: '删除行数', smooth: true, type: 'line' },
      { data: trendRows.value.map((item) => item.changed_lines), name: '总变更', smooth: true, type: 'line' },
    ],
    tooltip: { trigger: 'axis' },
    xAxis: { boundaryGap: false, data: trendRows.value.map((item) => item.date), type: 'category' },
    yAxis: { type: 'value' },
  });
}

async function loadOverview() {
  if (!props.entity) return;
  const requestId = ++overviewRequestId;
  overviewLoading.value = true;
  try {
    const filters = getFilters();
    const [summaryData, trendData, repositoryData] = await Promise.all([
      getContributionSummaryApi(filters),
      getContributionTrendApi(filters),
      getContributionRepositoryRankingApi({ ...filters, limit: 10 } as ContributionFilters),
    ]);
    // 快速切换下钻对象时，只允许最后一次请求刷新抽屉内容。
    if (requestId !== overviewRequestId || !props.modelValue) return;
    summary.value = summaryData;
    trendRows.value = trendData;
    repositoryRows.value = repositoryData;
    await nextTick();
    if (drawerOpened.value) {
      await renderTrend();
      resizeTrendChart();
    }
  } finally {
    if (requestId === overviewRequestId) overviewLoading.value = false;
  }
}

const [Grid, gridApi] = useZqTable<ContributionRecordItem>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: [
      { dataKey: 'source_mode', key: 'source_mode', title: '来源', width: 72 },
      { dataKey: 'merged_at', key: 'merged_at', title: '合入时间', width: 154 },
      { dataKey: 'repository_name', key: 'repository_name', title: '代码库', minWidth: 150 },
      { dataKey: 'branch_name', key: 'branch_name', title: '分支', width: 150 },
      { dataKey: 'title', key: 'title', title: '变更标题', minWidth: 220 },
      { dataKey: 'author_display_name', key: 'author_display_name', title: '创建人', width: 150 },
      { dataKey: 'author_pl_group_name', key: 'author_pl_group_name', title: 'PL组', width: 150 },
      { align: 'right', dataKey: 'added_lines', key: 'added_lines', title: '新增', width: 90 },
      { align: 'right', dataKey: 'removed_lines', key: 'removed_lines', title: '删除', width: 90 },
      { align: 'right', dataKey: 'changed_lines', key: 'changed_lines', title: '总变更', width: 100 },
    ],
    pagerConfig: { enabled: true, pageSize: 20, pageSizes: [10, 20, 50, 100] },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: ({ page }: { page: { currentPage: number; pageSize: number } }) =>
          listContributionRecordsApi({
            ...getFilters(),
            page: page.currentPage,
            pageSize: page.pageSize,
          }),
      },
    },
    stripe: true,
  },
});

function reloadRecords(resetPage = false) {
  if (resetPage) gridApi.pagination.currentPage = 1;
  gridApi.query();
}

function changeSourceMode() {
  loadOverview();
  reloadRecords(true);
}

function openRecord(row: ContributionRecordItem) {
  if (row.web_url) window.open(row.web_url, '_blank', 'noopener,noreferrer');
}

async function handleDrawerOpened() {
  drawerOpened.value = true;
  await nextTick();
  await renderTrend();
  resizeTrendChart();
}

watch(
  () => [
    props.modelValue,
    props.entity?.type,
    props.entity?.id,
    props.entity?.type === 'repository' ? props.entity.branchId : undefined,
  ] as const,
  ([visible]) => {
    if (!visible) {
      drawerOpened.value = false;
      overviewRequestId += 1;
      overviewLoading.value = false;
      return;
    }
    sourceMode.value = props.baseFilters.source_mode || '';
    summary.value = undefined;
    trendRows.value = [];
    repositoryRows.value = [];
    loadOverview();
    reloadRecords(true);
  },
);
</script>

<template>
  <ElDrawer
    :model-value="modelValue"
    :title="title"
    :size="'min(1160px, 94vw)'"
    @opened="handleDrawerOpened"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template v-if="entity">
      <div class="history-drawer" v-loading="overviewLoading">
        <section class="history-toolbar">
          <ElRadioGroup v-model="sourceMode" class="source-switch" @change="changeSourceMode">
            <ElRadioButton label="">全部</ElRadioButton>
            <ElRadioButton label="CR">CR</ElRadioButton>
            <ElRadioButton label="MR">MR</ElRadioButton>
          </ElRadioGroup>
        </section>

        <section class="history-metrics">
          <div class="history-metric"><span>新增行数</span><strong>{{ formatNumber(summary?.added_lines) }}</strong></div>
          <div class="history-metric"><span>删除行数</span><strong>{{ formatNumber(summary?.removed_lines) }}</strong></div>
          <div class="history-metric"><span>总变更</span><strong>{{ formatNumber(summary?.changed_lines) }}</strong></div>
          <div class="history-metric"><span>变更数</span><strong>{{ formatNumber(summary?.cr_count) }}</strong></div>
          <div class="history-metric"><span>涉及代码库</span><strong>{{ formatNumber(summary?.active_repository_count) }}</strong></div>
          <div class="history-metric"><span>涉及分支</span><strong>{{ formatNumber(summary?.active_branch_count) }}</strong></div>
        </section>

        <section class="history-overview">
          <div class="history-panel">
            <div class="history-panel-title">新增贡献趋势</div>
            <EchartsUI ref="trendChartRef" class="history-trend" />
          </div>
          <div class="history-panel history-repositories">
            <div class="history-panel-title">仓库 / 分支 Top 10</div>
            <ElTable :data="repositoryRows" height="264" size="small">
              <ElTableColumn label="代码库 / 分支" min-width="190">
                <template #default="{ row }">{{ row.repository_name }} · {{ row.branch_name }}</template>
              </ElTableColumn>
              <ElTableColumn align="right" label="新增" prop="added_lines" width="84" />
              <ElTableColumn align="right" label="变更数" prop="cr_count" width="84" />
            </ElTable>
          </div>
        </section>

        <section class="history-records">
          <div class="history-records-title">变更历史</div>
          <Grid class="history-grid">
            <template #cell-source_mode="{ row }">
              <ElTag :type="row.source_mode === 'MR' ? 'warning' : 'primary'" effect="plain" size="small">{{ row.source_mode }}</ElTag>
            </template>
            <template #cell-merged_at="{ row }">{{ formatTime(row.merged_at) }}</template>
            <template #cell-title="{ row }">
              <ElButton link type="primary" @click="openRecord(row)">{{ row.title || row.source_change_id }}</ElButton>
            </template>
          </Grid>
        </section>
      </div>
    </template>
    <ElEmpty v-else description="暂无历史数据" />
  </ElDrawer>
</template>

<style scoped lang="less">
.history-drawer { display: flex; min-height: 0; flex-direction: column; gap: 14px; }
.history-toolbar { display: flex; justify-content: flex-end; }
.source-switch :deep(.el-radio-button__inner) { min-width: 64px; }
.history-metrics { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; }
.history-metric { min-width: 0; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 12px; }
.history-metric span { display: block; color: #64748b; font-size: 12px; }
.history-metric strong { display: block; margin-top: 6px; color: #0f172a; font-size: 20px; line-height: 1; }
.history-overview { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(340px, 1fr); gap: 12px; }
.history-panel { min-width: 0; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; }
.history-panel-title, .history-records-title { color: #0f172a; font-size: 14px; font-weight: 700; }
.history-trend { height: 264px; margin-top: 8px; }
.history-records { display: flex; height: 460px; min-height: 0; flex-direction: column; gap: 8px; }
.history-grid { min-height: 0; flex: 1; }
@media (max-width: 900px) { .history-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); } .history-overview { grid-template-columns: 1fr; } .history-records { height: 520px; } }
</style>
