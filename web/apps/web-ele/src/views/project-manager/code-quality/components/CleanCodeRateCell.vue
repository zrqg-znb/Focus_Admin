<script lang="ts" setup>
import { computed } from 'vue';

import { ElTooltip } from 'element-plus';

interface Props {
  rate?: number;
  reasonText?: string;
}

const props = withDefaults(defineProps<Props>(), {
  rate: 0,
  reasonText: '',
});

const displayRate = computed(
  () => `${(Number(props.rate || 0) * 100).toFixed(2)}%`,
);
const hasReason = computed(
  () =>
    Number(props.rate || 0) < 1 &&
    !!props.reasonText &&
    props.reasonText !== '-',
);
const reasonList = computed(() =>
  String(props.reasonText || '')
    .split('；')
    .map((item) => item.trim())
    .filter(Boolean),
);
</script>

<template>
  <ElTooltip
    v-if="hasReason"
    effect="light"
    popper-class="pm-clean-code-tooltip"
    placement="top-start"
  >
    <template #content>
      <div class="pm-clean-code-tooltip-content">
        <div class="pm-clean-code-tooltip-title">未达标原因</div>
        <ul class="pm-clean-code-tooltip-list">
          <li v-for="(item, index) in reasonList" :key="`${index}-${item}`">
            {{ item }}
          </li>
        </ul>
      </div>
    </template>
    <span class="cursor-help">{{ displayRate }}</span>
  </ElTooltip>
  <span v-else>{{ displayRate }}</span>
</template>

<style scoped>
:deep(.pm-clean-code-tooltip.el-popper.is-light) {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  box-shadow: 0 10px 26px rgb(15 23 42 / 16%);
  color: var(--el-text-color-primary);
  max-width: 360px;
  padding: 10px 12px;
}

:deep(.pm-clean-code-tooltip.el-popper .el-popper__arrow::before) {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
}

.pm-clean-code-tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  line-height: 1.45;
}

.pm-clean-code-tooltip-title {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
}

.pm-clean-code-tooltip-list {
  color: var(--el-text-color-regular);
  font-size: 12px;
  margin: 0;
  max-height: 240px;
  overflow: auto;
  padding-left: 16px;
}

.pm-clean-code-tooltip-list li + li {
  margin-top: 2px;
}
</style>
