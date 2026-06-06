<script lang="ts" setup>
import type {
  OrganizationItem,
  RepositoryItem,
  RepositoryListParams,
} from '#/api/compliance/base';
import type { MissingMergeScanRunPayload } from '#/api/compliance/missing-merge';

import { computed, ref, watch } from 'vue';

import dayjs from 'dayjs';
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElMessage,
  ElTag,
} from 'element-plus';

import { listMissingMergeRepositoryOptionsApi } from '#/api/compliance/missing-merge';

import RepositorySelectorWorkbench from './RepositorySelectorWorkbench.vue';

const props = withDefaults(
  defineProps<{
    confirmLoading?: boolean;
    initialOrganizationId?: string;
    initialRepositories?: RepositoryItem[];
    modelValue: boolean;
    organizations?: OrganizationItem[];
  }>(),
  {
    confirmLoading: false,
    initialOrganizationId: '',
    initialRepositories: () => [],
    organizations: () => [],
  },
);

const emit = defineEmits<{
  (event: 'confirm', payload: MissingMergeScanRunPayload): void;
  (event: 'update:modelValue', value: boolean): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const selectedOrganizationId = ref('');
const selectedRepositories = ref<RepositoryItem[]>([]);
const timeRange = ref<string[]>([]);

const selectedRepositoryIds = computed(() =>
  selectedRepositories.value.map((item) => item.id),
);

const selectedOrganizationPath = computed(() =>
  findOrganizationPath(props.organizations, selectedOrganizationId.value),
);

const scopeSummary = computed(() => {
  if (selectedRepositories.value.length > 0) {
    return `将扫描：已选 ${selectedRepositories.value.length} 个代码库`;
  }
  if (selectedOrganizationPath.value.length > 0) {
    return `将扫描：${selectedOrganizationPath.value.map((item) => item.name).join(' / ')} 下全部代码库`;
  }
  return '将扫描：全部组织';
});

function formatApiTime(value = dayjs()) {
  return dayjs(value).format('YYYY-MM-DDTHH:mm:ssZ');
}

function resetDialog() {
  // 同步弹窗打开时带入当前列表筛选，并默认最近 1 天作为扫描窗口。
  const now = dayjs();
  timeRange.value = [
    formatApiTime(now.subtract(1, 'day')),
    formatApiTime(now),
  ];
  selectedOrganizationId.value = props.initialOrganizationId || '';
  selectedRepositories.value = [...props.initialRepositories];
}

function findOrganizationPath(
  nodes: OrganizationItem[],
  id: string,
  parents: OrganizationItem[] = [],
): OrganizationItem[] {
  // 只用于底部范围摘要，不影响选择器里的组织树导航。
  if (!id) return [];
  for (const node of nodes) {
    const path = [...parents, node];
    if (node.id === id) return path;
    const childPath = findOrganizationPath(node.children || [], id, path);
    if (childPath.length > 0) return childPath;
  }
  return [];
}

function loadOrganizations() {
  return Promise.resolve(props.organizations);
}

function loadRepositories(params: RepositoryListParams) {
  return listMissingMergeRepositoryOptionsApi(params);
}

function confirmScan() {
  if (timeRange.value.length !== 2) {
    ElMessage.warning('请选择扫描时间范围');
    return;
  }
  const [mergedAfter, mergedBefore] = timeRange.value;
  emit('confirm', {
    merged_after: mergedAfter!,
    merged_before: mergedBefore!,
    organization_id: selectedRepositoryIds.value.length
      ? undefined
      : selectedOrganizationId.value || undefined,
    repository_ids: selectedRepositoryIds.value.length
      ? selectedRepositoryIds.value
      : undefined,
  });
}

watch(
  () => props.modelValue,
  (show) => {
    if (show) resetDialog();
  },
);
</script>

<template>
  <ElDialog
    v-model="visible"
    append-to-body
    class="missing-merge-scan-dialog"
    destroy-on-close
    top="3vh"
    width="min(1180px, calc(100vw - 32px))"
    :close-on-click-modal="false"
  >
    <template #header>
      <div class="scan-title">
        <div>
          <div class="scan-title__main">手动同步漏合数据</div>
          <div class="scan-title__sub">选择 CR 合入时间窗口，并限定本次扫描的组织或代码库范围。</div>
        </div>
        <ElTag effect="light" type="primary">{{ scopeSummary }}</ElTag>
      </div>
    </template>

    <ElForm class="scan-form" label-width="92px">
      <ElFormItem label="时间范围" required>
        <ElDatePicker
          v-model="timeRange"
          class="scan-time-range"
          end-placeholder="合入结束"
          range-separator="至"
          start-placeholder="合入开始"
          type="datetimerange"
          value-format="YYYY-MM-DDTHH:mm:ssZ"
        />
      </ElFormItem>
    </ElForm>

    <RepositorySelectorWorkbench
      v-model:selected-organization-id="selectedOrganizationId"
      v-model:selected-repositories="selectedRepositories"
      candidate-empty-description="可直接同步全部组织，或先选择组织 / 输入关键词限定代码库"
      height="560px"
      :load-organizations="loadOrganizations"
      :load-repositories="loadRepositories"
      selected-title="本次同步代码库"
    />

    <template #footer>
      <div class="scan-footer">
        <span>{{ scopeSummary }}</span>
        <div>
          <ElButton @click="visible = false">取消</ElButton>
          <ElButton
            type="primary"
            :loading="confirmLoading"
            @click="confirmScan"
          >
            开始同步
          </ElButton>
        </div>
      </div>
    </template>
  </ElDialog>
</template>

<style scoped lang="less">
.scan-title,
.scan-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.scan-title__main {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.scan-title__sub,
.scan-footer {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.scan-form {
  padding: 12px 12px 0;
  margin-bottom: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-extra-light);
}

.scan-time-range {
  width: min(520px, 100%);
}

@media (max-width: 760px) {
  .scan-title,
  .scan-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
