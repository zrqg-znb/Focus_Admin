<script lang="ts" setup>
import type { FailureModeScopeBinding } from '#/api/failure_mode';
import type {
  FailureModeProductItem,
  VisibleSubsystemItem,
} from '#/api/failure_mode_workflow';

import { computed, onMounted, ref, watch } from 'vue';

import { Delete, Plus } from '@element-plus/icons-vue';
import { ElButton, ElEmpty, ElOption, ElSelect, ElTag } from 'element-plus';

import {
  listProductsApi,
  listVisibleSubsystemsApi,
} from '#/api/failure_mode_workflow';

interface DraftScopeBinding {
  key: number;
  product_id: string;
  subsystem: string;
  product_name: string;
}

const props = withDefaults(
  defineProps<{
    bodyMaxHeight?: string;
    description?: string;
    disabled?: boolean;
    label: string;
    modelValue?: FailureModeScopeBinding[];
    scrollable?: boolean;
  }>(),
  {
    bodyMaxHeight: '320px',
    description:
      '为当前故障模式选择需要落地的产品与子系统，支持配置多个独立范围。',
    disabled: false,
    modelValue: () => [],
    scrollable: true,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: FailureModeScopeBinding[]];
}>();

let sequence = 0;
const draftItems = ref<DraftScopeBinding[]>([]);
const products = ref<FailureModeProductItem[]>([]);
const productsLoading = ref(false);
const subsystemOptionsMap = ref<Record<string, VisibleSubsystemItem[]>>({});
const subsystemLoadingMap = ref<Record<string, boolean>>({});

const productOptions = computed(() =>
  products.value.map((item) => ({
    label: item.project_name,
    value: item.id,
  })),
);

const bodyClass = computed(() =>
  props.scrollable ? 'h-full min-h-0 overflow-y-auto pr-1' : '',
);

const filledCount = computed(
  () =>
    draftItems.value.filter((item) => item.product_id && item.subsystem).length,
);

function createDraft(
  value: Partial<FailureModeScopeBinding> = {},
): DraftScopeBinding {
  sequence += 1;
  return {
    key: sequence,
    product_id: String(value.product_id || '').trim(),
    subsystem: String(value.subsystem || '').trim(),
    product_name: String(value.product_name || '').trim(),
  };
}

function arraysEqual(left: DraftScopeBinding[], right: DraftScopeBinding[]) {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((item, index) => {
    const other = right[index];
    return (
      item.product_id === other.product_id &&
      item.subsystem === other.subsystem &&
      item.product_name === other.product_name
    );
  });
}

function normalizeDraftBindings(
  values: FailureModeScopeBinding[] = [],
): DraftScopeBinding[] {
  return (Array.isArray(values) ? values : []).map((item) => createDraft(item));
}

function getProductName(productId: string) {
  return (
    products.value.find((item) => item.id === productId)?.project_name || ''
  );
}

function getSubsystemOptions(productId: string) {
  return subsystemOptionsMap.value[productId] || [];
}

function emitValue() {
  emit(
    'update:modelValue',
    draftItems.value.map((item) => ({
      product_id: item.product_id.trim(),
      subsystem: item.subsystem.trim(),
      product_name: item.product_name.trim() || null,
    })),
  );
}

async function loadProducts() {
  if (productsLoading.value || products.value.length > 0) {
    return;
  }
  productsLoading.value = true;
  try {
    products.value = await listProductsApi();
  } finally {
    productsLoading.value = false;
  }
}

async function ensureSubsystemOptions(productId: string) {
  const normalizedProductId = String(productId || '').trim();
  if (!normalizedProductId || subsystemOptionsMap.value[normalizedProductId]) {
    return;
  }
  subsystemLoadingMap.value = {
    ...subsystemLoadingMap.value,
    [normalizedProductId]: true,
  };
  try {
    const items = await listVisibleSubsystemsApi(normalizedProductId);
    subsystemOptionsMap.value = {
      ...subsystemOptionsMap.value,
      [normalizedProductId]: items || [],
    };
  } finally {
    subsystemLoadingMap.value = {
      ...subsystemLoadingMap.value,
      [normalizedProductId]: false,
    };
  }
}

async function primeSubsystemOptions() {
  await loadProducts();
  const productIds = [
    ...new Set(
      draftItems.value.map((item) => item.product_id.trim()).filter(Boolean),
    ),
  ];
  await Promise.all(
    productIds.map((productId) => ensureSubsystemOptions(productId)),
  );
}

function syncDraftsFromModel(values: FailureModeScopeBinding[]) {
  const nextDraftItems = normalizeDraftBindings(values || []);
  if (
    arraysEqual(draftItems.value, nextDraftItems) &&
    draftItems.value.length > 0
  ) {
    return;
  }
  draftItems.value =
    nextDraftItems.length > 0 ? nextDraftItems : [createDraft()];
  void primeSubsystemOptions();
}

function handleAdd() {
  if (props.disabled) {
    return;
  }
  draftItems.value.push(createDraft());
  emitValue();
}

function handleRemove(index: number) {
  if (props.disabled) {
    return;
  }
  if (draftItems.value.length === 1) {
    draftItems.value[0] = createDraft();
  } else {
    draftItems.value.splice(index, 1);
  }
  emitValue();
}

async function handleProductChange(index: number, value?: string) {
  if (props.disabled) {
    return;
  }
  const item = draftItems.value[index];
  if (!item) {
    return;
  }
  const productId = String(value || '').trim();
  item.product_id = productId;
  item.product_name = getProductName(productId);
  item.subsystem = '';
  if (productId) {
    await ensureSubsystemOptions(productId);
  }
  emitValue();
}

function handleSubsystemChange() {
  if (props.disabled) {
    return;
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

onMounted(() => {
  void loadProducts();
  void primeSubsystemOptions();
});
</script>

<template>
  <div
    class="flex min-h-0 flex-col overflow-hidden rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] shadow-sm"
  >
    <div
      class="border-b border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] px-4 py-4"
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
        <ElTag round type="primary">已配置 {{ filledCount }} 组</ElTag>
      </div>
      <div v-if="!props.disabled" class="mt-3 flex justify-end">
        <ElButton :icon="Plus" link type="primary" @click="handleAdd">
          新增绑定
        </ElButton>
      </div>
    </div>

    <div
      class="min-h-0 flex-1 border-[var(--el-border-color-lighter)] bg-[var(--el-bg-color-page)] p-3"
      :style="
        props.bodyMaxHeight ? { maxHeight: props.bodyMaxHeight } : undefined
      "
    >
      <div v-if="draftItems.length > 0" :class="bodyClass" class="space-y-3">
        <div
          v-for="(item, index) in draftItems"
          :key="item.key"
          class="flex items-start gap-3 rounded-xl border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] px-3 py-3"
        >
          <div
            class="flex h-8 min-w-8 items-center justify-center rounded-full bg-[var(--el-color-primary-light-9)] text-xs font-semibold text-[var(--el-color-primary)]"
          >
            {{ index + 1 }}
          </div>

          <div class="grid min-w-0 flex-1 gap-3 md:grid-cols-2">
            <div class="min-w-0">
              <div class="mb-2 text-xs text-[var(--el-text-color-secondary)]">
                产品
              </div>
              <ElSelect
                v-model="item.product_id"
                class="w-full"
                clearable
                filterable
                :disabled="props.disabled || productsLoading"
                placeholder="请选择产品"
                @change="(value) => handleProductChange(index, value)"
              >
                <ElOption
                  v-for="option in productOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </ElSelect>
            </div>

            <div class="min-w-0">
              <div class="mb-2 text-xs text-[var(--el-text-color-secondary)]">
                子系统
              </div>
              <ElSelect
                v-model="item.subsystem"
                class="w-full"
                clearable
                filterable
                :disabled="props.disabled || !item.product_id"
                :loading="Boolean(subsystemLoadingMap[item.product_id])"
                placeholder="请选择子系统"
                @change="handleSubsystemChange"
              >
                <ElOption
                  v-for="option in getSubsystemOptions(item.product_id)"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </ElSelect>
            </div>
          </div>

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

      <div v-else class="flex min-h-[180px] items-center justify-center">
        <ElEmpty description="暂无产品范围绑定" :image-size="72" />
      </div>
    </div>
  </div>
</template>
