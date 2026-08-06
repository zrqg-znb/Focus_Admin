<script setup lang="ts">
import type {
  DomainMetricDirectoryDetail,
  DomainMetricHistoryDetail,
} from '#/api/integration-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, nextTick, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import {
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

const [Grid, gridApi] = useZqTable<DomainMetricDirectoryDetail>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: [
      {
        key: 'directory',
        prop: 'directory',
        title: '目录',
        minWidth: 320,
        slots: { default: 'directory_default' },
      },
      {
        align: 'right',
        key: 'issue_count',
        prop: 'issue_count',
        title: '问题数',
        width: 112,
        slots: { default: 'issue_count_default' },
      },
      {
        key: 'task_details',
        prop: 'task_details',
        title: '任务 ID',
        minWidth: 200,
        slots: { default: 'task_ids_default' },
      },
      {
        key: 'detail',
        prop: 'detail',
        title: '问题详情',
        minWidth: 210,
        slots: { default: 'detail_default' },
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
          const directories = activeDomain.value?.directories || [];
          const start = (page.currentPage - 1) * page.pageSize;
          return {
            items: directories.slice(start, start + page.pageSize),
            total: directories.length,
          };
        },
      },
    },
    stripe: true,
  } as ZqTableGridOptions<DomainMetricDirectoryDetail>,
});

function resetContent() {
  requestId += 1;
  detail.value = undefined;
  activeDomainName.value = '';
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
  } catch {
    if (currentRequestId === requestId) {
      ElMessage.error('领域问题详情加载失败');
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
          <template #directory_default="{ row }">
            <code class="domain-metric-dialog__directory">{{
              row.directory
            }}</code>
          </template>

          <template #issue_count_default="{ row }">
            <span class="domain-metric-dialog__issue-count">{{
              row.issue_count
            }}</span>
          </template>

          <template #task_ids_default="{ row }">
            <div class="domain-metric-dialog__task-list">
              <span
                v-for="task in row.task_details"
                :key="task.task_id"
                class="domain-metric-dialog__task-id"
              >
                {{ task.task_id }} · {{ task.issue_count }}
              </span>
              <span v-if="row.task_details.length === 0">-</span>
            </div>
          </template>

          <template #detail_default="{ row }">
            <div class="domain-metric-dialog__detail-links">
              <ElLink
                v-for="task in row.task_details"
                :key="task.task_id"
                :href="task.detail_url"
                :underline="false"
                target="_blank"
                type="primary"
              >
                {{ task.task_id }}
                <IconifyIcon icon="lucide:external-link" />
              </ElLink>
              <span v-if="row.task_details.length === 0">-</span>
            </div>
          </template>
        </Grid>
        <div v-else class="domain-metric-dialog__empty">
          <ElEmpty description="当前领域配置没有可展示的目录" />
        </div>
      </template>

      <div v-else-if="!loading" class="domain-metric-dialog__empty">
        <ElEmpty description="当前领域配置没有可展示的目录" />
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

.domain-metric-dialog__issue-count {
  color: var(--el-color-danger);
  font-variant-numeric: tabular-nums;
  font-weight: 650;
}

.domain-metric-dialog__task-list,
.domain-metric-dialog__detail-links {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  min-width: 0;
}

.domain-metric-dialog__task-id {
  color: var(--el-text-color-regular);
  font-family: var(--el-font-family-monospace);
  font-size: 12px;
}

.domain-metric-dialog__detail-links :deep(.el-link) {
  gap: 3px;
  font-family: var(--el-font-family-monospace);
  font-size: 12px;
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
