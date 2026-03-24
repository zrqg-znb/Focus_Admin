<script lang="ts" setup>
import { computed, ref, watch } from 'vue';

import { Delete, Plus } from '@element-plus/icons-vue';
import { ElButton, ElEmpty, ElInput, ElTag } from 'element-plus';

import { normalizeStringList } from '../data';

interface DraftItem {
  key: number;
  value: string;
}

const props = withDefaults(
  defineProps<{
    addText?: string;
    itemLabel?: string;
    label: string;
    modelValue?: string[];
    placeholder?: string;
  }>(),
  {
    addText: '新增一项',
    itemLabel: '条目',
    modelValue: () => [],
    placeholder: '请输入内容',
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
  draftItems.value.push(createDraft());
}

function handleRemove(index: number) {
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
</script>

<template>
  <div
    class="rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
  >
    <div class="mb-4 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <div class="text-sm font-semibold text-[var(--el-text-color-primary)]">
          {{ label }}
        </div>
        <ElTag size="small" type="info">{{ filledCount }} 条</ElTag>
      </div>
      <ElButton :icon="Plus" link type="primary" @click="handleAdd">
        {{ addText }}
      </ElButton>
    </div>

    <div v-if="draftItems.length > 0" class="space-y-3">
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
          :placeholder="placeholder"
          clearable
          @change="emitValue"
          @input="emitValue"
        />
        <ElButton
          :icon="Delete"
          circle
          link
          type="danger"
          @click="handleRemove(index)"
        />
      </div>
    </div>

    <ElEmpty v-else :description="`暂无${itemLabel}`" :image-size="72" />
  </div>
</template>
