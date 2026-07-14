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
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
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
  getContributionExportTaskApi,
  getContributionPersonRankingApi,
  getContributionPlGroupTrendApi,
  getContributionRepositoryRankingApi,
  getContributionSummaryApi,
  getContributionTrendApi,
  prepareContributionExportTaskApi,
  runContributionCollectTaskApi,
} from '#/api/compliance/contribution';
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
let exportPollTimer: ReturnType<typeof setInterval> | undefined;

const filters = ref<ContributionFilters>({
  branch_ids: [],
  organization_ids: [],
  pl_group_ids: [],
  repository_ids: [],
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
  repositoryOptions.value.forEach((item) => {
    const rows = result.get(item.organization_id) || [];
    rows.push(item);
    result.set(item.organization_id, rows);
  });
  return result;
});
const selectedRepositoryCount = computed(() => parseScopeSelection().repository_ids.length);

const scopeCascaderProps = {
  checkStrictly: true,
  emitPath: false,
  multiple: true,
  value: 'value',
};

const scopeOptions = computed<ScopeOption[]>(() => buildScopeOptions(organizationTree.value));

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
  } finally {
    loading.value = false;
  }
}

function drillByRepository(row: ContributionRankingItem) {
  const repo = repositoryOptions.value.find((item) => item.project_id === row.project_id);
  selectedScopeValues.value = repo ? [`repo:${repo.id}`] : [];
  const branch = branchOptions.value.find((item) => item.branch_name === row.branch_name);
  filters.value.branch_ids = branch ? [branch.id] : [];
  loadDashboard();
}

function drillByPerson(row: ContributionPersonRankingItem) {
  filters.value.author_username = row.author_username;
  loadDashboard();
}

function clearScope() {
  selectedScopeValues.value = [];
}

function selectAllScope() {
  selectedScopeValues.value = repositoryOptions.value.map((item) => `repo:${item.id}`);
}

function stopExportPolling() {
  if (!exportPollTimer) return;
  clearInterval(exportPollTimer);
  exportPollTimer = undefined;
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
    });
    collectTask.value = result.task;
    collectVisible.value = false;
    ElMessage[result.accepted ? 'success' : 'warning'](result.message);
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
});
</script>

<template>
  <Page auto-content-height>
    <div class="contribution-page" v-loading="loading">
      <section class="toolbar-panel">
        <ElForm class="filter-form" label-position="top">
          <ElFormItem class="scope-item" label="组织 / 代码库">
            <div class="scope-control">
              <ElCascader
                v-model="selectedScopeValues"
                :options="scopeOptions as any"
                :props="scopeCascaderProps"
                clearable
                collapse-tags
                collapse-tags-tooltip
                filterable
                placeholder="搜索组织或代码库，选择组织将包含子孙仓库"
              />
              <div class="scope-actions">
                <span class="muted">已选 {{ selectedRepositoryCount }} 个代码库</span>
                <ElButton link type="primary" @click="selectAllScope">全选</ElButton>
                <ElButton link @click="clearScope">清空</ElButton>
              </div>
            </div>
          </ElFormItem>
          <ElFormItem label="分支">
            <ElSelect v-model="filters.branch_ids" collapse-tags clearable filterable multiple placeholder="活跃分支">
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
          <ElFormItem label="PL组">
            <ElSelect v-model="filters.pl_group_ids" collapse-tags clearable filterable multiple placeholder="贡献人PL组">
              <ElOption v-for="item in plGroupOptions" :key="item.id" :label="item.name" :value="item.id" />
              <ElOption label="非底软领域" value="unknown" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="创建人">
            <ElInput v-model="filters.author_username" clearable placeholder="姓名 / 工号" />
          </ElFormItem>
          <ElFormItem class="filter-range" label="合入时间">
            <ElDatePicker v-model="mergedRange" clearable end-placeholder="结束" range-separator="至" start-placeholder="开始" type="datetimerange" value-format="YYYY-MM-DDTHH:mm:ssZ" />
          </ElFormItem>
          <ElFormItem class="filter-actions" label=" ">
            <ElButton type="primary" @click="loadDashboard">查询</ElButton>
            <ElButton @click="collectVisible = true">手动同步</ElButton>
            <ElButton :loading="exportLoading" @click="submitExport">导出看板</ElButton>
          </ElFormItem>
        </ElForm>
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
          <section class="table-grid">
            <div class="panel panel-wide">
              <div class="panel-title">仓库 / 分支新增贡献</div>
              <ElTable :data="repositoryRanking" border height="420">
                <ElTableColumn fixed label="代码库 / 分支" min-width="240">
                  <template #default="{ row }">
                    <ElButton link type="primary" @click="drillByRepository(row)">{{ row.repository_name }}</ElButton>
                    <div class="muted">{{ row.branch_name }} · {{ row.project_id }}</div>
                  </template>
                </ElTableColumn>
                <ElTableColumn align="right" label="新增行数" prop="added_lines" width="120" />
                <ElTableColumn align="right" label="删除行数" prop="removed_lines" width="110" />
                <ElTableColumn align="right" label="总变更" prop="changed_lines" width="110" />
                <ElTableColumn align="right" label="CR数" prop="cr_count" width="90" />
                <ElTableColumn align="right" label="贡献人数" prop="contributor_count" width="100" />
              </ElTable>
            </div>
            <div class="panel">
              <div class="panel-title">人员合入贡献</div>
              <ElTable :data="personRanking" border height="420">
                <ElTableColumn label="创建人" min-width="180">
                  <template #default="{ row }">
                    <ElButton link type="primary" @click="drillByPerson(row)">{{ row.author_display_name }}</ElButton>
                    <div class="muted">{{ row.author_pl_group_name }}</div>
                  </template>
                </ElTableColumn>
                <ElTableColumn align="right" label="仓库" prop="repository_count" width="72" />
                <ElTableColumn align="right" label="新增行数" prop="added_lines" width="110" />
                <ElTableColumn align="right" label="CR数" prop="cr_count" width="80" />
              </ElTable>
            </div>
            <div class="panel">
              <div class="panel-title">PL组新增贡献</div>
              <ElTable :data="categoryDistribution?.pl_groups || []" border height="420">
                <ElTableColumn label="PL组" min-width="160" prop="category_label" />
                <ElTableColumn align="right" label="新增行数" prop="added_lines" width="110" />
                <ElTableColumn align="right" label="CR数" prop="cr_count" width="80" />
              </ElTable>
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
            <div class="collect-summary">默认复用当前选择的代码库和分支；未筛选时采集全部活跃绑定分支。</div>
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
  overflow-x: auto;
  padding: 12px;
  background:
    linear-gradient(180deg, rgb(248 250 252 / 96%) 0%, #fff 100%);
}

.filter-form {
  display: grid;
  grid-template-columns: 320px 180px 160px 150px 180px 180px 340px 230px;
  gap: 12px;
  align-items: end;
  min-width: 1764px;
}

.filter-form :deep(.el-form-item) {
  width: 100%;
  margin: 0;
}

.filter-form :deep(.el-form-item__label) {
  padding-bottom: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.filter-form :deep(.el-select),
.filter-form :deep(.el-input),
.filter-form :deep(.el-date-editor),
.filter-form :deep(.el-cascader) {
  width: 100%;
}

.filter-form :deep(.scope-item) {
  width: 100%;
}

.filter-form :deep(.filter-range) {
  width: 100%;
}

.filter-form :deep(.filter-actions) {
  width: auto;
  min-width: 0;
}

.scope-control {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.scope-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
  white-space: nowrap;
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
}
</style>
