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
  ElTable,
  ElTableColumn,
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
const trendChartRef = ref<EchartsUIType>();
const categoryChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrendChart } = useEcharts(trendChartRef);
const { renderEcharts: renderCategoryChart } = useEcharts(categoryChartRef);

const organizationTree = ref<OrganizationItem[]>([]);
const repositoryOptions = ref<RepositoryItem[]>([]);
const branchOptions = ref<BranchItem[]>([]);
const repoTypeOptions = ref<DictItem[]>([]);
const plGroupOptions = ref<PlGroup[]>([]);
const selectedScopeValues = ref<string[]>([]);
const summary = ref<ContributionMetric>();
const trendRows = ref<ContributionTrendPoint[]>([]);
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
    { label: '单CR新增均值', value: data.cr_count ? Math.round(data.added_lines / data.cr_count) : 0 },
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

  const categories = categoryDistribution.value?.repo_types || [];
  renderCategoryChart({
    color: ['#2563eb', '#16a34a', '#f59e0b', '#64748b', '#0891b2'],
    series: [{ data: categories.map((item) => ({ name: item.category_label, value: item.added_lines })), radius: ['48%', '72%'], type: 'pie' }],
    tooltip: { trigger: 'item' },
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
    const [summaryData, trendData, repoData, personData, categoryData] = await Promise.all([
      getContributionSummaryApi(params),
      getContributionTrendApi(params),
      getContributionRepositoryRankingApi(params),
      getContributionPersonRankingApi(params),
      getContributionCategoryDistributionApi(params),
    ]);
    summary.value = summaryData;
    trendRows.value = trendData;
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
          <ElFormItem label="分支类型">
            <ElSelect v-model="filters.branch_type" clearable placeholder="全部类型">
              <ElOption label="开发" value="development" />
              <ElOption label="主干" value="trunk" />
              <ElOption label="发布" value="release" />
              <ElOption label="其他" value="other" />
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

      <section class="metric-grid">
        <div v-for="item in metricCards" :key="item.label" :class="['metric-card', item.tone && `metric-${item.tone}`]">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ formatNumber(item.value) }}</div>
        </div>
      </section>

      <section class="analysis-grid">
        <div class="panel panel-wide">
          <div class="panel-title">新增代码贡献趋势</div>
          <EchartsUI ref="trendChartRef" class="chart-body" />
        </div>
        <div class="panel">
          <div class="panel-title">仓库类型新增贡献分布</div>
          <EchartsUI ref="categoryChartRef" class="chart-body" />
        </div>
      </section>

      <section class="table-grid">
        <div class="panel panel-wide">
          <div class="panel-title">仓库 / 分支新增贡献</div>
          <ElTable :data="repositoryRanking" border height="360">
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
          <ElTable :data="personRanking" border height="360">
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
          <ElTable :data="categoryDistribution?.pl_groups || []" border height="360">
            <ElTableColumn label="PL组" min-width="160" prop="category_label" />
            <ElTableColumn align="right" label="新增行数" prop="added_lines" width="110" />
            <ElTableColumn align="right" label="CR数" prop="cr_count" width="80" />
          </ElTable>
        </div>
      </section>

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
  gap: 12px;
  min-height: 0;
}

.toolbar-panel,
.panel,
.metric-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.toolbar-panel {
  padding: 12px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
}

.filter-form :deep(.el-form-item) {
  width: 220px;
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
  width: 440px;
}

.filter-form :deep(.filter-range) {
  width: 390px;
}

.filter-form :deep(.filter-actions) {
  width: auto;
  min-width: 380px;
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
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(8, minmax(120px, 1fr));
  gap: 10px;
}

.metric-card {
  padding: 12px;
}

.metric-primary {
  border-color: #93c5fd;
  background: #eff6ff;
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

.analysis-grid,
.table-grid {
  display: grid;
  gap: 12px;
}

.analysis-grid {
  grid-template-columns: 2fr 1fr;
}

.table-grid {
  grid-template-columns: 2fr 1fr 1fr;
}

.panel {
  min-width: 0;
  padding: 12px;
}

.panel-wide {
  min-width: 0;
}

.panel-title {
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 600;
}

.chart-body {
  width: 100%;
  height: 320px;
}

.collect-summary {
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(4, minmax(120px, 1fr));
  }

  .analysis-grid,
  .table-grid {
    grid-template-columns: 1fr;
  }
}
</style>
