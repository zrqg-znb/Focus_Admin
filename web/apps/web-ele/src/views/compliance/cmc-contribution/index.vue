<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  CmcCommentDistribution,
  CmcPersonRanking,
  CmcPersonRecord,
  CmcSummary,
  CmcSyncTask,
  CmcTrendPoint,
} from '#/api/cmc-contribution';

import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElEmpty,
  ElInput,
  ElMessage,
  ElPopover,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';
import { RefreshCw } from 'lucide-vue-next';

import {
  createCmcSyncTask,
  getCmcCommentDistribution,
  getCmcPersonRanking,
  getCmcSummary,
  getCmcSyncTask,
  getCmcTrend,
  listCmcPersons,
} from '#/api/cmc-contribution';
import { useZqTable } from '#/components/zq-table';

defineOptions({ name: 'CmcContribution' });

const today = new Date();
const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
const formatDate = (value: Date) => value.toISOString().slice(0, 10);
const dateRange = ref<[string, string]>([
  formatDate(monthStart),
  formatDate(today),
]);
const activeTab = ref<'dashboard' | 'table'>('dashboard');
const summary = ref<CmcSummary>();
const trendRows = ref<CmcTrendPoint[]>([]);
const personRanking = ref<CmcPersonRanking[]>([]);
const commentDistribution = ref<CmcCommentDistribution[]>([]);
const loading = ref(false);
const userKeyword = ref('');
const userFilterVisible = ref(false);
const syncVisible = ref(false);
const syncRange = ref<[string, string]>();
const syncTask = ref<CmcSyncTask>();
const syncSubmitting = ref(false);
const trendChartRef = ref<EchartsUIType>();
const rankingChartRef = ref<EchartsUIType>();
const distributionChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrendChart } = useEcharts(trendChartRef);
const { renderEcharts: renderRankingChart } = useEcharts(rankingChartRef);
const { renderEcharts: renderDistributionChart } =
  useEcharts(distributionChartRef);
let pollTimer: ReturnType<typeof setInterval> | undefined;

const params = computed(() => ({
  startDate: dateRange.value[0],
  endDate: dateRange.value[1],
}));
const formatNumber = (value?: number) => Number(value || 0).toLocaleString();
const formatPercent = (value?: number) =>
  `${(Number(value || 0) * 100).toFixed(2)}%`;
const formatDensity = (value: null | number | undefined) =>
  value === null || value === undefined ? '--' : value.toFixed(4);
const metricCards = computed(() => {
  const data = summary.value;
  if (!data) return [];
  return [
    {
      label: '有效检视意见',
      tone: 'primary',
      value: formatNumber(data.effective_comment_count),
    },
    {
      label: '检视代码行',
      tone: 'cyan',
      value: formatNumber(data.checked_mr_lines),
    },
    {
      label: '意见密度',
      tone: 'amber',
      value: formatDensity(data.effective_comment_density),
    },
    { label: '合入 MR', value: formatNumber(data.cnt_total) },
    {
      label: '零检视占比',
      tone: 'danger',
      value: formatPercent(data.zero_comment_rate),
    },
    { label: '贡献人数', value: formatNumber(data.contributor_count) },
  ];
});
const periodDescription = computed(
  () => `${dateRange.value[0]} 至 ${dateRange.value[1]} · 底层软件开发部`,
);

const [Grid, gridApi] = useZqTable<CmcPersonRecord>({
  showSearchForm: false,
  gridOptions: {
    border: true,
    stripe: true,
    columns: [
      {
        field: 'user',
        minWidth: 140,
        slots: { header: 'header-user' },
        title: '人员',
      },
      { align: 'right', field: 'cnt_total', title: '合入MR' },
      { align: 'right', field: 'zero_comment_mr_count', title: '零检视MR' },
      {
        align: 'right',
        field: 'zero_comment_rate',
        formatter: ({ cellValue }) => formatPercent(Number(cellValue)),
        title: '零检视占比',
      },
      {
        align: 'right',
        field: 'effective_comment_count',
        title: '有效检视意见',
      },
      {
        align: 'right',
        field: 'effective_comment_density',
        formatter: ({ cellValue }) => formatDensity(cellValue),
        title: '意见密度',
      },
      { align: 'right', field: 'major_comments_cnt', title: '严重' },
      { align: 'right', field: 'fatal_comments_cnt', title: '致命' },
      { align: 'right', field: 'minor_comments_cnt', title: '一般' },
      { align: 'right', field: 'sugge_comments_cnt', title: '建议' },
      { align: 'right', field: 'cmt_issue', title: 'Issue' },
      { align: 'right', field: 'checked_mr_lines', title: '检视代码行' },
      { align: 'right', field: 'cmt_lines', title: '提交MR代码量' },
    ],
    pagerConfig: { enabled: true, pageSize: 20, pageSizes: [20, 50, 100] },
    proxyConfig: {
      // 页面进入总览时不加载；切换到人员明细后由 handleTabChange 主动查询。
      autoLoad: false,
      ajax: {
        query: async ({ page }) =>
          listCmcPersons({
            ...params.value,
            page: page.currentPage,
            pageSize: page.pageSize,
            userKeyword: userKeyword.value,
          }),
      },
    },
  },
});

function renderCharts() {
  renderTrendChart({
    color: ['#2563eb', '#d97706', '#0891b2'],
    grid: { bottom: 28, containLabel: true, left: 12, right: 20, top: 38 },
    legend: { top: 0 },
    series: [
      {
        data: trendRows.value.map((item) => item.effective_comment_count),
        name: '有效检视意见',
        smooth: true,
        type: 'line',
      },
      {
        data: trendRows.value.map((item) => item.cnt_total),
        name: '合入MR',
        smooth: true,
        type: 'line',
      },
      {
        data: trendRows.value.map((item) => item.checked_mr_lines),
        name: '检视代码行',
        smooth: true,
        type: 'line',
        yAxisIndex: 1,
      },
    ],
    tooltip: { trigger: 'axis' },
    xAxis: {
      boundaryGap: false,
      data: trendRows.value.map((item) => item.date),
      type: 'category',
    },
    yAxis: [{ type: 'value' }, { type: 'value' }],
  });

  const rankingRows = personRanking.value.slice(0, 10).reverse();
  renderRankingChart({
    color: ['#2563eb'],
    grid: { bottom: 18, containLabel: true, left: 10, right: 42, top: 12 },
    series: [
      {
        barMaxWidth: 18,
        data: rankingRows.map((item) => item.effective_comment_count),
        label: { position: 'right', show: true },
        type: 'bar',
      },
    ],
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value' },
    yAxis: {
      axisLabel: {
        formatter: (value: string) =>
          value.length > 10 ? `${value.slice(0, 10)}…` : value,
      },
      data: rankingRows.map((item) => item.user),
      type: 'category',
    },
  });

  renderDistributionChart({
    color: ['#dc2626', '#ea580c', '#eab308', '#2563eb', '#64748b'],
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        avoidLabelOverlap: true,
        data: commentDistribution.value.map((item) => ({
          name: item.label,
          value: item.value,
        })),
        label: { formatter: '{b}\n{d}%' },
        radius: ['48%', '72%'],
        type: 'pie',
      },
    ],
    tooltip: { trigger: 'item' },
  });
}

async function loadDashboard() {
  loading.value = true;
  try {
    const [summaryData, trendData, rankingData, distributionData] =
      await Promise.all([
        getCmcSummary(params.value),
        getCmcTrend(params.value),
        getCmcPersonRanking(params.value),
        getCmcCommentDistribution(params.value),
      ]);
    summary.value = summaryData;
    trendRows.value = trendData;
    personRanking.value = rankingData;
    commentDistribution.value = distributionData;
    await nextTick();
    renderCharts();
  } finally {
    loading.value = false;
  }
}
async function reloadAll() {
  await loadDashboard();
  if (activeTab.value === 'table') await reloadPersonTable();
}
async function reloadPersonTable() {
  // 日期或列头筛选条件变化后，始终从第一页重新读取人员汇总结果。
  gridApi.pagination.currentPage = 1;
  await gridApi.query();
}
async function handleTabChange(tab: number | string) {
  // 切换到明细 Tab 后等待 Grid 挂载完成，再发起首屏分页查询。
  if (tab !== 'table') return;
  await nextTick();
  await reloadPersonTable();
}
async function applyUserFilter() {
  userFilterVisible.value = false;
  await reloadPersonTable();
}
async function clearUserFilter() {
  userKeyword.value = '';
  await applyUserFilter();
}
function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = undefined;
}
async function pollTask(id: string) {
  const task = await getCmcSyncTask(id);
  syncTask.value = task;
  if (task.status === 'success') {
    stopPolling();
    ElMessage.success(
      `同步完成：${task.synced_dates.length} 天，${task.fetched_rows} 条数据`,
    );
    await reloadAll();
  }
  if (task.status === 'failed') {
    stopPolling();
    ElMessage.error(task.error_message || '同步任务失败');
  }
}
async function submitSync() {
  if (!syncRange.value?.[0] || !syncRange.value?.[1]) {
    ElMessage.warning('请选择同步日期范围');
    return;
  }
  syncSubmitting.value = true;
  try {
    syncTask.value = await createCmcSyncTask({
      startDate: syncRange.value[0],
      endDate: syncRange.value[1],
    });
    syncVisible.value = false;
    ElMessage.success('同步任务已提交');
    stopPolling();
    pollTimer = setInterval(() => pollTask(syncTask.value!.id), 2000);
  } finally {
    syncSubmitting.value = false;
  }
}
onMounted(loadDashboard);
onUnmounted(stopPolling);
</script>

<template>
  <Page auto-content-height>
    <div class="cmc-page" v-loading="loading">
      <section class="toolbar-panel">
        <div class="toolbar-context">
          <div class="eyebrow">CMC CONTRIBUTION / QUALITY SIGNAL</div>
          <div class="toolbar-title">检视贡献看板</div>
          <div class="toolbar-desc">{{ periodDescription }}</div>
        </div>
        <div class="toolbar-controls">
          <div class="date-field">
            <span>统计日期</span>
            <ElDatePicker
              v-model="dateRange"
              :clearable="false"
              end-placeholder="结束"
              range-separator="至"
              start-placeholder="开始"
              type="daterange"
              value-format="YYYY-MM-DD"
              @change="reloadAll"
            />
          </div>
          <ElTag
            v-if="syncTask"
            :type="
              syncTask.status === 'success'
                ? 'success'
                : syncTask.status === 'failed'
                  ? 'danger'
                  : 'warning'
            "
          >
            同步：{{ syncTask.status }}
          </ElTag>
          <ElButton :icon="RefreshCw" @click="syncVisible = true">
            管理员补数
          </ElButton>
          <ElButton type="primary" @click="reloadAll">刷新看板</ElButton>
        </div>
      </section>

      <ElTabs
        v-model="activeTab"
        class="cmc-tabs"
        @tab-change="handleTabChange"
      >
        <ElTabPane label="总览看板" name="dashboard">
          <section v-if="summary" class="metric-grid">
            <div
              v-for="item in metricCards"
              :key="item.label"
              class="metric-card"
              :class="[item.tone && `metric-${item.tone}`]"
            >
              <div class="metric-label">{{ item.label }}</div>
              <div class="metric-value">{{ item.value }}</div>
            </div>
          </section>
          <ElEmpty v-else description="当前日期范围暂无已同步数据" />
          <section v-if="summary" class="hero-grid">
            <div class="panel panel-hero">
              <div class="panel-header">
                <div>
                  <div class="panel-title">每日检视节奏</div>
                  <div class="panel-desc">
                    有效检视意见、合入 MR 与检视代码行的每日变化。
                  </div>
                </div>
              </div>
              <EchartsUI ref="trendChartRef" class="chart-body chart-large" />
            </div>
          </section>
          <section v-if="summary" class="insight-grid">
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">人员检视贡献 Top 10</div>
                  <div class="panel-desc">
                    以有效检视意见排序，快速识别主要检视贡献者。
                  </div>
                </div>
              </div>
              <EchartsUI ref="rankingChartRef" class="chart-body" />
            </div>
            <div class="panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">意见等级组成</div>
                  <div class="panel-desc">
                    四个等级意见与 Issue 的分布占比。
                  </div>
                </div>
              </div>
              <EchartsUI ref="distributionChartRef" class="chart-body" />
            </div>
          </section>
        </ElTabPane>
        <ElTabPane label="人员明细" name="table">
          <section class="table-panel">
            <div class="table-panel-title">
              人员检视贡献明细 <span>按当前统计日期范围汇总</span>
            </div>
            <div class="table-content">
              <Grid class="cmc-person-grid h-full">
                <template #header-user>
                  <div class="flex items-center gap-1">
                    <span>人员</span>
                    <ElPopover
                      v-model:visible="userFilterVisible"
                      trigger="click"
                      width="240"
                    >
                      <template #reference>
                        <Filter class="cursor-pointer" :size="15" />
                      </template>
                      <div class="space-y-2">
                        <ElInput
                          v-model="userKeyword"
                          clearable
                          placeholder="输入人员名称"
                          @keyup.enter="applyUserFilter"
                        />
                        <div class="flex justify-end gap-2">
                          <ElButton link @click="clearUserFilter">
                            清空
                          </ElButton>
                          <ElButton type="primary" @click="applyUserFilter">
                            应用
                          </ElButton>
                        </div>
                      </div>
                    </ElPopover>
                  </div>
                </template>
              </Grid>
            </div>
          </section>
        </ElTabPane>
      </ElTabs>
    </div>
    <ElDialog v-model="syncVisible" title="CMC 数据补数" width="460px">
      <p class="mb-3 text-sm text-gray-500">
        一次最多同步 31 个自然日，任务在后台执行。
      </p>
      <ElDatePicker
        v-model="syncRange"
        class="w-full"
        end-placeholder="结束日期"
        start-placeholder="开始日期"
        type="daterange"
        value-format="YYYY-MM-DD"
      />
      <template #footer>
        <ElButton @click="syncVisible = false">取消</ElButton>
        <ElButton :loading="syncSubmitting" type="primary" @click="submitSync">
          开始同步
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style scoped lang="less">
.cmc-page {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 14px;
}
.toolbar-panel,
.panel,
.metric-card,
.table-panel {
  border: 1px solid #dfe7f1;
  border-radius: 10px;
  background: var(--el-bg-color);
  box-shadow: 0 10px 28px rgb(15 23 42 / 5%);
}
.toolbar-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  overflow: hidden;
  padding: 15px 18px;
  background: linear-gradient(100deg, #f8fbff 0%, #fff 56%, #f9fafb 100%);
}
.toolbar-context {
  min-width: 260px;
}
.eyebrow {
  color: #2563eb;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.13em;
}
.toolbar-title {
  margin-top: 3px;
  color: #0f172a;
  font-size: 20px;
  font-weight: 750;
  letter-spacing: -0.03em;
}
.toolbar-desc {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
}
.toolbar-controls {
  display: flex;
  align-items: end;
  justify-content: flex-end;
  gap: 8px;
}
.date-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: #64748b;
  font-size: 11px;
  font-weight: 650;
}
.date-field :deep(.el-date-editor) {
  width: 265px;
}
.cmc-tabs {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
}
.cmc-tabs :deep(.el-tabs__header) {
  margin: 0 0 12px;
  border: 1px solid #dfe7f1;
  border-radius: 9px;
  background: var(--el-bg-color);
  padding: 0 14px;
}
.cmc-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}
.cmc-tabs :deep(.el-tabs__content),
.cmc-tabs :deep(.el-tab-pane) {
  min-height: 0;
  flex: 1;
}
.cmc-tabs :deep(.el-tab-pane) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(128px, 1fr));
  gap: 10px;
}
.metric-card {
  position: relative;
  min-height: 92px;
  overflow: hidden;
  padding: 13px;
}
.metric-card::after {
  position: absolute;
  top: 0;
  right: 0;
  width: 34px;
  height: 4px;
  background: #94a3b8;
  content: '';
}
.metric-primary {
  border-color: #bfdbfe;
  background:
    radial-gradient(circle at 90% 12%, rgb(37 99 235 / 16%), transparent 38%),
    #fff;
}
.metric-primary::after {
  background: #2563eb;
}
.metric-cyan::after {
  background: #0891b2;
}
.metric-amber {
  background: #fffbeb;
  border-color: #fde68a;
}
.metric-amber::after {
  background: #d97706;
}
.metric-danger {
  background: #fff7f7;
  border-color: #fecaca;
}
.metric-danger::after {
  background: #dc2626;
}
.metric-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}
.metric-value {
  margin-top: 11px;
  color: #0f172a;
  font-size: 24px;
  font-weight: 760;
  letter-spacing: -0.04em;
}
.hero-grid,
.insight-grid {
  display: grid;
  gap: 12px;
}
.insight-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.panel {
  min-width: 0;
  padding: 14px;
}
.panel-hero {
  background:
    radial-gradient(circle at 95% 0, rgb(37 99 235 / 10%), transparent 36%),
    var(--el-bg-color);
}
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 8px;
}
.panel-title,
.table-panel-title {
  color: #0f172a;
  font-size: 14px;
  font-weight: 750;
}
.panel-desc,
.table-panel-title span {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
  font-weight: 400;
}
.chart-body {
  width: 100%;
  height: 310px;
}
.chart-large {
  height: 335px;
}
.table-panel {
  display: flex;
  height: max(610px, calc(100vh - 275px));
  min-height: 0;
  flex-direction: column;
  padding: 13px;
}
.table-panel-title {
  flex: 0 0 auto;
  padding: 0 0 12px;
}
.table-content {
  min-height: 0;
  flex: 1;
}
.cmc-person-grid :deep(.el-table__header th.el-table__cell) {
  background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
}
.cmc-person-grid :deep(.el-table__row td.el-table__cell) {
  vertical-align: middle;
}
.cmc-person-grid :deep(.el-table__row td.el-table__cell:first-child) {
  color: #0f172a;
  font-weight: 700;
}
.cmc-person-grid :deep(.el-table__row td.el-table__cell:nth-child(n + 2)) {
  font-variant-numeric: tabular-nums;
}
@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(150px, 1fr));
  }
  .toolbar-panel {
    align-items: stretch;
    flex-direction: column;
  }
  .toolbar-controls {
    justify-content: flex-start;
  }
  .insight-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 720px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
  .toolbar-controls {
    align-items: stretch;
    flex-wrap: wrap;
  }
  .date-field {
    width: 100%;
  }
  .date-field :deep(.el-date-editor) {
    width: 100%;
  }
}
</style>
