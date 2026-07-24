<script lang="ts" setup>
import { computed, ref, watch } from 'vue';

import { Filter } from '@element-plus/icons-vue';
import { ElButton, ElIcon, ElInput, ElPopover } from 'element-plus';

const props = withDefaults(
  defineProps<{
    label: string;
    modelValue?: string;
    placeholder?: string;
  }>(),
  {
    modelValue: '',
    placeholder: '输入关键词',
  },
);

const emit = defineEmits<{
  apply: [];
  clear: [];
  'update:modelValue': [value: string];
}>();

const visible = ref(false);
const localValue = ref(props.modelValue);
const isActive = computed(() => Boolean(props.modelValue.trim()));

watch(
  () => props.modelValue,
  (value) => {
    localValue.value = value;
  },
);

function applyFilter() {
  emit('update:modelValue', localValue.value.trim());
  emit('apply');
  visible.value = false;
}

function clearFilter() {
  localValue.value = '';
  emit('update:modelValue', '');
  emit('clear');
  visible.value = false;
}
</script>

<template>
  <span class="case-header-filter" @click.stop>
    <span class="case-header-filter__label">{{ label }}</span>
    <ElPopover
      v-model:visible="visible"
      placement="bottom"
      :width="240"
      trigger="click"
    >
      <template #reference>
        <ElButton
          aria-label="关键词筛选"
          link
          class="case-header-filter__button"
          :class="{ 'is-active': isActive }"
        >
          <ElIcon><Filter /></ElIcon>
        </ElButton>
      </template>

      <div class="case-header-filter__panel">
        <ElInput
          v-model="localValue"
          clearable
          :placeholder="placeholder"
          @change="applyFilter"
          @clear="clearFilter"
          @keyup.enter="applyFilter"
        />
        <div class="case-header-filter__actions">
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
.case-header-filter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
}

.case-header-filter__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-header-filter__button {
  width: 22px;
  height: 22px;
  padding: 0;
  color: var(--el-text-color-secondary);
}

.case-header-filter__button.is-active {
  color: var(--el-color-primary);
}

.case-header-filter__panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.case-header-filter__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
