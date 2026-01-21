<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PerformanceDashboardItem, PerformanceTreeNode, PerformanceChipType } from '#/api/core/performance';

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
import { getDashboardDataApi, getIndicatorTreeApi, getChipTypesApi } from '#/api/core/performance';

import TrendChart from './components/TrendChart.vue';
import { getStatusType, useColumns } from './data';

defineOptions({ name: 'PerformanceDashboard' });

const treeData = ref<PerformanceTreeNode[]>([]);
const category = ref<'vehicle' | 'cockpit'>('vehicle');
const project = ref<string>('');
const module = ref<string>('');
const chipType = ref<string>('');
const chipTypes = ref<PerformanceChipType[]>([]);

const dateRange = ref<[string, string]>([
  dayjs().subtract(6, 'day').format('YYYY-MM-DD'),
  dayjs().format('YYYY-MM-DD'),
]);

const projectOptions = computed(() => {
  const catNode = treeData.value.find((i) => i.key === category.value);
  return (catNode?.children || []).map((i) => ({ label: i.label, value: i.label }));
});

const moduleOptions = computed(() => {
  const catNode = treeData.value.find((i) => i.key === category.value);
  const projNode = catNode?.children?.find((i) => i.label === project.value);
  return (projNode?.children || []).map((i) => ({ label: i.label, value: i.label }));
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
            module: module.value,
            chip_type: chipType.value,
            start_date: startDate.value,
            end_date: endDate.value,
          };
          return await getDashboardDataApi(params);
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

async function loadTree() {
  treeData.value = await getIndicatorTreeApi();
  if (!project.value) {
    const first = projectOptions.value[0]?.value;
    if (first) project.value = first;
  }
}

async function loadChipTypes() {
  if (!project.value) {
    chipTypes.value = [];
    return;
  }
  chipTypes.value = await getChipTypesApi({ project: project.value });
}

watch(
  () => category.value,
  () => {
    project.value = projectOptions.value[0]?.value || '';
    module.value = '';
    chipType.value = '';
    gridApi.query();
  },
);

watch(
  () => project.value,
  async () => {
    module.value = '';
    chipType.value = '';
    await loadChipTypes();
    gridApi.query();
  },
);

watch(
  () => [module.value, chipType.value, startDate.value, endDate.value] as const,
  () => {
    gridApi.query();
  },
);

onMounted(async () => {
  await loadTree();
  // Initial load might trigger watches, but let's ensure chip types are loaded if project is set
  if (project.value) {
    await loadChipTypes();
  }
  gridApi.query();
});
</script>

<template>
  <Page auto-content-height>
    <div class="mb-4 flex flex-col gap-4 border-b pb-4 px-4">
      <!-- 顶部：分类切换 -->
      <div class="flex items-center">
        <ElRadioGroup v-model="category" size="large">
          <ElRadioButton label="vehicle">车控应用</ElRadioButton>
          <ElRadioButton label="cockpit">座舱应用</ElRadioButton>
        </ElRadioGroup>
      </div>

      <!-- 筛选栏 -->
      <div class="flex flex-wrap items-center gap-4">
        <div class="flex items-center gap-2">
          <div class="text-sm text-[var(--el-text-color-regular)]">项目</div>
          <ElSelect
            v-model="project"
            class="w-[180px]"
            filterable
            placeholder="选择项目"
          >
            <ElOption
              v-for="p in projectOptions"
              :key="p.value"
              :label="p.label"
              :value="p.value"
            />
          </ElSelect>
        </div>

        <div class="flex items-center gap-2">
          <div class="text-sm text-[var(--el-text-color-regular)]">模块</div>
          <ElSelect
            v-model="module"
            class="w-[180px]"
            filterable
            clearable
            placeholder="全部模块"
          >
            <ElOption
              v-for="m in moduleOptions"
              :key="m.value"
              :label="m.label"
              :value="m.value"
            />
          </ElSelect>
        </div>

        <div class="flex items-center gap-2">
          <div class="text-sm text-[var(--el-text-color-regular)]">芯片类型</div>
          <ElSelect
            v-model="chipType"
            class="w-[180px]"
            filterable
            clearable
            placeholder="全部芯片"
          >
            <ElOption
              v-for="c in chipTypes"
              :key="c.chip_type"
              :label="c.chip_type"
              :value="c.chip_type"
            />
          </ElSelect>
        </div>

        <div class="flex items-center gap-2">
          <div class="text-sm text-[var(--el-text-color-regular)]">日期范围</div>
          <ElDatePicker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            class="!w-[260px]"
          />
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
