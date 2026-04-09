<script lang="ts" setup>
import { computed, ref, watch } from 'vue';

import { Delete, Plus } from '@element-plus/icons-vue';
import { ElButton, ElEmpty, ElInput } from 'element-plus';

import { normalizeStringList } from '../data';

interface DraftItem {
  key: number;
  value: string;
}

const props = withDefaults(
  defineProps<{
    addButtonPlacement?: 'footer' | 'header';
    addText?: string;
    bodyMaxHeight?: string;
    description?: string;
    disabled?: boolean;
    itemLabel?: string;
    label: string;
    modelValue?: string[];
    placeholder?: string;
    scrollable?: boolean;
  }>(),
  {
    addText: '新增一项',
    addButtonPlacement: 'header',
    bodyMaxHeight: '',
    description: '',
    disabled: false,
    itemLabel: '条目',
    modelValue: () => [],
    placeholder: '请输入内容',
    scrollable: false,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string[]];
}>();

let sequence = 0;
const draftItems = ref<DraftItem[]>([]);

function createDraft(value = ''): DraftItem {
  sequence += 1;
  return { key: sequence, value };
}

function buildNormalized(values: DraftItem[]) {
  return normalizeStringList(values.map((item) => item.value));
}

function arraysEqual(left: string[], right: string[]) {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((item, index) => item === right[index]);
}

function syncDraftsFromModel(values: string[]) {
  const next = normalizeStringList(values);
  const current = buildNormalized(draftItems.value);
  if (arraysEqual(current, next) && draftItems.value.length > 0) {
    return;
  }
  draftItems.value =
    next.length > 0 ? next.map((item) => createDraft(item)) : [createDraft()];
}

function emitValue() {
  emit('update:modelValue', buildNormalized(draftItems.value));
}

function handleAdd() {
  if (props.disabled) {
    return;
  }
  draftItems.value.push(createDraft());
}

function handleRemove(index: number) {
  if (props.disabled) {
    return;
  }
  if (draftItems.value.length === 1) {
    draftItems.value[0] = createDraft('');
  } else {
    draftItems.value.splice(index, 1);
  }
  emitValue();
}

watch(
  () => props.modelValue,
  (value) => {
    syncDraftsFromModel(value || []);
  },
  { deep: true, immediate: true },
);

const filledCount = computed(() => buildNormalized(draftItems.value).length);
const showHeaderAdd = computed(() => props.addButtonPlacement === 'header');
const showFooterAdd = computed(() => props.addButtonPlacement === 'footer');
const bodyClass = computed(() =>
  props.scrollable ? 'h-full min-h-0 overflow-y-auto pr-1' : '',
);
const bodyStyle = computed(() => {
  if (!props.bodyMaxHeight) {
    return undefined;
  }
  return {
    maxHeight: props.bodyMaxHeight,
  };
});
</script>

<template>
  <div
    class="flex min-h-0 flex-col overflow-hidden rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
  >
    <div
      class="mb-4 rounded-xl border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] px-4 py-3"
    >
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div
            class="text-sm font-semibold text-[var(--el-text-color-primary)]"
          >
            {{ label }}
          </div>
          <div
            v-if="description"
            class="mt-1 text-xs leading-5 text-[var(--el-text-color-secondary)]"
          >
            {{ description }}
          </div>
        </div>
        <div
          class="rounded-lg border border-[var(--el-color-primary-light-7)] bg-[var(--el-color-primary-light-9)] px-3 py-2 text-right"
        >
          <div
            class="text-[11px] font-medium leading-none text-[var(--el-text-color-secondary)]"
          >
            已录入
          </div>
          <div
            class="mt-1 text-lg font-semibold leading-none text-[var(--el-color-primary)]"
          >
            {{ filledCount }}
          </div>
        </div>
      </div>
      <div
        v-if="showHeaderAdd && !props.disabled"
        class="mt-3 flex justify-end"
      >
        <ElButton :icon="Plus" link type="primary" @click="handleAdd">
          {{ addText }}
        </ElButton>
      </div>
    </div>

    <div
      class="min-h-0 flex-1 rounded-xl border border-[var(--el-border-color-lighter)] bg-[var(--el-bg-color-page)] p-3"
      :style="bodyStyle"
    >
      <div v-if="draftItems.length > 0" :class="bodyClass" class="space-y-3">
        <div
          v-for="(item, index) in draftItems"
          :key="item.key"
          class="flex items-start gap-3 rounded-lg border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] px-3 py-3"
        >
          <div
            class="flex h-8 min-w-8 items-center justify-center rounded-full bg-[var(--el-color-primary-light-9)] text-xs font-semibold text-[var(--el-color-primary)]"
          >
            {{ index + 1 }}
          </div>
          <ElInput
            v-model="item.value"
            :clearable="!props.disabled"
            :disabled="props.disabled"
            :placeholder="placeholder"
            @change="emitValue"
            @input="emitValue"
          />
          <ElButton
            v-if="!props.disabled"
            :icon="Delete"
            circle
            link
            type="danger"
            @click="handleRemove(index)"
          />
        </div>
      </div>

      <div v-else class="flex h-full min-h-[180px] items-center justify-center">
        <ElEmpty :description="`暂无${itemLabel}`" :image-size="72" />
      </div>
    </div>

    <div
      v-if="showFooterAdd && !props.disabled"
      class="mt-4 border-t border-[var(--el-border-color-lighter)] pt-4"
    >
      <ElButton
        :icon="Plus"
        class="w-full"
        plain
        type="primary"
        @click="handleAdd"
      >
        {{ addText }}
      </ElButton>
    </div>
  </div>
</template>
