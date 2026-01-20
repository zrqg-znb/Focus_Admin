<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PerformanceDashboardItem, PerformanceTreeNode } from '#/api/core/performance';

import dayjs from 'dayjs';
import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElTag,
} from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getDashboardDataApi, getIndicatorTreeApi } from '#/api/core/performance';

import TrendChart from './components/TrendChart.vue';
import { getStatusType, useColumns } from './data';

defineOptions({ name: 'PerformanceDashboard' });

const treeData = ref<PerformanceTreeNode[]>([]);
const category = ref<'vehicle' | 'cockpit'>('vehicle');
const project = ref<string>('');
const dateRange = ref<[string, string]>([
  dayjs().subtract(6, 'day').format('YYYY-MM-DD'),
  dayjs().format('YYYY-MM-DD'),
]);

const projectOptions = computed(() => {
  const catNode = treeData.value.find((i) => i.key === category.value);
  return (catNode?.children || []).map((i) => ({ label: i.label, value: i.label }));
});

const startDate = computed(() => dateRange.value[0]);
const endDate = computed(() => dateRange.value[1]);

const trendVisible = ref(false);
const currentIndicatorId = ref('');
const currentIndicatorName = ref('');
const currentBaselineValue = ref<number | undefined>(undefined);

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: true,
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }) => {
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            category: category.value,
            project: project.value,
            start_date: startDate.value,
            end_date: endDate.value,
          };
          const res = await getDashboardDataApi(params);
          pageStats.value.total = res.items?.length || 0;
          recomputeStats(res.items || []);
          return res;
        },
      },
    },
    toolbarConfig: {
      custom: true,
      export: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<PerformanceDashboardItem>,
});

function showTrend(row: PerformanceDashboardItem) {
  currentIndicatorId.value = row.id;
  currentIndicatorName.value = row.name;
  currentBaselineValue.value = row.baseline_value;
  trendVisible.value = true;
}

const pageStats = ref({
  total: 0,
  danger: 0,
  warning: 0,
  modules: 0,
  chips: 0,
});

function recomputeStats(rows: PerformanceDashboardItem[]) {
  const danger = rows.filter((r) => getStatusType(r) === 'danger').length;
  const warning = rows.filter((r) => getStatusType(r) === 'warning').length;
  const modules = new Set(rows.map((r) => r.module)).size;
  const chips = new Set(rows.map((r) => r.chip_type)).size;
  pageStats.value = {
    ...pageStats.value,
    danger,
    warning,
    modules,
    chips,
  };
}

async function loadTree() {
  treeData.value = await getIndicatorTreeApi();
  if (!project.value) {
    const first = projectOptions.value[0]?.value;
    if (first) project.value = first;
  }
}

watch(
  () => category.value,
  () => {
    project.value = projectOptions.value[0]?.value || '';
    gridApi.query();
  },
);

watch(
  () => [project.value, startDate.value, endDate.value] as const,
  () => {
    gridApi.query();
  },
);

onMounted(async () => {
  await loadTree();
  gridApi.query();
});
</script>

<template>
  <Page auto-content-height>
    <div class="mb-3 flex items-center justify-between gap-3 px-4">
      <div class="flex items-center gap-2">
        <div class="text-sm text-[var(--el-text-color-regular)]">项目</div>
        <ElSelect v-model="project" class="w-[200px]" filterable placeholder="选择项目">
          <ElOption v-for="p in projectOptions" :key="p.value" :label="p.label" :value="p.value" />
        </ElSelect>
      </div>

      <div class="flex items-center gap-3">
        <ElDatePicker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
        />
        <ElRadioGroup v-model="category">
          <ElRadioButton label="vehicle">车控</ElRadioButton>
          <ElRadioButton label="cockpit">座舱</ElRadioButton>
        </ElRadioGroup>
      </div>
    </div>

    <div class="mb-3 grid grid-cols-4 gap-3 px-4">
      <div class="rounded bg-[var(--el-bg-color)] p-3">
        <div class="text-xs text-[var(--el-text-color-secondary)]">总条目（本页）</div>
        <div class="mt-1 text-2xl font-semibold">{{ pageStats.total }}</div>
      </div>
      <div class="rounded bg-[var(--el-bg-color)] p-3">
        <div class="text-xs text-[var(--el-text-color-secondary)]">异常（Danger）</div>
        <div class="mt-1 text-2xl font-semibold">{{ pageStats.danger }}</div>
      </div>
      <div class="rounded bg-[var(--el-bg-color)] p-3">
        <div class="text-xs text-[var(--el-text-color-secondary)]">警告（Warning）</div>
        <div class="mt-1 text-2xl font-semibold">{{ pageStats.warning }}</div>
      </div>
      <div class="rounded bg-[var(--el-bg-color)] p-3">
        <div class="text-xs text-[var(--el-text-color-secondary)]">模块/芯片（本页）</div>
        <div class="mt-1 text-2xl font-semibold">
          {{ pageStats.modules }}/{{ pageStats.chips }}
        </div>
      </div>
    </div>

    <Grid>
      <template #fluctuation="{ row }">
        <ElTag :type="getStatusType(row)" v-if="row.fluctuation_value !== null">
          {{ row.fluctuation_value?.toFixed(2) }}
        </ElTag>
      </template>

      <template #action="{ row }">
        <ElButton type="primary" size="small" @click="showTrend(row)">
          趋势
        </ElButton>
      </template>
    </Grid>

    <ElDialog
      v-model="trendVisible"
      :title="`趋势图 - ${currentIndicatorName}`"
      width="800px"
      destroy-on-close
    >
      <TrendChart
        :indicator-id="currentIndicatorId"
        :baseline-value="currentBaselineValue"
        :start-date="startDate"
        :end-date="endDate"
        v-if="trendVisible"
      />
    </ElDialog>
  </Page>
</template>
