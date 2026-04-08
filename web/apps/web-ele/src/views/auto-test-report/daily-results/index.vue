<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  DailyResultItem,
  DailySummary,
  VehicleOption,
} from '#/api/auto-test-report';

import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElCard,
  ElCascader,
  ElCheckbox,
  ElCheckboxGroup,
  ElDatePicker,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElLink,
  ElPopover,
  ElTag,
} from 'element-plus';

import {
  getDailySummaryApi,
  listDailyResultsApi,
  listVehicleOptionsApi,
} from '#/api/auto-test-report';
import { useZqTable } from '#/components/zq-table';

import TestCaseHistoryDrawer from '../components/test-case-history-drawer.vue';
import {
  formatDuration,
  RESULT_LABEL_MAP,
  RESULT_TAG_MAP,
  useResultColumns,
} from './data';

defineOptions({ name: 'AutoTestDailyResults' });

const route = useRoute();
const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

const vehicleOptions = ref<VehicleOption[]>([]);
const cascaderOptions = ref<any[]>([]);
const selectedVehiclePaths = ref<string[]>([]);
const vehicleKeyword = ref('');
const selectedDate = ref(new Date().toISOString().slice(0, 10));

const selectedStatus = ref<string[]>([]);
const draftStatus = ref<string[]>([]);
const statusPopoverVisible = ref(false);

const summary = ref<DailySummary | null>(null);
const loading = ref(false);

const statusOptions = Object.keys(RESULT_LABEL_MAP).map((key) => ({
  value: key,
  label: RESULT_LABEL_MAP[key],
}));

const historyVisible = ref(false);
const historyTitle = ref('');
const currentCaseId = ref('');

const selectedVehicleId = computed(() => selectedVehiclePaths.value[1] || '');

const [Grid, gridApi] = useZqTable({
  tableTitle: '每日执行结果',
  gridOptions: {
    columns: useResultColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          if (!selectedVehicleId.value) {
            return { items: [], total: 0 };
          }
          const items =
            (await listDailyResultsApi(
              selectedVehicleId.value,
              selectedDate.value,
            )) || [];

          let filtered = items;
          if (selectedStatus.value.length > 0) {
            filtered = items.filter((item) =>
              selectedStatus.value.includes(item.status),
            );
          }

          const total = filtered.length;
          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          const pagedItems = filtered.slice(start, end);
          return { items: pagedItems, total };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: { custom: true, refresh: true, search: false, zoom: true },
  },
  showSearchForm: false,
});

function rebuildCascaderOptions() {
  const keywordValue = vehicleKeyword.value.trim().toLowerCase();
  const platformMap = new Map<string, any>();
  for (const item of vehicleOptions.value) {
    const text =
      `${item.platform_name} ${item.name} ${item.vehicle_code}`.toLowerCase();
    if (keywordValue && !text.includes(keywordValue)) {
      continue;
    }
    if (!platformMap.has(item.platform_id)) {
      platformMap.set(item.platform_id, {
        value: item.platform_id,
        label: item.platform_name,
        children: [],
      });
    }
    platformMap.get(item.platform_id).children.push({
      value: item.id,
      label: `${item.name} (${item.vehicle_code})`,
    });
  }
  cascaderOptions.value = [...platformMap.values()];
}

function renderChart() {
  const stats = summary.value?.stats || [];
  renderEcharts({
    tooltip: { trigger: 'item' },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['35%', '50%'],
        data: stats.map((item) => ({ value: item.count, name: item.label })),
        label: {
          show: true,
          formatter: '{b}\n{d}%',
        },
      },
    ],
  });
}

async function loadVehicleOptions() {
  vehicleOptions.value = (await listVehicleOptionsApi()) || [];
  rebuildCascaderOptions();
  const routeVehicleId = String(route.query.vehicleId || '');
  const matched = vehicleOptions.value.find(
    (item) => item.id === routeVehicleId,
  );
  if (matched) {
    selectedVehiclePaths.value = [matched.platform_id, matched.id];
  } else if (!selectedVehicleId.value && vehicleOptions.value.length > 0) {
    const first = vehicleOptions.value[0]!;
    selectedVehiclePaths.value = [first.platform_id, first.id];
  }
}

async function loadPage() {
  if (!selectedVehicleId.value) {
    summary.value = null;
    await gridApi.reload();
    return;
  }
  loading.value = true;
  try {
    summary.value = await getDailySummaryApi(
      selectedVehicleId.value,
      selectedDate.value,
    );
    await gridApi.reload();
    await nextTick();
    renderChart();
  } finally {
    loading.value = false;
  }
}

function openHistory(row: DailyResultItem) {
  currentCaseId.value = row.case_id;
  historyTitle.value = `${row.case_no} / ${row.case_name}`;
  historyVisible.value = true;
}

watch(vehicleKeyword, () => {
  rebuildCascaderOptions();
});

watch([selectedVehicleId, selectedDate], () => {
  selectedStatus.value = [];
  draftStatus.value = [];
  loadPage();
});

function handleStatusFilterShow() {
  draftStatus.value = [...selectedStatus.value];
}

function confirmStatusFilter() {
  selectedStatus.value = [...draftStatus.value];
  statusPopoverVisible.value = false;
  gridApi.reload();
}

function resetStatusFilter() {
  draftStatus.value = [];
  selectedStatus.value = [];
  statusPopoverVisible.value = false;
  gridApi.reload();
}

onMounted(async () => {
  await loadVehicleOptions();
  await loadPage();
});
</script>

<template>
  <Page auto-content-height content-class="flex flex-col">
    <div class="flex h-full min-h-0 flex-col gap-4">
      <div class="shrink-0 rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm">
        <ElForm
          :inline="true"
          class="flex flex-wrap items-center gap-4"
          @submit.prevent
        >
          <ElFormItem label="MCU 平台 / 车型" class="!mb-0">
            <ElCascader
              v-model="selectedVehiclePaths"
              class="w-[320px]"
              clearable
              filterable
              placeholder="选择 MCU 平台 / 车型"
              :options="cascaderOptions"
              :props="{ emitPath: true }"
            />
          </ElFormItem>
          <ElFormItem label="车型关键词" class="!mb-0">
            <ElInput
              v-model="vehicleKeyword"
              class="w-[180px]"
              clearable
              placeholder="按关键词筛选"
            />
          </ElFormItem>
          <ElFormItem label="执行日期" class="!mb-0">
            <ElDatePicker
              v-model="selectedDate"
              placeholder="选择日期"
              type="date"
              value-format="YYYY-MM-DD"
              class="!w-[160px]"
            />
          </ElFormItem>
          <ElFormItem class="!mb-0">
            <ElButton :loading="loading" type="primary" @click="loadPage">
              刷新
            </ElButton>
          </ElFormItem>
        </ElForm>
      </div>

      <div v-loading="loading" class="flex min-h-0 flex-1 flex-col gap-4">
        <template v-if="summary">
          <div class="grid grid-cols-5 gap-4 shrink-0">
            <ElCard shadow="never" class="border-0 bg-blue-50/50">
              <div class="text-sm text-gray-500">总用例</div>
              <div class="text-2xl font-semibold text-blue-600">
                {{ summary.total_count }}
              </div>
            </ElCard>
            <ElCard shadow="never" class="border-0 bg-green-50/50">
              <div class="text-sm text-gray-500">成功</div>
              <div class="text-2xl font-semibold text-green-600">
                {{ summary.success_count }}
              </div>
            </ElCard>
            <ElCard shadow="never" class="border-0 bg-red-50/50">
              <div class="text-sm text-gray-500">失败</div>
              <div class="text-2xl font-semibold text-red-600">
                {{ summary.failed_count }}
              </div>
            </ElCard>
            <ElCard shadow="never" class="border-0 bg-orange-50/50">
              <div class="text-sm text-gray-500">超时</div>
              <div class="text-2xl font-semibold text-orange-500">
                {{ summary.timeout_count }}
              </div>
            </ElCard>
            <ElCard shadow="never" class="border-0 bg-gray-50/50">
              <div class="text-sm text-gray-500">跳过</div>
              <div class="text-2xl font-semibold text-gray-500">
                {{ summary.skip_count }}
              </div>
            </ElCard>
          </div>

          <div class="grid min-h-0 flex-1 grid-cols-[1fr_400px] gap-4">
            <Grid class="h-full rounded-lg shadow-sm border-0">
              <template #header-status="{ column }">
                <div
                  class="flex cursor-pointer select-none items-center justify-center gap-1"
                  @click.stop
                >
                  <span>{{ column.title }}</span>
                  <ElPopover
                    v-model:visible="statusPopoverVisible"
                    placement="bottom"
                    trigger="click"
                    width="200"
                    @show="handleStatusFilterShow"
                  >
                    <template #reference>
                      <ElIcon
                        class="hover:text-primary text-gray-400 transition-colors"
                        :class="{ 'text-primary': selectedStatus.length > 0 }"
                      >
                        <Filter />
                      </ElIcon>
                    </template>
                    <div class="p-1" @click.stop>
                      <ElCheckboxGroup
                        v-model="draftStatus"
                        class="flex flex-col gap-2"
                      >
                        <ElCheckbox
                          v-for="item in statusOptions"
                          :key="item.value"
                          :label="item.label"
                          :value="item.value"
                        />
                      </ElCheckboxGroup>
                      <div class="mt-4 flex justify-between border-t pt-2">
                        <ElButton size="small" link @click="resetStatusFilter">
                          重置
                        </ElButton>
                        <ElButton
                          size="small"
                          type="primary"
                          @click="confirmStatusFilter"
                        >
                          确定
                        </ElButton>
                      </div>
                    </div>
                  </ElPopover>
                </div>
              </template>

              <template #cell-status="{ row }">
                <ElTag :type="RESULT_TAG_MAP[row.status]">
                  {{ RESULT_LABEL_MAP[row.status] }}
                </ElTag>
              </template>
              <template #cell-duration_seconds="{ row }">
                {{ formatDuration(row.duration_seconds) }}
              </template>
              <template #cell-log_url="{ row }">
                <ElLink
                  v-if="row.log_url"
                  :href="row.log_url"
                  target="_blank"
                  type="primary"
                >
                  查看日志
                </ElLink>
                <span v-else class="text-gray-400">-</span>
              </template>
              <template #cell-actions="{ row }">
                <ElButton link type="primary" @click="openHistory(row)">
                  历史
                </ElButton>
              </template>
            </Grid>

            <ElCard
              shadow="never"
              class="flex h-full flex-col rounded-lg border-0 shadow-sm"
              body-class="flex flex-col flex-1 min-h-0"
            >
              <template #header>
                <div class="font-medium">当天全部用例执行占比</div>
              </template>
              <EchartsUI ref="chartRef" class="min-h-[280px] w-full flex-1" />
              <div class="mt-4 space-y-3 border-t pt-6 text-sm text-gray-600">
                <div class="flex justify-between">
                  <span>车型</span>
                  <span class="font-medium text-gray-900">
                    {{ summary.vehicle_name }}（{{ summary.vehicle_code }}）
                  </span>
                </div>
                <div class="flex justify-between">
                  <span>执行日期</span>
                  <span class="font-medium text-gray-900">
                    {{ summary.execute_date }}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span>最近上报</span>
                  <span class="font-medium text-gray-900">
                    {{ summary.last_report_at || '-' }}
                  </span>
                </div>
              </div>
            </ElCard>
          </div>
        </template>
        <ElEmpty v-else description="请选择车型并查询日报结果" />
      </div>
    </div>

    <TestCaseHistoryDrawer
      v-model:visible="historyVisible"
      :case-id="currentCaseId"
      :title="historyTitle"
    />
  </Page>
</template>
