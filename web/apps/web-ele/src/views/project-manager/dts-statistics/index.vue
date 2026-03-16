<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  DtsMergedDefect,
  DtsStatisticsFilters,
  DtsSummary,
} from '#/api/project-manager/dts-statistics';
import type { ProjectOut } from '#/api/project-manager/project';

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElMessage,
  ElOption,
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
import { listProjectsApi } from '#/api/project-manager/project';
import { useZqTable } from '#/components/zq-table';

import ProjectSelectorDialog from './components/project-selector-dialog.vue';
import {
  formatDateTime,
  getTodayDateRange,
  normalizeProjectOptions,
  resolveSeverityMeta,
  useColumns,
} from './data';
import DtsEditDrawer from './DtsEditDrawer.vue';

defineOptions({ name: 'DtsStatistics' });

type TabKey = 'dashboard' | 'list';

interface DtsStatisticsProjectOption {
  id: string;
  name: string;
  code: string;
  domain?: null | string;
  type?: null | string;
  enable_dts: boolean;
  version_c?: null | string;
  di_teams?: string[];
  config_complete: boolean;
  reason?: string;
}

const activeTab = ref<TabKey>('list');

const editVisible = ref(false);
const editingRow = ref<DtsMergedDefect | null>(null);

const projectSelectorVisible = ref(false);
const optionsLoading = ref(false);
const projectOptions = ref<DtsStatisticsProjectOption[]>([]);

const dateRange = ref<[Date, Date] | null>(getTodayDateRange());
const filters = ref<DtsStatisticsFilters>({
  project_ids: [],
  column_type: 'openDefects',
  start_time: '',
  end_time: '',
});

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
  return {
    project_ids: normalizeStringArray(source.project_ids),
    column_type: source.column_type || 'openDefects',
    start_time: source.start_time || '',
    end_time: source.end_time || '',
  };
}

function buildFingerprint(payload: DtsStatisticsFilters | null) {
  if (!payload) {
    return '';
  }
  return JSON.stringify({
    project_ids: [...(payload.project_ids || [])].sort(),
    column_type: payload.column_type || '',
    start_time: payload.start_time || '',
    end_time: payload.end_time || '',
  });
}

function buildDtsProjectOption(
  project: ProjectOut,
): DtsStatisticsProjectOption {
  const enable_dts = Boolean(project.enable_dts);
  const version_c = String(project.version_c || '').trim();
  const di_teams = Array.isArray(project.di_teams)
    ? project.di_teams.map((item) => String(item || '').trim()).filter(Boolean)
    : [];

  const reasons: string[] = [];
  if (!enable_dts) {
    reasons.push('未开启问题单统计');
  }
  if (!version_c) {
    reasons.push('未配置 version_c');
  }
  if (di_teams.length === 0) {
    reasons.push('未配置责任团队(di_teams)');
  }

  const config_complete =
    enable_dts && Boolean(version_c) && di_teams.length > 0;

  return {
    id: project.id,
    name: project.name,
    code: project.code,
    domain: project.domain,
    type: project.type,
    enable_dts,
    version_c: version_c || null,
    di_teams,
    config_complete,
    reason: reasons.join(' / '),
  };
}

async function loadProjects() {
  optionsLoading.value = true;
  try {
    const res = await listProjectsApi({ pageSize: 1000 });
    const items = normalizeProjectOptions(res.items || []);
    projectOptions.value = items.map((item) => buildDtsProjectOption(item));
  } catch (error) {
    console.error(error);
    ElMessage.error('加载项目列表失败');
  } finally {
    optionsLoading.value = false;
  }
}

watch(
  dateRange,
  (value) => {
    if (value && value.length === 2) {
      filters.value.start_time = formatDateTime(value[0]);
      filters.value.end_time = formatDateTime(value[1]);
      return;
    }
    filters.value.start_time = '';
    filters.value.end_time = '';
  },
  { immediate: true },
);

const selectableProjectCount = computed(
  () => projectOptions.value.filter((item) => item.config_complete).length,
);

const projectSelectorButtonLabel = computed(() =>
  filters.value.project_ids.length > 0
    ? `查看已选项目（${filters.value.project_ids.length}）`
    : '选择项目',
);
const projectSelectorButtonType = computed(() =>
  filters.value.project_ids.length > 0 ? 'success' : 'primary',
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
            page_no: page.currentPage,
            page_size: page.pageSize,
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
  if (
    !dataGridWrapRef.value ||
    !hasAppliedFilters.value ||
    activeTab.value !== 'list'
  ) {
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

watch(
  () => activeTab.value,
  (tab) => {
    if (tab === 'dashboard') {
      void fetchSummary();
    }
    void nextTick().then(() => updateDataGridHeight());
  },
);

function clearGridData() {
  gridApi.tableData.value = [];
  gridApi.total.value = 0;
  gridApi.pagination.total = 0;
}

function handleProjectSelectorConfirm(projectIds: string[]) {
  filters.value.project_ids = normalizeStringArray(projectIds);
}

function clearSelectedProjects() {
  filters.value.project_ids = [];
}

async function handleSearch() {
  const payload = cloneFilters(filters.value);
  if (payload.project_ids.length === 0) {
    ElMessage.warning('请至少选择一个项目');
    return;
  }
  if (!payload.start_time || !payload.end_time) {
    ElMessage.warning('请先选择起止时间范围');
    return;
  }

  // Remove projects that are not queryable to avoid confusing "empty list".
  const selectableSet = new Set(
    projectOptions.value
      .filter((item) => item.config_complete)
      .map((item) => item.id),
  );
  payload.project_ids = payload.project_ids.filter((id) =>
    selectableSet.has(id),
  );
  if (payload.project_ids.length === 0) {
    ElMessage.warning('当前已选项目均不可查询，请先完善项目 DTS 配置');
    return;
  }

  appliedFilters.value = payload;
  summaryFingerprint.value = '';
  gridApi.pagination.currentPage = 1;
  await nextTick();
  await gridApi.reload();
  await nextTick();
  updateDataGridHeight();
  if (activeTab.value === 'dashboard') {
    await fetchSummary(true);
  }
}

async function handleReset() {
  filters.value = {
    project_ids: [],
    column_type: 'openDefects',
    start_time: '',
    end_time: '',
  };
  dateRange.value = getTodayDateRange();
  projectSelectorVisible.value = false;
  appliedFilters.value = null;
  summaryFingerprint.value = '';
  gridApi.pagination.currentPage = 1;
  dataGridHeight.value = null;
  clearGridData();
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
  void loadProjects();
  updateDataGridHeight();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (resizeTimer) {
    window.clearTimeout(resizeTimer);
  }
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex flex-col gap-4">
      <ElCard shadow="never" class="dts-filter-card">
        <div class="dts-filter-card__header">
          <div>
            <div class="dts-filter-card__title">DTS 统计筛选</div>
            <div class="dts-filter-card__desc">
              支持多项目查询；项目未配置 version_c 或责任团队将被禁选。
            </div>
          </div>
          <div class="dts-filter-card__actions">
            <ElTag type="primary" effect="light">
              {{ selectableProjectCount }} 个项目可查询
            </ElTag>
          </div>
        </div>

        <ElForm :model="filters" label-width="84px" class="dts-filter-form">
          <ElFormItem
            label="项目"
            class="dts-filter-form__item dts-filter-form__item--project"
          >
            <div class="project-selector-trigger">
              <div class="project-selector-trigger__actions">
                <ElButton
                  :loading="optionsLoading"
                  :type="projectSelectorButtonType"
                  plain
                  @click="projectSelectorVisible = true"
                >
                  {{ projectSelectorButtonLabel }}
                </ElButton>
                <ElButton
                  text
                  :disabled="filters.project_ids.length === 0"
                  @click="clearSelectedProjects"
                >
                  清空
                </ElButton>
                <span
                  v-if="filters.project_ids.length > 0"
                  class="project-selector-trigger__summary-text"
                >
                  已选 {{ filters.project_ids.length }} 个项目
                </span>
              </div>
            </div>
          </ElFormItem>

          <ElFormItem label="单据范围" class="dts-filter-form__item">
            <ElSelect
              v-model="filters.column_type"
              class="dts-filter-control"
              placeholder="默认未关闭"
            >
              <ElOption label="未关闭" value="openDefects" />
              <ElOption label="已关闭" value="closeDefects" />
              <ElOption label="全部" value="totalDefects" />
            </ElSelect>
          </ElFormItem>

          <ElFormItem label="时间区间" class="dts-filter-form__item">
            <ElDatePicker
              v-model="dateRange"
              class="dts-filter-control"
              type="datetimerange"
              unlink-panels
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              range-separator="-"
              format="YYYY-MM-DD HH:mm:ss"
            />
          </ElFormItem>

          <ElFormItem
            label-width="0"
            class="dts-filter-form__item dts-filter-form__item--actions"
          >
            <ElButton
              type="primary"
              :loading="listLoading"
              @click="handleSearch"
            >
              查询
            </ElButton>
            <ElButton @click="handleReset">重置</ElButton>
          </ElFormItem>
        </ElForm>

        <div class="dts-filter-card__footer">
          <span>
            当前可查询项目 {{ selectableProjectCount }}
            个；未完成 DTS 配置的项目已禁用。
          </span>
          <span>查询后切换“统计看板”会复用相同筛选条件进行汇总。</span>
        </div>
      </ElCard>

      <ElTabs v-model="activeTab" class="dts-statistics-tabs flex flex-col">
        <ElTabPane label="数据明细" name="list">
          <ElCard shadow="never" class="dts-data-card">
            <template #header>
              <div class="dts-data-card__header">
                <div>
                  <div class="dts-data-card__title">DTS 明细表</div>
                  <div class="dts-data-card__desc">
                    查询后在下方表格展示问题单明细，可直接填报治理字段并导出全量结果。
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

            <div v-if="hasAppliedFilters" class="dts-data-card__body">
              <div
                ref="dataGridWrapRef"
                class="dts-data-grid-wrap"
                :style="dataGridWrapStyle"
              >
                <Grid class="dts-data-grid h-full min-h-0">
                  <template #table-title>
                    <div class="dts-table-title">
                      查询结果按 DTS
                      单号分页展示；支持列设置、刷新、缩放与填报治理字段。
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

                  <template #cell-dev_sub_category="{ row }">
                    <span
                      v-if="(row.dev_sub_category || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="formatArrayCell(row.dev_sub_category).tooltip"
                      placement="top-start"
                    >
                      <span class="cursor-help">
                        {{ formatArrayCell(row.dev_sub_category).text }}
                      </span>
                    </ElTooltip>
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

                  <template #cell-test_miss_reason="{ row }">
                    <span
                      v-if="(row.test_miss_reason || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="formatArrayCell(row.test_miss_reason).tooltip"
                      placement="top-start"
                    >
                      <span class="cursor-help">
                        {{ formatArrayCell(row.test_miss_reason).text }}
                      </span>
                    </ElTooltip>
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
                </Grid>
              </div>
            </div>

            <div v-else class="dts-data-guide">
              <div class="dts-data-guide__panel">
                <div class="dts-data-guide__eyebrow">DTS Statistics</div>
                <div class="dts-data-guide__title">先筛选，再查询</div>
                <div class="dts-data-guide__desc">
                  选择项目、单据范围和时间区间后点击“查询”，下方将展示问题单明细，并支持填报/导出。
                </div>
                <div class="dts-guide-steps">
                  <div class="dts-guide-step">
                    <div class="dts-guide-step__index">1</div>
                    <div class="dts-guide-step__title">选择项目</div>
                    <div class="dts-guide-step__desc">
                      仅支持已开启 DTS 且配置了 version_c/责任团队的项目。
                    </div>
                  </div>
                  <div class="dts-guide-step">
                    <div class="dts-guide-step__index">2</div>
                    <div class="dts-guide-step__title">设置范围</div>
                    <div class="dts-guide-step__desc">
                      可选择未关闭/已关闭/全部，并指定起止时间范围。
                    </div>
                  </div>
                  <div class="dts-guide-step">
                    <div class="dts-guide-step__index">3</div>
                    <div class="dts-guide-step__title">查看与填报</div>
                    <div class="dts-guide-step__desc">
                      点击“填报/编辑”进入 Drawer，分别填写
                      QA/开发/测试信息并一次保存。
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </ElCard>
        </ElTabPane>

        <ElTabPane label="统计看板" name="dashboard">
          <div v-loading="summaryLoading" class="dts-summary-panel">
            <ElEmpty
              v-if="!hasAppliedFilters"
              description="请先完成筛选并查询明细"
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

      <ProjectSelectorDialog
        v-model="projectSelectorVisible"
        :loading="optionsLoading"
        :projects="projectOptions"
        :selected-project-ids="filters.project_ids"
        @confirm="handleProjectSelectorConfirm"
      />

      <DtsEditDrawer
        v-model="editVisible"
        :row="editingRow"
        @success="handleSaved"
      />
    </div>
  </Page>
</template>

<style scoped>
.dts-filter-card {
  border-radius: 20px;
}

.dts-filter-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.dts-filter-card__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.dts-filter-card__title {
  color: #0f172a;
  font-size: 18px;
  font-weight: 700;
}

.dts-filter-card__desc {
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
  margin-top: 6px;
  max-width: 760px;
}

.dts-filter-card__footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
  margin-top: 14px;
}

.dts-filter-form {
  display: grid;
  gap: 16px 20px;
  grid-template-columns:
    minmax(320px, 1.8fr)
    minmax(180px, 0.7fr)
    minmax(340px, 1.3fr)
    minmax(180px, 0.6fr);
  overflow-x: auto;
  padding-bottom: 2px;
}

.dts-filter-form::-webkit-scrollbar {
  height: 6px;
}

.dts-filter-form::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 999px;
}

.dts-filter-form::-webkit-scrollbar-track {
  background: transparent;
}

.dts-filter-form :deep(.el-form-item) {
  align-items: flex-start;
  margin-bottom: 0;
}

.dts-filter-form :deep(.el-form-item__label) {
  align-items: center;
  color: #334155;
  font-weight: 600;
  justify-content: flex-end;
  line-height: 40px;
  padding-right: 14px;
}

.dts-filter-form :deep(.el-form-item__content) {
  min-width: 0;
}

.dts-filter-form__item--actions :deep(.el-form-item__content) {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.dts-filter-control {
  width: 100%;
}

.project-selector-trigger {
  display: flex;
  min-width: 0;
  width: 100%;
  flex-direction: column;
  gap: 10px;
}

.project-selector-trigger__actions,
.dts-data-card__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.project-selector-trigger__summary-text {
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
}

.dts-statistics-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.dts-statistics-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.dts-data-card {
  display: flex;
  min-height: 0;
  flex-direction: column;
  border-radius: 20px;
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
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
  padding: 6px 0 10px;
}

.dts-data-guide {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.dts-data-guide__panel {
  width: min(100%, 860px);
  border: 1px dashed #cbd5e1;
  border-radius: 24px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  padding: 32px;
}

.dts-data-guide__eyebrow {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.dts-data-guide__title {
  color: #0f172a;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  margin-top: 10px;
}

.dts-data-guide__desc {
  color: #475569;
  font-size: 14px;
  line-height: 1.7;
  margin-top: 10px;
  max-width: 680px;
}

.dts-guide-steps {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  margin-top: 24px;
}

.dts-guide-step {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 18px;
  min-height: 160px;
}

.dts-guide-step__index {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: #0f172a;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
}

.dts-guide-step__title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
  margin-top: 14px;
}

.dts-guide-step__desc {
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
  margin-top: 8px;
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
  border-radius: 20px;
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
  .dts-data-grid-wrap,
  .dts-data-grid {
    min-height: 360px;
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
  .dts-filter-card__header,
  .dts-data-card__header,
  .summary-section-card__header,
  .dense-overview-card__title-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
