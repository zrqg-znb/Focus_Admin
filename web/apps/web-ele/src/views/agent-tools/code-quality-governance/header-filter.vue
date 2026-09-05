<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script lang="ts" setup>
import { ref, watch } from 'vue';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElIcon,
  ElInput,
  ElPopover,
  ElRadio,
  ElRadioGroup,
} from 'element-plus';

export interface HeaderFilterOption {
  label: string;
  value: string;
}

const props = withDefaults(
  defineProps<{
    label: string;
    modelValue?: string;
    options?: HeaderFilterOption[];
    placeholder?: string;
  }>(),
  { modelValue: '', options: () => [], placeholder: '' },
);

const emit = defineEmits<{
  apply: [value: string];
  clear: [];
  'update:modelValue': [value: string];
}>();

const visible = ref(false);
const draft = ref(props.modelValue);

watch(
  () => visible.value,
  (nextVisible) => {
    if (nextVisible) draft.value = props.modelValue;
  },
);

function applyFilter() {
  emit('update:modelValue', draft.value);
  emit('apply', draft.value);
  visible.value = false;
}

function clearFilter() {
  draft.value = '';
  emit('update:modelValue', '');
  emit('clear');
  visible.value = false;
}
</script>

<template>
  <span class="header-filter" @click.stop>
    <span class="header-filter__label">{{ label }}</span>
    <ElPopover v-model:visible="visible" placement="bottom" :width="260">
      <template #reference>
        <ElButton
          circle
          link
          size="small"
          class="header-filter__button"
          :class="{ 'is-active': modelValue }"
          @click.stop
        >
          <ElIcon><Filter /></ElIcon>
        </ElButton>
      </template>
      <div class="header-filter__panel">
        <div class="header-filter__title">筛选{{ label }}</div>
        <ElRadioGroup
          v-if="options.length > 0"
          v-model="draft"
          class="header-filter__options"
        >
          <ElRadio
            v-for="option in options"
            :key="option.value"
            :label="option.value"
          >
            {{ option.label }}
          </ElRadio>
        </ElRadioGroup>
        <ElInput
          v-else
          v-model="draft"
          clearable
          :placeholder="placeholder || `请输入${label}`"
          @keyup.enter="applyFilter"
        />
        <div class="header-filter__footer">
          <ElButton size="small" @click="clearFilter">清空</ElButton>
          <ElButton size="small" type="primary" @click="applyFilter"
            >应用</ElButton
          >
        </div>
      </div>
    </ElPopover>
  </span>
</template>

<style scoped>
.header-filter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
}

.header-filter__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-filter__button {
  color: var(--el-text-color-secondary);
}

.header-filter__button.is-active {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.header-filter__panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-filter__title {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
}

.header-filter__options {
  display: flex;
  max-height: 240px;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  overflow-y: auto;
}

.header-filter__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
