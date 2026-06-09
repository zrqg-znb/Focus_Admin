<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  MissingMergePlDashboard,
  MissingMergeRecordListParams,
} from '#/api/compliance/missing-merge';

import { nextTick, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import dayjs from 'dayjs';
import {
  ElButton,
  ElEmpty,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { getMissingMergePlDashboardApi } from '#/api/compliance/missing-merge';

const props = defineProps<{
  active: boolean;
  params: MissingMergeRecordListParams;
}>();

const loading = ref(false);
const dashboard = ref<MissingMergePlDashboard>();
const trendChartRef = ref<EchartsUIType>();
const statusChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrendChart } = useEcharts(trendChartRef);
const { renderEcharts: renderStatusChart } = useEcharts(statusChartRef);

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function renderCharts() {
  // 图表只读取 dashboard 快照，避免列表筛选变化时出现半更新状态。
  const data = dashboard.value;
  if (!data) return;
  renderTrendChart({
    color: ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#7c3aed', '#0891b2'],
    grid: {
      bottom: 34,
      containLabel: true,
      left: 16,
      right: 24,
      top: 36,
    },
    legend: {
      top: 0,
      type: 'scroll',
    },
    series: data.trend_series.map((item) => ({
      data: item.data,
      name: item.pl_group_name,
      smooth: true,
      symbolSize: 6,
      type: 'line',
    })),
    tooltip: {
      trigger: 'axis',
    },
    xAxis: {
      boundaryGap: false,
      data: data.months,
      type: 'category',
    },
    yAxis: {
      minInterval: 1,
      type: 'value',
    },
  });

  renderStatusChart({
    color: ['#ef4444', '#22c55e', '#64748b'],
    series: [
      {
        data: data.status_distribution.map((item) => ({
          name: item.status_label,
          value: item.count,
        })),
        radius: ['48%', '72%'],
        type: 'pie',
      },
    ],
    tooltip: {
      trigger: 'item',
    },
  });
}

async function loadDashboard() {
  if (!props.active) return;
  loading.value = true;
  try {
    dashboard.value = await getMissingMergePlDashboardApi(props.params);
    await nextTick();
    renderCharts();
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.active, JSON.stringify(props.params)],
  () => {
    loadDashboard();
  },
  { immediate: true },
);
</script>

<template>
  <div class="pl-dashboard" v-loading="loading">
    <div class="dashboard-header">
      <div>
        <div class="dashboard-title">PL组漏合趋势</div>
        <div class="dashboard-subtitle">
          按主干合入时间统计月份趋势，空合入时间记录计入汇总但不进入趋势。
        </div>
      </div>
      <ElButton @click="loadDashboard">刷新看板</ElButton>
    </div>

    <template v-if="dashboard">
      <div class="metric-row">
        <div class="metric-item">
          <span>总风险</span>
          <strong>{{ dashboard.summary.total_count }}</strong>
        </div>
        <div class="metric-item metric-danger">
          <span>未处理</span>
          <strong>{{ dashboard.summary.open_count }}</strong>
        </div>
        <div class="metric-item metric-success">
          <span>已补合</span>
          <strong>{{ dashboard.summary.fixed_count }}</strong>
        </div>
        <div class="metric-item">
          <span>PL组数</span>
          <strong>{{ dashboard.summary.pl_group_count }}</strong>
        </div>
        <div class="metric-item">
          <span>无合入时间</span>
          <strong>{{ dashboard.summary.missing_merged_at_count }}</strong>
        </div>
      </div>

      <div class="chart-grid">
        <div class="chart-panel chart-panel-wide">
          <div class="panel-title">月度趋势</div>
          <EchartsUI ref="trendChartRef" class="chart-body" />
        </div>
        <div class="chart-panel">
          <div class="panel-title">状态分布</div>
          <EchartsUI ref="statusChartRef" class="chart-body" />
        </div>
      </div>

      <div class="table-panel">
        <div class="panel-title">PL组明细排行</div>
        <ElTable :data="dashboard.pl_groups" border height="320">
          <ElTableColumn label="PL组" min-width="180" prop="pl_group_name" />
          <ElTableColumn align="center" label="总量" prop="total_count" width="100" />
          <ElTableColumn align="center" label="未处理" prop="open_count" width="100">
            <template #default="{ row }">
              <ElTag :type="row.open_count > 0 ? 'danger' : 'success'">
                {{ row.open_count }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn align="center" label="已补合" prop="fixed_count" width="100" />
          <ElTableColumn align="center" label="已忽略" prop="ignored_count" width="100" />
          <ElTableColumn label="最近识别时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.latest_detected_at) }}
            </template>
          </ElTableColumn>
        </ElTable>
      </div>
    </template>

    <ElEmpty v-else description="暂无PL组看板数据" />
  </div>
</template>

<style scoped lang="less">
.pl-dashboard {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.dashboard-header,
.metric-row,
.chart-grid {
  display: flex;
  gap: 12px;
}

.dashboard-header {
  align-items: center;
  justify-content: space-between;
}

.dashboard-title,
.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.dashboard-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.metric-row {
  flex-wrap: wrap;
}

.metric-item {
  min-width: 132px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-extra-light);
}

.metric-item span {
  display: block;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.metric-item strong {
  display: block;
  margin-top: 6px;
  font-size: 24px;
  line-height: 1;
  color: var(--el-text-color-primary);
}

.metric-danger strong {
  color: var(--el-color-danger);
}

.metric-success strong {
  color: var(--el-color-success);
}

.chart-grid {
  min-height: 320px;
}

.chart-panel,
.table-panel {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.chart-panel {
  flex: 1;
}

.chart-panel-wide {
  flex: 2;
}

.chart-body {
  width: 100%;
  height: 280px;
}

@media (max-width: 960px) {
  .chart-grid,
  .dashboard-header {
    flex-direction: column;
  }
}
</style>
