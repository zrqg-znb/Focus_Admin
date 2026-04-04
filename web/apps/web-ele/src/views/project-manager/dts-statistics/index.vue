<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  DtsDictOptions,
  DtsMergedDefect,
  DtsStatisticsFilters,
  DtsSummary,
} from '#/api/project-manager/dts-statistics';

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElCard,
  ElCheckbox,
  ElCheckboxGroup,
  ElDatePicker,
  ElEmpty,
  ElMessage,
  ElOption,
  ElPopover,
  ElProgress,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTooltip,
} from 'element-plus';

import {
  exportDtsStatistics,
  getDtsList,
  getDtsSummary,
} from '#/api/project-manager/dts-statistics';
import { useZqTable } from '#/components/zq-table';

import {
  fetchDtsDictOptionsCached,
  resolveDtsGovernanceTagMeta,
  resolveSeverityMeta,
  useColumns,
} from './data';
import DtsEditDrawer from './DtsEditDrawer.vue';

defineOptions({ name: 'DtsStatistics' });

type TabKey = 'dashboard' | 'list';

const PRODUCT_OPTIONS = [
  { label: '座舱', value: '250539396', disabled: false },
  { label: '车控', value: '250539397', disabled: false },
  { label: '全部（暂不支持）', value: 'ALL', disabled: true },
];

const FLOW_STATE_OPTIONS: Array<{ label: string; value: string }> = [
  { value: 'DTS001', label: '问题提交人填写' },
  { value: 'DTS002', label: '测试(项目)经理审核' },
  { value: 'DTS003', label: '项目经理审核' },
  { value: 'DTS004', label: '开发人员定位' },
  { value: 'DTS005', label: '项目经理审核定位' },
  { value: 'DTS006', label: '开发人员方案审计' },
  { value: 'DTS007', label: 'CCB方案审核' },
  { value: 'DTS008', label: '评审专家在线评审' },
  { value: 'DTS009', label: '开发人员审核修改' },
  { value: 'DTS010', label: '审核人员审核修改' },
  { value: 'DTS011', label: 'CMO归档' },
  { value: 'DTS012', label: '测试经理组织测试' },
  { value: 'DTS013', label: '测试人员回归测试' },
  { value: 'DTS014', label: '确认问题单' },
  { value: 'DTS015', label: '制定修补计划' },
  { value: 'FS99', label: '关闭' },
  { value: 'FS01', label: '撤销' },
];

const SEVERITY_OPTIONS: Array<{ label: string; value: string }> = [
  { value: 'Suggestion', label: '提示' },
  { value: 'Minor', label: '一般' },
  { value: 'Major', label: '严重' },
  { value: 'Critical', label: '关键' },
];

function createDefaultDateRange(): [Date, Date] {
  const end = new Date();
  const start = new Date(end);
  start.setMonth(start.getMonth() - 1);
  return [start, end];
}

function toTimestampMs(date: Date) {
  return Math.max(Math.floor(date.getTime()), 0);
}

function createDefaultFilters(): DtsStatisticsFilters {
  const [start, end] = createDefaultDateRange();
  return {
    productId: '250539396',
    flowStates: ['FS99'],
    severityNos: [],
    updateTimeBegin: toTimestampMs(start),
    updateTimeEnd: toTimestampMs(end),
  };
}

const activeTab = ref<TabKey>('list');

const editVisible = ref(false);
const editingRow = ref<DtsMergedDefect | null>(null);

const dateRange = ref<[Date, Date] | null>(createDefaultDateRange());
const filters = ref<DtsStatisticsFilters>(createDefaultFilters());

const appliedFilters = ref<DtsStatisticsFilters | null>(null);
const summaryFingerprint = ref('');
const summary = ref<DtsSummary>({
  total_count: 0,
  open_count: 0,
  closed_count: 0,
  avg_process_days: 0,
  qa_filled_count: 0,
  qa_completion_rate: 0,
  dev_analyzed_count: 0,
  dev_analysis_completion_rate: 0,
  test_analyzed_count: 0,
  test_analysis_completion_rate: 0,
  severity_dist: [],
  status_dist: [],
  team_dist: [],
  stage_dist: [],
  close_type_dist: [],
  handler_dist: [],
  qa_category_dist: [],
  dev_sub_category_dist: [],
  test_miss_reason_dist: [],
  pl_group_dist: [],
  project_dist: [],
  action_status_dist: [],
});
const summaryLoading = ref(false);
const exportLoading = ref(false);
const dictOptions = ref<DtsDictOptions | null>(null);

function resolveGovTag(field: any, raw: unknown) {
  return resolveDtsGovernanceTagMeta(dictOptions.value, field, raw);
}

function openEdit(row: DtsMergedDefect) {
  editingRow.value = row;
  editVisible.value = true;
}

function normalizeStringArray(values?: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of values || []) {
    const text = String(item || '').trim();
    if (!text || seen.has(text)) {
      continue;
    }
    seen.add(text);
    result.push(text);
  }
  return result;
}

function cloneFilters(source: DtsStatisticsFilters): DtsStatisticsFilters {
  let begin = Number(source.updateTimeBegin || 0);
  let end = Number(source.updateTimeEnd || 0);
  if (begin > end) {
    const temp = begin;
    begin = end;
    end = temp;
  }
  return {
    productId: String(source.productId || '250539396'),
    flowStates: normalizeStringArray(source.flowStates),
    severityNos: normalizeStringArray(source.severityNos),
    updateTimeBegin: Math.max(begin, 0),
    updateTimeEnd: Math.max(end, 0),
  };
}

function buildFingerprint(payload: DtsStatisticsFilters | null) {
  if (!payload) {
    return '';
  }
  return JSON.stringify({
    productId: payload.productId || '',
    flowStates: [...(payload.flowStates || [])].sort(),
    severityNos: [...(payload.severityNos || [])].sort(),
    updateTimeBegin: payload.updateTimeBegin || 0,
    updateTimeEnd: payload.updateTimeEnd || 0,
  });
}

async function loadDictOptions() {
  try {
    dictOptions.value = await fetchDtsDictOptionsCached();
  } catch (error) {
    console.error(error);
    dictOptions.value = null;
  }
}

watch(
  dateRange,
  (value) => {
    if (value && value.length === 2) {
      filters.value.updateTimeBegin = toTimestampMs(value[0]);
      filters.value.updateTimeEnd = toTimestampMs(value[1]);
      return;
    }
    const [start, end] = createDefaultDateRange();
    filters.value.updateTimeBegin = toTimestampMs(start);
    filters.value.updateTimeEnd = toTimestampMs(end);
  },
  { immediate: true },
);

const hasAppliedFilters = computed(() => Boolean(appliedFilters.value));

async function fetchSummary(force = false) {
  if (!appliedFilters.value) {
    summary.value = {
      ...summary.value,
      total_count: 0,
      open_count: 0,
      closed_count: 0,
      avg_process_days: 0,
      qa_filled_count: 0,
      qa_completion_rate: 0,
      dev_analyzed_count: 0,
      dev_analysis_completion_rate: 0,
      test_analyzed_count: 0,
      test_analysis_completion_rate: 0,
      severity_dist: [],
      status_dist: [],
      team_dist: [],
      stage_dist: [],
      close_type_dist: [],
      handler_dist: [],
      qa_category_dist: [],
      dev_sub_category_dist: [],
      test_miss_reason_dist: [],
      pl_group_dist: [],
      project_dist: [],
      action_status_dist: [],
    };
    summaryFingerprint.value = '';
    return;
  }

  const currentFingerprint = buildFingerprint(appliedFilters.value);
  if (!force && summaryFingerprint.value === currentFingerprint) {
    return;
  }
  summaryLoading.value = true;
  try {
    summary.value = await getDtsSummary(appliedFilters.value);
    summaryFingerprint.value = currentFingerprint;
  } catch (error) {
    console.error(error);
    ElMessage.error('加载总结看板失败');
  } finally {
    summaryLoading.value = false;
  }
}

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    columns: useColumns(),
    border: true,
    stripe: true,
    rowKey: 'defectNo',
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
          if (!appliedFilters.value) {
            return { items: [], total: 0 };
          }
          const response = await getDtsList({
            ...appliedFilters.value,
            pageIndex: page.currentPage,
            pageSize: page.pageSize,
          });
          return { items: response.items || [], total: response.total || 0 };
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [20, 50, 100, 200, 500],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  },
});

const listLoading = computed(() => gridApi.loading.value);
const dataResultCount = computed(() => Number(gridApi.total.value || 0));
const canExport = computed(
  () =>
    hasAppliedFilters.value &&
    dataResultCount.value > 0 &&
    !exportLoading.value,
);
const selectedFlowStateLabel = computed(() => {
  const count = filters.value.flowStates.length;
  if (count === 0) {
    return '全部状态';
  }
  return `状态（${count}）`;
});
const selectedSeverityLabel = computed(() => {
  const count = filters.value.severityNos.length;
  if (count === 0) {
    return '全部级别';
  }
  return `级别（${count}）`;
});
const selectedProductLabel = computed(() => {
  return (
    PRODUCT_OPTIONS.find((item) => item.value === filters.value.productId)
      ?.label || '座舱'
  );
});

const flowFilterVisible = ref(false);
const severityFilterVisible = ref(false);
const draftFlowStates = ref<string[]>([]);
const draftSeverityNos = ref<string[]>([]);

let autoReloadTimer: null | number = null;

watch(
  () => gridApi.tableData.value.length,
  async () => {
    await nextTick();
    updateDataGridHeight();
  },
);

const dataGridWrapRef = ref<HTMLDivElement>();
const dataGridHeight = ref<null | number>(null);

const dataGridWrapStyle = computed(() => {
  if (!dataGridHeight.value) {
    return undefined;
  }
  return { height: `${dataGridHeight.value}px` };
});

let resizeTimer: null | number = null;

function updateDataGridHeight() {
  if (!dataGridWrapRef.value || activeTab.value !== 'list') {
    dataGridHeight.value = null;
    return;
  }
  const rect = dataGridWrapRef.value.getBoundingClientRect();
  const bottomOffset = 24;
  const available = window.innerHeight - rect.top - bottomOffset;
  dataGridHeight.value = Math.max(320, Math.floor(available));
}

function handleResize() {
  if (resizeTimer) {
    window.clearTimeout(resizeTimer);
  }
  resizeTimer = window.setTimeout(() => {
    updateDataGridHeight();
  }, 120);
}

function scheduleAutoReload() {
  if (autoReloadTimer) {
    window.clearTimeout(autoReloadTimer);
  }
  autoReloadTimer = window.setTimeout(() => {
    void handleSearch(true);
  }, 260);
}

watch(
  () => ({
    productId: filters.value.productId,
    updateTimeBegin: filters.value.updateTimeBegin,
    updateTimeEnd: filters.value.updateTimeEnd,
  }),
  () => {
    if (!filters.value.productId || filters.value.productId === 'ALL') {
      return;
    }
    scheduleAutoReload();
  },
  { deep: true },
);

watch(
  () => flowFilterVisible.value,
  (visible) => {
    if (visible) {
      draftFlowStates.value = [...filters.value.flowStates];
    }
  },
);

watch(
  () => severityFilterVisible.value,
  (visible) => {
    if (visible) {
      draftSeverityNos.value = [...filters.value.severityNos];
    }
  },
);

watch(
  () => activeTab.value,
  (tab) => {
    if (tab === 'dashboard') {
      void fetchSummary();
    }
    void nextTick().then(() => updateDataGridHeight());
  },
);

async function handleSearch(resetPage = true) {
  if (autoReloadTimer) {
    window.clearTimeout(autoReloadTimer);
    autoReloadTimer = null;
  }
  const payload = cloneFilters(filters.value);

  appliedFilters.value = payload;
  summaryFingerprint.value = '';
  if (resetPage) {
    gridApi.pagination.currentPage = 1;
  }
  await nextTick();
  await gridApi.reload();
  await nextTick();
  updateDataGridHeight();
  if (activeTab.value === 'dashboard') {
    await fetchSummary(true);
  }
}

async function handleReset() {
  if (autoReloadTimer) {
    window.clearTimeout(autoReloadTimer);
    autoReloadTimer = null;
  }
  const nextFilters = createDefaultFilters();
  filters.value = createDefaultFilters();
  dateRange.value = [
    new Date(nextFilters.updateTimeBegin),
    new Date(nextFilters.updateTimeEnd),
  ];
  await handleSearch(true);
}

async function confirmFlowFilter() {
  filters.value.flowStates = normalizeStringArray(draftFlowStates.value);
  flowFilterVisible.value = false;
  await handleSearch(true);
}

function resetFlowFilterDraft() {
  draftFlowStates.value = [];
}

async function confirmSeverityFilter() {
  filters.value.severityNos = normalizeStringArray(draftSeverityNos.value);
  severityFilterVisible.value = false;
  await handleSearch(true);
}

function resetSeverityFilterDraft() {
  draftSeverityNos.value = [];
}

function buildExportFilename() {
  const current = new Date();
  const pad = (value: number) => String(value).padStart(2, '0');
  return `DTS统计明细-${current.getFullYear()}${pad(current.getMonth() + 1)}${pad(current.getDate())}-${pad(current.getHours())}${pad(current.getMinutes())}${pad(current.getSeconds())}.xlsx`;
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(new Blob([blob]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.append(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

async function handleExport() {
  if (!appliedFilters.value) {
    ElMessage.warning('请先查询明细数据');
    return;
  }
  if (dataResultCount.value <= 0) {
    ElMessage.warning('当前没有可导出的数据');
    return;
  }

  exportLoading.value = true;
  try {
    const blob = await exportDtsStatistics(appliedFilters.value);
    triggerBlobDownload(blob as Blob, buildExportFilename());
    ElMessage.success('导出成功');
  } catch (error) {
    console.error(error);
    ElMessage.error('导出失败，请检查筛选条件后重试');
  } finally {
    exportLoading.value = false;
  }
}

function handleSaved() {
  gridApi.reload();
  if (activeTab.value === 'dashboard') {
    void fetchSummary(true);
  }
}

function formatArrayCell(value: unknown) {
  const items = Array.isArray(value) ? value : [];
  const normalized = items
    .map((item) => String(item || '').trim())
    .filter(Boolean);
  return {
    text: normalized.join(', '),
    tooltip: normalized.join('\n'),
  };
}

function formatArrayTooltip(value: unknown) {
  return formatArrayCell(value).tooltip;
}

function takeFirstTwo(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.slice(0, 2).map((item) => String(item || '').trim());
}

const severityChartRef = ref<EchartsUIType>();
const { renderEcharts: renderSeverityChart } = useEcharts(severityChartRef);
const statusChartRef = ref<EchartsUIType>();
const { renderEcharts: renderStatusChart } = useEcharts(statusChartRef);
const teamChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTeamChart } = useEcharts(teamChartRef);
const stageChartRef = ref<EchartsUIType>();
const { renderEcharts: renderStageChart } = useEcharts(stageChartRef);
const closeTypeChartRef = ref<EchartsUIType>();
const { renderEcharts: renderCloseTypeChart } = useEcharts(closeTypeChartRef);
const handlerChartRef = ref<EchartsUIType>();
const { renderEcharts: renderHandlerChart } = useEcharts(handlerChartRef);
const qaCategoryChartRef = ref<EchartsUIType>();
const { renderEcharts: renderQaCategoryChart } = useEcharts(qaCategoryChartRef);
const plGroupChartRef = ref<EchartsUIType>();
const { renderEcharts: renderPlGroupChart } = useEcharts(plGroupChartRef);
const projectChartRef = ref<EchartsUIType>();
const { renderEcharts: renderProjectChart } = useEcharts(projectChartRef);
const actionStatusChartRef = ref<EchartsUIType>();
const { renderEcharts: renderActionStatusChart } =
  useEcharts(actionStatusChartRef);
const devSubCategoryChartRef = ref<EchartsUIType>();
const { renderEcharts: renderDevSubCategoryChart } = useEcharts(
  devSubCategoryChartRef,
);
const testMissReasonChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTestMissReasonChart } = useEcharts(
  testMissReasonChartRef,
);

function renderEmptyChart(
  render: (options: Record<string, any>) => void,
  title: string,
) {
  render({
    title: {
      text: title,
      left: 'center',
      top: 'middle',
      textStyle: {
        color: '#94a3b8',
        fontSize: 14,
        fontWeight: 400,
      },
    },
    xAxis: { show: false },
    yAxis: { show: false },
    series: [],
  });
}

function renderDistBar(
  render: (options: Record<string, any>) => void,
  rows: Array<{ label: string; value: number }>,
  title: string,
  color: string,
) {
  if (!rows || rows.length === 0) {
    renderEmptyChart(render, `暂无${title}`);
    return;
  }
  const labels = rows.map((item) => item.label);
  const values = rows.map((item) => item.value);
  const total = values.reduce(
    (sum, value) => sum + (Number.isFinite(value) ? value : 0),
    0,
  );
  const enableZoom = labels.length > 12;

  const formatRate = (value: number) => {
    if (!total) {
      return '';
    }
    return `${((value / total) * 100).toFixed(1)}%`;
  };

  render({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const first = Array.isArray(params) ? params[0] : params;
        const name = String(first?.axisValue ?? first?.name ?? '');
        const value = Number(first?.value ?? 0);
        const rate = formatRate(value);
        return rate ? `${name}<br/>${value} (${rate})` : `${name}<br/>${value}`;
      },
    },
    grid: {
      left: 12,
      right: enableZoom ? 40 : 12,
      top: 16,
      bottom: 12,
      containLabel: true,
    },
    dataZoom: enableZoom
      ? [
          {
            type: 'slider',
            yAxisIndex: 0,
            orient: 'vertical',
            right: 8,
            top: 56,
            bottom: 12,
            start: 0,
            end: 100,
            width: 10,
          },
          {
            type: 'inside',
            yAxisIndex: 0,
            orient: 'vertical',
            start: 0,
            end: 100,
          },
        ]
      : [],
    xAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLabel: { color: '#64748b', fontSize: 11 },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: values,
        barMaxWidth: 18,
        itemStyle: { color },
        label: {
          show: true,
          position: 'right',
          color: '#475569',
          formatter: (params: any) => {
            const value = Number(params?.value ?? 0);
            const rate = formatRate(value);
            return rate ? `${value} (${rate})` : String(value);
          },
        },
      },
    ],
  });
}

const canRenderCharts = computed(
  () =>
    activeTab.value === 'dashboard' &&
    hasAppliedFilters.value &&
    summary.value.total_count > 0,
);

watch(
  [canRenderCharts, () => summary.value.severity_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderSeverityChart, rows, '严重程度分布', '#f87171');
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.status_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderStatusChart, rows, '状态分布', '#60a5fa');
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.stage_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderStageChart, rows, '阶段分布', '#94a3b8');
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.close_type_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderCloseTypeChart, rows, '关闭类型分布', '#f97316');
  },
  { deep: true, immediate: true },
);

watch(
  [canRenderCharts, () => summary.value.project_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderProjectChart, rows, '项目分布', '#fbbf24');
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.team_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderTeamChart, rows, '团队分布', '#22c55e');
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.handler_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderHandlerChart, rows, '处理人 Top', '#8b5cf6');
  },
  { deep: true, immediate: true },
);

watch(
  [canRenderCharts, () => summary.value.qa_category_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderQaCategoryChart, rows, 'QA类目分布', '#34d399');
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.pl_group_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderPlGroupChart, rows, '责任PL组分布', '#a78bfa');
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.action_status_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderActionStatusChart, rows, '措施状态分布', '#fb7185');
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.dev_sub_category_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(
      renderDevSubCategoryChart,
      rows,
      '开发问题小类 Top',
      '#38bdf8',
    );
  },
  { deep: true, immediate: true },
);
watch(
  [canRenderCharts, () => summary.value.test_miss_reason_dist] as const,
  ([ready, rows]) => {
    if (!ready) return;
    renderDistBar(renderTestMissReasonChart, rows, '漏测原因 Top', '#4ade80');
  },
  { deep: true, immediate: true },
);

onMounted(() => {
  void loadDictOptions();
  void handleSearch(true);
  updateDataGridHeight();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (resizeTimer) {
    window.clearTimeout(resizeTimer);
  }
  if (autoReloadTimer) {
    window.clearTimeout(autoReloadTimer);
  }
});
</script>

<template>
  <Page auto-content-height>
    <div class="dts-statistics-shell flex flex-col gap-4">
      <ElTabs v-model="activeTab" class="dts-statistics-tabs flex flex-col">
        <ElTabPane label="数据明细" name="list">
          <ElCard shadow="never" class="dts-data-card">
            <template #header>
              <div class="dts-data-card__header">
                <div>
                  <div class="dts-data-card__title">DTS 明细表</div>
                  <div class="dts-data-card__desc">
                    筛选入口已集成到表头与标题栏；查询后明细表与统计看板复用同一组条件。
                  </div>
                </div>
                <div class="dts-data-card__actions">
                  <ElButton
                    type="primary"
                    plain
                    :disabled="!canExport"
                    :loading="exportLoading"
                    @click="handleExport"
                  >
                    导出当前查询结果
                  </ElButton>
                  <ElTag
                    class="dts-data-card__status"
                    :effect="hasAppliedFilters ? 'light' : 'plain'"
                    :type="hasAppliedFilters ? 'success' : 'info'"
                  >
                    {{
                      hasAppliedFilters
                        ? `已加载 ${dataResultCount} 条结果`
                        : '等待查询'
                    }}
                  </ElTag>
                </div>
              </div>
            </template>

            <div class="dts-data-card__body">
              <div
                ref="dataGridWrapRef"
                class="dts-data-grid-wrap"
                :style="dataGridWrapStyle"
              >
                <Grid class="dts-data-grid h-full min-h-0">
                  <template #table-title>
                    <div class="dts-table-title">
                      <div class="dts-table-title__filters">
                        <div class="dts-table-title__field">
                          <span class="dts-table-title__label">产品线</span>
                          <ElSelect
                            v-model="filters.productId"
                            size="small"
                            class="dts-table-title__select"
                            placeholder="选择产品线"
                          >
                            <ElOption
                              v-for="item in PRODUCT_OPTIONS"
                              :key="item.value"
                              :label="item.label"
                              :value="item.value"
                              :disabled="item.disabled"
                            />
                          </ElSelect>
                        </div>
                        <div class="dts-table-title__field">
                          <span class="dts-table-title__label">时间区间</span>
                          <ElDatePicker
                            v-model="dateRange"
                            type="datetimerange"
                            unlink-panels
                            size="small"
                            class="dts-table-title__date"
                            start-placeholder="开始时间"
                            end-placeholder="结束时间"
                            range-separator="-"
                            format="YYYY-MM-DD HH:mm:ss"
                          />
                        </div>
                        <div class="dts-table-title__actions">
                          <ElButton
                            type="primary"
                            size="small"
                            :loading="listLoading"
                            @click="handleSearch(true)"
                          >
                            立即刷新
                          </ElButton>
                          <ElButton size="small" @click="handleReset">
                            重置
                          </ElButton>
                        </div>
                      </div>
                      <div class="dts-table-title__meta">
                        <ElTag type="info" effect="plain">
                          当前产品：{{ selectedProductLabel }}
                        </ElTag>
                        <ElTag type="success" effect="plain">
                          状态：{{ selectedFlowStateLabel }}
                        </ElTag>
                        <ElTag type="warning" effect="plain">
                          严重程度：{{ selectedSeverityLabel }}
                        </ElTag>
                      </div>
                    </div>
                  </template>

                  <template #header-currentStatus>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">状态</span>
                      <ElPopover
                        v-model:visible="flowFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="280"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.flowStates.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{
                                filters.flowStates.length > 0
                                  ? `${filters.flowStates.length} 项`
                                  : '全部'
                              }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElCheckboxGroup
                              v-model="draftFlowStates"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in FLOW_STATE_OPTIONS"
                                :key="item.value"
                                :label="item.value"
                                :value="item.value"
                              >
                                {{ item.label }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetFlowFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmFlowFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-severity>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">严重程度</span>
                      <ElPopover
                        v-model:visible="severityFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="240"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.severityNos.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{
                                filters.severityNos.length > 0
                                  ? `${filters.severityNos.length} 项`
                                  : '全部'
                              }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElCheckboxGroup
                              v-model="draftSeverityNos"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in SEVERITY_OPTIONS"
                                :key="item.value"
                                :label="item.value"
                                :value="item.value"
                              >
                                {{ item.label }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetSeverityFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmSeverityFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #cell-project_name="{ row }">
                    <ElTooltip
                      v-if="(row.project_names || []).length > 1"
                      :content="(row.project_names || []).join(', ')"
                      placement="top-start"
                    >
                      <span class="cursor-help">{{
                        row.project_name || '-'
                      }}</span>
                    </ElTooltip>
                    <span v-else>{{ row.project_name || '-' }}</span>
                  </template>

                  <template #cell-team_name="{ row }">
                    <ElTooltip
                      v-if="(row.team_names || []).length > 1"
                      :content="(row.team_names || []).join(', ')"
                      placement="top-start"
                    >
                      <span class="cursor-help">{{
                        row.team_name || '-'
                      }}</span>
                    </ElTooltip>
                    <span v-else>{{ row.team_name || '-' }}</span>
                  </template>

                  <template #cell-severity="{ row }">
                    <ElTooltip
                      :content="resolveSeverityMeta(row.severity).tip"
                      placement="top"
                    >
                      <ElTag
                        :type="resolveSeverityMeta(row.severity).type"
                        effect="light"
                      >
                        {{ resolveSeverityMeta(row.severity).label }}
                      </ElTag>
                    </ElTooltip>
                  </template>

                  <template #cell-qa_category="{ row }">
                    <span v-if="!row.qa_category" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('qa_category', row.qa_category)?.type ||
                        'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('qa_category', row.qa_category)?.label ||
                        row.qa_category
                      }}
                    </ElTag>
                  </template>

                  <template #cell-is_downstream="{ row }">
                    <span v-if="!row.is_downstream" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('is_downstream', row.is_downstream)
                          ?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('is_downstream', row.is_downstream)
                          ?.label || row.is_downstream
                      }}
                    </ElTag>
                  </template>

                  <template #cell-process_quality_type="{ row }">
                    <span
                      v-if="!row.process_quality_type"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag(
                          'process_quality_type',
                          row.process_quality_type,
                        )?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag(
                          'process_quality_type',
                          row.process_quality_type,
                        )?.label || row.process_quality_type
                      }}
                    </ElTag>
                  </template>

                  <template #cell-need_dev_analyze="{ row }">
                    <span v-if="!row.need_dev_analyze" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('need_dev_analyze', row.need_dev_analyze)
                          ?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('need_dev_analyze', row.need_dev_analyze)
                          ?.label || row.need_dev_analyze
                      }}
                    </ElTag>
                  </template>

                  <template #cell-need_test_analyze="{ row }">
                    <span v-if="!row.need_test_analyze" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag(
                          'need_test_analyze',
                          row.need_test_analyze,
                        )?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag(
                          'need_test_analyze',
                          row.need_test_analyze,
                        )?.label || row.need_test_analyze
                      }}
                    </ElTag>
                  </template>

                  <template #cell-is_dev_analyzed="{ row }">
                    <span v-if="!row.is_dev_analyzed" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('is_dev_analyzed', row.is_dev_analyzed)
                          ?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('is_dev_analyzed', row.is_dev_analyzed)
                          ?.label || row.is_dev_analyzed
                      }}
                    </ElTag>
                  </template>

                  <template #cell-is_test_analyzed="{ row }">
                    <span v-if="!row.is_test_analyzed" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('is_test_analyzed', row.is_test_analyzed)
                          ?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('is_test_analyzed', row.is_test_analyzed)
                          ?.label || row.is_test_analyzed
                      }}
                    </ElTag>
                  </template>

                  <template #cell-dev_status="{ row }">
                    <span v-if="!row.dev_status" class="text-slate-400">-</span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('dev_status', row.dev_status)?.type ||
                        'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('dev_status', row.dev_status)?.label ||
                        row.dev_status
                      }}
                    </ElTag>
                  </template>

                  <template #cell-test_status="{ row }">
                    <span v-if="!row.test_status" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('test_status', row.test_status)?.type ||
                        'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('test_status', row.test_status)?.label ||
                        row.test_status
                      }}
                    </ElTag>
                  </template>

                  <template #cell-dev_sub_category="{ row }">
                    <span
                      v-if="(row.dev_sub_category || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <div v-else class="dts-cell-tags">
                      <template
                        v-for="item in (row.dev_sub_category || []).slice(0, 2)"
                        :key="item"
                      >
                        <ElTag
                          :type="
                            resolveGovTag('dev_sub_category', item)?.type ||
                            'info'
                          "
                          effect="light"
                          size="small"
                        >
                          {{
                            resolveGovTag('dev_sub_category', item)?.label ||
                            item
                          }}
                        </ElTag>
                      </template>

                      <ElTooltip
                        v-if="(row.dev_sub_category || []).length > 2"
                        :content="formatArrayCell(row.dev_sub_category).tooltip"
                        placement="top-start"
                      >
                        <ElTag type="info" effect="plain" size="small">
                          +{{ (row.dev_sub_category || []).length - 2 }}
                        </ElTag>
                      </ElTooltip>
                    </div>
                  </template>

                  <template #cell-dev_improvements="{ row }">
                    <span
                      v-if="(row.dev_improvements || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="formatArrayCell(row.dev_improvements).tooltip"
                      placement="top-start"
                    >
                      <span class="cursor-help">
                        {{ formatArrayCell(row.dev_improvements).text }}
                      </span>
                    </ElTooltip>
                  </template>

                  <template #cell-dev_non_base_desc="{ row }">
                    <span
                      v-if="(row.dev_non_base_desc || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <div v-else class="dts-cell-tags">
                      <template
                        v-for="item in takeFirstTwo(row.dev_non_base_desc)"
                        :key="item"
                      >
                        <ElTag
                          :type="
                            resolveGovTag('dev_non_base_desc', item)?.type ||
                            'info'
                          "
                          effect="light"
                          size="small"
                        >
                          {{
                            resolveGovTag('dev_non_base_desc', item)?.label ||
                            item
                          }}
                        </ElTag>
                      </template>

                      <ElTooltip
                        v-if="(row.dev_non_base_desc || []).length > 2"
                        :content="formatArrayTooltip(row.dev_non_base_desc)"
                        placement="top-start"
                      >
                        <ElTag type="info" effect="plain" size="small">
                          +{{ (row.dev_non_base_desc || []).length - 2 }}
                        </ElTag>
                      </ElTooltip>
                    </div>
                  </template>

                  <template #cell-test_miss_reason="{ row }">
                    <span
                      v-if="(row.test_miss_reason || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <div v-else class="dts-cell-tags">
                      <template
                        v-for="item in (row.test_miss_reason || []).slice(0, 2)"
                        :key="item"
                      >
                        <ElTag
                          :type="
                            resolveGovTag('test_miss_reason', item)?.type ||
                            'info'
                          "
                          effect="light"
                          size="small"
                        >
                          {{
                            resolveGovTag('test_miss_reason', item)?.label ||
                            item
                          }}
                        </ElTag>
                      </template>

                      <ElTooltip
                        v-if="(row.test_miss_reason || []).length > 2"
                        :content="formatArrayCell(row.test_miss_reason).tooltip"
                        placement="top-start"
                      >
                        <ElTag type="info" effect="plain" size="small">
                          +{{ (row.test_miss_reason || []).length - 2 }}
                        </ElTag>
                      </ElTooltip>
                    </div>
                  </template>

                  <template #cell-test_improvements="{ row }">
                    <span
                      v-if="(row.test_improvements || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="formatArrayCell(row.test_improvements).tooltip"
                      placement="top-start"
                    >
                      <span class="cursor-help">
                        {{ formatArrayCell(row.test_improvements).text }}
                      </span>
                    </ElTooltip>
                  </template>

                  <template #cell-actions="{ row }">
                    <ElButton
                      type="primary"
                      link
                      size="small"
                      @click="openEdit(row)"
                    >
                      填报/编辑
                    </ElButton>
                  </template>

                  <template #empty>
                    <div v-if="!hasAppliedFilters" class="dts-data-guide">
                      <div class="dts-data-guide__panel">
                        <div class="dts-data-guide__title">先设置筛选条件</div>
                        <div class="dts-data-guide__desc">
                          默认已按最近一个月和关闭状态自动查询，可继续通过产品线、状态和严重程度收窄范围。
                        </div>
                        <div class="dts-data-guide__actions">
                          <ElButton
                            type="primary"
                            size="small"
                            @click="handleSearch(true)"
                          >
                            开始查询明细
                          </ElButton>
                        </div>
                      </div>
                    </div>
                    <div v-else class="dts-data-empty">
                      <ElEmpty description="当前筛选条件下暂无 DTS 数据" />
                    </div>
                  </template>
                </Grid>
              </div>
            </div>
          </ElCard>
        </ElTabPane>

        <ElTabPane label="统计看板" name="dashboard">
          <div
            v-loading="summaryLoading"
            class="dts-summary-panel space-y-4 pb-4"
          >
            <ElEmpty
              v-if="!hasAppliedFilters"
              description="正在准备默认筛选数据..."
            />
            <ElEmpty
              v-else-if="summary.total_count === 0"
              description="当前筛选无数据"
            />
            <div v-else class="flex flex-col gap-4">
              <div class="summary-overview-grid">
                <ElCard
                  shadow="never"
                  class="dense-overview-card dense-overview-card--hero"
                >
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">缺陷总览</div>
                    <ElTag type="primary" effect="light">
                      {{ summary.total_count }} 条
                    </ElTag>
                  </div>
                  <div class="dense-overview-card__hero-value">
                    {{ summary.total_count }}
                  </div>
                  <div class="dense-overview-card__hero-label">
                    当前筛选范围内的 DTS 问题单总数
                  </div>
                  <div
                    class="dense-overview-card__metric-grid dense-overview-card__metric-grid--three"
                  >
                    <div class="dense-metric-block dense-metric-block--danger">
                      <div class="dense-metric-block__label">未关闭</div>
                      <div class="dense-metric-block__value">
                        {{ summary.open_count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        占比
                        {{
                          summary.total_count
                            ? Math.round(
                                (summary.open_count / summary.total_count) *
                                  100,
                              )
                            : 0
                        }}%
                      </div>
                    </div>
                    <div class="dense-metric-block dense-metric-block--success">
                      <div class="dense-metric-block__label">已关闭</div>
                      <div class="dense-metric-block__value">
                        {{ summary.closed_count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        占比
                        {{
                          summary.total_count
                            ? Math.round(
                                (summary.closed_count / summary.total_count) *
                                  100,
                              )
                            : 0
                        }}%
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">平均处理天数</div>
                      <div class="dense-metric-block__value">
                        {{ summary.avg_process_days }}
                      </div>
                      <div class="dense-metric-block__subtext">近似口径</div>
                    </div>
                  </div>
                  <div class="dense-overview-card__meta">
                    填报完成度：QA
                    {{ Math.round((summary.qa_completion_rate || 0) * 100) }}% ·
                    开发
                    {{
                      Math.round(
                        (summary.dev_analysis_completion_rate || 0) * 100,
                      )
                    }}% · 测试
                    {{
                      Math.round(
                        (summary.test_analysis_completion_rate || 0) * 100,
                      )
                    }}%
                  </div>
                </ElCard>

                <ElCard shadow="never" class="dense-overview-card">
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">填报完成度</div>
                    <ElTag type="info" effect="plain">
                      共 {{ summary.total_count }} 条
                    </ElTag>
                  </div>

                  <div class="dense-completion-grid">
                    <div
                      class="dense-completion-panel dense-completion-panel--qa"
                    >
                      <div class="dense-completion-panel__title">QA填写率</div>
                      <div class="dense-completion-panel__headline">
                        {{
                          Math.round((summary.qa_completion_rate || 0) * 100)
                        }}%
                      </div>
                      <ElProgress
                        :percentage="
                          Math.round((summary.qa_completion_rate || 0) * 100)
                        "
                        :stroke-width="10"
                      />
                      <div class="dense-completion-panel__meta">
                        <span>
                          {{ summary.qa_filled_count }} /
                          {{ summary.total_count }}
                        </span>
                      </div>
                    </div>

                    <div
                      class="dense-completion-panel dense-completion-panel--dev"
                    >
                      <div class="dense-completion-panel__title">
                        开发分析完成率
                      </div>
                      <div class="dense-completion-panel__headline">
                        {{
                          Math.round(
                            (summary.dev_analysis_completion_rate || 0) * 100,
                          )
                        }}%
                      </div>
                      <ElProgress
                        status="success"
                        :percentage="
                          Math.round(
                            (summary.dev_analysis_completion_rate || 0) * 100,
                          )
                        "
                        :stroke-width="10"
                      />
                      <div class="dense-completion-panel__meta">
                        <span>
                          {{ summary.dev_analyzed_count }} /
                          {{ summary.total_count }}
                        </span>
                      </div>
                    </div>

                    <div
                      class="dense-completion-panel dense-completion-panel--test"
                    >
                      <div class="dense-completion-panel__title">
                        测试分析完成率
                      </div>
                      <div class="dense-completion-panel__headline">
                        {{
                          Math.round(
                            (summary.test_analysis_completion_rate || 0) * 100,
                          )
                        }}%
                      </div>
                      <ElProgress
                        status="success"
                        :percentage="
                          Math.round(
                            (summary.test_analysis_completion_rate || 0) * 100,
                          )
                        "
                        :stroke-width="10"
                      />
                      <div class="dense-completion-panel__meta">
                        <span>
                          {{ summary.test_analyzed_count }} /
                          {{ summary.total_count }}
                        </span>
                      </div>
                    </div>
                  </div>
                </ElCard>
              </div>

              <ElCard shadow="never" class="summary-section-card">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">缺陷属性</div>
                      <div class="summary-section-card__desc">
                        从严重程度、状态、阶段与关闭类型维度观察当前筛选下的分布。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="danger"
                      effect="plain"
                    >
                      {{ summary.severity_dist.length }} 类严重程度
                    </ElTag>
                  </div>
                </template>
                <div class="dts-charts-grid">
                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">严重程度分布</div>
                        <ElTag type="danger" effect="plain">
                          {{ summary.severity_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="severityChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">状态分布</div>
                        <ElTag type="primary" effect="plain">
                          {{ summary.status_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="statusChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">阶段分布</div>
                        <ElTag type="info" effect="plain">
                          {{ summary.stage_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="stageChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">关闭类型分布</div>
                        <ElTag type="warning" effect="plain">
                          {{ summary.close_type_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="closeTypeChartRef" height="320px" />
                  </ElCard>
                </div>
              </ElCard>

              <ElCard shadow="never" class="summary-section-card">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">组织维度</div>
                      <div class="summary-section-card__desc">
                        按项目、团队与处理人维度查看问题单集中情况，帮助定位重点投入方向。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="success"
                      effect="plain"
                    >
                      {{ summary.team_dist.length }} 个团队
                    </ElTag>
                  </div>
                </template>
                <div class="dts-charts-grid">
                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">项目分布</div>
                        <ElTag type="warning" effect="plain">
                          {{ summary.project_dist.length }} 项
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="projectChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">团队分布</div>
                        <ElTag type="success" effect="plain">
                          {{ summary.team_dist.length }} 团队
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="teamChartRef" height="320px" />
                  </ElCard>

                  <ElCard
                    shadow="never"
                    class="dts-chart-card dts-chart-card--wide"
                  >
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">处理人 Top</div>
                        <ElTag type="primary" effect="plain">
                          {{ summary.handler_dist.length }} 人
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="handlerChartRef" height="340px" />
                  </ElCard>
                </div>
              </ElCard>

              <ElCard shadow="never" class="summary-section-card">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">治理填报</div>
                      <div class="summary-section-card__desc">
                        查看 QA 类目、责任 PL
                        组、措施状态与开发/测试原因分布，辅助后续治理与复盘。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="primary"
                      effect="plain"
                    >
                      {{ summary.qa_category_dist.length }} 类 QA 类目
                    </ElTag>
                  </div>
                </template>

                <div class="dts-charts-grid">
                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">QA类目分布</div>
                        <ElTag type="success" effect="plain">
                          {{ summary.qa_category_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="qaCategoryChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">责任PL组分布</div>
                        <ElTag type="primary" effect="plain">
                          {{ summary.pl_group_dist.length }} 组
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="plGroupChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">措施状态分布</div>
                        <ElTag type="danger" effect="plain">
                          {{ summary.action_status_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="actionStatusChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">
                          开发问题小类 Top
                        </div>
                        <ElTag type="info" effect="plain">
                          {{ summary.dev_sub_category_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="devSubCategoryChartRef" height="320px" />
                  </ElCard>

                  <ElCard
                    shadow="never"
                    class="dts-chart-card dts-chart-card--wide"
                  >
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">漏测原因 Top</div>
                        <ElTag type="success" effect="plain">
                          {{ summary.test_miss_reason_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="testMissReasonChartRef" height="340px" />
                  </ElCard>
                </div>
              </ElCard>
            </div>
          </div>
        </ElTabPane>
      </ElTabs>

      <DtsEditDrawer
        v-model="editVisible"
        :row="editingRow"
        @success="handleSaved"
      />
    </div>
  </Page>
</template>

<style scoped>
.dts-statistics-shell {
  min-height: 0;
}

.dts-statistics-tabs {
  min-height: 0;
  border: 1px solid #dbe5f1;
  border-radius: 24px;
  background: linear-gradient(
    180deg,
    rgb(255 255 255 / 0.96) 0%,
    rgb(248 250 252 / 0.92) 100%
  );
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.96),
    0 12px 30px rgb(15 23 42 / 0.04);
  padding: 14px;
}

.dts-statistics-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
  border: 1px solid #dde6f2;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.92);
  padding: 8px;
}

.dts-statistics-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.dts-statistics-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0;
}

.dts-statistics-tabs :deep(.el-tabs__nav) {
  gap: 8px;
}

.dts-statistics-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.dts-statistics-tabs :deep(.el-tabs__item) {
  height: 40px;
  border-radius: 12px;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  padding: 0 18px !important;
  transition:
    background-color 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}

.dts-statistics-tabs :deep(.el-tabs__item:hover) {
  color: #1e293b;
}

.dts-statistics-tabs :deep(.el-tabs__item.is-active) {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #0f172a;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.9),
    0 8px 18px rgb(37 99 235 / 0.12);
  transform: translateY(-1px);
}

.dts-data-card__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dts-data-card {
  display: flex;
  min-height: 0;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  box-shadow: 0 14px 32px rgb(15 23 42 / 0.04);
}

.dts-data-card :deep(.el-card__header) {
  padding: 18px 20px 16px;
  border-bottom-color: #e2e8f0;
}

.dts-data-card :deep(.el-card__body) {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  padding: 0 0 16px;
}

.dts-data-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.dts-data-card__title {
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
}

.dts-data-card__desc {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
  margin-top: 4px;
  max-width: 720px;
}

.dts-data-card__status {
  flex-shrink: 0;
  margin-top: 2px;
}

.dts-data-card__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.dts-data-grid-wrap {
  min-height: 420px;
}

.dts-data-grid {
  min-height: 420px;
}

.dts-table-title {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px 16px;
  padding: 6px 0 10px;
}

.dts-table-title__filters {
  display: flex;
  flex: 1 1 720px;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
}

.dts-table-title__field {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dts-table-title__label,
.dts-header-filter__label {
  color: #475569;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
}

.dts-table-title__select {
  width: 180px;
}

.dts-table-title__date {
  width: 320px;
}

.dts-table-title__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dts-table-title__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dts-header-filter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.dts-header-filter-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #ffffff;
  color: #606266;
  font-size: 12px;
  line-height: 1;
  padding: 0 8px;
  cursor: pointer;
  transition:
    color 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease;
}

.dts-header-filter-trigger:hover {
  border-color: #c0c4cc;
}

.dts-header-filter-trigger.is-active {
  color: #409eff;
  border-color: #a0cfff;
  background: #ecf5ff;
}

.dts-header-filter-trigger__icon {
  width: 12px;
  height: 12px;
}

.dts-header-filter-trigger__text {
  white-space: nowrap;
}

.dts-header-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dts-header-filter-panel__body {
  max-height: 260px;
  overflow: auto;
  padding-right: 4px;
}

.dts-header-filter-check-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dts-header-filter-panel__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid #ebeef5;
  padding-top: 10px;
}

:deep(.dts-header-filter-popper.el-popper) {
  padding: 10px 12px;
}

.dts-data-grid :deep(.flex.items-center.justify-between.px-4.pb-4.pt-2) {
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.dts-data-grid
  :deep(.flex.items-center.justify-between.px-4.pb-4.pt-2 > div:first-child) {
  display: flex;
  flex: 1 1 760px;
  min-width: 0;
}

.dts-data-grid
  :deep(.flex.items-center.justify-between.px-4.pb-4.pt-2 > div:last-child) {
  flex-shrink: 0;
}

.dts-data-grid :deep(.zq-table-header th.el-table__cell) {
  vertical-align: middle;
}

.dts-data-grid :deep(.zq-table-header .cell) {
  overflow: visible;
  white-space: normal;
}

.dts-cell-tags {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
}

.dts-data-guide {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 16px 20px;
}

.dts-data-empty {
  display: flex;
  height: 100%;
  min-height: 280px;
  align-items: center;
  justify-content: center;
}

.dts-data-guide__panel {
  width: min(100%, 420px);
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  background: #ffffff;
  padding: 20px 22px;
  text-align: center;
}

.dts-data-guide__title {
  color: #0f172a;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.4;
}

.dts-data-guide__desc {
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
  margin-top: 8px;
}

.dts-data-guide__meta {
  color: #94a3b8;
  font-size: 12px;
  margin-top: 8px;
}

.dts-data-guide__actions {
  display: flex;
  justify-content: center;
  margin-top: 14px;
}

.dts-summary-panel {
  padding-right: 4px;
}

.summary-overview-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.dense-overview-card {
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  box-shadow: 0 12px 28px rgb(15 23 42 / 0.04);
  min-height: 216px;
}

.dense-overview-card--hero {
  background:
    radial-gradient(
      circle at top right,
      rgba(37, 99, 235, 0.14),
      transparent 42%
    ),
    linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
}

.dense-overview-card__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dense-overview-card__title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
}

.dense-overview-card__hero-value {
  color: #0f172a;
  font-size: 40px;
  font-weight: 800;
  line-height: 1;
  margin-top: 18px;
}

.dense-overview-card__hero-label {
  color: #475569;
  font-size: 13px;
  margin-top: 6px;
}

.dense-overview-card__metric-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 18px;
}

.dense-overview-card__meta {
  color: #64748b;
  font-size: 12px;
  margin-top: 10px;
}

.dense-overview-card__metric-grid--three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.dense-metric-block {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #ffffff;
  padding: 14px;
}

.dense-metric-block--warning {
  background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
  border-color: #fdba74;
}

.dense-metric-block--danger {
  background: linear-gradient(180deg, #fef2f2 0%, #ffffff 100%);
  border-color: #fca5a5;
}

.dense-metric-block--success {
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
  border-color: #86efac;
}

.dense-metric-block__label {
  color: #64748b;
  font-size: 12px;
}

.dense-metric-block__value {
  color: #0f172a;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.1;
  margin-top: 10px;
}

.dense-metric-block__subtext {
  color: #475569;
  font-size: 12px;
  margin-top: 6px;
}

.dense-completion-grid {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.dense-completion-panel {
  border-radius: 18px;
  padding: 16px;
}

.dense-completion-panel--qa {
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
  border: 1px solid #bfdbfe;
}

.dense-completion-panel--dev {
  background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
  border: 1px solid #fdba74;
}

.dense-completion-panel--test {
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
  border: 1px solid #86efac;
}

.dense-completion-panel__title {
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.dense-completion-panel__headline {
  color: #0f172a;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.2;
  margin: 10px 0 12px;
}

.dense-completion-panel__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
  margin-top: 10px;
}

.summary-section-card {
  border-radius: 18px;
}

.summary-section-card :deep(.el-card__header) {
  padding: 18px 20px 16px;
  border-bottom-color: #e2e8f0;
}

.summary-section-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.summary-section-card__title {
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
}

.summary-section-card__desc {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
  margin-top: 4px;
  max-width: 720px;
}

.summary-section-card__tag {
  flex-shrink: 0;
  margin-top: 2px;
}

.dts-charts-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.dts-chart-card {
  border-radius: 18px;
}

.dts-chart-card :deep(.el-card__header) {
  padding: 14px 18px 12px;
  border-bottom-color: #e2e8f0;
}

.dts-chart-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dts-chart-card__title {
  color: #0f172a;
  font-size: 13px;
  line-height: 18px;
  font-weight: 600;
}

.dts-chart-card--wide {
  grid-column: 1 / -1;
}

@media (max-width: 1024px) {
  .dense-overview-card__metric-grid--three {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }

  .dts-data-grid-wrap,
  .dts-data-grid {
    min-height: 360px;
  }

  .dts-table-title__filters {
    flex-basis: 100%;
  }

  .dts-table-title__date {
    width: 260px;
  }

  .dts-data-grid :deep(.p-4) {
    position: sticky;
    bottom: 0;
    background: #ffffff;
    z-index: 3;
    box-shadow: 0 -6px 16px rgba(15, 23, 42, 0.08);
  }

  .dts-data-grid :deep(.el-table__body-wrapper) {
    padding-bottom: 64px;
  }

  .dts-charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dts-statistics-tabs {
    border-radius: 18px;
    padding: 10px;
  }

  .dts-data-card__header,
  .summary-section-card__header,
  .dense-overview-card__title-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
