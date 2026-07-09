<script lang="ts" setup>
import { computed, ref, watch } from 'vue';

import { Filter } from '@element-plus/icons-vue';
import { ElButton, ElIcon, ElPopover } from 'element-plus';

const props = withDefaults(
  defineProps<{
    active?: boolean;
    label: string;
    panelWidth?: number;
  }>(),
  {
    active: false,
    panelWidth: 280,
  },
);

const emit = defineEmits<{
  apply: [];
  clear: [];
}>();

const visible = ref(false);
const popoverWidth = computed(() => `${props.panelWidth}px`);

function applyFilter() {
  emit('apply');
  visible.value = false;
}

function clearFilter() {
  emit('clear');
  visible.value = false;
}

watch(
  () => visible.value,
  (nextVisible) => {
    // 打开筛选面板时由父层保持草稿值，当前组件只负责交互容器和视觉反馈。
    if (!nextVisible) return;
  },
);
</script>

<template>
  <span class="compliance-header-filter" @click.stop>
    <span class="compliance-header-filter__label">{{ label }}</span>
    <ElPopover
      v-model:visible="visible"
      placement="bottom"
      trigger="click"
      popper-class="compliance-header-filter-popper"
      :width="panelWidth"
    >
      <template #reference>
        <ElButton
          circle
          link
          size="small"
          class="compliance-header-filter__button"
          :class="{ 'is-active': active }"
          @click.stop
        >
          <ElIcon><Filter /></ElIcon>
        </ElButton>
      </template>

      <div class="compliance-header-filter__panel" :style="{ width: popoverWidth }">
        <div class="compliance-header-filter__title">{{ label }}</div>
        <slot />
        <div class="compliance-header-filter__footer">
          <ElButton size="small" @click="clearFilter">清空</ElButton>
          <ElButton size="small" type="primary" @click="applyFilter">
            应用
          </ElButton>
        </div>
      </div>
    </ElPopover>
  </span>
</template>

<style scoped lang="less">
.compliance-header-filter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
}

.compliance-header-filter__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compliance-header-filter__button {
  color: var(--el-text-color-secondary);
}

.compliance-header-filter__button.is-active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.compliance-header-filter__panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: min(420px, calc(100vw - 48px));
}

.compliance-header-filter__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.compliance-header-filter__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.compliance-header-filter__panel :deep(.el-cascader),
.compliance-header-filter__panel :deep(.el-date-editor),
.compliance-header-filter__panel :deep(.el-input),
.compliance-header-filter__panel :deep(.el-select) {
  width: 100%;
}
</style>
