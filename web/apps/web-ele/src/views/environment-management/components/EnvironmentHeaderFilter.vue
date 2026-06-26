<script lang="ts" setup>
import type {
  HeaderFilterConfig,
  HeaderFilterOption,
} from './header-filter';

import { computed, ref, watch } from 'vue';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElCascader,
  ElCheckbox,
  ElCheckboxGroup,
  ElDatePicker,
  ElIcon,
  ElInput,
  ElPopover,
  ElRadio,
  ElRadioGroup,
} from 'element-plus';

import { hasHeaderFilterValue } from './header-filter';

const props = withDefaults(
  defineProps<{
    config: HeaderFilterConfig;
    modelValue?: any;
    options?: HeaderFilterOption[];
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
const cascaderOptions = computed(() => props.options as any[]);

function cloneValue(value: any) {
  return Array.isArray(value) ? [...value] : value;
}

watch(
  () => visible.value,
  (nextVisible) => {
    if (nextVisible) {
      draft.value = cloneValue(props.modelValue);
      if (props.config.type === 'checkbox' && !Array.isArray(draft.value)) {
        draft.value = [];
      }
      if (props.config.type === 'cascader' && !Array.isArray(draft.value)) {
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
  draft.value = ['cascader', 'checkbox'].includes(props.config.type)
    ? []
    : undefined;
  emit('clear');
  visible.value = false;
}
</script>

<template>
  <span class="environment-header-filter">
    <span class="environment-header-filter__label">{{ config.label }}</span>
    <ElPopover
      v-model:visible="visible"
      placement="bottom"
      popper-class="environment-header-filter-popper"
      trigger="click"
      :width="config.type === 'date-range' || config.type === 'cascader' ? 320 : 260"
    >
      <template #reference>
        <ElButton
          circle
          link
          size="small"
          :class="{ 'is-active': hasHeaderFilterValue(modelValue) }"
          class="environment-header-filter__button"
          @click.stop
        >
          <ElIcon><Filter /></ElIcon>
        </ElButton>
      </template>

      <div class="environment-header-filter__panel">
        <div class="environment-header-filter__title">{{ config.label }}</div>
        <ElCheckboxGroup
          v-if="config.type === 'checkbox'"
          v-model="draft"
          class="environment-header-filter__options"
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
          class="environment-header-filter__options"
        >
          <ElRadio
            v-for="item in options"
            :key="item.value"
            :label="item.value"
          >
            {{ item.label }}
          </ElRadio>
        </ElRadioGroup>
        <ElDatePicker
          v-else-if="config.type === 'date-range'"
          v-model="draft"
          class="w-full"
          end-placeholder="结束时间"
          range-separator="至"
          start-placeholder="开始时间"
          type="datetimerange"
          value-format="YYYY-MM-DDTHH:mm:ssZ"
        />
        <ElCascader
          v-else-if="config.type === 'cascader'"
          v-model="draft"
          :options="cascaderOptions"
          :props="{
            multiple: true,
            emitPath: false,
            checkStrictly: false,
            value: 'value',
            label: 'label',
            children: 'children',
          }"
          class="w-full"
          clearable
          collapse-tags
          collapse-tags-tooltip
          filterable
          placeholder="请选择测试设备"
        />
        <ElInput
          v-else
          v-model="draft"
          clearable
          :placeholder="config.placeholder || `请输入${config.label}`"
          @keyup.enter="applyFilter"
        />
        <div class="environment-header-filter__footer">
          <ElButton size="small" @click="clearFilter">清空</ElButton>
          <ElButton size="small" type="primary" @click="applyFilter">应用</ElButton>
        </div>
      </div>
    </ElPopover>
  </span>
</template>

<style scoped>
.environment-header-filter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
}

.environment-header-filter__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.environment-header-filter__button {
  color: var(--el-text-color-secondary);
}

.environment-header-filter__button.is-active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.environment-header-filter__panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.environment-header-filter__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.environment-header-filter__options {
  display: flex;
  max-height: 240px;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
}

.environment-header-filter__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
