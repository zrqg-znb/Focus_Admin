<script lang="ts" setup>
import { computed } from 'vue';

import { InfoFilled } from '@element-plus/icons-vue';
import { ElIcon, ElPopover } from 'element-plus';

interface Props {
  label: string;
  definition?: string;
  formula?: string;
  editableHint?: string;
  placement?:
    | 'bottom'
    | 'bottom-end'
    | 'bottom-start'
    | 'left'
    | 'right'
    | 'top'
    | 'top-end'
    | 'top-start';
  width?: number;
}

const props = withDefaults(defineProps<Props>(), {
  definition: '',
  formula: '',
  editableHint: '',
  placement: 'top',
  width: 460,
});

const hasHelpContent = computed(() => {
  return Boolean(props.definition || props.formula || props.editableHint);
});
</script>

<template>
  <span class="zq-table-header-help">
    <span class="zq-table-header-help__label">{{ label }}</span>
    <ElPopover
      v-if="hasHelpContent"
      :width="width"
      :placement="placement"
      trigger="hover"
      popper-class="zq-table-header-help-popper"
      :show-arrow="false"
    >
      <template #reference>
        <span class="zq-table-header-help__icon-wrap">
          <ElIcon class="zq-table-header-help__icon">
            <InfoFilled />
          </ElIcon>
        </span>
      </template>
      <div class="zq-table-header-help__panel">
        <div v-if="definition" class="zq-table-header-help__row">
          <div class="zq-table-header-help__title">指标定义</div>
          <div class="zq-table-header-help__text">{{ definition }}</div>
        </div>
        <div v-if="formula" class="zq-table-header-help__row">
          <div class="zq-table-header-help__title">计算规则</div>
          <div class="zq-table-header-help__text">{{ formula }}</div>
        </div>
        <div v-if="editableHint" class="zq-table-header-help__row">
          <div class="zq-table-header-help__title">编辑说明</div>
          <div class="zq-table-header-help__text">
            <span class="zq-table-header-help__hint">{{ editableHint }}</span>
          </div>
        </div>
      </div>
    </ElPopover>
  </span>
</template>

<style scoped>
.zq-table-header-help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.zq-table-header-help__label {
  font-weight: 500;
  line-height: 1;
}

.zq-table-header-help__icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.2s ease;
}

.zq-table-header-help__icon-wrap:hover {
  color: hsl(var(--primary));
  background-color: hsl(var(--accent));
}

.zq-table-header-help__icon {
  font-size: 13px;
}

.zq-table-header-help__panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px 4px;
}

.zq-table-header-help__row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.zq-table-header-help__title {
  flex-shrink: 0;
  width: 60px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.6;
  color: hsl(var(--foreground));
}

.zq-table-header-help__text {
  flex: 1;
  font-size: 12px;
  line-height: 1.6;
  color: hsl(var(--muted-foreground));
  text-align: left;
}

.zq-table-header-help__hint {
  display: inline-flex;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
  color: hsl(var(--primary));
  background-color: hsl(var(--accent));
}
</style>

<style>
.zq-table-header-help-popper.el-popper {
  border: 1px solid hsl(var(--border)) !important;
  border-radius: 12px !important;
  background: hsl(var(--background)) !important;
  box-shadow: 0 10px 30px rgb(0 0 0 / 10%) !important;
}
</style>
