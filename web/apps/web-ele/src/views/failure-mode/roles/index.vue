<script lang="ts" setup>
import type { FailureModeProductItem } from '#/api/failure_mode_workflow';

import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElCard, ElEmpty, ElInput } from 'element-plus';

import { listProductsApi } from '#/api/failure_mode_workflow';

defineOptions({ name: 'FailureModeRoleIndex' });

const router = useRouter();

const loading = ref(false);
const keyword = ref('');
const products = ref<FailureModeProductItem[]>([]);
const selectedProductId = ref('');

const filteredProducts = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLowerCase();
  if (!normalizedKeyword) {
    return products.value;
  }
  return products.value.filter((item) =>
    item.project_name.toLowerCase().includes(normalizedKeyword),
  );
});

const selectedProduct = computed(() => {
  return (
    products.value.find((item) => item.id === selectedProductId.value) || null
  );
});

const assignmentSummary = computed(
  () => selectedProduct.value?.role_preview || [],
);

function formatUserNames(
  items?: Array<{ name?: null | string; username: string }>,
) {
  if (!items || items.length === 0) {
    return '未配置';
  }
  return items.map((item) => item.name || item.username).join(' / ');
}

async function loadProducts() {
  loading.value = true;
  try {
    const rows = await listProductsApi();
    products.value = rows;
    if (!selectedProductId.value && rows.length > 0) {
      selectedProductId.value = rows[0]!.id;
    }
  } finally {
    loading.value = false;
  }
}

function handleOpenDetail() {
  if (!selectedProductId.value) {
    return;
  }
  router.push(`/failure-mode/roles/detail/${selectedProductId.value}`);
}

void loadProducts();
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div v-loading="loading" class="flex min-h-0 flex-1 flex-col gap-4">
      <div class="rounded-xl bg-white p-5 shadow-sm">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div class="text-xl font-semibold text-gray-900">角色配置</div>
            <div class="mt-1 text-sm text-gray-500">
              统一维护产品主版本SE、子系统特性SE与普通成员授权
            </div>
          </div>
          <ElButton
            type="primary"
            :disabled="!selectedProductId"
            @click="handleOpenDetail"
          >
            进入配置详情
          </ElButton>
        </div>
        <ElInput v-model="keyword" clearable placeholder="搜索产品名称" />
      </div>

      <div
        class="grid min-h-0 flex-1 gap-4 xl:grid-cols-[340px_minmax(0,1fr)_320px]"
      >
        <ElCard
          class="h-full"
          shadow="never"
          :body-style="{ height: '100%', overflow: 'hidden', padding: '20px' }"
        >
          <template #header>
            <span class="font-medium">产品列表</span>
          </template>
          <div v-if="filteredProducts.length === 0" class="py-8">
            <ElEmpty description="暂无可配置产品" />
          </div>
          <div v-else class="h-full space-y-3 overflow-auto pr-1">
            <button
              v-for="item in filteredProducts"
              :key="item.id"
              class="w-full rounded-xl border p-3 text-left transition-colors"
              :class="
                item.id === selectedProductId
                  ? 'border-primary bg-primary/5'
                  : 'hover:border-primary/40 border-gray-200'
              "
              type="button"
              @click="selectedProductId = item.id"
            >
              <div class="font-medium text-gray-900">
                {{ item.project_name }}
              </div>
              <div class="mt-2 text-sm text-gray-500">
                主版本SE：{{
                  item.owner_info?.name || item.owner_info?.username || '未配置'
                }}
              </div>
            </button>
          </div>
        </ElCard>

        <ElCard
          class="h-full"
          shadow="never"
          :body-style="{ height: '100%', overflow: 'hidden', padding: '20px' }"
        >
          <template #header>
            <span class="font-medium">矩阵预览</span>
          </template>
          <div v-if="!selectedProduct" class="py-8">
            <ElEmpty description="请选择左侧产品" />
          </div>
          <div v-else class="h-full space-y-3 overflow-auto pr-1">
            <div class="rounded-lg bg-gray-50 p-3 text-sm text-gray-600">
              当前产品：<span class="font-medium text-gray-900">{{
                selectedProduct.project_name
              }}</span>
            </div>
            <div
              class="rounded-lg border border-dashed p-3 text-sm text-gray-600"
            >
              主版本SE：{{
                selectedProduct.owner_info?.name ||
                selectedProduct.owner_info?.username ||
                '未配置'
              }}
            </div>
            <div
              v-for="item in assignmentSummary"
              :key="item.subsystem"
              class="rounded-xl border p-3"
            >
              <div class="font-medium text-gray-900">{{ item.subsystem }}</div>
              <div class="mt-2 text-sm text-gray-600">
                特性SE：{{ formatUserNames(item.feature_se_info) }}
              </div>
              <div class="mt-1 text-sm text-gray-600">
                普通成员：{{ formatUserNames(item.member_info) }}
              </div>
            </div>
            <div
              v-if="assignmentSummary.length === 0"
              class="text-sm text-gray-500"
            >
              当前产品暂无子系统授权矩阵
            </div>
          </div>
        </ElCard>

        <ElCard
          class="h-full"
          shadow="never"
          :body-style="{ height: '100%', overflow: 'hidden', padding: '20px' }"
        >
          <template #header>
            <span class="font-medium">配置说明</span>
          </template>
          <div class="h-full space-y-3 overflow-auto text-sm text-gray-600">
            <div>
              角色配置是低频高复杂动作，建议独立成页，不再嵌在基线页抽屉里。
            </div>
            <div>
              主版本SE负责产品级任务流转；特性SE和普通成员按子系统授权。
            </div>
            <div>进入详情页后再做矩阵编辑、保存与影响范围确认。</div>
          </div>
        </ElCard>
      </div>
    </div>
  </Page>
</template>
