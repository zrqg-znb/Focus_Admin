<script lang="ts" setup>
import type {
  ComplianceBindMode,
  RepositoryItem,
} from '#/api/compliance/base';

import { computed, ref, watch } from 'vue';

import {
  ElButton,
  ElDialog,
  ElRadioButton,
  ElRadioGroup,
} from 'element-plus';

import RepositorySelectorWorkbench from './RepositorySelectorWorkbench.vue';

const BIND_MODE_OPTIONS: Array<{ label: string; value: ComplianceBindMode }> = [
  { label: '追加绑定', value: 'append' },
  { label: '替换绑定', value: 'replace' },
];

interface ConfirmPayload {
  mode: ComplianceBindMode;
  repository_ids: string[];
}

const props = withDefaults(
  defineProps<{
    confirmLoading?: boolean;
    modelValue: boolean;
  }>(),
  {
    confirmLoading: false,
  },
);

const emit = defineEmits<{
  (event: 'confirm', payload: ConfirmPayload): void;
  (event: 'update:modelValue', value: boolean): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const mode = ref<ComplianceBindMode>('append');
const selectedOrganizationId = ref('');
const selectedRepositories = ref<RepositoryItem[]>([]);

const selectedIds = computed(() =>
  selectedRepositories.value.map((item) => item.id),
);

function resetDialog() {
  // 绑定弹窗每次打开都从空选择开始，避免沿用上一次批量绑定范围。
  mode.value = 'append';
  selectedOrganizationId.value = '';
  selectedRepositories.value = [];
}

function confirmSelection() {
  emit('confirm', {
    mode: mode.value,
    repository_ids: selectedIds.value,
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
    class="compliance-bind-dialog"
    destroy-on-close
    top="4vh"
    width="min(1180px, calc(100vw - 32px))"
    :close-on-click-modal="false"
  >
    <template #header>
      <div class="bind-title">
        <div>
          <div class="bind-title__main">批量绑定代码库</div>
          <div class="bind-title__sub">先进入组织，再选择需要绑定到当前分支的代码库。</div>
        </div>
        <ElRadioGroup v-model="mode" class="bind-mode-switch">
          <ElRadioButton
            v-for="item in BIND_MODE_OPTIONS"
            :key="item.value"
            :label="item.value"
          >
            {{ item.label }}
          </ElRadioButton>
        </ElRadioGroup>
      </div>
    </template>

    <RepositorySelectorWorkbench
      v-model:selected-organization-id="selectedOrganizationId"
      v-model:selected-repositories="selectedRepositories"
    />

    <template #footer>
      <div class="bind-footer">
        <span>确认后将以当前绑定方式作用于已勾选分支。</span>
        <div>
          <ElButton @click="visible = false">取消</ElButton>
          <ElButton
            type="primary"
            :disabled="!selectedIds.length"
            :loading="confirmLoading"
            @click="confirmSelection"
          >
            确定绑定
          </ElButton>
        </div>
      </div>
    </template>
  </ElDialog>
</template>

<style scoped lang="less">
.bind-title,
.bind-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.bind-title__main {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.bind-title__sub,
.bind-footer {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
