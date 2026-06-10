<script lang="ts" setup>
import type {
  FailureModeProductItem,
  ProductFailureModeItem,
  VisibleSubsystemItem,
} from '#/api/failure_mode_workflow';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElEmpty,
  ElInput,
  ElOption,
  ElSelect,
  ElSelectV2,
  ElTag,
} from 'element-plus';

import {
  listProductsApi,
  listVisibleSubsystemsApi,
  searchProductFailureModesApi,
} from '#/api/failure_mode_workflow';
import { useZqTable } from '#/components/zq-table';

import { useProductFailureModeColumns } from '../../workflow/products/data';

defineOptions({ name: 'FailureModeProductBaseline' });

const router = useRouter();

const products = ref<FailureModeProductItem[]>([]);
const selectedProductId = ref('');
const selectedSubsystem = ref('');
const keyword = ref('');
const subsystemOptions = ref<VisibleSubsystemItem[]>([]);
const loadingProducts = ref(false);
const hasSearched = ref(false);

const selectedProduct = computed(() => {
  return (
    products.value.find((item) => item.id === selectedProductId.value) || null
  );
});

const productSelectOptions = computed(() => {
  return products.value.map((item) => ({
    label: item.project_name,
    value: item.id,
  }));
});

const baselineEmptyDescription = computed(() => {
  if (!selectedProductId.value) {
    return '请先选择一个产品以查看基线结果';
  }
  if (!hasSearched.value) {
    return '请选择产品后点击查询加载当前基线';
  }
  return '';
});

const [BaselineGrid, baselineGridApi] = useZqTable<ProductFailureModeItem>({
  gridOptions: {
    border: true,
    columns: useProductFailureModeColumns(),
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page?: { currentPage?: number; pageSize?: number };
        }) => {
          if (!selectedProductId.value) {
            return { items: [], total: 0 };
          }
          return searchProductFailureModesApi({
            keyword: keyword.value.trim() || undefined,
            page: page?.currentPage || 1,
            pageSize: page?.pageSize || 20,
            product_id: selectedProductId.value,
            subsystem: selectedSubsystem.value || undefined,
          });
        },
      },
    },
  },
});

async function loadProducts() {
  loadingProducts.value = true;
  try {
    products.value = await listProductsApi({
      compact: true,
      project_type: '平台项目',
    });
    if (!selectedProductId.value && products.value.length > 0) {
      selectedProductId.value = products.value[0]!.id;
      await loadSubsystems();
      await handleSearch();
    }
  } finally {
    loadingProducts.value = false;
  }
}

async function loadSubsystems() {
  if (!selectedProductId.value) {
    subsystemOptions.value = [];
    selectedSubsystem.value = '';
    return;
  }
  subsystemOptions.value = await listVisibleSubsystemsApi(
    selectedProductId.value,
  );
}

async function handleProductChange() {
  selectedSubsystem.value = '';
  await loadSubsystems();
  await handleSearch();
}

async function handleSearch() {
  hasSearched.value = true;
  baselineGridApi.pagination.currentPage = 1;
  await baselineGridApi.query();
}

function handleGoRoleConfig() {
  if (!selectedProductId.value) {
    return;
  }
  router.push(`/failure-mode/config/roles/detail/${selectedProductId.value}`);
}

onMounted(() => {
  void loadProducts();
});
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div class="flex min-h-0 flex-1 flex-col gap-4">
      <div class="rounded-xl bg-white p-4 shadow-sm">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div class="text-xl font-semibold text-gray-900">产品基线</div>
            <div class="mt-1 text-sm text-gray-500">
              查看某产品某子系统当前已生效的故障模式基线结果
            </div>
          </div>
          <ElButton
            type="primary"
            plain
            :disabled="!selectedProductId"
            @click="handleGoRoleConfig"
          >
            前往角色配置
          </ElButton>
        </div>

        <div
          class="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_220px_minmax(220px,0.8fr)_140px]"
        >
          <ElSelectV2
            v-model="selectedProductId"
            filterable
            :options="productSelectOptions"
            placeholder="请选择产品"
            :loading="loadingProducts"
            @change="handleProductChange"
          />
          <ElSelect
            v-model="selectedSubsystem"
            clearable
            filterable
            placeholder="选择子系统"
            @change="handleSearch"
          >
            <ElOption
              v-for="item in subsystemOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
          <ElInput
            v-model="keyword"
            clearable
            placeholder="搜索故障模式简述"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
          <div class="flex items-center justify-end">
            <ElButton
              type="primary"
              plain
              :disabled="!selectedProductId"
              :loading="baselineGridApi.loading.value"
              @click="handleSearch"
            >
              查询
            </ElButton>
          </div>
        </div>

        <div
          v-if="selectedProduct"
          class="mt-4 flex items-center gap-3 text-sm text-gray-600"
        >
          <span>主版本SE：</span>
          <ElTag type="primary">
            {{
              selectedProduct.owner_info?.name ||
              selectedProduct.owner_info?.username ||
              '未配置'
            }}
          </ElTag>
        </div>
      </div>

      <div
        class="relative min-h-0 flex-1 overflow-hidden rounded-xl bg-white p-4 shadow-sm"
      >
        <div
          v-if="!selectedProductId || !hasSearched"
          class="absolute inset-0 z-10 flex items-center justify-center bg-white"
        >
          <ElEmpty :description="baselineEmptyDescription" />
        </div>
        <div class="h-full">
          <BaselineGrid />
        </div>
      </div>
    </div>
  </Page>
</template>
