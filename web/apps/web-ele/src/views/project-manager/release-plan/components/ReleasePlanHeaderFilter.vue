<script lang="ts" setup>
import { computed, ref, watch } from 'vue';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElDatePicker,
  ElIcon,
  ElInput,
  ElOption,
  ElPopover,
  ElSelect,
} from 'element-plus';

type HeaderFilterType = 'date-range' | 'select-create' | 'text';
type FilterValue = string | string[] | undefined;

const props = withDefaults(
  defineProps<{
    label: string;
    modelValue?: FilterValue;
    options?: { label: string; value: string }[];
    placeholder?: string;
    type?: HeaderFilterType;
  }>(),
  {
    modelValue: '',
    options: () => [],
    placeholder: '',
    type: 'text',
  },
);

const emit = defineEmits<{
  apply: [value: FilterValue];
  clear: [];
  'update:modelValue': [value: FilterValue];
}>();

const opened = ref(false);
const localValue = ref<FilterValue>(props.modelValue);
const textValue = computed({
  get: () => (Array.isArray(localValue.value) ? '' : localValue.value || ''),
  set: (value: string) => {
    localValue.value = value;
  },
});
const dateValue = computed({
  get: () => (Array.isArray(localValue.value) ? localValue.value : []),
  set: (value: string[]) => {
    localValue.value = value;
  },
});

const isActive = computed(() => {
  if (Array.isArray(props.modelValue)) {
    return props.modelValue.some(Boolean);
  }
  return Boolean(props.modelValue);
});

watch(
  () => props.modelValue,
  (value) => {
    localValue.value = Array.isArray(value) ? [...value] : value;
  },
);

function applyValue() {
  emit('update:modelValue', localValue.value);
  emit('apply', localValue.value);
  opened.value = false;
}

function clearValue() {
  localValue.value = props.type === 'date-range' ? [] : '';
  emit('update:modelValue', localValue.value);
  emit('clear');
  opened.value = false;
}
</script>

<template>
  <span class="release-header-filter">
    <span class="release-header-filter__label">{{ label }}</span>
    <ElPopover
      v-model:visible="opened"
      trigger="click"
      :width="type === 'date-range' ? 292 : 226"
      popper-class="release-header-filter-popper"
    >
      <template #reference>
        <ElButton
          link
          class="release-header-filter__button"
          :class="{ 'is-active': isActive }"
        >
          <ElIcon><Filter /></ElIcon>
        </ElButton>
      </template>

      <div class="release-header-filter__panel">
        <div class="release-header-filter__title">{{ label }}筛选</div>
        <ElDatePicker
          v-if="type === 'date-range'"
          v-model="dateValue"
          class="release-header-filter__control"
          end-placeholder="结束日期"
          start-placeholder="开始日期"
          type="daterange"
          value-format="YYYY-MM-DD"
          @change="applyValue"
        />
        <ElSelect
          v-else-if="type === 'select-create'"
          v-model="textValue"
          allow-create
          clearable
          default-first-option
          filterable
          :placeholder="placeholder || label"
          class="release-header-filter__control"
          @change="applyValue"
        >
          <ElOption
            v-for="item in options"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>
        <ElInput
          v-else
          v-model="textValue"
          clearable
          :placeholder="placeholder || label"
          class="release-header-filter__control"
          @keyup.enter="applyValue"
        />

        <div class="release-header-filter__footer">
          <button type="button" class="release-header-filter__action" @click="clearValue">
            清空
          </button>
          <button
            type="button"
            class="release-header-filter__action is-primary"
            @click="applyValue"
          >
            应用
          </button>
        </div>
      </div>
    </ElPopover>
  </span>
</template>

<style scoped>
.release-header-filter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
}

.release-header-filter__label {
  overflow: hidden;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.release-header-filter__button {
  width: 22px;
  height: 22px;
  padding: 0;
  color: #94a3b8;
}

.release-header-filter__button.is-active {
  border-radius: 6px;
  background: #e0f2fe;
  color: #0369a1;
}

.release-header-filter__panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.release-header-filter__title {
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.release-header-filter__control {
  width: 100%;
}

.release-header-filter__footer {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.release-header-filter__action {
  height: 26px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #fff;
  color: #475569;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  padding: 0 10px;
}

.release-header-filter__action.is-primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}
</style>

<style>
.release-header-filter-popper.el-popper {
  padding: 10px;
}
</style>
