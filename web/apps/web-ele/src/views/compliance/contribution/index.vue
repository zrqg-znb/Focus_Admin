<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { BranchItem, OrganizationItem, RepositoryItem } from '#/api/compliance/base';
import type {
  ContributionCategoryDistribution,
  ContributionCollectTask,
  ContributionExportTask,
  ContributionFilters,
  ContributionMetric,
  ContributionPersonRankingItem,
  ContributionPlGroupRankingItem,
  ContributionPlGroupTrendPoint,
  ContributionRankingItem,
  ContributionTrendPoint,
} from '#/api/compliance/contribution';
import type { DictItem } from '#/api/core/dict';
import type { PlGroup } from '#/api/core/pl';

import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import dayjs from 'dayjs';
import { RotateCcw, SlidersHorizontal } from 'lucide-vue-next';
import {
  ElButton,
  ElCascader,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElPopover,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElTabPane,
  ElTag,
  ElTabs,
} from 'element-plus';

import {
  listBranchesApi,
  listOrganizationsApi,
  listRepositoriesApi,
} from '#/api/compliance/base';
import {
  downloadContributionExportTaskApi,
  getContributionCategoryDistributionApi,
  getContributionCollectTaskApi,
  getContributionExportTaskApi,
  getContributionPersonRankingApi,
  getContributionPlGroupTrendApi,
  getContributionRepositoryRankingApi,
  getContributionSummaryApi,
  getContributionTrendApi,
  listContributionPersonRankingsApi,
  listContributionPlGroupRankingsApi,
  listContributionRepositoryRankingsApi,
  prepareContributionExportTaskApi,
  runContributionCollectTaskApi,
} from '#/api/compliance/contribution';
import ContributionHistoryDrawer from './components/ContributionHistoryDrawer.vue';
import { useZqTable } from '#/components/zq-table';
import { getDictItemByCodeApi } from '#/api/core/dict';
import { getAllPlApi } from '#/api/core/pl';

defineOptions({ name: 'ComplianceContribution' });

interface ScopeOption {
  children?: ScopeOption[];
  label: string;
  repositoryIds?: string[];
  type: 'org' | 'repo';
  value: string;
}

const REPO_TYPE_DICT_CODE = 'code_compliance_repo_type';
const loading = ref(false);
const exportLoading = ref(false);
const collectSubmitting = ref(false);
const collectVisible = ref(false);
const advancedFilterVisible = ref(false);
const activeTab = ref('overview');
const trendChartRef = ref<EchartsUIType>();
const personRankChartRef = ref<EchartsUIType>();
const plGroupRankChartRef = ref<EchartsUIType>();
const plGroupTrendChartRef = ref<EchartsUIType>();
const repositoryRankChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrendChart } = useEcharts(trendChartRef);
const { renderEcharts: renderPersonRankChart } = useEcharts(personRankChartRef);
const { renderEcharts: renderPlGroupRankChart } = useEcharts(plGroupRankChartRef);
const { renderEcharts: renderPlGroupTrendChart } = useEcharts(plGroupTrendChartRef);
const { renderEcharts: renderRepositoryRankChart } = useEcharts(repositoryRankChartRef);

const organizationTree = ref<OrganizationItem[]>([]);
const repositoryOptions = ref<RepositoryItem[]>([]);
const branchOptions = ref<BranchItem[]>([]);
const repoTypeOptions = ref<DictItem[]>([]);
const plGroupOptions = ref<PlGroup[]>([]);
const selectedScopeValues = ref<string[]>([]);
const summary = ref<ContributionMetric>();
const trendRows = ref<ContributionTrendPoint[]>([]);
const plGroupTrendRows = ref<ContributionPlGroupTrendPoint[]>([]);
const repositoryRanking = ref<ContributionRankingItem[]>([]);
const personRanking = ref<ContributionPersonRankingItem[]>([]);
const categoryDistribution = ref<ContributionCategoryDistribution>();
const exportTask = ref<ContributionExportTask>();
const collectTask = ref<ContributionCollectTask>();
const historyVisible = ref(false);
const historyEntity = ref<
  | { id: string; label: string; type: 'person' }
  | { id: string; label: string; type: 'pl_group' }
  | { branchId?: string; id: string; label: string; type: 'repository' }
>();
let exportPollTimer: ReturnType<typeof setInterval> | undefined;
let collectPollTimer: ReturnType<typeof setInterval> | undefined;

const filters = ref<ContributionFilters>({
  branch_ids: [],
  organization_ids: [],
  pl_group_ids: [],
  repository_ids: [],
  source_mode: '',
});
const mergedRange = ref<string[]>([
  dayjs().subtract(30, 'day').startOf('day').format('YYYY-MM-DDTHH:mm:ssZ'),
  dayjs().endOf('day').format('YYYY-MM-DDTHH:mm:ssZ'),
]);
const collectRange = ref<string[]>([
  dayjs().subtract(1, 'day').startOf('day').format('YYYY-MM-DDTHH:mm:ssZ'),
  dayjs().startOf('day').format('YYYY-MM-DDTHH:mm:ssZ'),
]);

const repositoriesByOrg = computed(() => {
  const result = new Map<string, RepositoryItem[]>();
  visibleRepositories.value.forEach((item) => {
    const rows = result.get(item.organization_id) || [];
    rows.push(item);
    result.set(item.organization_id, rows);
  });
  return result;
});
const visibleRepositories = computed(() => repositoryOptions.value.filter((item) => !filters.value.source_mode || item.mode === filters.value.source_mode));
const visibleOrganizationTree = computed(() => filterOrganizationsByMode(organizationTree.value));
const selectedRepositoryCount = computed(() => parseScopeSelection().repository_ids.length);
const activeAdvancedFilterCount = computed(() => [
  filters.value.branch_ids?.length,
  filters.value.repo_type,
  filters.value.domain,
  filters.value.pl_group_ids?.length,
  filters.value.author_username,
].filter(Boolean).length);

const scopeCascaderProps = {
  emitPath: false,
  multiple: true,
  value: 'value',
};

const scopeOptions = computed<ScopeOption[]>(() => buildScopeOptions(visibleOrganizationTree.value));

const metricCards = computed(() => {
  const data = summary.value || {
    active_branch_count: 0,
    active_repository_count: 0,
    added_lines: 0,
    changed_lines: 0,
    contributor_count: 0,
    cr_count: 0,
    net_lines: 0,
    removed_lines: 0,
  };
  return [
    { label: '新增行数贡献', tone: 'primary', value: data.added_lines },
    { label: '参与代码库', value: data.active_repository_count },
    { label: '参与分支', value: data.active_branch_count },
    { label: 'CR数量', value: data.cr_count },
    { label: '贡献人数', value: data.contributor_count },
    { label: '本期删除', value: data.removed_lines },
    { label: '总变更行数', value: data.changed_lines },
  ];
});

function buildScopeOptions(nodes: OrganizationItem[]): ScopeOption[] {
  return nodes.map((node) => {
    const repoChildren = (repositoriesByOrg.value.get(node.id) || []).map((repo) => ({
      label: `${repo.project_name}（${repo.project_id}）`,
      repositoryIds: [repo.id],
      type: 'repo' as const,
      value: `repo:${repo.id}`,
    }));
    const childOptions = buildScopeOptions(node.children || []);
    const repositoryIds = [...repoChildren.flatMap((item) => item.repositoryIds || []), ...childOptions.flatMap((item) => item.repositoryIds || [])];
    return {
      children: [...childOptions, ...repoChildren],
      label: `${node.name}（${node.group_id}）`,
      repositoryIds,
      type: 'org' as const,
      value: `org:${node.id}`,
    };
  });
}

function filterOrganizationsByMode(nodes: OrganizationItem[]): OrganizationItem[] {
  return nodes
    .filter((node) => !filters.value.source_mode || node.mode === filters.value.source_mode)
    .map((node) => ({ ...node, children: filterOrganizationsByMode(node.children || []) }));
}

function collectRepositoryIdsFromOptions(values: string[], options = scopeOptions.value) {
  const selected = new Set<string>();
  const walk = (items: ScopeOption[]) => {
    items.forEach((item) => {
      if (values.includes(item.value)) {
        (item.repositoryIds || []).forEach((id) => selected.add(id));
      }
      if (item.children?.length) walk(item.children);
    });
  };
  walk(options);
  return [...selected];
}

function parseScopeSelection() {
  return { repository_ids: collectRepositoryIdsFromOptions(selectedScopeValues.value) };
}

function buildParams(): ContributionFilters {
  return {
    ...filters.value,
    ...parseScopeSelection(),
    merged_after: mergedRange.value?.[0],
    merged_before: mergedRange.value?.[1],
  };
}

function resetAdvancedFilters() {
  filters.value.branch_ids = [];
  filters.value.repo_type = undefined;
  filters.value.domain = undefined;
  filters.value.pl_group_ids = [];
  filters.value.author_username = undefined;
}

function applyAdvancedFilters() {
  advancedFilterVisible.value = false;
  loadDashboard();
}

const [RepositoryRankingGrid, repositoryRankingGridApi] = useZqTable<ContributionRankingItem>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: [
      { dataKey: 'repository_name', key: 'repository_name', title: '代码库 / 分支', minWidth: 250 },
      { align: 'right', dataKey: 'added_lines', key: 'added_lines', title: '新增行数', width: 110 },
      { align: 'right', dataKey: 'removed_lines', key: 'removed_lines', title: '删除行数', width: 100 },
      { align: 'right', dataKey: 'changed_lines', key: 'changed_lines', title: '总变更', width: 100 },
      { align: 'right', dataKey: 'cr_count', key: 'cr_count', title: '变更数', width: 90 },
      { align: 'right', dataKey: 'contributor_count', key: 'contributor_count', title: '贡献人数', width: 100 },
    ],
    pagerConfig: { enabled: true, pageSize: 20, pageSizes: [10, 20, 50, 100] },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: ({ page }: { page: { currentPage: number; pageSize: number } }) =>
          listContributionRepositoryRankingsApi({ ...buildParams(), page: page.currentPage, pageSize: page.pageSize }),
      },
    },
    stripe: true,
  },
});

const [PersonRankingGrid, personRankingGridApi] = useZqTable<ContributionPersonRankingItem>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: [
      { dataKey: 'author_display_name', key: 'author_display_name', title: '创建人', minWidth: 170 },
      { align: 'right', dataKey: 'repository_count', key: 'repository_count', title: '仓库', width: 72 },
      { align: 'right', dataKey: 'added_lines', key: 'added_lines', title: '新增', width: 94 },
      { align: 'right', dataKey: 'cr_count', key: 'cr_count', title: '变更数', width: 82 },
    ],
    pagerConfig: { enabled: true, pageSize: 20, pageSizes: [10, 20, 50, 100] },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: ({ page }: { page: { currentPage: number; pageSize: number } }) =>
          listContributionPersonRankingsApi({ ...buildParams(), page: page.currentPage, pageSize: page.pageSize }),
      },
    },
    stripe: true,
  },
});

const [PlGroupRankingGrid, plGroupRankingGridApi] = useZqTable<ContributionPlGroupRankingItem>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: [
      { dataKey: 'pl_group_name', key: 'pl_group_name', title: 'PL组', minWidth: 160 },
      { align: 'right', dataKey: 'contributor_count', key: 'contributor_count', title: '人数', width: 72 },
      { align: 'right', dataKey: 'added_lines', key: 'added_lines', title: '新增', width: 94 },
      { align: 'right', dataKey: 'cr_count', key: 'cr_count', title: '变更数', width: 82 },
    ],
    pagerConfig: { enabled: true, pageSize: 20, pageSizes: [10, 20, 50, 100] },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: ({ page }: { page: { currentPage: number; pageSize: number } }) =>
          listContributionPlGroupRankingsApi({ ...buildParams(), page: page.currentPage, pageSize: page.pageSize }),
      },
    },
    stripe: true,
  },
});

function reloadRankingTables(resetPage = false) {
  const grids = [repositoryRankingGridApi, personRankingGridApi, plGroupRankingGridApi];
  grids.forEach((gridApi) => {
    if (resetPage) gridApi.pagination.currentPage = 1;
    gridApi.query();
  });
}

function openPersonHistory(row: ContributionPersonRankingItem) {
  historyEntity.value = { id: row.author_username, label: row.author_display_name, type: 'person' };
  historyVisible.value = true;
}

function openPlGroupHistory(row: ContributionPlGroupRankingItem) {
  historyEntity.value = { id: row.pl_group_id, label: row.pl_group_name, type: 'pl_group' };
  historyVisible.value = true;
}

function changeSourceMode() {
  // 模式切换后清理可能属于另一数据湖的范围，避免筛选条件不可见却仍参与查询。
  selectedScopeValues.value = [];
  filters.value.branch_ids = [];
  loadDashboard();
}

function formatNumber(value?: number) {
  return Number(value || 0).toLocaleString();
}

function compactNumber(value?: number) {
  const amount = Number(value || 0);
  if (amount >= 10_000) return `${(amount / 10_000).toFixed(1)}万`;
  return amount.toLocaleString();
}

function shortLabel(value: string, max = 16) {
  return value.length > max ? `${value.slice(0, max)}...` : value;
}

function formatChartValue(params: { value?: number | string }) {
  return compactNumber(Number(params.value || 0));
}

function saveBlob(data: any, filename: string) {
  const blob = data instanceof Blob ? data : new Blob([data]);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderCharts() {
  const palette = ['#2563eb', '#16a34a', '#f59e0b', '#0891b2', '#ef4444', '#64748b', '#7c3aed', '#0f766e'];
  renderTrendChart({
    color: ['#2563eb', '#ef4444', '#64748b'],
    grid: { bottom: 28, containLabel: true, left: 16, right: 20, top: 34 },
    legend: { top: 0 },
    series: [
      { data: trendRows.value.map((item) => item.added_lines), name: '新增行数', smooth: true, type: 'line' },
      { data: trendRows.value.map((item) => item.removed_lines), name: '删除行数', smooth: true, type: 'line' },
      { data: trendRows.value.map((item) => item.changed_lines), name: '总变更', smooth: true, type: 'line' },
    ],
    tooltip: { trigger: 'axis' },
    xAxis: { boundaryGap: false, data: trendRows.value.map((item) => item.date), type: 'category' },
    yAxis: { type: 'value' },
  });

  const plGroupTotals = new Map<string, number>();
  plGroupTrendRows.value.forEach((item) => {
    plGroupTotals.set(item.pl_group_name, (plGroupTotals.get(item.pl_group_name) || 0) + item.added_lines);
  });
  const topPlGroups = [...plGroupTotals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name]) => name);
  const dates = [...new Set(plGroupTrendRows.value.map((item) => item.date))];
  renderPlGroupTrendChart({
    color: palette,
    grid: { bottom: 28, containLabel: true, left: 16, right: 20, top: 42 },
    legend: { top: 0, type: 'scroll' },
    series: topPlGroups.map((name) => ({
      data: dates.map((date) => plGroupTrendRows.value.find((item) => item.date === date && item.pl_group_name === name)?.added_lines || 0),
      emphasis: { focus: 'series' },
      name,
      smooth: true,
      type: 'line',
    })),
    tooltip: { trigger: 'axis' },
    xAxis: { boundaryGap: false, data: dates, type: 'category' },
    yAxis: { axisLabel: { formatter: (value: number) => compactNumber(value) }, type: 'value' },
  });

  const repoRows = repositoryRanking.value.slice(0, 12).reverse();
  renderRepositoryRankChart({
    color: ['#2563eb'],
    grid: { bottom: 18, containLabel: true, left: 12, right: 24, top: 12 },
    series: [
      {
        barMaxWidth: 16,
        data: repoRows.map((item) => item.added_lines),
        label: { formatter: formatChartValue, position: 'right', show: true },
        type: 'bar',
      },
    ] as any,
    tooltip: { trigger: 'axis' },
    xAxis: { axisLabel: { formatter: (value: number) => compactNumber(value) }, type: 'value' },
    yAxis: { axisLabel: { formatter: (value: string) => shortLabel(value, 18) }, data: repoRows.map((item) => `${item.repository_name}/${item.branch_name}`), type: 'category' },
  });

  const plGroupRows = (categoryDistribution.value?.pl_groups || []).slice(0, 10).reverse();
  renderPlGroupRankChart({
    color: ['#16a34a'],
    grid: { bottom: 18, containLabel: true, left: 12, right: 24, top: 12 },
    series: [
      {
        barMaxWidth: 16,
        data: plGroupRows.map((item) => item.added_lines),
        label: { formatter: formatChartValue, position: 'right', show: true },
        type: 'bar',
      },
    ] as any,
    tooltip: { trigger: 'axis' },
    xAxis: { axisLabel: { formatter: (value: number) => compactNumber(value) }, type: 'value' },
    yAxis: { axisLabel: { formatter: (value: string) => shortLabel(value, 18) }, data: plGroupRows.map((item) => item.category_label), type: 'category' },
  });

  const personRows = personRanking.value.slice(0, 10).reverse();
  renderPersonRankChart({
    color: ['#f59e0b'],
    grid: { bottom: 18, containLabel: true, left: 12, right: 24, top: 12 },
    series: [
      {
        barMaxWidth: 16,
        data: personRows.map((item) => item.added_lines),
        label: { formatter: formatChartValue, position: 'right', show: true },
        type: 'bar',
      },
    ] as any,
    tooltip: { trigger: 'axis' },
    xAxis: { axisLabel: { formatter: (value: number) => compactNumber(value) }, type: 'value' },
    yAxis: { axisLabel: { formatter: (value: string) => shortLabel(value, 14) }, data: personRows.map((item) => item.author_display_name), type: 'category' },
  });

}

async function loadOptions() {
  const [organizations, repositories, branches, repoTypes, plGroups] = await Promise.all([
    listOrganizationsApi(),
    listRepositoriesApi({ page: 1, pageSize: 5000 }),
    listBranchesApi({ is_active: true, page: 1, pageSize: 5000 }),
    getDictItemByCodeApi(REPO_TYPE_DICT_CODE),
    getAllPlApi(),
  ]);
  organizationTree.value = organizations;
  repositoryOptions.value = repositories.items || [];
  branchOptions.value = branches.items || [];
  repoTypeOptions.value = repoTypes.filter((item) => item.status);
  plGroupOptions.value = plGroups.filter((item) => item.status);
}

async function loadDashboard() {
  loading.value = true;
  try {
    const params = buildParams();
    const [summaryData, trendData, plGroupTrendData, repoData, personData, categoryData] = await Promise.all([
      getContributionSummaryApi(params),
      getContributionTrendApi(params),
      getContributionPlGroupTrendApi(params),
      getContributionRepositoryRankingApi(params),
      getContributionPersonRankingApi(params),
      getContributionCategoryDistributionApi(params),
    ]);
    summary.value = summaryData;
    trendRows.value = trendData;
    plGroupTrendRows.value = plGroupTrendData;
    repositoryRanking.value = repoData;
    personRanking.value = personData;
    categoryDistribution.value = categoryData;
    await nextTick();
    renderCharts();
    reloadRankingTables(true);
  } finally {
    loading.value = false;
  }
}

function openRepositoryHistory(row: ContributionRankingItem) {
  historyEntity.value = {
    branchId: row.branch_id || undefined,
    id: row.repository_id,
    label: `${row.repository_name} · ${row.branch_name}`,
    type: 'repository',
  };
  historyVisible.value = true;
}

function clearScope() {
  selectedScopeValues.value = [];
}

function selectAllScope() {
  selectedScopeValues.value = visibleRepositories.value.map((item) => `repo:${item.id}`);
}

function stopExportPolling() {
  if (!exportPollTimer) return;
  clearInterval(exportPollTimer);
  exportPollTimer = undefined;
}

function stopCollectPolling() {
  if (!collectPollTimer) return;
  clearInterval(collectPollTimer);
  collectPollTimer = undefined;
}

async function refreshCollectTask(id: string) {
  const task = await getContributionCollectTaskApi(id);
  collectTask.value = task;
  if (task.status === 'success') {
    stopCollectPolling();
    ElMessage.success(`同步完成：拉取 ${task.fetched_count} 条，新增 ${task.created_count} 条`);
    await loadDashboard();
  }
  if (task.status === 'failed') {
    stopCollectPolling();
    ElMessage.error(task.error_message || '同步任务失败');
  }
}

function startCollectPolling(id: string) {
  stopCollectPolling();
  collectPollTimer = setInterval(() => refreshCollectTask(id), 2000);
}

async function downloadExportTask(task?: ContributionExportTask) {
  const current = task || exportTask.value;
  if (!current || current.status !== 'success') return;
  const data = await downloadContributionExportTaskApi(current.id);
  saveBlob(data, current.file_name || 'code_contribution_dashboard.xlsx');
}

async function refreshExportTask(id: string) {
  const task = await getContributionExportTaskApi(id);
  exportTask.value = task;
  if (task.status === 'success') {
    stopExportPolling();
    ElMessage.success('导出文件已生成');
    await downloadExportTask(task);
  }
  if (task.status === 'failed') {
    stopExportPolling();
    ElMessage.error(task.error_message || '导出失败');
  }
}

function startExportPolling(id: string) {
  stopExportPolling();
  exportPollTimer = setInterval(() => refreshExportTask(id), 2000);
}

async function submitExport() {
  exportLoading.value = true;
  try {
    const result = await prepareContributionExportTaskApi({ filters: buildParams(), scope: 'summary' });
    exportTask.value = result.task;
    ElMessage.success('导出任务已提交');
    if (result.task.status === 'success') await downloadExportTask(result.task);
    else startExportPolling(result.task.id);
  } finally {
    exportLoading.value = false;
  }
}

async function submitCollectTask() {
  if (!collectRange.value?.[0] || !collectRange.value?.[1]) {
    ElMessage.warning('请选择采集时间范围');
    return;
  }
  collectSubmitting.value = true;
  try {
    const result = await runContributionCollectTaskApi({
      branch_ids: filters.value.branch_ids,
      merged_after: collectRange.value[0],
      merged_before: collectRange.value[1],
      repository_ids: parseScopeSelection().repository_ids,
      source_mode: filters.value.source_mode,
    });
    collectTask.value = result.task;
    collectVisible.value = false;
    ElMessage[result.accepted ? 'success' : 'warning'](result.message);
    if (result.accepted) startCollectPolling(result.task.id);
  } finally {
    collectSubmitting.value = false;
  }
}

onMounted(async () => {
  await loadOptions();
  await loadDashboard();
});

onUnmounted(() => {
  stopExportPolling();
  stopCollectPolling();
});
</script>

<template>
  <Page auto-content-height>
    <div class="contribution-page" v-loading="loading">
      <section class="toolbar-panel">
        <div class="filter-ribbon">
          <div class="ribbon-field ribbon-scope">
            <div class="ribbon-label">
              <span>组织 / 代码库</span>
              <span class="scope-state">已选 {{ selectedRepositoryCount }} 个</span>
              <ElButton link type="primary" @click="selectAllScope">全选</ElButton>
              <ElButton link @click="clearScope">清空</ElButton>
            </div>
            <ElCascader
              v-model="selectedScopeValues"
              :options="scopeOptions"
              :props="scopeCascaderProps"
              clearable
              collapse-tags
              collapse-tags-tooltip
              filterable
              placeholder="搜索组织或代码库"
            />
          </div>
          <div class="ribbon-field ribbon-time">
            <div class="ribbon-label">合入时间</div>
            <ElDatePicker v-model="mergedRange" clearable end-placeholder="结束" range-separator="至" start-placeholder="开始" type="datetimerange" value-format="YYYY-MM-DDTHH:mm:ssZ" />
          </div>
          <div class="ribbon-field ribbon-source">
            <div class="ribbon-label">数据来源</div>
            <ElRadioGroup v-model="filters.source_mode" class="source-mode" @change="changeSourceMode">
              <ElRadioButton label="">全部</ElRadioButton>
              <ElRadioButton label="CR">CR</ElRadioButton>
              <ElRadioButton label="MR">MR</ElRadioButton>
            </ElRadioGroup>
          </div>
        </div>
        <div class="ribbon-commands">
          <ElPopover v-model:visible="advancedFilterVisible" :width="760" placement="bottom-end" trigger="click">
            <template #reference>
              <ElButton :class="{ 'is-active-filter': activeAdvancedFilterCount > 0 }" aria-label="高级筛选" circle title="高级筛选">
                <SlidersHorizontal :size="16" />
              </ElButton>
            </template>
            <div class="advanced-filter-panel">
              <div class="advanced-filter-header">
                <span>高级条件</span>
                <span v-if="activeAdvancedFilterCount" class="advanced-filter-count">已启用 {{ activeAdvancedFilterCount }} 项</span>
              </div>
              <ElForm class="advanced-filter-form" label-position="top">
                <ElFormItem label="分支">
                  <ElSelect v-model="filters.branch_ids" collapse-tags clearable filterable multiple placeholder="全部活跃分支">
                    <ElOption v-for="item in branchOptions" :key="item.id" :label="item.branch_name" :value="item.id" />
                  </ElSelect>
                </ElFormItem>
                <ElFormItem label="仓库类型">
                  <ElSelect v-model="filters.repo_type" clearable placeholder="全部类型">
                    <ElOption v-for="item in repoTypeOptions" :key="item.value || item.id" :label="item.label" :value="item.value || ''" />
                  </ElSelect>
                </ElFormItem>
                <ElFormItem label="领域">
                  <ElSelect v-model="filters.domain" clearable placeholder="全部领域">
                    <ElOption label="座舱" value="cockpit" />
                    <ElOption label="车控" value="vehicle" />
                  </ElSelect>
                </ElFormItem>
                <ElFormItem label="贡献人 PL 组">
                  <ElSelect v-model="filters.pl_group_ids" collapse-tags clearable filterable multiple placeholder="全部 PL 组">
                    <ElOption v-for="item in plGroupOptions" :key="item.id" :label="item.name" :value="item.id" />
                    <ElOption label="非底软领域" value="unknown" />
                  </ElSelect>
                </ElFormItem>
                <ElFormItem label="创建人">
                  <ElInput v-model="filters.author_username" clearable placeholder="姓名 / 工号" />
                </ElFormItem>
              </ElForm>
              <div class="advanced-filter-footer">
                <ElButton :icon="RotateCcw" @click="resetAdvancedFilters">重置</ElButton>
                <ElButton type="primary" @click="applyAdvancedFilters">应用条件</ElButton>
              </div>
            </div>
          </ElPopover>
          <ElButton @click="collectVisible = true">手动同步</ElButton>
          <ElButton :loading="exportLoading" @click="submitExport">导出看板</ElButton>
          <ElButton type="primary" @click="loadDashboard">查询</ElButton>
        </div>
      </section>

      <ElTabs v-model="activeTab" class="contribution-tabs">
        <ElTabPane label="总览看板" name="overview">
          <section class="metric-grid">
            <div v-for="item in metricCards" :key="item.label" :class="['metric-card', item.tone && `metric-${item.tone}`]">
              <div class="metric-label">{{ item.label }}</div>
              <div class="metric-value">{{ formatNumber(item.value) }}</div>
            </div>
          </section>

          <section class="hero-grid">
            <div class="panel panel-hero">
              <div class="panel-header">
                <div>
                  <div class="panel-title">新增代码贡献趋势</div>
                  <div class="panel-desc">按合入日期观察统计期内新增、删除和总变更走势。</div>
                </div>
              </div>
              <EchartsUI ref="trendChartRef" class="chart-body chart-body-large" />
            </div>
          </section>

          <section class="focus-grid">
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">PL组新增贡献趋势</div>
                  <div class="panel-desc">展示新增贡献最高的 PL 组随时间变化，适合判断贡献集中度和节奏。</div>
                </div>
              </div>
              <EchartsUI ref="plGroupTrendChartRef" class="chart-body chart-body-large" />
            </div>
          </section>

          <section class="rank-grid">
            <div class="panel">
              <div class="panel-title">仓库 / 分支 Top</div>
              <EchartsUI ref="repositoryRankChartRef" class="chart-body" />
            </div>
            <div class="panel">
              <div class="panel-title">PL组 Top</div>
              <EchartsUI ref="plGroupRankChartRef" class="chart-body" />
            </div>
            <div class="panel">
              <div class="panel-title">人员 Top</div>
              <EchartsUI ref="personRankChartRef" class="chart-body" />
            </div>
          </section>
        </ElTabPane>

        <ElTabPane label="排行明细" name="ranking">
          <section class="table-grid ranking-workbench">
            <div class="panel ranking-panel panel-wide">
              <div class="panel-header"><div class="panel-title">仓库 / 分支新增贡献</div></div>
              <RepositoryRankingGrid class="ranking-grid">
                <template #cell-repository_name="{ row }">
                  <ElButton link type="primary" @click="openRepositoryHistory(row)">{{ row.repository_name }}</ElButton>
                  <div class="muted">
                    <ElTag effect="plain" size="small" :type="row.source_mode === 'MR' ? 'warning' : 'primary'">{{ row.source_mode }}</ElTag>
                    <ElButton link type="primary" @click="openRepositoryHistory(row)">{{ row.branch_name }}</ElButton>
                    · {{ row.project_id }}
                  </div>
                </template>
              </RepositoryRankingGrid>
            </div>
            <div class="panel ranking-panel">
              <div class="panel-header"><div class="panel-title">人员合入贡献</div></div>
              <PersonRankingGrid class="ranking-grid">
                <template #cell-author_display_name="{ row }">
                  <ElButton link type="primary" @click="openPersonHistory(row)">{{ row.author_display_name }}</ElButton>
                  <div class="muted">{{ row.author_pl_group_name }}</div>
                </template>
              </PersonRankingGrid>
            </div>
            <div class="panel ranking-panel">
              <div class="panel-header"><div class="panel-title">PL组新增贡献</div></div>
              <PlGroupRankingGrid class="ranking-grid">
                <template #cell-pl_group_name="{ row }">
                  <ElButton link type="primary" @click="openPlGroupHistory(row)">{{ row.pl_group_name }}</ElButton>
                </template>
              </PlGroupRankingGrid>
            </div>
          </section>
        </ElTabPane>
      </ElTabs>

      <ElDialog v-model="collectVisible" title="手动同步合入代码量" width="560px">
        <ElForm label-width="92px">
          <ElFormItem label="时间范围">
            <ElDatePicker v-model="collectRange" end-placeholder="结束" range-separator="至" start-placeholder="开始" type="datetimerange" value-format="YYYY-MM-DDTHH:mm:ssZ" />
          </ElFormItem>
          <ElFormItem label="同步范围">
            <div class="collect-summary">默认复用当前选择的代码库和分支；未筛选时采集全部活跃绑定分支。MR 将按项目逐个请求。</div>
          </ElFormItem>
          <ElFormItem v-if="collectTask" label="最近任务">
            <div class="collect-summary">{{ collectTask.status_label }} · 拉取 {{ collectTask.fetched_count }} 条 · 新增 {{ collectTask.created_count }} 条</div>
          </ElFormItem>
        </ElForm>
        <template #footer>
          <ElButton @click="collectVisible = false">取消</ElButton>
          <ElButton :loading="collectSubmitting" type="primary" @click="submitCollectTask">提交任务</ElButton>
        </template>
      </ElDialog>

      <ContributionHistoryDrawer
        v-model="historyVisible"
        :base-filters="buildParams()"
        :entity="historyEntity"
      />
    </div>
  </Page>
</template>

<style scoped lang="less">
.contribution-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}

.toolbar-panel,
.panel,
.metric-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: var(--el-bg-color);
  box-shadow: 0 10px 24px rgb(15 23 42 / 4%);
}

.toolbar-panel {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 16px;
  box-shadow: 0 6px 18px rgb(15 23 42 / 3%);
}

.filter-ribbon {
  display: grid;
  min-width: 0;
  flex: 1;
  grid-template-columns: minmax(340px, 1.45fr) minmax(330px, 1.1fr) 178px;
  gap: 14px;
}

.ribbon-field {
  min-width: 0;
}

.ribbon-label {
  display: flex;
  height: 20px;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.ribbon-field :deep(.el-date-editor),
.ribbon-field :deep(.el-cascader) {
  width: 100%;
}

.scope-state {
  margin-left: auto;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 400;
}

.ribbon-label :deep(.el-button) {
  height: 18px;
  padding: 0 2px;
  font-size: 12px;
}

.source-mode {
  display: flex;
  width: 100%;
}

.source-mode :deep(.el-radio-button) {
  flex: 1;
}

.source-mode :deep(.el-radio-button__inner) {
  width: 100%;
  border-color: #d6dee9;
  padding-inline: 8px;
}

.ribbon-commands {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 1px;
}

.ribbon-commands :deep(.el-button) {
  margin: 0;
}

.ribbon-commands .is-active-filter {
  border-color: #93c5fd;
  color: #2563eb;
  background: #eff6ff;
}

.advanced-filter-panel {
  padding: 2px;
}

.advanced-filter-header,
.advanced-filter-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.advanced-filter-header {
  padding: 3px 2px 12px;
  color: #0f172a;
  font-size: 14px;
  font-weight: 700;
}

.advanced-filter-count {
  color: #2563eb;
  font-size: 12px;
  font-weight: 500;
}

.advanced-filter-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.advanced-filter-form :deep(.el-form-item) {
  width: 100%;
  margin: 0;
}

.advanced-filter-form :deep(.el-select),
.advanced-filter-form :deep(.el-input) {
  width: 100%;
}

.advanced-filter-footer {
  margin-top: 16px;
  border-top: 1px solid #e2e8f0;
  padding-top: 12px;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 1260px) {
  .filter-ribbon {
    grid-template-columns: minmax(300px, 1fr) minmax(300px, 1fr);
  }

  .ribbon-source {
    grid-column: span 2;
    max-width: 220px;
  }
}

@media (max-width: 900px) {
  .toolbar-panel { align-items: stretch; flex-direction: column; }
  .filter-ribbon { grid-template-columns: 1fr; }
  .ribbon-source { grid-column: auto; max-width: none; }
  .ribbon-commands { justify-content: flex-end; }
  .advanced-filter-form { grid-template-columns: 1fr; }
}

.contribution-tabs {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.contribution-tabs :deep(.el-tabs__header) {
  margin: 0 0 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  padding: 0 12px;
}

.contribution-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.contribution-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
}

.contribution-tabs :deep(.el-tab-pane) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(140px, 1fr));
  gap: 10px;
}

.metric-card {
  padding: 12px;
  min-height: 86px;
}

.metric-primary {
  border-color: #bfdbfe;
  background:
    radial-gradient(circle at top right, rgb(37 99 235 / 14%), transparent 46%),
    linear-gradient(135deg, #eff6ff 0%, #fff 100%);
}

.metric-danger {
  border-color: #fecaca;
  background: #fef2f2;
}

.metric-label,
.muted {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.metric-value {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.hero-grid,
.focus-grid,
.rank-grid,
.table-grid {
  display: grid;
  gap: 12px;
}

.hero-grid,
.focus-grid {
  grid-template-columns: minmax(0, 1fr);
}

.rank-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.table-grid {
  grid-template-columns: 2fr 1fr 1fr;
}

.ranking-workbench {
  height: max(620px, calc(100vh - 278px));
  min-height: 0;
}

.ranking-panel {
  display: flex;
  min-height: 0;
  flex-direction: column;
}

.ranking-panel .panel-header {
  flex: 0 0 auto;
}

.ranking-grid {
  min-height: 0;
  flex: 1;
}

.panel {
  min-width: 0;
  padding: 12px;
}

.panel-hero {
  background:
    radial-gradient(circle at top right, rgb(37 99 235 / 10%), transparent 38%),
    #fff;
}

.panel-wide {
  min-width: 0;
}

.panel-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 10px;
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.panel-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

.chart-body {
  width: 100%;
  height: 300px;
}

.chart-body-large {
  height: 340px;
}

.collect-summary {
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(4, minmax(120px, 1fr));
  }

  .hero-grid,
  .focus-grid,
  .rank-grid,
  .table-grid {
    grid-template-columns: 1fr;
  }

  .ranking-workbench {
    height: auto;
  }

  .ranking-panel {
    height: 620px;
  }
}
</style>
