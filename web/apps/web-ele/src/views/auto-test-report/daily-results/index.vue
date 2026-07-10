<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { AutoTestReportDailyResultsView } from '../shared/daily-results-state';
import type { AutoTestReportDomain } from '../shared/domain';

import type {
  DailyOverviewResponse,
  DailyOverviewRow,
  DailyResultItem,
  DailySummary,
  DownstreamCommitItem,
  FailureCategory,
  VehicleOption,
} from '#/api/auto-test-report';

import { computed, nextTick, onMounted, ref, watch } from 'vue';

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
  ElDialog,
  ElDrawer,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElLink,
  ElMessage,
  ElOption,
  ElPagination,
  ElPopover,
  ElSegmented,
  ElSelect,
  ElSwitch,
  ElTag,
  ElTooltip,
} from 'element-plus';

import {
  getDailyOverviewApi,
  getDailySummaryApi,
  listDailyResultsApi,
  listDownstreamCommitsApi,
  listDownstreamCommitUsagesApi,
  listVehicleOptionsApi,
  triggerCockpitDownstreamApi,
  updateDailyResultFailureReasonApi,
} from '#/api/auto-test-report';
import { useZqTable } from '#/components/zq-table';

import DomainSwitcher from '../components/domain-switcher.vue';
import TestCaseHistoryDrawer from '../components/test-case-history-drawer.vue';
import {
  getAutoTestReportDailyResultsState,
  setAutoTestReportDailyResultsState,
  setAutoTestReportDailyResultsVehicleId,
  setAutoTestReportDailyResultsView,
} from '../shared/daily-results-state';
import { useAutoTestReportDomain } from '../shared/domain';
import {
  FAILURE_CATEGORY_LABEL_MAP,
  FAILURE_CATEGORY_OPTIONS,
  formatDuration,
  RESULT_LABEL_MAP,
  RESULT_TAG_MAP,
  useCommitColumns,
  useCommitUsageColumns,
  useOverviewColumns,
  useResultColumns,
} from './data';

defineOptions({ name: 'AutoTestDailyResults' });

const { domain, domainMeta } = useAutoTestReportDomain();
const overviewChartRef = ref<EchartsUIType>();
const { renderEcharts: renderOverviewChart } = useEcharts(overviewChartRef);

const vehicleChartRef = ref<EchartsUIType>();
const { renderEcharts: renderVehicleChart } = useEcharts(vehicleChartRef);

const activeView = ref<AutoTestReportDailyResultsView>(
  getAutoTestReportDailyResultsState(domain.value)
    .activeView as AutoTestReportDailyResultsView,
);
const viewOptions = [
  { label: '全量', value: 'overview' },
  { label: '车型', value: 'vehicle' },
];
const activeViewModel = computed<AutoTestReportDailyResultsView>({
  get: () => activeView.value,
  set: (next) => {
    void handleViewChange(next);
  },
});

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
const downstreamTriggerLoading = ref(false);
const commitHistoryVisible = ref(false);
const commitHistoryLoading = ref(false);
const commitUsageVisible = ref(false);
const commitUsageLoading = ref(false);
const commitSelectVisible = ref(false);
const commitSelectLoading = ref(false);
const overviewData = ref<DailyOverviewResponse | null>(null);
const summary = ref<DailySummary | null>(null);
const commitKeyword = ref('');
const commitSelectKeyword = ref('');
const commitSelectPage = ref(1);
const commitSelectPageSize = ref(5);
const commitSelectTotal = ref(0);
const commitSelectUploadedRange = ref<[] | [string, string]>([]);
const commitSelectOptions = ref<DownstreamCommitItem[]>([]);
const selectedCommitId = ref('');
const selectedUsageCommit = ref<DownstreamCommitItem | null>(null);

const historyVisible = ref(false);
const historyTitle = ref('');
const currentCaseId = ref('');
const editingReasonCell = ref<null | { resultId: string }>(null);
const editingReasonValue = ref('');
const detailSortState = ref<null | {
  order: 'ascending' | 'descending' | null;
  prop: string;
}>(null);

const selectedVehicleId = computed(() => selectedVehiclePaths.value[1] || '');
const sortedCommitSelectOptions = computed(() => {
  return [...commitSelectOptions.value].sort((left, right) => {
    const leftUnused = left.use_count <= 0 ? 1 : 0;
    const rightUnused = right.use_count <= 0 ? 1 : 0;
    if (leftUnused !== rightUnused) {
      return rightUnused - leftUnused;
    }
    return getCommitUploadedTimestamp(right) - getCommitUploadedTimestamp(left);
  });
});
const recommendedCommitId = computed(
  () => sortedCommitSelectOptions.value[0]?.commit_id || '',
);
const latestUploadedCommitId = computed(() => {
  const latest = [...commitSelectOptions.value].sort(
    (left, right) =>
      getCommitUploadedTimestamp(right) - getCommitUploadedTimestamp(left),
  )[0];
  return latest?.commit_id || '';
});
const selectedCommitItem = computed(
  () =>
    commitSelectOptions.value.find(
      (item) => item.commit_id === selectedCommitId.value,
    ) || null,
);
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
const downstreamTriggerBlockReasons = computed(() => {
  if (domain.value !== 'cockpit') {
    return ['仅座舱 MCU 视图支持触发下游任务'];
  }
  if (selectedPlatformId.value) {
    return ['触发下游任务前请先切换为全部平台'];
  }
  return overviewData.value?.summary.downstream_trigger_block_reasons || [];
});
const canTriggerDownstream = computed(
  () =>
    domain.value === 'cockpit' &&
    activeView.value === 'overview' &&
    !selectedPlatformId.value &&
    Boolean(overviewData.value?.summary.downstream_trigger_enabled),
);
const downstreamTriggerTip = computed(() => {
  if (canTriggerDownstream.value) {
    return '当前座舱 MCU 结果满足下游任务触发条件';
  }
  return (
    downstreamTriggerBlockReasons.value.join('；') ||
    '请先加载座舱 MCU 全量概览'
  );
});

let overviewLoadSeq = 0;
let detailLoadSeq = 0;
let vehicleOptionsLoadSeq = 0;
let vehicleOptionsLoadPromise: null | Promise<void> = null;
let vehicleOptionsLoadedDomain: AutoTestReportDomain | null = null;

function cancelInactiveViewLoads(nextView: AutoTestReportDailyResultsView) {
  if (nextView === 'overview') {
    detailLoadSeq += 1;
    detailLoading.value = false;
    return;
  }

  overviewLoadSeq += 1;
  overviewLoading.value = false;
}

function resetDomainScopedVehicleOptions() {
  vehicleOptionsLoadSeq += 1;
  vehicleOptionsLoadPromise = null;
  vehicleOptionsLoadedDomain = null;
  vehicleOptions.value = [];
  cascaderOptions.value = [];
}

function getVehiclePath(vehicleId: string) {
  const matchedVehicle = vehicleOptions.value.find((v) => v.id === vehicleId);
  return matchedVehicle ? [matchedVehicle.platform_id, matchedVehicle.id] : [];
}

function resetVehicleDetailFilters() {
  selectedStatus.value = [];
  draftStatus.value = [];
  detailSortState.value = null;
  statusPopoverVisible.value = false;
}

function canEditFailureReason(row: DailyResultItem) {
  return Boolean(
    row.result_id && ['failed', 'skip', 'timeout'].includes(row.status),
  );
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
      row.failure_category,
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

async function submitFailureCategory(
  row: DailyResultItem,
  failureCategory?: string,
) {
  if (!row.result_id || !canEditFailureReason(row)) {
    return;
  }
  const nextCategory = (failureCategory || undefined) as
    | FailureCategory
    | undefined;
  row.failure_category = nextCategory;
  await updateDailyResultFailureReasonApi(
    row.result_id,
    row.failure_reason || undefined,
    nextCategory,
  );
  ElMessage.success('根因大类已保存');
  if (activeView.value === 'vehicle') {
    await loadVehicleView();
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
    columns: useOverviewColumns(domain.value),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
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
    columns: useResultColumns(domain.value),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
          if (!selectedVehicleId.value) {
            return { items: [], total: 0 };
          }
          const items =
            (await listDailyResultsApi(
              selectedVehicleId.value,
              selectedDate.value,
              domain.value,
            )) || [];
          let filtered = items;
          if (selectedStatus.value.length > 0) {
            filtered = items.filter((item) =>
              selectedStatus.value.includes(item.status),
            );
          }
          if (
            detailSortState.value?.prop === 'start_time' &&
            detailSortState.value.order
          ) {
            const direction =
              detailSortState.value.order === 'ascending' ? 1 : -1;
            filtered = [...filtered].sort((left, right) => {
              const leftValue = left.start_time
                ? new Date(left.start_time).getTime()
                : Number.NEGATIVE_INFINITY;
              const rightValue = right.start_time
                ? new Date(right.start_time).getTime()
                : Number.NEGATIVE_INFINITY;
              return (leftValue - rightValue) * direction;
            });
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

const [CommitGrid, commitGridApi] = useZqTable({
  tableTitle: 'Commit ID 历史',
  gridOptions: {
    columns: useCommitColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
          const result = await listDownstreamCommitsApi({
            keyword: commitKeyword.value || undefined,
            page: page.currentPage,
            pageSize: page.pageSize,
          });
          return { items: result.items, total: result.total };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: { custom: true, refresh: true, search: false, zoom: true },
  },
  showSearchForm: false,
});

const [CommitUsageGrid, commitUsageGridApi] = useZqTable({
  tableTitle: 'Commit ID 使用记录',
  gridOptions: {
    columns: useCommitUsageColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
          if (!selectedUsageCommit.value) {
            return { items: [], total: 0 };
          }
          const result = await listDownstreamCommitUsagesApi(
            selectedUsageCommit.value.id,
            {
              page: page.currentPage,
              pageSize: page.pageSize,
            },
          );
          return { items: result.items, total: result.total };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 10 },
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
    成功: '#10b981',
    失败: '#ef4444',
    超时: '#f59e0b',
    跳过: '#94a3b8',
    未执行: '#64748b',
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
  if (vehicleOptionsLoadPromise) {
    return vehicleOptionsLoadPromise;
  }

  const requestSeq = ++vehicleOptionsLoadSeq;
  const requestDomain = domain.value;

  const requestPromise = (async () => {
    try {
      const nextVehicleOptions =
        (await listVehicleOptionsApi(requestDomain)) || [];
      if (
        requestSeq !== vehicleOptionsLoadSeq ||
        requestDomain !== domain.value
      ) {
        return;
      }
      vehicleOptions.value = nextVehicleOptions;
    } catch (error) {
      if (
        requestSeq !== vehicleOptionsLoadSeq ||
        requestDomain !== domain.value
      ) {
        return;
      }
      console.error(error);
      ElMessage.error('车型列表加载失败');
      vehicleOptions.value = [];
    }

    if (
      requestSeq !== vehicleOptionsLoadSeq ||
      requestDomain !== domain.value
    ) {
      return;
    }

    vehicleOptionsLoadedDomain = requestDomain;
    rebuildCascaderOptions();

    const currentPlatformIds = new Set(
      platformOptions.value.map((item) => item.value),
    );
    if (
      selectedPlatformId.value &&
      !currentPlatformIds.has(selectedPlatformId.value)
    ) {
      selectedPlatformId.value = '';
    }

    const storedState = getAutoTestReportDailyResultsState(requestDomain);
    const matchedVehicle = vehicleOptions.value.find(
      (item) => item.id === storedState.vehicleId,
    );

    if (matchedVehicle) {
      selectedVehiclePaths.value = getVehiclePath(matchedVehicle.id);
      setAutoTestReportDailyResultsVehicleId(requestDomain, matchedVehicle.id);
      return;
    }

    if (vehicleOptions.value.length > 0) {
      const first = vehicleOptions.value[0]!;
      selectedVehiclePaths.value = [first.platform_id, first.id];
      setAutoTestReportDailyResultsVehicleId(requestDomain, first.id);
      return;
    }

    selectedVehiclePaths.value = [];
    setAutoTestReportDailyResultsVehicleId(requestDomain, '');
    if (activeView.value === 'vehicle' && requestDomain === domain.value) {
      activeView.value = 'overview';
      setAutoTestReportDailyResultsView(requestDomain, 'overview');
    }
  })();

  vehicleOptionsLoadPromise = requestPromise;
  try {
    await requestPromise;
  } finally {
    if (vehicleOptionsLoadPromise === requestPromise) {
      vehicleOptionsLoadPromise = null;
    }
  }
}

async function ensureVehicleOptionsLoaded() {
  if (vehicleOptionsLoadedDomain === domain.value) {
    return;
  }

  if (vehicleOptionsLoadPromise) {
    await vehicleOptionsLoadPromise;
    return;
  }

  await loadVehicleOptions();
}

async function loadOverview() {
  const requestSeq = ++overviewLoadSeq;
  overviewLoading.value = true;
  try {
    const data = await getDailyOverviewApi({
      domain: domain.value,
      execute_date: selectedDate.value,
      platform_id: selectedPlatformId.value || undefined,
      abnormal_only: abnormalOnly.value || undefined,
    });
    if (requestSeq !== overviewLoadSeq) {
      return;
    }
    overviewData.value = data;
    await overviewGridApi.reload();
    if (requestSeq !== overviewLoadSeq) {
      return;
    }
    await nextTick();
    if (requestSeq !== overviewLoadSeq) {
      return;
    }
    renderChart(renderOverviewChart, data.summary.stats);
  } catch (error) {
    if (requestSeq === overviewLoadSeq) {
      console.error(error);
      ElMessage.error('全量数据加载失败');
    }
  } finally {
    if (requestSeq === overviewLoadSeq) {
      overviewLoading.value = false;
    }
  }
}

async function loadVehicleView() {
  const requestSeq = ++detailLoadSeq;
  if (!selectedVehicleId.value) {
    summary.value = null;
    await detailGridApi.reload();
    return;
  }

  detailLoading.value = true;
  try {
    const nextSummary = await getDailySummaryApi(
      selectedVehicleId.value,
      selectedDate.value,
      domain.value,
    );
    if (requestSeq !== detailLoadSeq) {
      return;
    }
    summary.value = nextSummary;
    await detailGridApi.reload();
    if (requestSeq !== detailLoadSeq) {
      return;
    }
    await nextTick();
    if (requestSeq !== detailLoadSeq) {
      return;
    }
    renderChart(renderVehicleChart, nextSummary.stats);
  } catch (error) {
    if (requestSeq === detailLoadSeq) {
      console.error(error);
      ElMessage.error('车型数据加载失败');
    }
  } finally {
    if (requestSeq === detailLoadSeq) {
      detailLoading.value = false;
    }
  }
}

async function loadCurrentView() {
  if (activeView.value === 'overview') {
    await loadOverview();
    return;
  }
  await ensureVehicleOptionsLoaded();
  const nextActiveView = activeView.value as AutoTestReportDailyResultsView;
  if (nextActiveView === 'overview') {
    await loadOverview();
    return;
  }
  await loadVehicleView();
}

async function handleViewChange(next: AutoTestReportDailyResultsView) {
  if (next === activeView.value) {
    return;
  }
  activeView.value = next;
  setAutoTestReportDailyResultsView(domain.value, next);
  if (next !== 'vehicle') {
    historyVisible.value = false;
    historyTitle.value = '';
    currentCaseId.value = '';
    cancelFailureReasonEdit();
  }
  cancelInactiveViewLoads(next);
  await loadCurrentView();
}

function handleOverviewFilterChange() {
  if (activeView.value !== 'overview') {
    return;
  }
  setAutoTestReportDailyResultsView(domain.value, 'overview');
  void loadOverview();
}

function handleVehicleSelectionChange() {
  resetVehicleDetailFilters();
  setAutoTestReportDailyResultsVehicleId(domain.value, selectedVehicleId.value);
  if (activeView.value === 'vehicle') {
    void loadVehicleView();
  }
}

function handleVehicleDateChange() {
  resetVehicleDetailFilters();
  if (activeView.value === 'vehicle') {
    void loadVehicleView();
  }
}

function openHistory(row: DailyResultItem) {
  currentCaseId.value = row.case_id;
  historyTitle.value = `${row.case_no}${row.viu_code ? ` / ${row.viu_code}` : ''}${row.module ? ` / ${row.module}` : ''} / ${row.case_name}`;
  historyVisible.value = true;
}

function handleStatusFilterShow() {
  draftStatus.value = [...selectedStatus.value];
}

async function confirmStatusFilter() {
  selectedStatus.value = [...draftStatus.value];
  statusPopoverVisible.value = false;
  if (activeView.value === 'vehicle') {
    await loadVehicleView();
  }
}

async function resetStatusFilter() {
  draftStatus.value = [];
  selectedStatus.value = [];
  statusPopoverVisible.value = false;
  if (activeView.value === 'vehicle') {
    await loadVehicleView();
  }
}

function handleDetailSortChange(data: {
  order: 'ascending' | 'descending' | null;
  prop?: string;
}) {
  detailSortState.value = data.prop
    ? { order: data.order, prop: data.prop }
    : null;
  if (activeView.value === 'vehicle') {
    void loadVehicleView();
  }
}

function getCommitUploadedTimestamp(item: DownstreamCommitItem) {
  const timestamp = new Date(
    item.last_uploaded_at || item.first_uploaded_at || 0,
  ).getTime();
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function isRecommendedCommit(item: DownstreamCommitItem) {
  return item.commit_id === recommendedCommitId.value;
}

function selectCommit(item: DownstreamCommitItem) {
  selectedCommitId.value = item.commit_id;
}

function formatCommitUseState(item: DownstreamCommitItem) {
  return item.use_count > 0 ? `已使用 ${item.use_count} 次` : '未使用';
}

async function jumpToVehicle(row: DailyOverviewRow) {
  selectedVehiclePaths.value = [row.platform_id, row.vehicle_id];
  resetVehicleDetailFilters();
  setAutoTestReportDailyResultsState(domain.value, {
    activeView: 'vehicle',
    vehicleId: row.vehicle_id,
  });
  await handleViewChange('vehicle');
}

async function loadCommitSelectOptions() {
  commitSelectLoading.value = true;
  try {
    const [uploadedStart, uploadedEnd] = commitSelectUploadedRange.value;
    const result = await listDownstreamCommitsApi({
      keyword: commitSelectKeyword.value || undefined,
      page: commitSelectPage.value,
      pageSize: commitSelectPageSize.value,
      uploaded_end: uploadedEnd || undefined,
      uploaded_start: uploadedStart || undefined,
    });
    commitSelectOptions.value = result.items || [];
    commitSelectTotal.value = result.total || 0;
    selectedCommitId.value = recommendedCommitId.value;
  } finally {
    commitSelectLoading.value = false;
  }
}

async function openCommitSelectDialog() {
  if (!canTriggerDownstream.value) {
    ElMessage.warning(downstreamTriggerTip.value);
    return;
  }
  commitSelectVisible.value = true;
  commitSelectPage.value = 1;
  await loadCommitSelectOptions();
}

async function searchCommitSelectOptions() {
  commitSelectPage.value = 1;
  await loadCommitSelectOptions();
}

async function resetCommitSelectFilters() {
  commitSelectKeyword.value = '';
  commitSelectUploadedRange.value = [];
  commitSelectPage.value = 1;
  await loadCommitSelectOptions();
}

async function triggerDownstream() {
  if (!selectedCommitId.value) {
    ElMessage.warning('请选择 commit-id');
    return;
  }
  downstreamTriggerLoading.value = true;
  try {
    const result = await triggerCockpitDownstreamApi(
      selectedDate.value,
      selectedCommitId.value,
    );
    ElMessage.success(result.message || '下游任务已触发');
    commitSelectVisible.value = false;
    await loadOverview();
    if (commitHistoryVisible.value) {
      await commitGridApi.reload();
    }
  } catch (error) {
    console.error(error);
  } finally {
    downstreamTriggerLoading.value = false;
  }
}

async function openCommitHistory() {
  commitHistoryVisible.value = true;
  await nextTick();
  await loadCommitHistory();
}

async function loadCommitHistory() {
  commitHistoryLoading.value = true;
  try {
    await commitGridApi.reload();
  } finally {
    commitHistoryLoading.value = false;
  }
}

async function searchCommitHistory() {
  await loadCommitHistory();
}

async function resetCommitHistorySearch() {
  commitKeyword.value = '';
  await loadCommitHistory();
}

async function openCommitUsage(row: DownstreamCommitItem) {
  selectedUsageCommit.value = row;
  commitUsageVisible.value = true;
  await nextTick();
  commitUsageLoading.value = true;
  try {
    await commitUsageGridApi.reload();
  } finally {
    commitUsageLoading.value = false;
  }
}

watch(vehicleKeyword, () => {
  rebuildCascaderOptions();
});

watch(
  domain,
  () => {
    activeView.value = 'overview';
    setAutoTestReportDailyResultsView(domain.value, 'overview');
    overviewData.value = null;
    summary.value = null;
    selectedPlatformId.value = '';
    selectedVehiclePaths.value = [];
    vehicleKeyword.value = '';
    historyVisible.value = false;
    historyTitle.value = '';
    currentCaseId.value = '';
    cancelFailureReasonEdit();
    resetVehicleDetailFilters();
    resetDomainScopedVehicleOptions();
    cancelInactiveViewLoads('overview');
    overviewGridApi.setGridOptions({
      columns: useOverviewColumns(domain.value),
    });
    detailGridApi.setGridOptions({
      columns: useResultColumns(domain.value),
    });
    void loadVehicleOptions();
    void loadCurrentView();
  },
  { immediate: false },
);

onMounted(async () => {
  if (activeView.value === 'overview') {
    void loadVehicleOptions();
    await loadCurrentView();
    return;
  }

  await loadVehicleOptions();
  await loadCurrentView();
});
</script>

<template>
  <Page auto-content-height content-class="flex min-w-0 flex-col">
    <div class="flex h-full min-h-0 min-w-0 flex-col gap-4">
      <div class="shrink-0 rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div class="text-base font-semibold text-gray-900">
              {{ domainMeta.badge }} · 每日执行结果
            </div>
            <div class="text-sm text-gray-500">
              先看全量异常，再下钻到单车型明细。
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <DomainSwitcher />
            <div
              class="flex items-center gap-2 rounded-full bg-gray-50 px-3 py-2"
            >
              <span class="text-sm text-gray-500">查看模式</span>
              <ElSegmented
                v-model="activeViewModel"
                :options="viewOptions"
                size="default"
              />
            </div>
          </div>
        </div>

        <div class="mt-4 rounded-xl bg-gray-50/60 px-4 py-3">
          <template v-if="activeView === 'overview'">
            <div class="flex flex-wrap items-center gap-3">
              <ElForm
                :inline="true"
                class="flex flex-wrap items-center gap-3"
                @submit.prevent
              >
                <ElFormItem label="执行日期" class="!mb-0">
                  <ElDatePicker
                    v-model="selectedDate"
                    class="!w-[160px]"
                    type="date"
                    value-format="YYYY-MM-DD"
                    @change="handleOverviewFilterChange"
                  />
                </ElFormItem>
                <ElFormItem :label="domainMeta.platformLabel" class="!mb-0">
                  <ElSelect
                    v-model="selectedPlatformId"
                    clearable
                    class="!w-[220px]"
                    :placeholder="`全部${domainMeta.platformLabel}`"
                    @change="handleOverviewFilterChange"
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
                  <ElSwitch
                    v-model="abnormalOnly"
                    @change="handleOverviewFilterChange"
                  />
                </ElFormItem>
              </ElForm>
              <div class="ml-auto flex items-center gap-2">
                <ElTooltip
                  v-if="domain === 'cockpit'"
                  :content="downstreamTriggerTip"
                  placement="top"
                >
                  <span>
                    <ElButton
                      :disabled="!canTriggerDownstream"
                      :loading="commitSelectLoading"
                      type="success"
                      @click="openCommitSelectDialog"
                    >
                      触发下游任务
                    </ElButton>
                  </span>
                </ElTooltip>
                <ElButton
                  v-if="domain === 'cockpit'"
                  @click="openCommitHistory"
                >
                  Commit ID 历史
                </ElButton>
                <ElButton
                  :loading="overviewLoading"
                  type="primary"
                  @click="loadOverview"
                >
                  刷新
                </ElButton>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="flex flex-wrap items-center gap-3">
              <ElForm
                :inline="true"
                class="flex flex-wrap items-center gap-3"
                @submit.prevent
              >
                <ElFormItem :label="domainMeta.selectorLabel" class="!mb-0">
                  <ElCascader
                    v-model="selectedVehiclePaths"
                    class="w-[320px]"
                    clearable
                    filterable
                    :placeholder="domainMeta.selectorPlaceholder"
                    :options="cascaderOptions"
                    :props="{ emitPath: true }"
                    @change="handleVehicleSelectionChange"
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
                    class="!w-[160px]"
                    placeholder="选择日期"
                    type="date"
                    value-format="YYYY-MM-DD"
                    @change="handleVehicleDateChange"
                  />
                </ElFormItem>
              </ElForm>
              <div class="ml-auto flex items-center gap-2">
                <ElButton
                  :loading="detailLoading"
                  type="primary"
                  @click="loadVehicleView"
                >
                  刷新
                </ElButton>
              </div>
            </div>
          </template>
        </div>
      </div>

      <template v-if="activeView === 'overview'">
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
              <template #cell-non_version_failure_count="{ row }">
                <ElTag
                  :type="
                    row.non_version_failure_count > 0 ? 'warning' : 'success'
                  "
                >
                  {{ row.non_version_failure_count }}
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
        <div
          v-loading="detailLoading"
          class="flex min-h-0 flex-1 flex-col gap-4"
        >
          <template v-if="summary">
            <div class="grid min-h-0 flex-1 grid-cols-[1fr_400px] gap-4">
              <div class="h-full min-h-0 min-w-0">
                <DetailGrid
                  class="h-full rounded-lg border-0 shadow-sm"
                  @sort-change="handleDetailSortChange"
                >
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
                    <ElTag :type="RESULT_TAG_MAP[row.status] || 'info'">
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
                  <template #cell-failure_category="{ row }">
                    <ElSelect
                      v-if="canEditFailureReason(row)"
                      v-model="row.failure_category"
                      clearable
                      placeholder="请选择"
                      size="small"
                      @change="submitFailureCategory(row, $event)"
                    >
                      <ElOption
                        v-for="item in FAILURE_CATEGORY_OPTIONS"
                        :key="item.value"
                        :label="item.label"
                        :value="item.value"
                      />
                    </ElSelect>
                    <span v-else class="text-gray-400">
                      {{
                        row.failure_category
                          ? FAILURE_CATEGORY_LABEL_MAP[row.failure_category]
                          : '-'
                      }}
                    </span>
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
                  <template #cell-car_log_url="{ row }">
                    <ElLink
                      v-if="row.car_log_url"
                      :href="row.car_log_url"
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

    <ElDialog
      v-model="commitSelectVisible"
      title="选择 Commit ID"
      width="720px"
    >
      <div v-loading="commitSelectLoading" class="space-y-4">
        <div class="grid gap-3 md:grid-cols-[1fr_260px_auto]">
          <ElInput
            v-model="commitSelectKeyword"
            clearable
            placeholder="按 Commit ID 搜索"
            @keyup.enter="searchCommitSelectOptions"
          />
          <ElDatePicker
            v-model="commitSelectUploadedRange"
            class="!w-full"
            end-placeholder="结束上传日期"
            range-separator="至"
            start-placeholder="开始上传日期"
            type="daterange"
            value-format="YYYY-MM-DD"
          />
          <div class="flex gap-2">
            <ElButton type="primary" @click="searchCommitSelectOptions">
              查询
            </ElButton>
            <ElButton @click="resetCommitSelectFilters">重置</ElButton>
          </div>
        </div>
        <div
          v-if="sortedCommitSelectOptions.length > 0"
          class="max-h-[420px] space-y-3 overflow-y-auto pr-1"
        >
          <button
            v-for="item in sortedCommitSelectOptions"
            :key="item.id"
            class="hover:border-primary hover:bg-primary/5 w-full rounded border px-4 py-3 text-left transition"
            :class="
              selectedCommitId === item.commit_id
                ? 'border-primary bg-primary/5 shadow-sm'
                : 'border-gray-200 bg-white'
            "
            type="button"
            @click="selectCommit(item)"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="break-all font-mono text-sm text-gray-900">
                    {{ item.commit_id }}
                  </span>
                  <ElTag
                    v-if="isRecommendedCommit(item)"
                    effect="dark"
                    size="small"
                    type="success"
                  >
                    推荐
                  </ElTag>
                  <ElTag
                    :type="item.use_count > 0 ? 'info' : 'success'"
                    size="small"
                  >
                    {{ formatCommitUseState(item) }}
                  </ElTag>
                  <ElTag
                    v-if="item.commit_id === latestUploadedCommitId"
                    size="small"
                    type="primary"
                  >
                    最近上传
                  </ElTag>
                </div>
                <div
                  class="mt-2 grid gap-2 text-xs text-gray-500 sm:grid-cols-2"
                >
                  <span>最近上传：{{ item.last_uploaded_at || '-' }}</span>
                  <span>首次上传：{{ item.first_uploaded_at || '-' }}</span>
                  <span>上传次数：{{ item.upload_count }}</span>
                  <span>最近使用：{{ item.last_used_at || '-' }}</span>
                </div>
              </div>
              <span
                class="mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border"
                :class="
                  selectedCommitId === item.commit_id
                    ? 'border-primary bg-primary'
                    : 'border-gray-300'
                "
              >
                <span
                  v-if="selectedCommitId === item.commit_id"
                  class="h-1.5 w-1.5 rounded-full bg-white"
                ></span>
              </span>
            </div>
          </button>
        </div>
        <div
          v-if="selectedCommitItem"
          class="rounded border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-blue-700"
        >
          将使用
          <span class="font-mono">{{ selectedCommitItem.commit_id }}</span>
          触发 {{ selectedDate }} 的座舱下游任务
        </div>
        <ElEmpty
          v-if="!commitSelectLoading && sortedCommitSelectOptions.length === 0"
          description="暂无可用 Commit ID"
        />
        <div
          v-if="commitSelectTotal > 0"
          class="flex justify-end border-t border-gray-100 pt-3"
        >
          <ElPagination
            v-model:current-page="commitSelectPage"
            v-model:page-size="commitSelectPageSize"
            :page-sizes="[5, 10, 20]"
            :total="commitSelectTotal"
            background
            layout="total, sizes, prev, pager, next"
            @current-change="loadCommitSelectOptions"
            @size-change="searchCommitSelectOptions"
          />
        </div>
      </div>
      <template #footer>
        <ElButton @click="commitSelectVisible = false">取消</ElButton>
        <ElButton
          :disabled="!selectedCommitId"
          :loading="downstreamTriggerLoading"
          type="primary"
          @click="triggerDownstream"
        >
          确认触发
        </ElButton>
      </template>
    </ElDialog>

    <ElDrawer v-model="commitHistoryVisible" title="Commit ID 历史" size="80%">
      <div class="flex h-full min-h-0 flex-col gap-3">
        <div class="flex shrink-0 items-center gap-2">
          <ElInput
            v-model="commitKeyword"
            class="!w-[320px]"
            clearable
            placeholder="搜索 Commit ID"
            @keyup.enter="searchCommitHistory"
          />
          <ElButton type="primary" @click="searchCommitHistory">查询</ElButton>
          <ElButton @click="resetCommitHistorySearch">重置</ElButton>
        </div>
        <CommitGrid v-loading="commitHistoryLoading" class="h-full min-h-0">
          <template #cell-commit_id="{ row }">
            <span class="font-mono text-xs">{{ row.commit_id }}</span>
          </template>
          <template #cell-last_used_at="{ row }">
            {{ row.last_used_at || '-' }}
          </template>
          <template #cell-actions="{ row }">
            <ElButton link type="primary" @click="openCommitUsage(row)">
              使用记录
            </ElButton>
          </template>
        </CommitGrid>
      </div>
    </ElDrawer>

    <ElDrawer
      v-model="commitUsageVisible"
      :title="`使用记录${selectedUsageCommit ? ` - ${selectedUsageCommit.commit_id}` : ''}`"
      size="70%"
    >
      <CommitUsageGrid v-loading="commitUsageLoading" class="h-full min-h-0">
        <template #cell-trigger_type="{ row }">
          {{ row.trigger_type === 'scheduled' ? '定时触发' : '人工触发' }}
        </template>
        <template #cell-success="{ row }">
          <ElTag :type="row.success ? 'success' : 'danger'">
            {{ row.success ? '成功' : '失败' }}
          </ElTag>
        </template>
        <template #cell-message="{ row }">
          <span class="block truncate text-left">{{ row.message || '-' }}</span>
        </template>
      </CommitUsageGrid>
    </ElDrawer>

    <TestCaseHistoryDrawer
      v-model:visible="historyVisible"
      :case-id="currentCaseId"
      :title="historyTitle"
    />
  </Page>
</template>
