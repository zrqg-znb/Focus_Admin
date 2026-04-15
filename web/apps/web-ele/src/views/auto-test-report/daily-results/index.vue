<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  DailyOverviewResponse,
  DailyOverviewRow,
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
  ElMessage,
  ElOption,
  ElPopover,
  ElSelect,
  ElSwitch,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import {
  getDailyOverviewApi,
  getDailySummaryApi,
  listDailyResultsApi,
  listVehicleOptionsApi,
  updateDailyResultFailureReasonApi,
} from '#/api/auto-test-report';
import { useZqTable } from '#/components/zq-table';

import TestCaseHistoryDrawer from '../components/test-case-history-drawer.vue';
import {
  formatDuration,
  RESULT_LABEL_MAP,
  RESULT_TAG_MAP,
  useOverviewColumns,
  useResultColumns,
} from './data';

defineOptions({ name: 'AutoTestDailyResults' });

const route = useRoute();
const overviewChartRef = ref<EchartsUIType>();
const { renderEcharts: renderOverviewChart } = useEcharts(overviewChartRef);

const vehicleChartRef = ref<EchartsUIType>();
const { renderEcharts: renderVehicleChart } = useEcharts(vehicleChartRef);

const activeView = ref<'overview' | 'vehicle'>('overview');
const vehicleOptions = ref<VehicleOption[]>([]);
const cascaderOptions = ref<any[]>([]);
const selectedVehiclePaths = ref<string[]>([]);
const selectedDate = ref(new Date().toISOString().slice(0, 10));
const vehicleKeyword = ref('');
const selectedPlatformId = ref('');
const abnormalOnly = ref(false);

const selectedStatus = ref<string[]>([]);
const draftStatus = ref<string[]>([]);
const statusPopoverVisible = ref(false);
const overviewLoading = ref(false);
const detailLoading = ref(false);
const overviewData = ref<DailyOverviewResponse | null>(null);
const summary = ref<DailySummary | null>(null);

const historyVisible = ref(false);
const historyTitle = ref('');
const currentCaseId = ref('');
const editingReasonCell = ref<null | { resultId: string }>(null);
const editingReasonValue = ref('');

const selectedVehicleId = computed(() => selectedVehiclePaths.value[1] || '');
const platformOptions = computed(() => {
  const map = new Map<string, { label: string; value: string }>();
  for (const item of vehicleOptions.value) {
    if (!map.has(item.platform_id)) {
      map.set(item.platform_id, {
        label: item.platform_name,
        value: item.platform_id,
      });
    }
  }
  return [...map.values()];
});
const statusOptions = Object.keys(RESULT_LABEL_MAP).map((key) => ({
  value: key,
  label: RESULT_LABEL_MAP[key],
}));

function canEditFailureReason(row: DailyResultItem) {
  return Boolean(row.result_id && ['failed', 'timeout'].includes(row.status));
}

function isEditingFailureReason(row: DailyResultItem) {
  return Boolean(
    row.result_id &&
      editingReasonCell.value?.resultId &&
      editingReasonCell.value.resultId === row.result_id,
  );
}

function beginFailureReasonEdit(row: DailyResultItem) {
  if (!canEditFailureReason(row) || !row.result_id) {
    return;
  }
  editingReasonCell.value = { resultId: row.result_id };
  editingReasonValue.value =
    row.failure_reason || row.suggested_failure_reason || '';
}

function cancelFailureReasonEdit() {
  editingReasonCell.value = null;
  editingReasonValue.value = '';
}

async function submitFailureReason(row: DailyResultItem, value?: string) {
  if (!row.result_id || !canEditFailureReason(row)) {
    cancelFailureReasonEdit();
    return;
  }
  const nextValue = (value ?? editingReasonValue.value ?? '').trim();
  try {
    await updateDailyResultFailureReasonApi(
      row.result_id,
      nextValue || undefined,
    );
    row.failure_reason = nextValue || '';
    row.suggested_failure_reason = row.failure_reason
      ? undefined
      : row.suggested_failure_reason;
    ElMessage.success('异常原因已保存');
  } finally {
    cancelFailureReasonEdit();
  }
}

async function applySuggestedFailureReason(row: DailyResultItem) {
  if (!row.suggested_failure_reason || !row.result_id) {
    return;
  }
  await submitFailureReason(row, row.suggested_failure_reason);
}

const [OverviewGrid, overviewGridApi] = useZqTable({
  tableTitle: '全量车型执行概览',
  gridOptions: {
    columns: useOverviewColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          const rows = overviewData.value?.items || [];
          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          return {
            items: rows.slice(start, end),
            total: rows.length,
          };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: { custom: true, refresh: true, search: false, zoom: true },
  },
  showSearchForm: false,
});

const [DetailGrid, detailGridApi] = useZqTable({
  tableTitle: '车型执行明细',
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
          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          return { items: filtered.slice(start, end), total: filtered.length };
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

function renderChart(
  renderFn: any,
  stats: Array<{ count: number; label: string }>,
) {
  const statusColors: Record<string, string> = {
    成功: '#10b981', // 绿色
    失败: '#ef4444', // 红色
    超时: '#f59e0b', // 黄色
    跳过: '#94a3b8', // 灰色
  };

  renderFn({
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', right: '5%', top: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['35%', '50%'],
        data: stats.map((item) => ({
          value: item.count,
          name: item.label,
          itemStyle: {
            color: statusColors[item.label] || '#94a3b8',
          },
        })),
        label: { show: true, formatter: '{b}\n{d}%' },
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
    activeView.value = 'vehicle';
  } else if (vehicleOptions.value.length > 0 && !selectedVehicleId.value) {
    const first = vehicleOptions.value[0]!;
    selectedVehiclePaths.value = [first.platform_id, first.id];
  }
}

async function loadOverview() {
  overviewLoading.value = true;
  try {
    overviewData.value = await getDailyOverviewApi({
      execute_date: selectedDate.value,
      platform_id: selectedPlatformId.value || undefined,
      abnormal_only: abnormalOnly.value || undefined,
    });
    await overviewGridApi.reload();
    await nextTick();
    renderChart(renderOverviewChart, overviewData.value.summary.stats);
  } finally {
    overviewLoading.value = false;
  }
}

async function loadVehicleView() {
  if (!selectedVehicleId.value) {
    summary.value = null;
    await detailGridApi.reload();
    return;
  }
  detailLoading.value = true;
  try {
    summary.value = await getDailySummaryApi(
      selectedVehicleId.value,
      selectedDate.value,
    );
    await detailGridApi.reload();
    await nextTick();
    renderChart(renderVehicleChart, summary.value.stats);
  } finally {
    detailLoading.value = false;
  }
}

async function loadActiveView() {
  if (activeView.value === 'overview') {
    await loadOverview();
    return;
  }
  await loadVehicleView();
}

function openHistory(row: DailyResultItem) {
  currentCaseId.value = row.case_id;
  historyTitle.value = `${row.case_no} / ${row.case_name}`;
  historyVisible.value = true;
}

function handleStatusFilterShow() {
  draftStatus.value = [...selectedStatus.value];
}

function confirmStatusFilter() {
  selectedStatus.value = [...draftStatus.value];
  statusPopoverVisible.value = false;
  detailGridApi.reload();
}

function resetStatusFilter() {
  draftStatus.value = [];
  selectedStatus.value = [];
  statusPopoverVisible.value = false;
  detailGridApi.reload();
}

async function jumpToVehicle(row: DailyOverviewRow) {
  selectedVehiclePaths.value = [row.platform_id, row.vehicle_id];
  activeView.value = 'vehicle';
  await loadVehicleView();
}

watch(vehicleKeyword, () => {
  rebuildCascaderOptions();
});

watch([selectedDate, selectedPlatformId, abnormalOnly], () => {
  if (activeView.value === 'overview') {
    loadOverview();
  }
});

watch([selectedVehicleId, selectedDate], () => {
  if (activeView.value === 'vehicle') {
    selectedStatus.value = [];
    draftStatus.value = [];
    loadVehicleView();
  }
});

watch(activeView, () => {
  loadActiveView();
});

onMounted(async () => {
  await loadVehicleOptions();
  await loadActiveView();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col gap-4">
      <div class="shrink-0 rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm">
        <div class="flex items-center justify-between gap-4">
          <div>
            <div class="text-base font-semibold text-gray-900">
              每日执行结果
            </div>
            <div class="text-sm text-gray-500">
              先看全量异常，再下钻到单车型明细。
            </div>
          </div>
          <ElTabs v-model="activeView" class="auto-test-result-tabs">
            <ElTabPane label="全量视图" name="overview" />
            <ElTabPane label="车型视图" name="vehicle" />
          </ElTabs>
        </div>
      </div>

      <template v-if="activeView === 'overview'">
        <div class="shrink-0 rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm">
          <ElForm
            :inline="true"
            class="flex flex-wrap items-center gap-4"
            @submit.prevent
          >
            <ElFormItem label="执行日期" class="!mb-0">
              <ElDatePicker
                v-model="selectedDate"
                type="date"
                value-format="YYYY-MM-DD"
                class="!w-[160px]"
              />
            </ElFormItem>
            <ElFormItem label="MCU 平台" class="!mb-0">
              <ElSelect
                v-model="selectedPlatformId"
                class="!w-[220px]"
                clearable
                placeholder="全部平台"
              >
                <ElOption
                  v-for="item in platformOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>
            <ElFormItem label="仅看异常" class="!mb-0">
              <ElSwitch v-model="abnormalOnly" />
            </ElFormItem>
            <ElFormItem class="!mb-0">
              <ElButton
                :loading="overviewLoading"
                type="primary"
                @click="loadOverview"
              >
                刷新
              </ElButton>
            </ElFormItem>
          </ElForm>
        </div>

        <div
          v-loading="overviewLoading"
          class="grid min-h-0 flex-1 grid-cols-[1fr_400px] gap-4"
        >
          <div class="h-full min-h-0 min-w-0">
            <OverviewGrid class="h-full rounded-lg border-0 shadow-sm">
              <template #cell-is_abnormal="{ row }">
                <ElTag :type="row.is_abnormal ? 'danger' : 'success'">
                  {{ row.is_abnormal ? '异常' : '正常' }}
                </ElTag>
              </template>
              <template #cell-total_duration_seconds="{ row }">
                {{ formatDuration(row.total_duration_seconds) }}
              </template>
              <template #cell-actions="{ row }">
                <ElButton link type="primary" @click="jumpToVehicle(row)">
                  查看明细
                </ElButton>
              </template>
            </OverviewGrid>
          </div>

          <ElCard
            shadow="never"
            class="flex h-full flex-col rounded-lg border-0 shadow-sm"
            body-class="flex flex-col flex-1 min-h-0"
          >
            <template #header>
              <div class="font-medium">当日全量执行占比</div>
            </template>
            <EchartsUI
              ref="overviewChartRef"
              class="min-h-[280px] w-full flex-1"
            />
            <div
              v-if="overviewData?.summary"
              class="mt-4 space-y-3 border-t pt-6 text-sm text-gray-600"
            >
              <div class="flex justify-between">
                <span>车型总数</span>
                <span class="font-medium text-gray-900">
                  {{ overviewData.summary.vehicle_count }}
                </span>
              </div>
              <div class="flex justify-between">
                <span>异常车型</span>
                <span class="font-medium text-red-600">
                  {{ overviewData.summary.abnormal_vehicle_count }}
                </span>
              </div>
              <div class="flex justify-between">
                <span>累计用例</span>
                <span class="font-medium text-gray-900">
                  {{ overviewData.summary.total_case_count }}
                </span>
              </div>
              <div class="flex justify-between">
                <span>累计耗时</span>
                <span class="font-medium text-gray-900">
                  {{
                    formatDuration(overviewData.summary.total_duration_seconds)
                  }}
                </span>
              </div>
              <div class="flex justify-between">
                <span>最近上报</span>
                <span class="font-medium text-gray-900">
                  {{ overviewData.summary.last_report_at || '-' }}
                </span>
              </div>
            </div>
            <ElEmpty v-else description="暂无全量数据" />
          </ElCard>
        </div>
      </template>

      <template v-else>
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
              <ElButton
                :loading="detailLoading"
                type="primary"
                @click="loadVehicleView"
              >
                刷新
              </ElButton>
            </ElFormItem>
          </ElForm>
        </div>

        <div
          v-loading="detailLoading"
          class="flex min-h-0 flex-1 flex-col gap-4"
        >
          <template v-if="summary">
            <div class="grid min-h-0 flex-1 grid-cols-[1fr_400px] gap-4">
              <div class="h-full min-h-0 min-w-0">
                <DetailGrid class="h-full rounded-lg border-0 shadow-sm">
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
                            :class="{
                              'text-primary': selectedStatus.length > 0,
                            }"
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
                            <ElButton
                              size="small"
                              link
                              @click="resetStatusFilter"
                            >
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
                  <template #cell-remark="{ row }">
                    <ElPopover
                      v-if="row.remark"
                      placement="top"
                      trigger="hover"
                      :content="row.remark"
                      width="240"
                    >
                      <template #reference>
                        <span class="block truncate text-left">
                          {{ row.remark }}
                        </span>
                      </template>
                    </ElPopover>
                    <span v-else class="text-gray-400">-</span>
                  </template>
                  <template #cell-failure_reason="{ row }">
                    <div class="w-full text-left">
                      <ElInput
                        v-if="isEditingFailureReason(row)"
                        v-model="editingReasonValue"
                        autofocus
                        clearable
                        placeholder="请输入异常原因"
                        @blur="submitFailureReason(row)"
                        @keydown.enter.prevent="submitFailureReason(row)"
                        @keydown.esc.prevent="cancelFailureReasonEdit"
                      />
                      <template v-else>
                        <div
                          v-if="canEditFailureReason(row)"
                          class="flex items-center gap-2"
                        >
                          <div
                            class="min-w-0 flex-1 cursor-pointer"
                            @dblclick="beginFailureReasonEdit(row)"
                          >
                            <ElPopover
                              v-if="row.failure_reason"
                              placement="top"
                              trigger="hover"
                              :content="row.failure_reason"
                              width="240"
                            >
                              <template #reference>
                                <span class="block truncate text-gray-900">
                                  {{ row.failure_reason }}
                                </span>
                              </template>
                            </ElPopover>
                            <template v-else-if="row.suggested_failure_reason">
                              <ElPopover
                                placement="top"
                                trigger="hover"
                                :content="row.suggested_failure_reason"
                                width="240"
                              >
                                <template #reference>
                                  <span class="block truncate text-gray-400">
                                    建议沿用：{{ row.suggested_failure_reason }}
                                  </span>
                                </template>
                              </ElPopover>
                            </template>
                            <span v-else class="text-gray-400">请填写</span>
                          </div>
                          <ElButton
                            v-if="
                              !row.failure_reason &&
                              row.suggested_failure_reason
                            "
                            link
                            type="primary"
                            @click="applySuggestedFailureReason(row)"
                          >
                            沿用上次原因
                          </ElButton>
                        </div>
                        <span v-else class="text-gray-400">-</span>
                      </template>
                    </div>
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
                </DetailGrid>
              </div>

              <ElCard
                shadow="never"
                class="flex h-full flex-col rounded-lg border-0 shadow-sm"
                body-class="flex flex-col flex-1 min-h-0"
              >
                <template #header>
                  <div class="font-medium">车型执行占比</div>
                </template>
                <EchartsUI
                  ref="vehicleChartRef"
                  class="min-h-[280px] w-full flex-1"
                />
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
                    <span>总耗时</span>
                    <span class="font-medium text-gray-900">
                      {{ formatDuration(summary.total_duration_seconds) }}
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
      </template>
    </div>

    <TestCaseHistoryDrawer
      v-model:visible="historyVisible"
      :case-id="currentCaseId"
      :title="historyTitle"
    />
  </Page>
</template>
