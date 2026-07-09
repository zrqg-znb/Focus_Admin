<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';
import type { OrganizationItem, RepositoryItem } from '#/api/compliance/base';
import type { MissingMergePlGroupOption } from '#/api/compliance/missing-merge';

import type {
  MissingMergePlDashboard,
  MissingMergeRecordListParams,
} from '#/api/compliance/missing-merge';

import { computed, nextTick, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import dayjs from 'dayjs';
import {
  ElButton,
  ElCascader,
  ElDatePicker,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { getMissingMergePlDashboardApi } from '#/api/compliance/missing-merge';

const props = defineProps<{
  active: boolean;
  mergedRange: string[];
  organizations: OrganizationItem[];
  plGroupIds: string[];
  plGroups: MissingMergePlGroupOption[];
  params: MissingMergeRecordListParams;
  repositoryOptions: RepositoryItem[];
  scopeValues: string[];
}>();

const emit = defineEmits<{
  'update:mergedRange': [value: string[]];
  'update:plGroupIds': [value: string[]];
  'update:scopeValues': [value: string[]];
}>();

const loading = ref(false);
const dashboard = ref<MissingMergePlDashboard>();
const trendChartRef = ref<EchartsUIType>();
const statusChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrendChart } = useEcharts(trendChartRef);
const { renderEcharts: renderStatusChart } = useEcharts(statusChartRef);

const ORG_SCOPE_PREFIX = 'org:';
const REPO_SCOPE_PREFIX = 'repo:';
const scopeCascaderProps = {
  checkStrictly: true,
  children: 'children',
  emitPath: false,
  label: 'label',
  multiple: true,
  value: 'value',
};

const scopeCascaderOptions = computed(() =>
  buildScopeCascaderOptions(props.organizations, props.repositoryOptions),
);

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function buildScopeCascaderOptions(
  organizations: OrganizationItem[],
  repositories: RepositoryItem[],
) {
  // 看板沿用列表相同的组织/代码库树，保证两个视图的范围定义一致。
  const repositoriesByOrg = new Map<string, RepositoryItem[]>();
  repositories.forEach((repository) => {
    const rows = repositoriesByOrg.get(repository.organization_id) || [];
    rows.push(repository);
    repositoriesByOrg.set(repository.organization_id, rows);
  });
  const buildNode = (item: OrganizationItem) => ({
    children: [
      ...(item.children || []).map(buildNode),
      ...((repositoriesByOrg.get(item.id) || [])
        .slice()
        .sort((left, right) =>
          left.project_name.localeCompare(right.project_name, 'zh-CN'),
        )
        .map((repository) => ({
          label: `${repository.project_name}（${repository.project_id}）`,
          value: `${REPO_SCOPE_PREFIX}${repository.id}`,
        })) as Array<{ label: string; value: string }>),
    ],
    label: `${item.name}（${item.group_id}）`,
    value: `${ORG_SCOPE_PREFIX}${item.id}`,
  });
  return organizations.map(buildNode);
}

function handleScopeChange(value: string[]) {
  emit('update:scopeValues', value || []);
}

function handlePlGroupChange(value: string[]) {
  emit('update:plGroupIds', value || []);
}

function handleMergedRangeChange(value?: string[] | null) {
  emit('update:mergedRange', value || []);
}

function renderCharts() {
  // 图表只读取 dashboard 快照，避免列表筛选变化时出现半更新状态。
  const data = dashboard.value;
  if (!data) return;
  const weekLabels = data.weeks?.length ? data.weeks : data.months;
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
      data: weekLabels,
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
          按主干合入时间统计周趋势，空合入时间记录计入明细但不进入趋势。
        </div>
      </div>
      <ElButton @click="loadDashboard">刷新看板</ElButton>
    </div>

    <ElForm class="dashboard-toolbar" inline label-position="top">
      <ElFormItem class="dashboard-toolbar__scope" label="组织/代码库">
        <ElCascader
          :model-value="scopeValues"
          clearable
          collapse-tags
          collapse-tags-tooltip
          filterable
          :max-collapse-tags="1"
          :options="scopeCascaderOptions"
          placeholder="选择组织或代码库（支持多选）"
          :props="scopeCascaderProps"
          @change="handleScopeChange"
          @clear="handleScopeChange([])"
        />
      </ElFormItem>
      <ElFormItem class="dashboard-toolbar__pl" label="PL组">
        <ElSelect
          :model-value="plGroupIds"
          clearable
          collapse-tags
          collapse-tags-tooltip
          filterable
          multiple
          placeholder="全部PL组"
          @change="handlePlGroupChange"
          @clear="handlePlGroupChange([])"
        >
          <ElOption
            v-for="item in plGroups"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </ElSelect>
      </ElFormItem>
      <ElFormItem class="dashboard-toolbar__range" label="合入时间">
        <ElDatePicker
          :model-value="mergedRange"
          clearable
          end-placeholder="合入结束"
          range-separator="至"
          start-placeholder="合入开始"
          type="datetimerange"
          value-format="YYYY-MM-DDTHH:mm:ssZ"
          @change="handleMergedRangeChange"
        />
      </ElFormItem>
    </ElForm>

    <template v-if="dashboard">
      <div class="chart-grid">
        <div class="chart-panel chart-panel-wide">
          <div class="panel-title">周趋势</div>
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

.dashboard-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.dashboard-toolbar :deep(.el-form-item) {
  margin: 0;
}

.dashboard-toolbar :deep(.el-form-item__label) {
  padding-bottom: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.dashboard-toolbar :deep(.el-cascader),
.dashboard-toolbar :deep(.el-date-editor),
.dashboard-toolbar :deep(.el-select) {
  width: 100%;
}

.dashboard-toolbar__scope {
  width: 420px;
}

.dashboard-toolbar__pl {
  width: 280px;
}

.dashboard-toolbar__range {
  width: 420px;
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

  .dashboard-toolbar__pl,
  .dashboard-toolbar__range,
  .dashboard-toolbar__scope {
    width: 100%;
  }
}
</style>
