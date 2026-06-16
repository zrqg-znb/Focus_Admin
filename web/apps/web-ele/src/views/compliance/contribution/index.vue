<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { BranchItem, RepositoryItem } from '#/api/compliance/base';
import type {
  ContributionCategoryDistribution,
  ContributionCollectTask,
  ContributionExportTask,
  ContributionFilters,
  ContributionMetric,
  ContributionPersonRankingItem,
  ContributionRankingItem,
  ContributionRecordItem,
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
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElLink,
  ElMessage,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  listBranchesApi,
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
  listContributionRecordsApi,
  prepareContributionExportTaskApi,
  runContributionCollectTaskApi,
} from '#/api/compliance/contribution';
import { getDictItemByCodeApi } from '#/api/core/dict';
import { getAllPlApi } from '#/api/core/pl';

defineOptions({ name: 'ComplianceContribution' });

const REPO_TYPE_DICT_CODE = 'code_compliance_repo_type';
const loading = ref(false);
const recordsLoading = ref(false);
const exportLoading = ref(false);
const collectSubmitting = ref(false);
const collectVisible = ref(false);
const trendChartRef = ref<EchartsUIType>();
const categoryChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrendChart } = useEcharts(trendChartRef);
const { renderEcharts: renderCategoryChart } = useEcharts(categoryChartRef);

const repositoryOptions = ref<RepositoryItem[]>([]);
const branchOptions = ref<BranchItem[]>([]);
const repoTypeOptions = ref<DictItem[]>([]);
const plGroupOptions = ref<PlGroup[]>([]);
const summary = ref<ContributionMetric>();
const trendRows = ref<ContributionTrendPoint[]>([]);
const repositoryRanking = ref<ContributionRankingItem[]>([]);
const personRanking = ref<ContributionPersonRankingItem[]>([]);
const categoryDistribution = ref<ContributionCategoryDistribution>();
const recordRows = ref<ContributionRecordItem[]>([]);
const recordTotal = ref(0);
const recordPage = ref(1);
const recordPageSize = ref(20);
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
    { label: '活跃仓库', value: data.active_repository_count },
    { label: '活跃分支', value: data.active_branch_count },
    { label: 'CR数', value: data.cr_count },
    { label: '贡献人数', value: data.contributor_count },
    { label: '新增行数', value: data.added_lines },
    { label: '删除行数', value: data.removed_lines },
    { label: '净增行数', value: data.net_lines },
    { label: '总变更行数', value: data.changed_lines },
  ];
});

function buildParams(): ContributionFilters {
  return {
    ...filters.value,
    merged_after: mergedRange.value?.[0],
    merged_before: mergedRange.value?.[1],
  };
}

function formatNumber(value?: number) {
  return Number(value || 0).toLocaleString();
}

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
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
    color: ['#2563eb', '#ef4444', '#16a34a'],
    grid: { bottom: 28, containLabel: true, left: 16, right: 20, top: 34 },
    legend: { top: 0 },
    series: [
      {
        data: trendRows.value.map((item) => item.added_lines),
        name: '新增',
        smooth: true,
        type: 'line',
      },
      {
        data: trendRows.value.map((item) => item.removed_lines),
        name: '删除',
        smooth: true,
        type: 'line',
      },
      {
        data: trendRows.value.map((item) => item.net_lines),
        name: '净增',
        smooth: true,
        type: 'line',
      },
    ],
    tooltip: { trigger: 'axis' },
    xAxis: {
      boundaryGap: false,
      data: trendRows.value.map((item) => item.date),
      type: 'category',
    },
    yAxis: { type: 'value' },
  });

  const categories = categoryDistribution.value?.repo_types || [];
  renderCategoryChart({
    color: ['#2563eb', '#16a34a', '#f59e0b', '#64748b', '#0891b2'],
    series: [
      {
        data: categories.map((item) => ({
          name: item.category_label,
          value: item.changed_lines,
        })),
        radius: ['48%', '72%'],
        type: 'pie',
      },
    ],
    tooltip: { trigger: 'item' },
  });
}

async function loadOptions() {
  const [repositories, branches, repoTypes, plGroups] = await Promise.all([
    listRepositoriesApi({ page: 1, pageSize: 1000 }),
    listBranchesApi({ is_active: true, page: 1, pageSize: 1000 }),
    getDictItemByCodeApi(REPO_TYPE_DICT_CODE),
    getAllPlApi(),
  ]);
  repositoryOptions.value = repositories.items || [];
  branchOptions.value = branches.items || [];
  repoTypeOptions.value = repoTypes.filter((item) => item.status);
  plGroupOptions.value = plGroups.filter((item) => item.status);
}

async function loadDashboard() {
  loading.value = true;
  try {
    const params = buildParams();
    const [summaryData, trendData, repoData, personData, categoryData] =
      await Promise.all([
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

async function loadRecords(resetPage = false) {
  if (resetPage) recordPage.value = 1;
  recordsLoading.value = true;
  try {
    const result = await listContributionRecordsApi({
      ...buildParams(),
      page: recordPage.value,
      pageSize: recordPageSize.value,
    });
    recordRows.value = result.items || [];
    recordTotal.value = result.total || 0;
  } finally {
    recordsLoading.value = false;
  }
}

async function reloadAll(resetPage = true) {
  await Promise.all([loadDashboard(), loadRecords(resetPage)]);
}

function drillByRepository(row: ContributionRankingItem) {
  const repo = repositoryOptions.value.find((item) => item.project_id === row.project_id);
  filters.value.repository_ids = repo ? [repo.id] : [];
  const branch = branchOptions.value.find((item) => item.branch_name === row.branch_name);
  filters.value.branch_ids = branch ? [branch.id] : [];
  reloadAll(true);
}

function drillByPerson(row: ContributionPersonRankingItem) {
  filters.value.author_username = row.author_username;
  reloadAll(true);
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
  saveBlob(data, current.file_name || 'code_contribution.xlsx');
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
  exportPollTimer = setInterval(() => {
    refreshExportTask(id);
  }, 2000);
}

async function submitExport(scope: 'records' | 'summary') {
  exportLoading.value = true;
  try {
    const result = await prepareContributionExportTaskApi({
      filters: buildParams(),
      scope,
    });
    exportTask.value = result.task;
    ElMessage.success('导出任务已提交');
    if (result.task.status === 'success') {
      await downloadExportTask(result.task);
    } else {
      startExportPolling(result.task.id);
    }
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
      repository_ids: filters.value.repository_ids,
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
  await reloadAll(true);
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
          <ElFormItem label="代码库">
            <ElSelect
              v-model="filters.repository_ids"
              collapse-tags
              collapse-tags-tooltip
              clearable
              filterable
              multiple
              placeholder="选择代码库"
            >
              <ElOption
                v-for="item in repositoryOptions"
                :key="item.id"
                :label="`${item.project_name}（${item.project_id}）`"
                :value="item.id"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="分支">
            <ElSelect
              v-model="filters.branch_ids"
              collapse-tags
              collapse-tags-tooltip
              clearable
              filterable
              multiple
              placeholder="选择活跃分支"
            >
              <ElOption
                v-for="item in branchOptions"
                :key="item.id"
                :label="item.branch_name"
                :value="item.id"
              />
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
              <ElOption
                v-for="item in repoTypeOptions"
                :key="item.value || item.id"
                :label="item.label"
                :value="item.value || ''"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="领域">
            <ElSelect v-model="filters.domain" clearable placeholder="全部领域">
              <ElOption label="座舱" value="cockpit" />
              <ElOption label="车控" value="vehicle" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="PL组">
            <ElSelect
              v-model="filters.pl_group_ids"
              collapse-tags
              collapse-tags-tooltip
              clearable
              filterable
              multiple
              placeholder="选择PL组"
            >
              <ElOption
                v-for="item in plGroupOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
              <ElOption label="非底软领域" value="unknown" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="创建人">
            <ElInput v-model="filters.author_username" clearable placeholder="姓名 / 工号" />
          </ElFormItem>
          <ElFormItem label="关键词">
            <ElInput v-model="filters.keyword" clearable placeholder="CR / 仓库 / 分支" />
          </ElFormItem>
          <ElFormItem class="filter-range" label="合入时间">
            <ElDatePicker
              v-model="mergedRange"
              clearable
              end-placeholder="结束"
              range-separator="至"
              start-placeholder="开始"
              type="datetimerange"
              value-format="YYYY-MM-DDTHH:mm:ssZ"
            />
          </ElFormItem>
          <ElFormItem class="filter-actions" label=" ">
            <ElButton type="primary" @click="reloadAll(true)">查询</ElButton>
            <ElButton @click="collectVisible = true">手动同步</ElButton>
            <ElButton :loading="exportLoading" @click="submitExport('summary')">
              导出聚合
            </ElButton>
            <ElButton :loading="exportLoading" @click="submitExport('records')">
              导出明细
            </ElButton>
          </ElFormItem>
        </ElForm>
      </section>

      <section class="metric-grid">
        <div v-for="item in metricCards" :key="item.label" class="metric-card">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ formatNumber(item.value) }}</div>
        </div>
      </section>

      <section class="analysis-grid">
        <div class="panel panel-wide">
          <div class="panel-title">代码变更日趋势</div>
          <EchartsUI ref="trendChartRef" class="chart-body" />
        </div>
        <div class="panel">
          <div class="panel-title">仓库类型分布</div>
          <EchartsUI ref="categoryChartRef" class="chart-body" />
        </div>
      </section>

      <section class="table-grid">
        <div class="panel">
          <div class="panel-title">仓库 / 分支排行</div>
          <ElTable :data="repositoryRanking" border height="320">
            <ElTableColumn label="代码库 / 分支" min-width="220">
              <template #default="{ row }">
                <ElButton link type="primary" @click="drillByRepository(row)">
                  {{ row.repository_name }}
                </ElButton>
                <div class="muted">{{ row.branch_name }} · {{ row.project_id }}</div>
              </template>
            </ElTableColumn>
            <ElTableColumn align="right" label="CR" prop="cr_count" width="72" />
            <ElTableColumn align="right" label="贡献人" prop="contributor_count" width="86" />
            <ElTableColumn align="right" label="总变更" prop="changed_lines" width="110" />
          </ElTable>
        </div>
        <div class="panel">
          <div class="panel-title">人员贡献排行</div>
          <ElTable :data="personRanking" border height="320">
            <ElTableColumn label="创建人" min-width="180">
              <template #default="{ row }">
                <ElButton link type="primary" @click="drillByPerson(row)">
                  {{ row.author_display_name }}
                </ElButton>
                <div class="muted">{{ row.author_pl_group_name }}</div>
              </template>
            </ElTableColumn>
            <ElTableColumn align="right" label="仓库" prop="repository_count" width="72" />
            <ElTableColumn align="right" label="分支" prop="branch_count" width="72" />
            <ElTableColumn align="right" label="总变更" prop="changed_lines" width="110" />
          </ElTable>
        </div>
        <div class="panel">
          <div class="panel-title">类别分布</div>
          <ElTable :data="categoryDistribution?.pl_groups || []" border height="320">
            <ElTableColumn label="PL组" min-width="160" prop="category_label" />
            <ElTableColumn align="right" label="CR" prop="cr_count" width="72" />
            <ElTableColumn align="right" label="总变更" prop="changed_lines" width="110" />
          </ElTable>
        </div>
      </section>

      <section class="panel">
        <div class="record-header">
          <div>
            <div class="panel-title">CR 贡献明细</div>
            <div class="muted">点击仓库、人员排行可快速下钻到对应明细</div>
          </div>
          <ElButton @click="loadRecords(false)">刷新明细</ElButton>
        </div>
        <ElTable :data="recordRows" border height="420" v-loading="recordsLoading">
          <ElTableColumn fixed label="CR标题" min-width="260">
            <template #default="{ row }">
              <ElLink
                v-if="row.web_url"
                :href="row.web_url"
                target="_blank"
                type="primary"
              >
                {{ row.title || row.change_key }}
              </ElLink>
              <span v-else>{{ row.title || row.change_key }}</span>
              <div class="muted">{{ row.change_key }}</div>
            </template>
          </ElTableColumn>
          <ElTableColumn label="代码库" min-width="180" prop="repository_name" />
          <ElTableColumn label="分支" min-width="160" prop="branch_name" />
          <ElTableColumn label="创建人" min-width="150" prop="author_display_name" />
          <ElTableColumn label="PL组" min-width="140" prop="author_pl_group_name" />
          <ElTableColumn align="right" label="新增" prop="added_lines" width="90" />
          <ElTableColumn align="right" label="删除" prop="removed_lines" width="90" />
          <ElTableColumn align="right" label="净增" prop="net_lines" width="90" />
          <ElTableColumn align="right" label="总变更" prop="changed_lines" width="100" />
          <ElTableColumn label="合入时间" width="170">
            <template #default="{ row }">{{ formatTime(row.merged_at) }}</template>
          </ElTableColumn>
          <ElTableColumn label="类型" width="90">
            <template #default="{ row }">
              <ElTag effect="plain">{{ row.branch_type_label }}</ElTag>
            </template>
          </ElTableColumn>
        </ElTable>
        <div class="pagination-row">
          <ElPagination
            v-model:current-page="recordPage"
            v-model:page-size="recordPageSize"
            :page-sizes="[20, 50, 100]"
            :total="recordTotal"
            layout="total, sizes, prev, pager, next"
            @current-change="loadRecords(false)"
            @size-change="loadRecords(true)"
          />
        </div>
      </section>

      <ElDialog v-model="collectVisible" title="手动同步代码贡献数据" width="560px">
        <ElForm label-width="92px">
          <ElFormItem label="时间范围">
            <ElDatePicker
              v-model="collectRange"
              end-placeholder="结束"
              range-separator="至"
              start-placeholder="开始"
              type="datetimerange"
              value-format="YYYY-MM-DDTHH:mm:ssZ"
            />
          </ElFormItem>
          <ElFormItem label="同步范围">
            <div class="collect-summary">
              默认复用当前筛选中的代码库和分支；未筛选时采集全部活跃绑定分支。
            </div>
          </ElFormItem>
          <ElFormItem v-if="collectTask" label="最近任务">
            <div class="collect-summary">
              {{ collectTask.status_label }} · 拉取 {{ collectTask.fetched_count }} 条 · 新增
              {{ collectTask.created_count }} 条
            </div>
          </ElFormItem>
        </ElForm>
        <template #footer>
          <ElButton @click="collectVisible = false">取消</ElButton>
          <ElButton :loading="collectSubmitting" type="primary" @click="submitCollectTask">
            提交任务
          </ElButton>
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
.filter-form :deep(.el-date-editor) {
  width: 100%;
}

.filter-form :deep(.filter-range) {
  width: 390px;
}

.filter-form :deep(.filter-actions) {
  width: auto;
  min-width: 360px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(8, minmax(120px, 1fr));
  gap: 10px;
}

.metric-card {
  padding: 12px;
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.panel {
  min-width: 0;
  padding: 12px;
}

.panel-title {
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 650;
  color: var(--el-text-color-primary);
}

.chart-body {
  width: 100%;
  height: 300px;
}

.record-header,
.pagination-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pagination-row {
  justify-content: flex-end;
  margin-top: 12px;
}

.collect-summary {
  font-size: 13px;
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

@media (max-width: 768px) {
  .filter-form :deep(.el-form-item),
  .filter-form :deep(.filter-range),
  .filter-form :deep(.filter-actions) {
    width: 100%;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}
</style>
