<script lang="ts" setup>
import type {
  RequirementHeaderFilterConfig,
  RequirementHeaderFilterOption,
} from './requirement-header-filter';

import { computed, ref, watch } from 'vue';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElCheckbox,
  ElCheckboxGroup,
  ElDatePicker,
  ElIcon,
  ElInput,
  ElPopover,
  ElRadio,
  ElRadioGroup,
} from 'element-plus';

import { hasRequirementHeaderFilterValue } from './requirement-header-filter';

const props = withDefaults(
  defineProps<{
    config: RequirementHeaderFilterConfig;
    modelValue?: any;
    options?: RequirementHeaderFilterOption[];
  }>(),
  {
    modelValue: undefined,
    options: () => [],
  },
);

const emit = defineEmits<{
  apply: [value: any];
  clear: [];
}>();

const visible = ref(false);
const draft = ref<any>(undefined);
const popoverWidth = computed(() =>
  props.config.type === 'date-range' ? 280 : 260,
);

function cloneValue(value: any) {
  return Array.isArray(value) ? [...value] : value;
}

function setDraftRange(index: 0 | 1, value: string) {
  const nextValue = Array.isArray(draft.value) ? [...draft.value] : ['', ''];
  nextValue[index] = value;
  draft.value = nextValue[0] || nextValue[1] ? nextValue : [];
}

watch(
  () => visible.value,
  (nextVisible) => {
    if (nextVisible) {
      draft.value = cloneValue(props.modelValue);
      if (props.config.type === 'checkbox' && !Array.isArray(draft.value)) {
        draft.value = [];
      }
      if (props.config.type === 'date-range' && !Array.isArray(draft.value)) {
        draft.value = [];
      }
    }
  },
);

function applyFilter() {
  emit('apply', cloneValue(draft.value));
  visible.value = false;
}

function clearFilter() {
  draft.value = props.config.type === 'checkbox' ? [] : undefined;
  emit('clear');
  visible.value = false;
}
</script>

<template>
  <span class="requirement-header-filter-trigger">
    <span class="requirement-header-filter-trigger__label">
      {{ config.label }}
    </span>
    <ElPopover
      v-model:visible="visible"
      placement="bottom"
      popper-class="requirement-header-filter-popper"
      trigger="click"
      :width="popoverWidth"
    >
      <template #reference>
        <ElButton
          circle
          link
          size="small"
          :class="{ 'is-active': hasRequirementHeaderFilterValue(modelValue) }"
          class="requirement-header-filter-trigger__button"
          @click.stop
        >
          <ElIcon><Filter /></ElIcon>
        </ElButton>
      </template>

      <div class="requirement-header-filter-panel">
        <div class="requirement-header-filter-panel__title">
          {{ config.label }}
        </div>
        <ElCheckboxGroup
          v-if="config.type === 'checkbox'"
          v-model="draft"
          class="requirement-header-filter-panel__options"
        >
          <ElCheckbox
            v-for="item in options"
            :key="item.value"
            :label="item.value"
          >
            {{ item.label }}
          </ElCheckbox>
        </ElCheckboxGroup>
        <ElRadioGroup
          v-else-if="config.type === 'radio'"
          v-model="draft"
          class="requirement-header-filter-panel__options"
        >
          <ElRadio
            v-for="item in options"
            :key="item.value"
            :label="item.value"
          >
            {{ item.label }}
          </ElRadio>
        </ElRadioGroup>
        <div
          v-else-if="config.type === 'date-range'"
          class="requirement-header-filter-panel__date-stack"
        >
          <ElDatePicker
            class="w-full"
            placeholder="开始日期"
            type="date"
            :model-value="Array.isArray(draft) ? draft[0] : ''"
            value-format="YYYY-MM-DD"
            @update:model-value="(value) => setDraftRange(0, value)"
          />
          <ElDatePicker
            class="w-full"
            placeholder="结束日期"
            type="date"
            :model-value="Array.isArray(draft) ? draft[1] : ''"
            value-format="YYYY-MM-DD"
            @update:model-value="(value) => setDraftRange(1, value)"
          />
        </div>
        <ElInput
          v-else
          v-model="draft"
          clearable
          :placeholder="config.placeholder || `请输入${config.label}`"
          @keyup.enter="applyFilter"
        />
        <div class="requirement-header-filter-panel__footer">
          <ElButton size="small" @click="clearFilter">清空</ElButton>
          <ElButton size="small" type="primary" @click="applyFilter">
            应用
          </ElButton>
        </div>
      </div>
    </ElPopover>
  </span>
</template>

<style scoped>
.requirement-header-filter-trigger {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.requirement-header-filter-trigger__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.requirement-header-filter-trigger__button {
  color: var(--el-text-color-secondary);
}

.requirement-header-filter-trigger__button.is-active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.requirement-header-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.requirement-header-filter-panel__title {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
}

.requirement-header-filter-panel__options {
  display: flex;
  max-height: 240px;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
}

.requirement-header-filter-panel__options :deep(.el-checkbox),
.requirement-header-filter-panel__options :deep(.el-radio) {
  display: flex;
  width: 100%;
  height: auto;
  min-height: 24px;
  align-items: center;
  margin-right: 0;
  white-space: normal;
}

.requirement-header-filter-panel__options :deep(.el-checkbox__label),
.requirement-header-filter-panel__options :deep(.el-radio__label) {
  min-width: 0;
  line-height: 1.4;
  word-break: break-word;
}

.requirement-header-filter-panel__date-stack {
  display: grid;
  gap: 8px;
}

.requirement-header-filter-panel__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
