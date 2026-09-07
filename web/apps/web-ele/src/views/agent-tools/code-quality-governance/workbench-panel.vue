<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script lang="ts" setup>
import type { WorkbenchSummary } from '#/api/agent-tools/code-quality-governance';

import { onMounted, ref } from 'vue';

import { ElButton, ElCard, ElEmpty, ElStatistic, ElTag } from 'element-plus';

import { getWorkbenchSummaryApi } from '#/api/agent-tools/code-quality-governance';

const data = ref<WorkbenchSummary>();
const loading = ref(false);

const metrics: {
  key:
    | 'link_count'
    | 'normal_count'
    | 'pending_application_count'
    | 'project_count'
    | 'responsibility_count'
    | 'shielded_count';
  label: string;
  tone?: 'danger' | 'warning';
}[] = [
  { key: 'project_count', label: '治理项目' },
  { key: 'responsibility_count', label: '责任田' },
  { key: 'link_count', label: '已建立关联' },
  { key: 'normal_count', label: '待治理问题', tone: 'danger' },
  {
    key: 'pending_application_count',
    label: '待审批申请',
    tone: 'warning',
  },
  { key: 'shielded_count', label: '已屏蔽问题' },
] as const;

async function load() {
  loading.value = true;
  try {
    data.value = await getWorkbenchSummaryApi();
  } finally {
    loading.value = false;
  }
}

function reportStatus(report: Record<string, unknown>) {
  if (report.complete === false) {
    return '扫描未完成';
  }
  if (report.status === 'failed') {
    return '解析失败';
  }
  return '成功';
}

function metricValue(key: (typeof metrics)[number]['key']) {
  return data.value?.[key] ?? 0;
}

onMounted(load);
</script>

<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<template>
  <section class="workbench" v-loading="loading">
    <header class="page-heading">
      <div>
        <span class="eyebrow">QUALITY GOVERNANCE</span>
        <h2>治理工作台</h2>
        <p>先处理高风险问题和审批待办，再进入具体治理范围。</p>
      </div>
      <ElButton :loading="loading" @click="load">刷新数据</ElButton>
    </header>

    <div class="metric-grid">
      <ElCard
        v-for="metric in metrics"
        :key="metric.key"
        shadow="never"
        class="metric-card"
        :class="metric.tone"
      >
        <ElStatistic :title="metric.label" :value="metricValue(metric.key)" />
      </ElCard>
    </div>

    <div class="workbench-grid">
      <ElCard shadow="never" class="work-card">
        <template #header>
          <div class="card-title">
            <span>我的审批待办</span>
            <ElTag v-if="data" type="warning">{{ data.my_todo_count }}</ElTag>
          </div>
        </template>
        <div v-if="data?.my_todos.length" class="todo-list">
          <div v-for="todo in data.my_todos" :key="todo.id" class="todo-row">
            <div>
              <b>{{ todo.project_name }} / {{ todo.responsibility_name }}</b>
              <span>{{ todo.file_path }} · {{ todo.rule_id }}</span>
            </div>
            <ElTag
              :type="
                todo.severity === 'blocker' || todo.severity === 'critical'
                  ? 'danger'
                  : 'warning'
              "
            >
              {{ todo.severity }}
            </ElTag>
          </div>
        </div>
        <ElEmpty v-else description="暂无待审批事项" :image-size="56" />
      </ElCard>

      <ElCard shadow="never" class="work-card">
        <template #header>高风险项目</template>
        <div v-if="data?.risk_projects.length" class="rank-list">
          <div
            v-for="(row, index) in data.risk_projects"
            :key="row.name"
            class="rank-row"
          >
            <i>{{ index + 1 }}</i>
            <span>{{ row.name }}</span>
            <strong>{{ row.count }}</strong>
          </div>
        </div>
        <ElEmpty v-else description="暂无风险项目" :image-size="56" />
      </ElCard>

      <ElCard shadow="never" class="work-card">
        <template #header>扫描异常与未完成</template>
        <div v-if="data?.scan_exceptions.length" class="exception-list">
          <div
            v-for="report in data.scan_exceptions"
            :key="String(report.id)"
            class="exception-row"
          >
            <div>
              <b
                >{{ report.project_name }} / {{ report.responsibility_name }}</b
              >
              <span
                >{{ report.tool_name }} ·
                {{ report.error_message || '扫描结果未完成' }}</span
              >
            </div>
            <ElTag type="danger">{{ reportStatus(report) }}</ElTag>
          </div>
        </div>
        <ElEmpty v-else description="扫描运行正常" :image-size="56" />
      </ElCard>
    </div>
  </section>
</template>

<style scoped>
.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.eyebrow {
  color: var(--el-color-primary);
  font-size: 11px;
  letter-spacing: 0.12em;
}

h2 {
  margin: 5px 0 0;
  color: var(--el-text-color-primary);
  font-size: 22px;
}

.page-heading p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.metric-card,
.work-card {
  border-color: var(--el-border-color-lighter);
}

.metric-card :deep(.el-card__body) {
  padding: 15px 16px;
}

.metric-card.danger :deep(.el-statistic__number) {
  color: var(--el-color-danger);
}

.metric-card.warning :deep(.el-statistic__number) {
  color: var(--el-color-warning-dark);
}

.workbench-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr;
  gap: 12px;
}

.work-card {
  min-height: 270px;
}

.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.todo-list,
.rank-list,
.exception-list {
  display: grid;
  gap: 2px;
}

.todo-row,
.exception-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.todo-row > div,
.exception-row > div {
  display: grid;
  min-width: 0;
  gap: 4px;
}

b {
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-row span,
.exception-row span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.rank-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.rank-row i {
  width: 20px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-style: normal;
  text-align: center;
}

.rank-row strong {
  margin-left: auto;
  color: var(--el-text-color-primary);
}

@media (max-width: 1100px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .workbench-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .page-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .metric-grid,
  .workbench-grid {
    grid-template-columns: 1fr;
  }
}
</style>
