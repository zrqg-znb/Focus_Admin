<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  RequirementBoardFilterPayload,
  RequirementBoardProjectOption,
  RequirementBoardSummary,
  RequirementDeliveryTrendItem,
  RequirementTimeField,
  RequirementUserSummaryItem,
} from '#/api/project-manager/requirement_board';

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
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import { searchUserApi } from '#/api/core/user';
import {
  exportRequirementBoardApi,
  getRequirementBoardDataApi,
  getRequirementBoardFilterOptionsApi,
  getRequirementBoardSummaryApi,
} from '#/api/project-manager/requirement_board';
import { useZqTable } from '#/components/zq-table';

import ProjectSelectorDialog from './components/project-selector-dialog.vue';
import {
  CATEGORY_OPTIONS,
  createEmptyRequirementSummary,
  DEFAULT_CATEGORIES,
  DEFAULT_TIME_FIELD,
  formatDateTime,
  formatMetric,
  formatPercent,
  STATUS_META,
  STATUS_META_MAP,
  TIME_FIELD_OPTIONS,
  useRequirementColumns,
  VERIFICATION_POLICY_OPTIONS,
} from './data';

defineOptions({ name: 'RequirementBoard' });

interface UserOption {
  label: string;
  value: string;
}

const activeTab = ref('data');
const optionsLoading = ref(false);
const summaryLoading = ref(false);
const exportLoading = ref(false);
const developUserLoading = ref(false);
const testUserLoading = ref(false);
const projectOptions = ref<RequirementBoardProjectOption[]>([]);
const developUserOptions = ref<UserOption[]>([]);
const testUserOptions = ref<UserOption[]>([]);
const filterCollapsed = ref(false);
const projectSelectorVisible = ref(false);
const dataGridWrapRef = ref<HTMLDivElement>();
const dataGridHeight = ref<null | number>(null);
const filters = ref<RequirementBoardFilterPayload>({
  project_ids: [],
  sub_teams: [],
  categories: [...DEFAULT_CATEGORIES],
  verification_policies: [],
  develop_users: [],
  test_users: [],
  time_field: DEFAULT_TIME_FIELD,
  time_start: '',
  time_end: '',
});
const dateRange = ref<[Date, Date] | null>(null);
const appliedFilters = ref<null | RequirementBoardFilterPayload>(null);
const summary = ref<RequirementBoardSummary>(createEmptyRequirementSummary());
const summaryFingerprint = ref('');

const teamStatusChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTeamStatusChart } = useEcharts(teamStatusChartRef);
const developmentTrendChartRef = ref<EchartsUIType>();
const { renderEcharts: renderDevelopmentTrendChart } = useEcharts(
  developmentTrendChartRef,
);
const acceptanceTrendChartRef = ref<EchartsUIType>();
const { renderEcharts: renderAcceptanceTrendChart } = useEcharts(
  acceptanceTrendChartRef,
);
const developOwnerChartRef = ref<EchartsUIType>();
const { renderEcharts: renderDevelopOwnerChart } =
  useEcharts(developOwnerChartRef);
const testOwnerChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTestOwnerChart } = useEcharts(testOwnerChartRef);

const TEAM_STATUS_CHART_COLORS: Record<string, string> = {
  I: '#fecdd3',
  D: '#bfdbfe',
  P: '#ddd6fe',
  C: '#fed7aa',
  A: '#bbf7d0',
};

function getTeamStatusChartColor(statusCode: string) {
  return (
    TEAM_STATUS_CHART_COLORS[statusCode] ||
    STATUS_META_MAP[statusCode]?.accent ||
    '#cbd5f5'
  );
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

function sortProjectOptions(options: RequirementBoardProjectOption[]) {
  return [...options].sort((left, right) => {
    if (left.config_complete !== right.config_complete) {
      return left.config_complete ? -1 : 1;
    }
    return left.name.localeCompare(right.name, 'zh-CN');
  });
}

function formatDateBoundary(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

watch(dateRange, (value) => {
  if (value && value.length === 2) {
    filters.value.time_start = formatDateBoundary(value[0]);
    filters.value.time_end = formatDateBoundary(value[1]);
  } else {
    filters.value.time_start = '';
    filters.value.time_end = '';
  }
});

function cloneFilterPayload(
  source: RequirementBoardFilterPayload,
): RequirementBoardFilterPayload {
  const categories = normalizeStringArray(source.categories);
  return {
    project_ids: normalizeStringArray(source.project_ids),
    sub_teams: normalizeStringArray(source.sub_teams),
    categories: categories.length > 0 ? categories : [...DEFAULT_CATEGORIES],
    verification_policies: normalizeStringArray(source.verification_policies),
    develop_users: normalizeStringArray(source.develop_users),
    test_users: normalizeStringArray(source.test_users),
    time_field: (source.time_field ||
      DEFAULT_TIME_FIELD) as RequirementTimeField,
    time_start: source.time_start || '',
    time_end: source.time_end || '',
  };
}

function buildFingerprint(payload: null | RequirementBoardFilterPayload) {
  if (!payload) {
    return '';
  }
  return JSON.stringify({
    project_ids: [...(payload.project_ids || [])].sort(),
    sub_teams: [...(payload.sub_teams || [])].sort(),
    categories: [...(payload.categories || [])].sort(),
    verification_policies: [...(payload.verification_policies || [])].sort(),
    develop_users: [...(payload.develop_users || [])].sort(),
    test_users: [...(payload.test_users || [])].sort(),
    time_field: payload.time_field || '',
    time_start: payload.time_start || '',
    time_end: payload.time_end || '',
  });
}

const configuredProjectOptions = computed(() =>
  projectOptions.value.filter((item) => item.config_complete),
);

const selectedProjects = computed(() => {
  const projectMap = new Map(
    projectOptions.value.map((item) => [item.id, item]),
  );
  return normalizeStringArray(filters.value.project_ids)
    .map((item) => projectMap.get(item))
    .filter(Boolean);
});

const teamOptions = computed(() => {
  const seen = new Set<string>();
  const result: Array<{ label: string; value: string }> = [];
  selectedProjects.value.forEach((project) => {
    (project.sub_teams || []).forEach((team) => {
      const text = String(team || '').trim();
      if (!text || seen.has(text)) {
        return;
      }
      seen.add(text);
      result.push({ label: text, value: text });
    });
  });
  return result;
});

const projectSelectorButtonLabel = computed(() =>
  filters.value.project_ids.length > 0
    ? `查看已选项目（${filters.value.project_ids.length}）`
    : '选择项目',
);
const projectSelectorButtonType = computed(() =>
  filters.value.project_ids.length > 0 ? 'success' : 'primary',
);

const hasAppliedFilters = computed(() => Boolean(appliedFilters.value));
const selectedCategoryCount = computed(() => {
  const categories = normalizeStringArray(filters.value.categories);
  return categories.length > 0 ? categories.length : DEFAULT_CATEGORIES.length;
});
const selectedVerificationPolicyCount = computed(
  () => normalizeStringArray(filters.value.verification_policies).length,
);
const filterToggleLabel = computed(() =>
  filterCollapsed.value ? '展开筛选' : '收起筛选',
);
const summaryTeamCount = computed(() => summary.value.team_summary.length);
const summaryProjectCount = computed(
  () => summary.value.project_summary.length,
);
const summaryTypeCount = computed(() => summary.value.type_summary.length);
const activeTimeFieldLabel = computed(() => {
  return (
    TIME_FIELD_OPTIONS.find((item) => item.value === filters.value.time_field)
      ?.label || '测试完成时间'
  );
});
const dispatchRate = computed(() => {
  return (
    summary.value.dispatch_rate || {
      p_total: 0,
      develop_owner_count: 0,
      develop_owner_rate: 0,
      test_owner_count: 0,
      test_owner_rate: 0,
    }
  );
});
const planRefreshRate = computed(() => {
  return (
    summary.value.plan_refresh_rate || {
      planned_test_time_count: 0,
      planned_test_time_rate: 0,
      due_date_count: 0,
      due_date_rate: 0,
    }
  );
});

const teamChartHeight = computed(() => {
  const count = summary.value.team_summary.length;
  if (count <= 0) {
    return 320;
  }
  const base = 220;
  const rowHeight = 26;
  const height = base + count * rowHeight;
  return Math.min(520, Math.max(320, height));
});

const teamChartZoomEnd = computed(() => {
  const count = summary.value.team_summary.length;
  const visible = 12;
  if (count <= visible || count === 0) {
    return 100;
  }
  return Math.min(100, Math.round((visible / count) * 100));
});

const filterSummaryText = computed(() => {
  const timeRange =
    filters.value.time_start && filters.value.time_end
      ? `${filters.value.time_start} ~ ${filters.value.time_end}`
      : '未设置';
  return [
    `项目 ${filters.value.project_ids.length} 个`,
    `团队 ${filters.value.sub_teams.length} 个`,
    `类型 ${selectedCategoryCount.value} 种`,
    `验证策略 ${selectedVerificationPolicyCount.value} 个`,
    `开发责任人 ${filters.value.develop_users.length} 个`,
    `测试责任人 ${filters.value.test_users.length} 个`,
    `时间区间 ${timeRange}`,
  ].join(' / ');
});

const filterAutoCollapseBreakpoint = 1280;
let filterResizeTimer: null | number = null;

const dataGridWrapStyle = computed(() => {
  if (!dataGridHeight.value) {
    return undefined;
  }
  return { height: `${dataGridHeight.value}px` };
});

function updateFilterCollapseByWidth() {
  if (window.innerWidth < filterAutoCollapseBreakpoint) {
    filterCollapsed.value = true;
  }
}

function updateDataGridHeight() {
  if (
    !dataGridWrapRef.value ||
    !hasAppliedFilters.value ||
    activeTab.value !== 'data'
  ) {
    dataGridHeight.value = null;
    return;
  }
  const rect = dataGridWrapRef.value.getBoundingClientRect();
  const bottomOffset = 24;
  const available = window.innerHeight - rect.top - bottomOffset;
  const nextHeight = Math.max(320, Math.floor(available));
  dataGridHeight.value = nextHeight;
}

function handleFilterResize() {
  if (filterResizeTimer) {
    window.clearTimeout(filterResizeTimer);
  }
  filterResizeTimer = window.setTimeout(() => {
    updateFilterCollapseByWidth();
    updateDataGridHeight();
  }, 120);
}

const statusCards = computed(() => {
  const countMap = new Map(
    (summary.value.status_summary || []).map((item) => [
      item.status_code,
      item,
    ]),
  );
  return STATUS_META.map((item) => ({
    ...item,
    ...countMap.get(item.status_code),
  }));
});

const overallCompletion = computed(() => {
  const statusMap = new Map(
    statusCards.value.map((item) => [item.status_code, item]),
  );
  const c = statusMap.get('C');
  const a = statusMap.get('A');
  const totalCount = summary.value.total_count || 0;
  const totalManDay = summary.value.total_workload_man_day || 0;
  const totalKloc = summary.value.total_workload_kloc || 0;
  const developmentCount = Number(c?.count || 0) + Number(a?.count || 0);
  const developmentManDay =
    Number(c?.workload_man_day || 0) + Number(a?.workload_man_day || 0);
  const developmentKloc =
    Number(c?.workload_kloc || 0) + Number(a?.workload_kloc || 0);
  const acceptanceCount = Number(a?.count || 0);
  const acceptanceManDay = Number(a?.workload_man_day || 0);
  const acceptanceKloc = Number(a?.workload_kloc || 0);

  return {
    development: {
      count: developmentCount,
      countRate: totalCount ? developmentCount / totalCount : 0,
      workloadManDay: developmentManDay,
      workloadManDayRate: totalManDay ? developmentManDay / totalManDay : 0,
      workloadKloc: developmentKloc,
      workloadKlocRate: totalKloc ? developmentKloc / totalKloc : 0,
    },
    acceptance: {
      count: acceptanceCount,
      countRate: totalCount ? acceptanceCount / totalCount : 0,
      workloadManDay: acceptanceManDay,
      workloadManDayRate: totalManDay ? acceptanceManDay / totalManDay : 0,
      workloadKloc: acceptanceKloc,
      workloadKlocRate: totalKloc ? acceptanceKloc / totalKloc : 0,
    },
  };
});

function currentMonthKey() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function resolveMonthlySnapshot(rows: RequirementDeliveryTrendItem[]) {
  const row = rows.find((item) => item.month === currentMonthKey());
  return {
    planned_count: Number(row?.planned_count || 0),
    actual_count: Number(row?.actual_count || 0),
  };
}

const developmentMonthSnapshot = computed(() =>
  resolveMonthlySnapshot(summary.value.development_delivery_trend || []),
);
const acceptanceMonthSnapshot = computed(() =>
  resolveMonthlySnapshot(summary.value.acceptance_delivery_trend || []),
);

function getStatusValue(
  row: RequirementBoardSummary['team_summary'][number],
  code: string,
) {
  switch (code) {
    case 'A': {
      return row.a_count;
    }
    case 'C': {
      return row.c_count;
    }
    case 'D': {
      return row.d_count;
    }
    case 'I': {
      return row.i_count;
    }
    case 'P': {
      return row.p_count;
    }
    default: {
      return 0;
    }
  }
}

function getCategoryTagType(category: string) {
  if (category === 'AR') return 'danger';
  if (category === 'DR') return 'warning';
  if (category === 'SR') return 'success';
  return 'info';
}

function getStatusBadgeClass(statusCode: string) {
  return `requirement-status-badge ${
    STATUS_META_MAP[statusCode]?.badgeClass || 'requirement-status-badge--i'
  }`;
}

function getStatusAccent(statusCode: string) {
  return STATUS_META_MAP[statusCode]?.accent || '#0f172a';
}

function getStableTagType(text: string) {
  const normalized = String(text || '').trim();
  if (!normalized) {
    return 'info';
  }
  const palette = ['primary', 'success', 'warning', 'danger', 'info'];
  let hash = 0;
  for (const char of normalized) {
    hash = (hash * 31 + (char.codePointAt(0) || 0)) >>> 0;
  }
  return palette[hash % palette.length];
}

function getTeamTagType(teamName: string) {
  if (!String(teamName || '').trim() || teamName === '未识别团队') {
    return 'info';
  }
  return getStableTagType(teamName);
}

function buildUserOption(item: { name?: string; username?: string }) {
  const username = String(item.username || '').trim();
  const name = String(item.name || '').trim();
  return {
    label: name ? `${username} · ${name}` : username,
    value: username,
  };
}

function mergeUserOptions(
  target: typeof developUserOptions,
  selectedValues?: string[],
  incoming?: UserOption[],
) {
  const next = new Map<string, UserOption>();
  [...(target.value || []), ...(incoming || [])].forEach((item) => {
    if (!item?.value) {
      return;
    }
    next.set(item.value, item);
  });
  (selectedValues || []).forEach((item) => {
    if (!next.has(item)) {
      next.set(item, { label: item, value: item });
    }
  });
  target.value = [...next.values()].sort((a, b) =>
    a.value.localeCompare(b.value),
  );
}

async function searchUsers(keyword: string, type: 'develop' | 'test') {
  const target = type === 'develop' ? developUserOptions : testUserOptions;
  const loading = type === 'develop' ? developUserLoading : testUserLoading;
  const selectedValues =
    type === 'develop' ? filters.value.develop_users : filters.value.test_users;
  const normalizedKeyword = String(keyword || '').trim();
  if (!normalizedKeyword) {
    mergeUserOptions(target, selectedValues);
    return;
  }

  loading.value = true;
  try {
    const response = await searchUserApi(normalizedKeyword);
    const incoming = (response.items || [])
      .map((item) => buildUserOption(item))
      .filter((item) => item.value);
    mergeUserOptions(target, selectedValues, incoming);
  } catch (error) {
    console.error(error);
    ElMessage.error('检索责任人失败');
  } finally {
    loading.value = false;
  }
}

watch(
  () => filters.value.develop_users,
  (value) => {
    mergeUserOptions(developUserOptions, value);
  },
  { deep: true, immediate: true },
);

watch(
  () => filters.value.test_users,
  (value) => {
    mergeUserOptions(testUserOptions, value);
  },
  { deep: true, immediate: true },
);

async function loadFilterOptions() {
  optionsLoading.value = true;
  try {
    const result = await getRequirementBoardFilterOptionsApi();
    projectOptions.value = sortProjectOptions(result.projects || []);
  } catch (error) {
    console.error(error);
    ElMessage.error('加载需求看板筛选项失败');
  } finally {
    optionsLoading.value = false;
  }
}

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    columns: useRequirementColumns(),
    border: true,
    stripe: true,
    rowKey: 'requirement_id',
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
          const response = await getRequirementBoardDataApi({
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

const dataResultCount = computed(() => Number(gridApi.total.value || 0));
const canExport = computed(
  () =>
    hasAppliedFilters.value &&
    dataResultCount.value > 0 &&
    !exportLoading.value,
);

watch(
  () => gridApi.tableData.value.length,
  async () => {
    await nextTick();
    updateDataGridHeight();
  },
);

async function fetchSummary(force = false) {
  if (!appliedFilters.value) {
    summary.value = createEmptyRequirementSummary();
    summaryFingerprint.value = '';
    return;
  }

  const currentFingerprint = buildFingerprint(appliedFilters.value);
  if (!force && summaryFingerprint.value === currentFingerprint) {
    return;
  }

  summaryLoading.value = true;
  try {
    summary.value = await getRequirementBoardSummaryApi(appliedFilters.value);
    summaryFingerprint.value = currentFingerprint;
  } catch (error) {
    console.error(error);
    ElMessage.error('加载需求总结失败');
  } finally {
    summaryLoading.value = false;
  }
}

function toggleFilterCollapsed() {
  filterCollapsed.value = !filterCollapsed.value;
}

function handleProjectSelectorConfirm(projectIds: string[]) {
  filters.value.project_ids = normalizeStringArray(projectIds);
}

function clearSelectedProjects() {
  filters.value.project_ids = [];
}

function buildExportFilename() {
  const current = new Date();
  const pad = (value: number) => String(value).padStart(2, '0');
  return `需求数据看板-${current.getFullYear()}${pad(current.getMonth() + 1)}${pad(current.getDate())}-${pad(current.getHours())}${pad(current.getMinutes())}${pad(current.getSeconds())}.xlsx`;
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

async function handleSearch() {
  const payload = cloneFilterPayload(filters.value);
  if (payload.project_ids.length === 0) {
    ElMessage.warning('请至少选择一个项目');
    return;
  }

  appliedFilters.value = payload;
  summaryFingerprint.value = '';
  gridApi.pagination.currentPage = 1;
  await nextTick();
  await gridApi.reload();
  await nextTick();
  updateDataGridHeight();
  if (activeTab.value === 'summary') {
    await fetchSummary(true);
  }
}

function clearGridData() {
  gridApi.tableData.value = [];
  gridApi.total.value = 0;
  gridApi.pagination.total = 0;
}

async function handleReset() {
  filters.value = {
    project_ids: [],
    sub_teams: [],
    categories: [...DEFAULT_CATEGORIES],
    verification_policies: [],
    develop_users: [],
    test_users: [],
    time_field: DEFAULT_TIME_FIELD,
    time_start: '',
    time_end: '',
  };
  dateRange.value = null;
  developUserOptions.value = [];
  testUserOptions.value = [];
  projectSelectorVisible.value = false;
  appliedFilters.value = null;
  summary.value = createEmptyRequirementSummary();
  summaryFingerprint.value = '';
  gridApi.pagination.currentPage = 1;
  clearGridData();
}

async function handleExport() {
  if (!appliedFilters.value) {
    ElMessage.warning('请先查询需求数据');
    return;
  }
  if (dataResultCount.value <= 0) {
    ElMessage.warning('当前没有可导出的需求数据');
    return;
  }

  exportLoading.value = true;
  try {
    const blob = await exportRequirementBoardApi(appliedFilters.value);
    triggerBlobDownload(blob as Blob, buildExportFilename());
    ElMessage.success('导出成功');
  } catch (error) {
    console.error(error);
    ElMessage.error('导出失败，请检查筛选条件后重试');
  } finally {
    exportLoading.value = false;
  }
}

watch(
  () => filters.value.project_ids,
  () => {
    const available = new Set(teamOptions.value.map((item) => item.value));
    filters.value.sub_teams = normalizeStringArray(
      filters.value.sub_teams,
    ).filter((item) => available.has(item));
  },
  { deep: true },
);

watch(
  () => activeTab.value,
  async (value) => {
    if (value === 'summary' && appliedFilters.value) {
      await fetchSummary();
    }
  },
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

watch(
  () => summary.value.team_summary,
  (rows) => {
    if (rows.length === 0) {
      renderEmptyChart(renderTeamStatusChart, '暂无团队状态分布');
      return;
    }

    const zoomEnd = teamChartZoomEnd.value;
    const enableZoom = rows.length > 12;

    renderTeamStatusChart({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: {
        type: 'scroll',
        top: 0,
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 12,
        textStyle: { color: '#64748b', fontSize: 12 },
      },
      grid: {
        left: 16,
        right: enableZoom ? 40 : 16,
        top: 48,
        bottom: 16,
        containLabel: true,
      },
      dataZoom: enableZoom
        ? [
            {
              type: 'slider',
              yAxisIndex: 0,
              orient: 'vertical',
              right: 6,
              top: 56,
              bottom: 16,
              start: 0,
              end: zoomEnd,
              width: 10,
            },
            {
              type: 'inside',
              yAxisIndex: 0,
              orient: 'vertical',
              start: 0,
              end: zoomEnd,
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
        data: rows.map((item) => item.team_name || '未识别团队'),
        axisLabel: {
          color: '#475569',
          fontSize: 12,
          interval: 0,
          formatter: (value: string) =>
            value.length > 10 ? `${value.slice(0, 10)}…` : value,
        },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: STATUS_META.map((item) => ({
        name: `${item.status_code} · ${item.status_label}`,
        type: 'bar',
        stack: 'total',
        emphasis: { focus: 'series' },
        barMaxWidth: 18,
        itemStyle: {
          color: getTeamStatusChartColor(item.status_code),
          borderRadius: [4, 4, 4, 4],
        },
        data: rows.map((row) => getStatusValue(row, item.status_code)),
      })),
    });
  },
  { deep: true, immediate: true },
);

watch(
  [activeTab, hasAppliedFilters, filterCollapsed],
  async () => {
    await nextTick();
    updateDataGridHeight();
  },
  { immediate: true },
);

function renderTrendChart(
  render: (options: Record<string, any>) => void,
  rows: RequirementDeliveryTrendItem[],
  title: string,
  plannedLabel: string,
  actualLabel: string,
  plannedColor: string,
  actualColor: string,
) {
  if (rows.length === 0) {
    renderEmptyChart(render, `${title}暂无数据`);
    return;
  }

  render({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: '3%', right: '4%', top: 46, bottom: 16, containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map((item) => item.month),
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: plannedLabel,
        type: 'bar',
        data: rows.map((item) => item.planned_count),
        itemStyle: { color: plannedColor, borderRadius: [6, 6, 0, 0] },
      },
      {
        name: actualLabel,
        type: 'line',
        smooth: true,
        data: rows.map((item) => item.actual_count),
        lineStyle: { color: actualColor, width: 3 },
        itemStyle: { color: actualColor },
      },
    ],
  });
}

watch(
  () => summary.value.development_delivery_trend,
  (rows) => {
    renderTrendChart(
      renderDevelopmentTrendChart,
      rows,
      '开发交付趋势',
      '计划转测',
      '实际开发完成',
      '#93c5fd',
      '#f97316',
    );
  },
  { deep: true, immediate: true },
);

watch(
  () => summary.value.acceptance_delivery_trend,
  (rows) => {
    renderTrendChart(
      renderAcceptanceTrendChart,
      rows,
      '测试交付趋势',
      '计划完成',
      '实际验收完成',
      '#86efac',
      '#0f766e',
    );
  },
  { deep: true, immediate: true },
);

function renderOwnerRankChart(
  render: (options: Record<string, any>) => void,
  rows: RequirementUserSummaryItem[],
  title: string,
  color: string,
) {
  const displayRows = [...rows].slice(0, 10).reverse();
  if (displayRows.length === 0) {
    renderEmptyChart(render, `${title}暂无数据`);
    return;
  }

  render({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: Array<{ dataIndex: number; value: number }>) {
        const index = params?.[0]?.dataIndex ?? 0;
        const row = displayRows[index];
        return [
          row.username,
          `任务数：${row.task_count}`,
          `工作量：${formatMetric(row.workload_man_day)} 人天`,
          `代码量：${formatMetric(row.workload_kloc)} KLOC`,
        ].join('<br/>');
      },
    },
    grid: { left: '4%', right: '6%', top: 16, bottom: 18, containLabel: true },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: {
      type: 'category',
      data: displayRows.map((item) => item.username),
      axisLabel: {
        width: 110,
        overflow: 'truncate',
      },
    },
    series: [
      {
        name: title,
        type: 'bar',
        barWidth: 18,
        itemStyle: { color, borderRadius: [0, 8, 8, 0] },
        data: displayRows.map((item) => item.task_count),
      },
    ],
  });
}

watch(
  () => summary.value.user_summary.develop_users,
  (rows) => {
    renderOwnerRankChart(
      renderDevelopOwnerChart,
      rows,
      '开发责任人排行',
      '#2563eb',
    );
  },
  { deep: true, immediate: true },
);

watch(
  () => summary.value.user_summary.test_users,
  (rows) => {
    renderOwnerRankChart(
      renderTestOwnerChart,
      rows,
      '测试责任人排行',
      '#059669',
    );
  },
  { deep: true, immediate: true },
);

onMounted(async () => {
  updateFilterCollapseByWidth();
  updateDataGridHeight();
  window.addEventListener('resize', handleFilterResize);
  await loadFilterOptions();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleFilterResize);
  if (filterResizeTimer) {
    window.clearTimeout(filterResizeTimer);
  }
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex flex-col gap-4">
      <ElCard shadow="never" class="requirement-filter-card">
        <div class="requirement-filter-card__header">
          <div>
            <div class="requirement-filter-card__title">需求看板筛选</div>
            <div class="requirement-filter-card__desc">
              项目/团队/类型/验证策略为基础筛选，责任人和时间区间支持组合查询；责任人命中任一
              username 即计入结果。
            </div>
          </div>
          <div class="requirement-filter-card__actions">
            <ElTag type="primary" effect="light">
              {{ configuredProjectOptions.length }} 个项目可查询
            </ElTag>
            <ElButton
              text
              size="small"
              class="requirement-filter-card__toggle"
              @click="toggleFilterCollapsed"
            >
              {{ filterToggleLabel }}
            </ElButton>
          </div>
        </div>

        <div v-show="!filterCollapsed">
          <ElForm
            :model="filters"
            label-width="92px"
            class="requirement-filter-form"
          >
            <ElFormItem
              label="项目"
              class="requirement-filter-form__item requirement-filter-form__item--project"
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

            <ElFormItem label="责任团队" class="requirement-filter-form__item">
              <ElSelect
                v-model="filters.sub_teams"
                class="requirement-filter-control"
                collapse-tags
                collapse-tags-tooltip
                filterable
                multiple
                clearable
                :disabled="selectedProjects.length === 0"
                placeholder="按所选项目动态生成"
              >
                <ElOption
                  v-for="item in teamOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>

            <ElFormItem label="需求类型" class="requirement-filter-form__item">
              <ElSelect
                v-model="filters.categories"
                class="requirement-filter-control"
                collapse-tags
                collapse-tags-tooltip
                filterable
                multiple
                clearable
                placeholder="默认全选"
              >
                <ElOption
                  v-for="item in CATEGORY_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>

            <ElFormItem label="验证策略" class="requirement-filter-form__item">
              <ElSelect
                v-model="filters.verification_policies"
                class="requirement-filter-control"
                collapse-tags
                collapse-tags-tooltip
                filterable
                multiple
                clearable
                placeholder="默认不过滤"
              >
                <ElOption
                  v-for="item in VERIFICATION_POLICY_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>

            <ElFormItem
              label="开发责任人"
              class="requirement-filter-form__item"
            >
              <ElSelect
                v-model="filters.develop_users"
                class="requirement-filter-control"
                multiple
                collapse-tags
                collapse-tags-tooltip
                filterable
                remote
                reserve-keyword
                clearable
                :loading="developUserLoading"
                placeholder="按 username 搜索"
                :remote-method="
                  (value: string) => searchUsers(value, 'develop')
                "
              >
                <ElOption
                  v-for="item in developUserOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>

            <ElFormItem
              label="测试责任人"
              class="requirement-filter-form__item"
            >
              <ElSelect
                v-model="filters.test_users"
                class="requirement-filter-control"
                multiple
                collapse-tags
                collapse-tags-tooltip
                filterable
                remote
                reserve-keyword
                clearable
                :loading="testUserLoading"
                placeholder="按 username 搜索"
                :remote-method="(value: string) => searchUsers(value, 'test')"
              >
                <ElOption
                  v-for="item in testUserOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>

            <ElFormItem label="时间维度" class="requirement-filter-form__item">
              <ElSelect
                v-model="filters.time_field"
                class="requirement-filter-control"
                clearable
                placeholder="默认测试完成时间"
              >
                <ElOption
                  v-for="item in TIME_FIELD_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>

            <ElFormItem label="时间区间" class="requirement-filter-form__item">
              <ElDatePicker
                v-model="dateRange"
                class="requirement-filter-control"
                type="daterange"
                range-separator="-"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
              />
            </ElFormItem>

            <ElFormItem
              class="requirement-filter-form__item requirement-filter-form__item--actions"
            >
              <ElButton type="primary" @click="handleSearch">查询</ElButton>
              <ElButton @click="handleReset">重置</ElButton>
            </ElFormItem>
          </ElForm>

          <div class="requirement-filter-card__footer">
            <span>
              当前可查询项目
              {{ configuredProjectOptions.length }}
              个；团队随项目自动去重，未完成配置的项目已禁用。
            </span>
            <span>
              当前时间维度：{{
                activeTimeFieldLabel
              }}；只有选择时间区间后才参与筛选。
            </span>
            <span>
              多责任人统计按“每位责任人全量计入”口径汇总，因此责任人排行总量可能大于全局总量。
            </span>
          </div>
        </div>

        <div v-show="filterCollapsed" class="requirement-filter-card__summary">
          <span>{{ filterSummaryText }}</span>
          <span class="requirement-filter-card__summary-hint">
            展开筛选可调整条件或重新查询
          </span>
        </div>
      </ElCard>

      <ElTabs v-model="activeTab" class="requirement-board-tabs flex flex-col">
        <ElTabPane label="需求数据看板" name="data">
          <div class="flex flex-col">
            <ElCard shadow="never" class="requirement-data-card">
              <template #header>
                <div class="requirement-data-card__header">
                  <div>
                    <div class="requirement-data-card__title">需求明细表</div>
                    <div class="requirement-data-card__desc">
                      查询后在下方表格展示明细，可按验证策略进一步收敛范围。
                    </div>
                  </div>
                  <div class="requirement-data-card__actions">
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
                      class="requirement-data-card__status"
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

              <div v-if="hasAppliedFilters" class="requirement-data-card__body">
                <div
                  ref="dataGridWrapRef"
                  class="requirement-data-grid-wrap"
                  :style="dataGridWrapStyle"
                >
                  <Grid class="requirement-data-grid h-full min-h-0">
                    <template #table-title>
                      <div class="requirement-table-title">
                        需求明细表、分页展示需求明细，可快速查看团队、状态、时间节点、延期标签与多责任人分布。
                      </div>
                    </template>
                    <template #cell-team_name="{ row }">
                      <ElTag
                        :type="getTeamTagType(row.team_name)"
                        effect="light"
                        class="requirement-team-badge"
                      >
                        <span class="requirement-team-badge__text">
                          {{ row.team_name || '未识别团队' }}
                        </span>
                      </ElTag>
                    </template>

                    <template #cell-category="{ row }">
                      <ElTag
                        :type="getCategoryTagType(row.category)"
                        effect="plain"
                        class="requirement-category-badge"
                      >
                        {{ row.category }}
                      </ElTag>
                    </template>

                    <template #cell-verification_policy_label="{ row }">
                      <ElTag effect="light" type="info">
                        {{ row.verification_policy_label || '--' }}
                      </ElTag>
                    </template>

                    <template #cell-status_code="{ row }">
                      <ElTag
                        :class="getStatusBadgeClass(row.status_code)"
                        effect="plain"
                      >
                        <span class="requirement-status-dot"></span>
                        {{ row.status_code }} · {{ row.status_label }}
                      </ElTag>
                    </template>

                    <template #cell-planned_test_time="{ row }">
                      {{ formatDateTime(row.planned_test_time) }}
                    </template>

                    <template #cell-due_date="{ row }">
                      {{ formatDateTime(row.due_date) }}
                    </template>

                    <template #cell-completed_time="{ row }">
                      {{ formatDateTime(row.completed_time) }}
                    </template>

                    <template #cell-accepted_time="{ row }">
                      {{ formatDateTime(row.accepted_time) }}
                    </template>

                    <template #cell-is_dev_delayed="{ row }">
                      <ElTag
                        :type="row.is_dev_delayed ? 'danger' : 'success'"
                        :effect="row.is_dev_delayed ? 'dark' : 'plain'"
                        class="delay-indicator"
                      >
                        {{ row.is_dev_delayed ? '延期' : '正常' }}
                      </ElTag>
                    </template>

                    <template #cell-is_test_delayed="{ row }">
                      <ElTag
                        :type="row.is_test_delayed ? 'danger' : 'success'"
                        :effect="row.is_test_delayed ? 'dark' : 'plain'"
                        class="delay-indicator"
                      >
                        {{ row.is_test_delayed ? '延期' : '正常' }}
                      </ElTag>
                    </template>

                    <template #cell-workload_kloc="{ row }">
                      {{ formatMetric(row.workload_kloc) }}
                    </template>

                    <template #cell-workload_man_day="{ row }">
                      {{ formatMetric(row.workload_man_day) }}
                    </template>

                    <template #cell-develop_user_display="{ row }">
                      <div class="owner-tag-list">
                        <ElTag
                          v-for="item in row.develop_users"
                          :key="`dev-${row.requirement_id}-${item}`"
                          :type="getStableTagType(item)"
                          effect="plain"
                          class="owner-tag"
                        >
                          {{ item }}
                        </ElTag>
                        <span
                          v-if="!row.develop_users?.length"
                          class="text-slate-400"
                        >
                          --
                        </span>
                      </div>
                    </template>

                    <template #cell-test_user_display="{ row }">
                      <div class="owner-tag-list">
                        <ElTag
                          v-for="item in row.test_users"
                          :key="`test-${row.requirement_id}-${item}`"
                          :type="getStableTagType(item)"
                          effect="plain"
                          class="owner-tag"
                        >
                          {{ item }}
                        </ElTag>
                        <span
                          v-if="!row.test_users?.length"
                          class="text-slate-400"
                        >
                          --
                        </span>
                      </div>
                    </template>
                  </Grid>
                </div>
              </div>

              <div v-else class="requirement-data-guide">
                <div class="requirement-data-guide__panel">
                  <div class="requirement-data-guide__eyebrow">
                    需求数据看板
                  </div>
                  <div class="requirement-data-guide__title">
                    先组合筛选条件，再拉取需求明细
                  </div>
                  <div class="requirement-data-guide__desc">
                    数据看板不会预加载全量需求。请选择项目，可按团队、类型、责任人和自定义时间区间进行组合查询。
                  </div>

                  <div class="requirement-guide-steps">
                    <div class="requirement-guide-step">
                      <div class="requirement-guide-step__index">1</div>
                      <div class="requirement-guide-step__title">选择项目</div>
                      <div class="requirement-guide-step__desc">
                        当前已选
                        {{ filters.project_ids.length }}
                        个项目；未完成配置的项目已自动禁用。
                      </div>
                    </div>
                    <div class="requirement-guide-step">
                      <div class="requirement-guide-step__index">2</div>
                      <div class="requirement-guide-step__title">
                        选择团队与类型
                      </div>
                      <div class="requirement-guide-step__desc">
                        当前已选 {{ filters.sub_teams?.length || 0 }} 个团队、{{
                          selectedCategoryCount
                        }}
                        种需求类型，验证策略
                        {{ selectedVerificationPolicyCount }} 个。
                      </div>
                    </div>
                    <div class="requirement-guide-step">
                      <div class="requirement-guide-step__index">3</div>
                      <div class="requirement-guide-step__title">
                        补充责任人与时间
                      </div>
                      <div class="requirement-guide-step__desc">
                        可按开发/测试责任人筛选；时间维度当前为
                        {{ activeTimeFieldLabel }}。
                      </div>
                    </div>
                    <div class="requirement-guide-step">
                      <div class="requirement-guide-step__index">4</div>
                      <div class="requirement-guide-step__title">点击查询</div>
                      <div class="requirement-guide-step__desc">
                        查询后切换到总结看板，可直接复用同一组筛选条件查看统计结果。
                      </div>
                    </div>
                  </div>

                  <div class="mt-6 flex flex-wrap items-center gap-3">
                    <ElButton type="primary" @click="handleSearch">
                      开始查询明细
                    </ElButton>
                    <span class="text-xs text-slate-500">
                      查询后保留筛选条件，可直接切换到总结看板查看趋势、延期和责任人排行。
                    </span>
                  </div>
                </div>
              </div>
            </ElCard>
          </div>
        </ElTabPane>

        <ElTabPane label="需求总结看板" name="summary">
          <div
            v-loading="summaryLoading"
            class="requirement-summary-panel space-y-4 pb-4"
          >
            <ElEmpty
              v-if="!hasAppliedFilters"
              description="请选择项目并点击查询后查看总结"
            />
            <template v-else>
              <div class="summary-overview-grid">
                <ElCard
                  shadow="never"
                  class="dense-overview-card dense-overview-card--hero"
                >
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">总览卡</div>
                    <ElTag type="primary" effect="light">当前筛选</ElTag>
                  </div>
                  <div class="dense-overview-card__hero-value">
                    {{ summary.total_count }}
                  </div>
                  <div class="dense-overview-card__hero-label">总需求数</div>
                  <div class="dense-overview-card__metric-grid">
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">总人天</div>
                      <div class="dense-metric-block__value">
                        {{ formatMetric(summary.total_workload_man_day) }}
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">总 KLOC</div>
                      <div class="dense-metric-block__value">
                        {{ formatMetric(summary.total_workload_kloc) }}
                      </div>
                    </div>
                  </div>
                </ElCard>

                <ElCard shadow="never" class="dense-overview-card">
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">整体完成卡</div>
                    <ElTag type="success" effect="light">C+A / A</ElTag>
                  </div>
                  <div class="dense-completion-grid">
                    <div
                      class="dense-completion-panel dense-completion-panel--dev"
                    >
                      <div class="dense-completion-panel__title">
                        开发完成（C+A）
                      </div>
                      <div class="dense-completion-panel__headline">
                        {{ overallCompletion.development.count }} /
                        {{
                          formatPercent(overallCompletion.development.countRate)
                        }}
                      </div>
                      <ElProgress
                        :percentage="
                          Number(
                            (
                              overallCompletion.development.countRate * 100
                            ).toFixed(1),
                          )
                        "
                        :stroke-width="8"
                        :show-text="false"
                        color="#f97316"
                      />
                      <div class="dense-completion-panel__meta">
                        <span>
                          人天
                          {{
                            formatMetric(
                              overallCompletion.development.workloadManDay,
                            )
                          }}
                          /
                          {{
                            formatPercent(
                              overallCompletion.development.workloadManDayRate,
                            )
                          }}
                        </span>
                        <span>
                          KLOC
                          {{
                            formatMetric(
                              overallCompletion.development.workloadKloc,
                            )
                          }}
                          /
                          {{
                            formatPercent(
                              overallCompletion.development.workloadKlocRate,
                            )
                          }}
                        </span>
                      </div>
                    </div>
                    <div
                      class="dense-completion-panel dense-completion-panel--acceptance"
                    >
                      <div class="dense-completion-panel__title">
                        验收完成（A）
                      </div>
                      <div class="dense-completion-panel__headline">
                        {{ overallCompletion.acceptance.count }} /
                        {{
                          formatPercent(overallCompletion.acceptance.countRate)
                        }}
                      </div>
                      <ElProgress
                        :percentage="
                          Number(
                            (
                              overallCompletion.acceptance.countRate * 100
                            ).toFixed(1),
                          )
                        "
                        :stroke-width="8"
                        :show-text="false"
                        color="#16a34a"
                      />
                      <div class="dense-completion-panel__meta">
                        <span>
                          人天
                          {{
                            formatMetric(
                              overallCompletion.acceptance.workloadManDay,
                            )
                          }}
                          /
                          {{
                            formatPercent(
                              overallCompletion.acceptance.workloadManDayRate,
                            )
                          }}
                        </span>
                        <span>
                          KLOC
                          {{
                            formatMetric(
                              overallCompletion.acceptance.workloadKloc,
                            )
                          }}
                          /
                          {{
                            formatPercent(
                              overallCompletion.acceptance.workloadKlocRate,
                            )
                          }}
                        </span>
                      </div>
                    </div>
                  </div>
                </ElCard>

                <ElCard shadow="never" class="dense-overview-card">
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">需求分发率</div>
                    <ElTag type="info" effect="light">P 状态</ElTag>
                  </div>
                  <div class="dense-overview-card__metric-grid">
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">
                        开发责任人已填
                      </div>
                      <div class="dense-metric-block__value">
                        {{ dispatchRate.develop_owner_count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        {{ formatPercent(dispatchRate.develop_owner_rate) }}
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">
                        测试责任人已填
                      </div>
                      <div class="dense-metric-block__value">
                        {{ dispatchRate.test_owner_count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        {{ formatPercent(dispatchRate.test_owner_rate) }}
                      </div>
                    </div>
                  </div>
                  <div class="dense-overview-card__meta">
                    已置 P 需求 {{ dispatchRate.p_total }} 条
                  </div>
                </ElCard>

                <ElCard shadow="never" class="dense-overview-card">
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">需求计划刷新率</div>
                    <ElTag type="warning" effect="light">计划字段</ElTag>
                  </div>
                  <div class="dense-overview-card__metric-grid">
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">
                        计划转测时间已填
                      </div>
                      <div class="dense-metric-block__value">
                        {{ planRefreshRate.planned_test_time_count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        {{
                          formatPercent(planRefreshRate.planned_test_time_rate)
                        }}
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">
                        计划完成时间已填
                      </div>
                      <div class="dense-metric-block__value">
                        {{ planRefreshRate.due_date_count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        {{ formatPercent(planRefreshRate.due_date_rate) }}
                      </div>
                    </div>
                  </div>
                  <div class="dense-overview-card__meta">
                    总需求 {{ summary.total_count }} 条
                  </div>
                </ElCard>

                <ElCard shadow="never" class="dense-overview-card">
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">开发交付卡</div>
                    <ElTag type="warning" effect="light">转测维度</ElTag>
                  </div>
                  <div
                    class="dense-overview-card__metric-grid dense-overview-card__metric-grid--three"
                  >
                    <div class="dense-metric-block dense-metric-block--warning">
                      <div class="dense-metric-block__label">开发延期</div>
                      <div class="dense-metric-block__value">
                        {{ summary.delay_summary.development.count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        {{
                          formatPercent(summary.delay_summary.development.rate)
                        }}
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">本月计划转测</div>
                      <div class="dense-metric-block__value">
                        {{ developmentMonthSnapshot.planned_count }}
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">本月实际完成</div>
                      <div class="dense-metric-block__value">
                        {{ developmentMonthSnapshot.actual_count }}
                      </div>
                    </div>
                  </div>
                </ElCard>

                <ElCard shadow="never" class="dense-overview-card">
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">测试交付卡</div>
                    <ElTag type="success" effect="light">验收维度</ElTag>
                  </div>
                  <div
                    class="dense-overview-card__metric-grid dense-overview-card__metric-grid--three"
                  >
                    <div class="dense-metric-block dense-metric-block--danger">
                      <div class="dense-metric-block__label">测试延期</div>
                      <div class="dense-metric-block__value">
                        {{ summary.delay_summary.acceptance.count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        {{
                          formatPercent(summary.delay_summary.acceptance.rate)
                        }}
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">本月计划交付</div>
                      <div class="dense-metric-block__value">
                        {{ acceptanceMonthSnapshot.planned_count }}
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">本月实际验收</div>
                      <div class="dense-metric-block__value">
                        {{ acceptanceMonthSnapshot.actual_count }}
                      </div>
                    </div>
                  </div>
                </ElCard>
              </div>

              <div class="status-density-grid">
                <ElCard
                  v-for="item in statusCards"
                  :key="item.status_code"
                  shadow="never"
                  class="status-density-card"
                  :style="{
                    '--status-accent': getStatusAccent(item.status_code),
                  }"
                >
                  <div class="status-density-card__top">
                    <div class="status-density-card__code">
                      <span class="status-density-card__code-text">{{
                        item.status_code
                      }}</span>
                      <span class="status-density-card__hint">{{
                        item.shortHint
                      }}</span>
                    </div>
                    <ElTag
                      :class="getStatusBadgeClass(item.status_code)"
                      effect="plain"
                    >
                      {{ item.status_label }}
                    </ElTag>
                  </div>
                  <div class="status-density-card__desc">
                    {{ item.description }}
                  </div>
                  <div class="status-density-card__metrics">
                    <div>
                      <div class="status-density-card__metric-label">数量</div>
                      <div class="status-density-card__metric-value">
                        {{ item.count }}
                      </div>
                    </div>
                    <div>
                      <div class="status-density-card__metric-label">占比</div>
                      <div class="status-density-card__metric-value">
                        {{ formatPercent(item.count_rate) }}
                      </div>
                    </div>
                    <div>
                      <div class="status-density-card__metric-label">人天</div>
                      <div class="status-density-card__metric-value">
                        {{ formatMetric(item.workload_man_day) }}
                      </div>
                    </div>
                    <div>
                      <div class="status-density-card__metric-label">KLOC</div>
                      <div class="status-density-card__metric-value">
                        {{ formatMetric(item.workload_kloc) }}
                      </div>
                    </div>
                  </div>
                </ElCard>
              </div>

              <div class="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
                <ElCard
                  shadow="never"
                  class="summary-section-card summary-section-card--compact"
                >
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">
                          团队状态堆叠图
                        </div>
                        <div class="summary-section-card__desc">
                          以团队为维度查看 I/D/P/C/A
                          状态分布，快速识别推进中、待验收和已完成的需求规模。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="primary"
                        effect="plain"
                      >
                        {{ summaryTeamCount }} 个团队
                      </ElTag>
                    </div>
                  </template>
                  <div
                    class="team-status-chart w-full"
                    :style="{ height: `${teamChartHeight}px` }"
                  >
                    <EchartsUI ref="teamStatusChartRef" />
                  </div>
                </ElCard>

                <ElCard
                  shadow="never"
                  class="summary-section-card summary-section-card--compact"
                >
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">类型分布</div>
                        <div class="summary-section-card__desc">
                          统计 AR / DR / SR
                          在当前筛选条件下的数量、工作量和代码量占比。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="warning"
                        effect="plain"
                      >
                        {{ summaryTypeCount }} 类类型
                      </ElTag>
                    </div>
                  </template>
                  <ElTable
                    :data="summary.type_summary"
                    size="small"
                    class="summary-simple-table"
                  >
                    <ElTableColumn label="类型" min-width="120">
                      <template #default="{ row }">
                        <ElTag
                          :type="getCategoryTagType(row.category)"
                          effect="plain"
                          class="requirement-category-badge"
                        >
                          {{ row.category }}
                        </ElTag>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="需求数" min-width="100">
                      <template #default="{ row }">
                        <span class="summary-count-pill">{{
                          row.total_count
                        }}</span>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="工作量(人天)" min-width="120">
                      <template #default="{ row }">
                        <span class="summary-metric-text">
                          {{ formatMetric(row.total_workload_man_day) }}
                        </span>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="代码量(KLOC)" min-width="120">
                      <template #default="{ row }">
                        <span class="summary-metric-text">
                          {{ formatMetric(row.total_workload_kloc) }}
                        </span>
                      </template>
                    </ElTableColumn>
                  </ElTable>
                </ElCard>
              </div>

              <div class="grid gap-4 xl:grid-cols-2">
                <ElCard shadow="never" class="summary-section-card">
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">
                          开发交付趋势图
                        </div>
                        <div class="summary-section-card__desc">
                          以月为维度对比计划转测数量与实际开发完成数量，判断开发交付节奏是否稳定。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="warning"
                        effect="light"
                      >
                        planned_test_time vs completed_time
                      </ElTag>
                    </div>
                  </template>
                  <div class="h-[320px] w-full">
                    <EchartsUI ref="developmentTrendChartRef" />
                  </div>
                </ElCard>

                <ElCard shadow="never" class="summary-section-card">
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">
                          测试交付趋势图
                        </div>
                        <div class="summary-section-card__desc">
                          以月为维度对比计划完成数量与实际验收完成数量，观察测试验收是否按期收敛。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="success"
                        effect="light"
                      >
                        due_date vs accepted_time
                      </ElTag>
                    </div>
                  </template>
                  <div class="h-[320px] w-full">
                    <EchartsUI ref="acceptanceTrendChartRef" />
                  </div>
                </ElCard>
              </div>

              <div class="grid gap-4 xl:grid-cols-2">
                <ElCard shadow="never" class="summary-section-card">
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">
                          开发责任人排行图
                        </div>
                        <div class="summary-section-card__desc">
                          按任务数排序展示开发责任人负载。多人责任需求会对每位责任人全量计入。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="primary"
                        effect="plain"
                      >
                        Top 10
                      </ElTag>
                    </div>
                  </template>
                  <div class="h-[320px] w-full">
                    <EchartsUI ref="developOwnerChartRef" />
                  </div>
                </ElCard>

                <ElCard shadow="never" class="summary-section-card">
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">
                          测试责任人排行图
                        </div>
                        <div class="summary-section-card__desc">
                          按任务数排序展示测试责任人负载，便于快速定位验收压力集中区域。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="success"
                        effect="plain"
                      >
                        Top 10
                      </ElTag>
                    </div>
                  </template>
                  <div class="h-[320px] w-full">
                    <EchartsUI ref="testOwnerChartRef" />
                  </div>
                </ElCard>
              </div>

              <div class="grid gap-4 xl:grid-cols-2">
                <ElCard shadow="never" class="summary-section-card">
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">
                          开发延期风险
                        </div>
                        <div class="summary-section-card__desc">
                          判定口径：开发完成时间晚于计划转测时间，或当前未到 C/A
                          且已超过计划转测时间。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="danger"
                        effect="light"
                      >
                        {{ summary.delay_summary.development.count }} /
                        {{
                          formatPercent(summary.delay_summary.development.rate)
                        }}
                      </ElTag>
                    </div>
                  </template>
                  <div class="delay-overview-strip delay-overview-strip--dev">
                    <div>
                      <div class="delay-overview-strip__label">
                        开发延期数量
                      </div>
                      <div class="delay-overview-strip__value">
                        {{ summary.delay_summary.development.count }}
                      </div>
                    </div>
                    <div>
                      <div class="delay-overview-strip__label">延期占比</div>
                      <div class="delay-overview-strip__value">
                        {{
                          formatPercent(summary.delay_summary.development.rate)
                        }}
                      </div>
                    </div>
                  </div>
                  <ElTable
                    :data="summary.delay_summary.development.preview_items"
                    size="small"
                    class="summary-simple-table"
                  >
                    <ElTableColumn label="项目 / 团队" min-width="180">
                      <template #default="{ row }">
                        <div class="delay-preview-main">
                          {{ row.project_name }}
                        </div>
                        <ElTag
                          :type="getTeamTagType(row.team_name)"
                          effect="light"
                          class="requirement-team-badge mt-1"
                        >
                          {{ row.team_name || '未识别团队' }}
                        </ElTag>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="需求" min-width="220">
                      <template #default="{ row }">
                        <div class="delay-preview-main">
                          {{ row.requirement_id }}
                        </div>
                        <div class="delay-preview-sub">{{ row.title }}</div>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="状态" min-width="150">
                      <template #default="{ row }">
                        <ElTag
                          :class="getStatusBadgeClass(row.status_code)"
                          effect="plain"
                        >
                          {{ row.status_code }} · {{ row.status_label }}
                        </ElTag>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="计划转测" min-width="160">
                      <template #default="{ row }">
                        {{ formatDateTime(row.planned_test_time) }}
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="开发完成" min-width="160">
                      <template #default="{ row }">
                        {{ formatDateTime(row.completed_time) }}
                      </template>
                    </ElTableColumn>
                  </ElTable>
                </ElCard>

                <ElCard shadow="never" class="summary-section-card">
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">
                          测试延期风险
                        </div>
                        <div class="summary-section-card__desc">
                          判定口径：测试完成时间晚于计划完成时间，或当前未到 A
                          且已超过计划完成时间。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="danger"
                        effect="light"
                      >
                        {{ summary.delay_summary.acceptance.count }} /
                        {{
                          formatPercent(summary.delay_summary.acceptance.rate)
                        }}
                      </ElTag>
                    </div>
                  </template>
                  <div
                    class="delay-overview-strip delay-overview-strip--acceptance"
                  >
                    <div>
                      <div class="delay-overview-strip__label">
                        测试延期数量
                      </div>
                      <div class="delay-overview-strip__value">
                        {{ summary.delay_summary.acceptance.count }}
                      </div>
                    </div>
                    <div>
                      <div class="delay-overview-strip__label">延期占比</div>
                      <div class="delay-overview-strip__value">
                        {{
                          formatPercent(summary.delay_summary.acceptance.rate)
                        }}
                      </div>
                    </div>
                  </div>
                  <ElTable
                    :data="summary.delay_summary.acceptance.preview_items"
                    size="small"
                    class="summary-simple-table"
                  >
                    <ElTableColumn label="项目 / 团队" min-width="180">
                      <template #default="{ row }">
                        <div class="delay-preview-main">
                          {{ row.project_name }}
                        </div>
                        <ElTag
                          :type="getTeamTagType(row.team_name)"
                          effect="light"
                          class="requirement-team-badge mt-1"
                        >
                          {{ row.team_name || '未识别团队' }}
                        </ElTag>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="需求" min-width="220">
                      <template #default="{ row }">
                        <div class="delay-preview-main">
                          {{ row.requirement_id }}
                        </div>
                        <div class="delay-preview-sub">{{ row.title }}</div>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="状态" min-width="150">
                      <template #default="{ row }">
                        <ElTag
                          :class="getStatusBadgeClass(row.status_code)"
                          effect="plain"
                        >
                          {{ row.status_code }} · {{ row.status_label }}
                        </ElTag>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="计划完成" min-width="160">
                      <template #default="{ row }">
                        {{ formatDateTime(row.due_date) }}
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="测试完成" min-width="160">
                      <template #default="{ row }">
                        {{ formatDateTime(row.accepted_time) }}
                      </template>
                    </ElTableColumn>
                  </ElTable>
                </ElCard>
              </div>

              <ElCard shadow="never" class="summary-section-card">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">
                        团队完成统计
                      </div>
                      <div class="summary-section-card__desc">
                        同时给出总量、I/D/P/C/A
                        状态分布，以及开发完成（C+A）和验收完成（A）的数量、人天、KLOC
                        完成情况。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="success"
                      effect="light"
                    >
                      {{ summaryTeamCount }} 行团队汇总
                    </ElTag>
                  </div>
                </template>
                <ElTable
                  :data="summary.team_summary"
                  size="small"
                  class="summary-team-table"
                >
                  <ElTableColumn label="团队" min-width="180" fixed="left">
                    <template #default="{ row }">
                      <ElTag
                        :type="getTeamTagType(row.team_name)"
                        effect="light"
                        class="requirement-team-badge"
                      >
                        <span
                          class="requirement-team-badge__text requirement-team-badge__text--wide"
                        >
                          {{ row.team_name || '未识别团队' }}
                        </span>
                      </ElTag>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="总需求数" min-width="110">
                    <template #default="{ row }">
                      <span class="summary-count-pill">{{
                        row.total_count
                      }}</span>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="总工作量(人天)" min-width="130">
                    <template #default="{ row }">
                      <span class="summary-metric-text">
                        {{ formatMetric(row.total_workload_man_day) }}
                      </span>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="总代码量(KLOC)" min-width="130">
                    <template #default="{ row }">
                      <span class="summary-metric-text">
                        {{ formatMetric(row.total_workload_kloc) }}
                      </span>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn
                    v-for="item in STATUS_META"
                    :key="item.status_code"
                    :label="item.status_code"
                    min-width="84"
                  >
                    <template #default="{ row }">
                      <ElTag
                        class="summary-status-pill"
                        :class="[getStatusBadgeClass(item.status_code)]"
                        effect="plain"
                      >
                        {{ getStatusValue(row, item.status_code) }}
                      </ElTag>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="开发完成 数量/占比" min-width="170">
                    <template #default="{ row }">
                      <div
                        class="summary-progress-chip summary-progress-chip--dev"
                      >
                        <div class="summary-progress-chip__value">
                          {{ row.dev_done.count }}
                        </div>
                        <div class="summary-progress-chip__meta">
                          {{ formatPercent(row.dev_done.count_rate) }}
                        </div>
                      </div>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="开发完成 人天/占比" min-width="182">
                    <template #default="{ row }">
                      <div
                        class="summary-progress-chip summary-progress-chip--dev"
                      >
                        <div class="summary-progress-chip__value">
                          {{ formatMetric(row.dev_done.workload_man_day) }}
                        </div>
                        <div class="summary-progress-chip__meta">
                          {{
                            formatPercent(row.dev_done.workload_man_day_rate)
                          }}
                        </div>
                      </div>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="开发完成 KLOC/占比" min-width="182">
                    <template #default="{ row }">
                      <div
                        class="summary-progress-chip summary-progress-chip--dev"
                      >
                        <div class="summary-progress-chip__value">
                          {{ formatMetric(row.dev_done.workload_kloc) }}
                        </div>
                        <div class="summary-progress-chip__meta">
                          {{ formatPercent(row.dev_done.workload_kloc_rate) }}
                        </div>
                      </div>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="验收完成 数量/占比" min-width="170">
                    <template #default="{ row }">
                      <div
                        class="summary-progress-chip summary-progress-chip--acceptance"
                      >
                        <div class="summary-progress-chip__value">
                          {{ row.acceptance_done.count }}
                        </div>
                        <div class="summary-progress-chip__meta">
                          {{ formatPercent(row.acceptance_done.count_rate) }}
                        </div>
                      </div>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="验收完成 人天/占比" min-width="182">
                    <template #default="{ row }">
                      <div
                        class="summary-progress-chip summary-progress-chip--acceptance"
                      >
                        <div class="summary-progress-chip__value">
                          {{
                            formatMetric(row.acceptance_done.workload_man_day)
                          }}
                        </div>
                        <div class="summary-progress-chip__meta">
                          {{
                            formatPercent(
                              row.acceptance_done.workload_man_day_rate,
                            )
                          }}
                        </div>
                      </div>
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="验收完成 KLOC/占比" min-width="182">
                    <template #default="{ row }">
                      <div
                        class="summary-progress-chip summary-progress-chip--acceptance"
                      >
                        <div class="summary-progress-chip__value">
                          {{ formatMetric(row.acceptance_done.workload_kloc) }}
                        </div>
                        <div class="summary-progress-chip__meta">
                          {{
                            formatPercent(
                              row.acceptance_done.workload_kloc_rate,
                            )
                          }}
                        </div>
                      </div>
                    </template>
                  </ElTableColumn>
                </ElTable>
              </ElCard>

              <div class="grid gap-4 xl:grid-cols-2">
                <ElCard shadow="never" class="summary-section-card">
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">项目分布</div>
                        <div class="summary-section-card__desc">
                          查看各项目在当前筛选条件下的需求来源、工作量与代码量分布，判断整体负载来源。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="info"
                        effect="plain"
                      >
                        {{ summaryProjectCount }} 个项目
                      </ElTag>
                    </div>
                  </template>
                  <ElTable
                    :data="summary.project_summary"
                    size="small"
                    class="summary-simple-table"
                  >
                    <ElTableColumn label="项目" min-width="190">
                      <template #default="{ row }">
                        <span class="summary-project-name">{{
                          row.project_name
                        }}</span>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="需求数" min-width="100">
                      <template #default="{ row }">
                        <span class="summary-count-pill">{{
                          row.total_count
                        }}</span>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="工作量(人天)" min-width="120">
                      <template #default="{ row }">
                        <span class="summary-metric-text">
                          {{ formatMetric(row.total_workload_man_day) }}
                        </span>
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="代码量(KLOC)" min-width="120">
                      <template #default="{ row }">
                        <span class="summary-metric-text">
                          {{ formatMetric(row.total_workload_kloc) }}
                        </span>
                      </template>
                    </ElTableColumn>
                  </ElTable>
                </ElCard>

                <ElCard shadow="never" class="summary-section-card">
                  <template #header>
                    <div class="summary-section-card__header">
                      <div>
                        <div class="summary-section-card__title">
                          类型负载概览
                        </div>
                        <div class="summary-section-card__desc">
                          从类型维度对比数量、人天和
                          KLOC，快速识别当前筛选范围内的需求结构。
                        </div>
                      </div>
                      <ElTag
                        class="summary-section-card__tag"
                        type="warning"
                        effect="plain"
                      >
                        {{ summaryTypeCount }} 类类型
                      </ElTag>
                    </div>
                  </template>
                  <div class="type-overview-stack">
                    <div
                      v-for="item in summary.type_summary"
                      :key="item.category"
                      class="type-overview-row"
                    >
                      <div class="type-overview-row__left">
                        <ElTag
                          :type="getCategoryTagType(item.category)"
                          effect="plain"
                          class="requirement-category-badge"
                        >
                          {{ item.category }}
                        </ElTag>
                      </div>
                      <div class="type-overview-row__metrics">
                        <div>
                          <span class="type-overview-row__label">数量</span>
                          <span class="type-overview-row__value">{{
                            item.total_count
                          }}</span>
                        </div>
                        <div>
                          <span class="type-overview-row__label">人天</span>
                          <span class="type-overview-row__value">
                            {{ formatMetric(item.total_workload_man_day) }}
                          </span>
                        </div>
                        <div>
                          <span class="type-overview-row__label">KLOC</span>
                          <span class="type-overview-row__value">
                            {{ formatMetric(item.total_workload_kloc) }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </ElCard>
              </div>
            </template>
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
    </div>
  </Page>
</template>

<style scoped>
.requirement-filter-card {
  border-radius: 20px;
}

.requirement-filter-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.requirement-filter-card__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.requirement-filter-card__toggle {
  color: #475569;
  font-weight: 600;
}

.requirement-filter-card__title {
  color: #0f172a;
  font-size: 18px;
  font-weight: 700;
}

.requirement-filter-card__desc {
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
  margin-top: 6px;
  max-width: 760px;
}

.requirement-filter-card__footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
  margin-top: 14px;
}

.requirement-filter-card__summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  margin-top: 12px;
  color: #475569;
  font-size: 12px;
}

.requirement-filter-card__summary-hint {
  color: #94a3b8;
}

.requirement-filter-form {
  display: grid;
  gap: 16px 20px;
  grid-template-columns: repeat(3, minmax(360px, 1fr));
}

.requirement-filter-form :deep(.el-form-item) {
  align-items: flex-start;
  margin-bottom: 0;
}

.requirement-filter-form :deep(.el-form-item__label) {
  align-items: center;
  color: #334155;
  font-weight: 600;
  justify-content: flex-end;
  line-height: 40px;
  padding-right: 14px;
}

.requirement-filter-form :deep(.el-form-item__content) {
  min-width: 0;
}

.requirement-filter-form__item--actions {
  grid-column: 1 / -1;
}

.requirement-filter-form__item--actions :deep(.el-form-item__content) {
  display: flex;
  gap: 12px;
  justify-content: flex-start;
  margin-left: 92px;
}

.requirement-filter-control {
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
.requirement-data-card__actions {
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

.requirement-data-card {
  display: flex;
  min-height: 0;
  flex-direction: column;
  border-radius: 20px;
}

.requirement-data-card :deep(.el-card__header) {
  padding: 18px 20px 16px;
  border-bottom-color: #e2e8f0;
}

.requirement-data-card :deep(.el-card__body) {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  padding: 0 0 16px;
}

.requirement-data-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.requirement-data-card__title {
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
}

.requirement-data-card__desc {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
  margin-top: 4px;
  max-width: 720px;
}

.requirement-data-card__status {
  flex-shrink: 0;
  margin-top: 2px;
}

.requirement-data-card__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.requirement-data-grid-wrap {
  min-height: 420px;
}

.requirement-data-grid {
  min-height: 420px;
}

.requirement-table-title {
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
  padding: 6px 0 10px;
}

.team-status-chart {
  min-height: 320px;
}

.owner-tag-list {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
}

.owner-tag {
  margin: 0;
}

.delay-indicator {
  min-width: 58px;
  justify-content: center;
}

.requirement-data-guide {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.requirement-data-guide__panel {
  width: min(100%, 860px);
  border: 1px dashed #cbd5e1;
  border-radius: 24px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  padding: 32px;
}

.requirement-data-guide__eyebrow {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.requirement-data-guide__title {
  color: #0f172a;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  margin-top: 10px;
}

.requirement-data-guide__desc {
  color: #475569;
  font-size: 14px;
  line-height: 1.7;
  margin-top: 10px;
  max-width: 680px;
}

.requirement-guide-steps {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  margin-top: 24px;
}

.requirement-guide-step {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 18px;
  min-height: 160px;
}

.requirement-guide-step__index {
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

.requirement-guide-step__title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
  margin-top: 14px;
}

.requirement-guide-step__desc {
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
  margin-top: 8px;
}

.requirement-summary-panel {
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

.dense-completion-panel--dev {
  background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
  border: 1px solid #fdba74;
}

.dense-completion-panel--acceptance {
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

.status-density-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.status-density-card {
  border-radius: 18px;
  position: relative;
  overflow: hidden;
}

.status-density-card::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--status-accent);
}

.status-density-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.status-density-card__code {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.status-density-card__code-text {
  color: var(--status-accent);
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
}

.status-density-card__hint {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.status-density-card__desc {
  color: #475569;
  font-size: 12px;
  line-height: 1.7;
  margin-top: 12px;
  min-height: 40px;
}

.status-density-card__metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 16px;
}

.status-density-card__metric-label {
  color: #64748b;
  font-size: 12px;
}

.status-density-card__metric-value {
  color: #0f172a;
  font-size: 18px;
  font-weight: 700;
  margin-top: 6px;
}

.summary-section-card {
  border-radius: 18px;
}

.summary-section-card.summary-section-card--compact :deep(.el-card__header) {
  padding: 14px 18px 12px;
}

.summary-section-card.summary-section-card--compact :deep(.el-card__body) {
  padding: 12px 16px 16px;
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

.summary-team-table :deep(.el-table__cell),
.summary-simple-table :deep(.el-table__cell) {
  vertical-align: middle;
}

.summary-count-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  padding: 7px 10px;
}

.summary-metric-text {
  color: #0f172a;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.summary-project-name {
  color: #0f172a;
  font-weight: 600;
}

.summary-status-pill {
  min-width: 46px;
  justify-content: center;
  font-weight: 700;
}

.summary-progress-chip {
  display: inline-flex;
  min-width: 96px;
  flex-direction: column;
  gap: 4px;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  padding: 8px 10px;
}

.summary-progress-chip__value {
  color: #0f172a;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  line-height: 1.2;
}

.summary-progress-chip__meta {
  color: #475569;
  font-size: 12px;
  line-height: 1.2;
}

.summary-progress-chip--dev {
  background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
  border-color: #fdba74;
}

.summary-progress-chip--acceptance {
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
  border-color: #86efac;
}

.delay-overview-strip {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-radius: 18px;
  padding: 16px;
  margin-bottom: 14px;
}

.delay-overview-strip--dev {
  background: linear-gradient(135deg, #fff7ed 0%, #ffffff 100%);
  border: 1px solid #fdba74;
}

.delay-overview-strip--acceptance {
  background: linear-gradient(135deg, #fef2f2 0%, #ffffff 100%);
  border: 1px solid #fca5a5;
}

.delay-overview-strip__label {
  color: #64748b;
  font-size: 12px;
}

.delay-overview-strip__value {
  color: #0f172a;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.1;
  margin-top: 8px;
}

.delay-preview-main {
  color: #0f172a;
  font-weight: 600;
}

.delay-preview-sub {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
  margin-top: 4px;
}

.type-overview-stack {
  display: grid;
  gap: 10px;
}

.type-overview-row {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 14px;
}

.type-overview-row__left {
  flex-shrink: 0;
}

.type-overview-row__metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: 100%;
}

.type-overview-row__label {
  color: #64748b;
  font-size: 12px;
}

.type-overview-row__value {
  display: block;
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
  margin-top: 6px;
}

.requirement-team-badge {
  max-width: 100%;
}

.requirement-team-badge__text {
  display: inline-block;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
  white-space: nowrap;
}

.requirement-team-badge__text--wide {
  max-width: 150px;
}

.requirement-category-badge {
  min-width: 54px;
  font-weight: 600;
}

.requirement-status-badge {
  border-width: 1px;
  font-weight: 600;
}

.requirement-status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: currentColor;
  margin-right: 6px;
  vertical-align: middle;
}

.requirement-status-badge--i {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #b91c1c;
}

.requirement-status-badge--d {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.requirement-status-badge--p {
  background: #eef2ff;
  border-color: #a5b4fc;
  color: #4338ca;
}

.requirement-status-badge--c {
  background: #fff7ed;
  border-color: #fdba74;
  color: #c2410c;
}

.requirement-status-badge--a {
  background: #f0fdf4;
  border-color: #86efac;
  color: #15803d;
}

.requirement-board-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.requirement-board-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

@media (max-width: 1024px) {
  .dense-overview-card__metric-grid--three,
  .type-overview-row__metrics {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }

  .requirement-filter-form {
    grid-template-columns: repeat(2, minmax(320px, 1fr));
  }

  .requirement-data-grid-wrap,
  .requirement-data-grid {
    min-height: 360px;
  }

  .requirement-data-grid :deep(.p-4) {
    position: sticky;
    bottom: 0;
    background: #ffffff;
    z-index: 3;
    box-shadow: 0 -6px 16px rgba(15, 23, 42, 0.08);
  }

  .requirement-data-grid :deep(.el-table__body-wrapper) {
    padding-bottom: 64px;
  }
}

@media (max-width: 768px) {
  .requirement-filter-card__header,
  .requirement-data-card__header,
  .summary-section-card__header,
  .dense-overview-card__title-row,
  .status-density-card__top {
    flex-direction: column;
    align-items: flex-start;
  }

  .requirement-filter-card__actions {
    width: 100%;
    justify-content: space-between;
  }

  .requirement-filter-form {
    grid-template-columns: 1fr;
  }

  .requirement-filter-form__item--actions :deep(.el-form-item__content) {
    margin-left: 0;
  }

  .requirement-filter-form :deep(.el-form-item__label) {
    justify-content: flex-start;
    line-height: 1.6;
    padding-bottom: 8px;
    padding-right: 0;
  }

  .requirement-filter-form :deep(.el-form-item) {
    flex-direction: column;
  }

  .project-selector-trigger {
    min-width: 100%;
    max-width: 100%;
  }

  .requirement-data-guide {
    padding: 16px;
  }

  .requirement-data-guide__panel {
    padding: 24px;
  }

  .requirement-data-guide__title {
    font-size: 24px;
  }

  .summary-overview-grid,
  .status-density-grid,
  .dense-overview-card__metric-grid,
  .delay-overview-strip {
    grid-template-columns: 1fr;
  }

  .type-overview-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .requirement-data-grid-wrap,
  .requirement-data-grid {
    min-height: 300px;
  }
}
</style>
