<script setup lang="ts">
import type {
  DomainMetricHistoryDetail,
  DomainMetricIssue,
} from '#/api/integration-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, nextTick, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElLink,
  ElMessage,
  ElTabPane,
  ElTabs,
} from 'element-plus';

import { getDomainMetricHistoryDetailsApi } from '#/api/integration-report';
import { useZqTable } from '#/components/zq-table';

export interface DomainMetricDetailContext {
  configId: string;
  configName: string;
  metricKey: string;
  projectName: string;
  recordDate: string;
}

const props = defineProps<{
  context?: DomainMetricDetailContext;
  modelValue: boolean;
}>();

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>();

const detail = ref<DomainMetricHistoryDetail>();
const activeDomainName = ref('');
const loading = ref(false);
const loadError = ref('');
let requestId = 0;

const activeDomain = computed(() =>
  detail.value?.domains.find(
    (domain) => domain.domain_name === activeDomainName.value,
  ),
);

const title = computed(() => {
  const context = props.context;
  return context ? `${context.configName} · 领域问题详情` : '领域问题详情';
});

const [Grid, gridApi] = useZqTable<DomainMetricIssue>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: [
      {
        key: 'expand',
        type: 'expand',
        width: 46,
        fixed: 'left',
        slots: { default: 'expand_content' },
      },
      {
        key: 'task_id',
        prop: 'task_id',
        title: '任务 ID',
        width: 160,
        slots: { default: 'task_id_default' },
      },
      {
        key: 'directory',
        prop: 'directory',
        title: '目录',
        minWidth: 180,
        slots: { default: 'directory_default' },
      },
      {
        key: 'file_path',
        prop: 'file_path',
        title: '文件',
        minWidth: 280,
        slots: { default: 'file_default' },
      },
      {
        key: 'function_name',
        prop: 'function_name',
        title: '函数',
        minWidth: 170,
        slots: { default: 'function_default' },
      },
      {
        align: 'right',
        key: 'line_num',
        prop: 'line_num',
        title: '行号',
        width: 84,
      },
      {
        key: 'description',
        prop: 'description',
        title: '问题描述',
        minWidth: 280,
        slots: { default: 'description_default' },
      },
      {
        key: 'code_context',
        prop: 'code_context',
        title: '代码上下文',
        minWidth: 220,
        slots: { default: 'code_context_default' },
      },
    ],
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [20, 50, 100],
    },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          const issues = activeDomain.value?.issues || [];
          const start = (page.currentPage - 1) * page.pageSize;
          return {
            items: issues.slice(start, start + page.pageSize),
            total: issues.length,
          };
        },
      },
    },
    stripe: true,
  } as ZqTableGridOptions<DomainMetricIssue>,
});

function resetContent() {
  requestId += 1;
  detail.value = undefined;
  activeDomainName.value = '';
  loadError.value = '';
  gridApi.pagination.currentPage = 1;
}

async function reloadDomainTable(resetPage = false) {
  if (resetPage) gridApi.pagination.currentPage = 1;
  await nextTick();
  await gridApi.reload();
}

async function loadDetails() {
  const context = props.context;
  if (!context) return;

  const currentRequestId = ++requestId;
  loading.value = true;
  loadError.value = '';
  detail.value = undefined;
  activeDomainName.value = '';
  try {
    const result = await getDomainMetricHistoryDetailsApi({
      config_id: context.configId,
      metric_key: context.metricKey,
      record_date: context.recordDate,
    });
    if (currentRequestId !== requestId || !props.modelValue) return;
    detail.value = result;
    activeDomainName.value = result.domains[0]?.domain_name || '';
    await reloadDomainTable(true);
  } catch (error) {
    if (currentRequestId === requestId) {
      loadError.value =
        error instanceof Error ? error.message : '领域问题详情加载失败';
      ElMessage.error(loadError.value);
    }
  } finally {
    if (currentRequestId === requestId) loading.value = false;
  }
}

async function changeDomain(domainName: number | string) {
  activeDomainName.value = `${domainName}`;
  await reloadDomainTable(true);
}

watch(
  () => [
    props.modelValue,
    props.context?.configId,
    props.context?.metricKey,
    props.context?.recordDate,
  ],
  ([visible]) => {
    if (visible) {
      void loadDetails();
      return;
    }
    loading.value = false;
    resetContent();
  },
);
</script>

<template>
  <ElDialog
    :model-value="modelValue"
    :title="title"
    width="min(1080px, 94vw)"
    append-to-body
    class="domain-metric-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-loading="loading" class="domain-metric-dialog__content">
      <template v-if="detail">
        <section class="domain-metric-dialog__summary">
          <div class="domain-metric-dialog__summary-main">
            <span class="domain-metric-dialog__metric">{{
              detail.metric_name
            }}</span>
            <span class="domain-metric-dialog__separator">/</span>
            <span>{{ detail.project_name || '未关联项目' }}</span>
            <span class="domain-metric-dialog__separator">/</span>
            <span>{{ detail.record_date }}</span>
          </div>
          <div class="domain-metric-dialog__summary-count">
            <span>目录问题总数</span>
            <strong>{{ detail.issue_count }}</strong>
          </div>
          <ElButton
            :loading="loading"
            circle
            plain
            title="重新读取已采集明细"
            @click="loadDetails"
          >
            <IconifyIcon icon="lucide:refresh-cw" />
          </ElButton>
        </section>

        <div class="domain-metric-dialog__set-name">
          责任田目录配置：{{ detail.domain_directory_set_name }}
        </div>

        <ElTabs
          :model-value="activeDomainName"
          class="domain-metric-dialog__tabs"
          @update:model-value="changeDomain"
        >
          <ElTabPane
            v-for="domain in detail.domains"
            :key="domain.domain_name"
            :label="`${domain.domain_name} (${domain.issue_count})`"
            :name="domain.domain_name"
          />
        </ElTabs>

        <Grid
          v-if="detail.domains.length > 0"
          class="domain-metric-dialog__grid"
        >
          <template #task_id_default="{ row }">
            <ElLink
              :href="row.task_detail_url"
              :underline="false"
              target="_blank"
              type="primary"
            >
              <code class="domain-metric-dialog__task-id">{{
                row.task_id
              }}</code>
              <IconifyIcon icon="lucide:external-link" />
            </ElLink>
          </template>

          <template #directory_default="{ row }">
            <code class="domain-metric-dialog__directory">{{
              row.directory
            }}</code>
          </template>

          <template #file_default="{ row }">
            <div class="domain-metric-dialog__file">
              <span>{{ row.file_name || '-' }}</span>
              <code>{{ row.file_path || '-' }}</code>
            </div>
          </template>

          <template #function_default="{ row }">
            <code class="domain-metric-dialog__function">{{
              row.function_name || '-'
            }}</code>
          </template>

          <template #description_default="{ row }">
            <span class="domain-metric-dialog__description">{{
              row.description || '-'
            }}</span>
          </template>

          <template #code_context_default="{ row }">
            <code class="domain-metric-dialog__code-preview">{{
              row.code_context || '-'
            }}</code>
          </template>

          <template #expand_content="{ row }">
            <div class="domain-metric-dialog__expanded-code">
              <div class="domain-metric-dialog__code-title">
                {{
                  row.code_context_start_line
                    ? `从第 ${row.code_context_start_line} 行开始`
                    : '代码上下文'
                }}
              </div>
              <pre class="domain-metric-dialog__code-context">{{
                row.code_context || '-'
              }}</pre>
            </div>
          </template>
        </Grid>
        <div v-else class="domain-metric-dialog__empty">
          <ElEmpty description="当前领域配置没有可展示的目录" />
        </div>
      </template>

      <div v-else-if="!loading" class="domain-metric-dialog__empty">
        <ElEmpty :description="loadError || '当前领域配置没有可展示的问题'">
          <ElButton v-if="loadError" plain type="primary" @click="loadDetails">
            重试
          </ElButton>
        </ElEmpty>
      </div>
      <div v-else class="domain-metric-dialog__loading-space"></div>
    </div>
  </ElDialog>
</template>

<style scoped>
.domain-metric-dialog__content {
  display: flex;
  min-height: 430px;
  flex-direction: column;
}

.domain-metric-dialog__summary {
  display: flex;
  min-height: 54px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding: 0 2px 12px;
}

.domain-metric-dialog__summary-main {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.domain-metric-dialog__metric {
  color: var(--el-text-color-primary);
  font-weight: 650;
}

.domain-metric-dialog__separator,
.domain-metric-dialog__set-name {
  color: var(--el-text-color-secondary);
}

.domain-metric-dialog__summary-count {
  display: flex;
  flex: 0 0 auto;
  align-items: baseline;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.domain-metric-dialog__summary-count strong {
  color: var(--el-color-danger);
  font-size: 22px;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.domain-metric-dialog__set-name {
  padding: 10px 2px 2px;
  font-size: 12px;
}

.domain-metric-dialog__tabs {
  margin-bottom: 4px;
}

.domain-metric-dialog__tabs :deep(.el-tabs__header) {
  margin: 8px 0;
}

.domain-metric-dialog__grid {
  height: 348px;
}

.domain-metric-dialog__directory {
  color: var(--el-text-color-primary);
  font-family: var(--el-font-family-monospace);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.domain-metric-dialog__task-id,
.domain-metric-dialog__function {
  color: var(--el-text-color-regular);
  font-family: var(--el-font-family-monospace);
  font-size: 12px;
}

.domain-metric-dialog__grid :deep(.el-link) {
  gap: 4px;
}

.domain-metric-dialog__file {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.domain-metric-dialog__file code,
.domain-metric-dialog__description {
  color: var(--el-text-color-secondary);
  font-family: var(--el-font-family-monospace);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.domain-metric-dialog__code-title {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 8px;
}

.domain-metric-dialog__code-preview {
  display: block;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-family: var(--el-font-family-monospace);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.domain-metric-dialog__expanded-code {
  background: var(--el-fill-color-lighter);
  padding: 12px 16px;
}

.domain-metric-dialog__code-context {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font-family: var(--el-font-family-monospace);
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
  max-height: 360px;
  overflow: auto;
  padding: 10px;
  white-space: pre-wrap;
}

.domain-metric-dialog__empty,
.domain-metric-dialog__loading-space {
  display: flex;
  flex: 1;
  min-height: 320px;
  align-items: center;
  justify-content: center;
}

@media (max-width: 640px) {
  .domain-metric-dialog__summary {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .domain-metric-dialog__summary-main {
    flex-wrap: wrap;
  }

  .domain-metric-dialog__grid {
    height: 360px;
  }
}
</style>
