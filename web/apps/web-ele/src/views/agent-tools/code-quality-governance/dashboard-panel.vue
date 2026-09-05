<!-- eslint-disable vue/html-self-closing -->
<script lang="ts" setup>
import type {
  GovernanceProject,
  GovernanceResponsibility,
  Summary,
} from '#/api/agent-tools/code-quality-governance';

import { computed, onMounted, ref, watch } from 'vue';

import {
  ElButton,
  ElCard,
  ElEmpty,
  ElOption,
  ElSelect,
  ElStatistic,
  ElTag,
} from 'element-plus';

import {
  getSummaryApi,
  getTrendApi,
} from '#/api/agent-tools/code-quality-governance';

defineOptions({ name: 'CodeQualityGovernanceDashboard' });

const props = defineProps<{
  projects: GovernanceProject[];
  responsibilities: GovernanceResponsibility[];
}>();

const severityKeys = ['blocker', 'critical', 'major', 'minor', 'info'];
const summary = ref<Summary>({
  normal: 0,
  pending: 0,
  pending_applications: 0,
  project_rank: [],
  responsibility_rank: [],
  severity: {},
  shielded: 0,
  tool_rank: [],
  total: 0,
});
const trend = ref<{ count: number; date: string }[]>([]);
const projectId = ref('');
const responsibilityId = ref('');
const loading = ref(false);

const maxTrendCount = computed(() =>
  Math.max(...trend.value.map((item) => item.count), 1),
);

const latestReport = computed(() => summary.value.latest_report);

function severityCount(key: string) {
  return summary.value.severity[key] || 0;
}

function reportValue(key: string) {
  return latestReport.value?.[key] ?? '-';
}

function reportComplete() {
  return latestReport.value?.complete !== false;
}

async function loadDashboard() {
  loading.value = true;
  try {
    const params = {
      project_id: projectId.value || undefined,
      responsibility_id: responsibilityId.value || undefined,
    };
    const [nextSummary, nextTrend] = await Promise.all([
      getSummaryApi(params),
      getTrendApi({ ...params, days: 30 }),
    ]);
    summary.value = nextSummary;
    trend.value = nextTrend;
  } finally {
    loading.value = false;
  }
}

function selectProject(value: string) {
  projectId.value = value;
  void loadDashboard();
}

function selectResponsibility(value: string) {
  responsibilityId.value = value;
  void loadDashboard();
}

watch(
  () => [props.projects.length, props.responsibilities.length],
  () => {
    if (!loading.value) void loadDashboard();
  },
);

onMounted(loadDashboard);
</script>

<template>
  <section class="dashboard-panel">
    <div class="panel-toolbar">
      <div>
        <h2>问题概览</h2>
        <p>按项目和责任田查看扫描问题与治理进度</p>
      </div>
      <div class="toolbar-filters">
        <ElSelect
          v-model="projectId"
          clearable
          placeholder="项目"
          @change="selectProject"
        >
          <ElOption
            v-for="item in projects"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </ElSelect>
        <ElSelect
          v-model="responsibilityId"
          clearable
          placeholder="责任田"
          @change="selectResponsibility"
        >
          <ElOption
            v-for="item in responsibilities"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </ElSelect>
        <ElButton :loading="loading" @click="loadDashboard">刷新</ElButton>
      </div>
    </div>

    <div class="stat-grid">
      <ElCard class="metric-card" shadow="never">
        <ElStatistic title="问题总数" :value="summary.total" />
      </ElCard>
      <ElCard class="metric-card" shadow="never">
        <ElStatistic title="待治理" :value="summary.normal" />
      </ElCard>
      <ElCard class="metric-card" shadow="never">
        <ElStatistic title="待审批" :value="summary.pending_applications" />
      </ElCard>
      <ElCard class="metric-card" shadow="never">
        <ElStatistic title="已屏蔽" :value="summary.shielded" />
      </ElCard>
    </div>

    <div class="dashboard-grid dashboard-grid--three">
      <ElCard class="panel-card" shadow="never">
        <template #header>严重级别</template>
        <div class="metric-list">
          <div v-for="key in severityKeys" :key="key" class="metric-row">
            <span>{{ key }}</span>
            <strong>{{ severityCount(key) }}</strong>
          </div>
        </div>
      </ElCard>
      <ElCard class="panel-card" shadow="never">
        <template #header>项目问题排行</template>
        <div v-if="summary.project_rank.length" class="metric-list">
          <div
            v-for="row in summary.project_rank"
            :key="row.name"
            class="metric-row"
          >
            <span>{{ row.name }}</span>
            <strong>{{ row.count }}</strong>
          </div>
        </div>
        <ElEmpty v-else description="暂无数据" :image-size="48" />
      </ElCard>
      <ElCard class="panel-card" shadow="never">
        <template #header>责任田问题排行</template>
        <div v-if="summary.responsibility_rank.length" class="metric-list">
          <div
            v-for="row in summary.responsibility_rank"
            :key="row.name"
            class="metric-row"
          >
            <span>{{ row.name }}</span>
            <strong>{{ row.count }}</strong>
          </div>
        </div>
        <ElEmpty v-else description="暂无数据" :image-size="48" />
      </ElCard>
    </div>

    <div class="dashboard-grid dashboard-grid--two">
      <ElCard class="panel-card" shadow="never">
        <template #header>扫描趋势（近 30 天）</template>
        <div v-if="trend.length > 0" class="trend-list">
          <div v-for="item in trend" :key="item.date" class="trend-row">
            <span>{{ item.date }}</span>
            <div class="trend-bar-track">
              <i :style="{ width: `${(item.count / maxTrendCount) * 100}%` }" />
            </div>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
        <ElEmpty v-else description="暂无趋势数据" :image-size="48" />
      </ElCard>
      <ElCard class="panel-card" shadow="never">
        <template #header>最近扫描</template>
        <div v-if="latestReport" class="latest-report">
          <div class="latest-report__title">
            <ElTag :type="reportComplete() ? 'success' : 'warning'">
              {{ reportComplete() ? '扫描完成' : '扫描未完成' }}
            </ElTag>
            <strong>
              {{ reportValue('project_name') }} /
              {{ reportValue('responsibility_name') }}
            </strong>
          </div>
          <div class="latest-report__meta">
            <span>工具：{{ reportValue('tool_name') }}</span>
            <span>问题：{{ reportValue('finding_count') }}</span>
            <span>时间：{{ reportValue('created_at') }}</span>
          </div>
        </div>
        <ElEmpty v-else description="暂无扫描报告" :image-size="48" />
      </ElCard>
    </div>
  </section>
</template>

<style scoped>
.dashboard-panel {
  min-height: 100%;
}

.panel-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.panel-toolbar h2 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 18px;
  font-weight: 600;
}

.panel-toolbar p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.toolbar-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.toolbar-filters .el-select {
  width: 180px;
}

.stat-grid,
.dashboard-grid {
  display: grid;
  gap: 12px;
  margin-bottom: 12px;
}

.stat-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-grid--three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.dashboard-grid--two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.metric-card,
.panel-card {
  border-color: var(--el-border-color-lighter);
}

.metric-card :deep(.el-card__body) {
  padding: 16px 18px;
}

.panel-card :deep(.el-card__header) {
  padding: 12px 16px;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
}

.panel-card :deep(.el-card__body) {
  min-height: 168px;
  padding: 8px 16px 14px;
}

.metric-row,
.trend-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.metric-row:last-child,
.trend-row:last-child {
  border-bottom: 0;
}

.metric-row strong,
.trend-row strong {
  margin-left: auto;
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.trend-row > span {
  width: 86px;
  flex: 0 0 86px;
}

.trend-bar-track {
  height: 6px;
  flex: 1;
  overflow: hidden;
  border-radius: 3px;
  background: var(--el-fill-color-light);
}

.trend-bar-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--el-color-primary);
}

.latest-report {
  padding: 10px 0;
}

.latest-report__title,
.latest-report__meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.latest-report__title strong {
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 500;
}

.latest-report__meta {
  margin-top: 18px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

@media (max-width: 1080px) {
  .stat-grid,
  .dashboard-grid--three {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .panel-toolbar,
  .latest-report__meta {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-filters .el-select {
    width: 100%;
  }

  .stat-grid,
  .dashboard-grid--two,
  .dashboard-grid--three {
    grid-template-columns: 1fr;
  }
}
</style>
