<script lang="ts" setup>
import type {
  FailureModeProductItem,
  ProductRoleAssignmentSaveItem,
  VisibleSubsystemItem,
} from '#/api/failure_mode_workflow';

import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElCard,
  ElMessage,
  ElOption,
  ElSelect,
  ElTag,
} from 'element-plus';

import { getFailureModeDictOptionsApi } from '#/api/failure_mode';
import {
  listProductRoleAssignmentsApi,
  listProductsApi,
  listVisibleSubsystemsApi,
  saveProductRoleAssignmentsApi,
  updateProductOwnerApi,
} from '#/api/failure_mode_workflow';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

defineOptions({ name: 'FailureModeRoleDetail' });

interface EditableRoleRow {
  role: 'feature_se' | 'member';
  subsystem: string;
  tempKey: string;
  user_id: string;
}

const route = useRoute();
const router = useRouter();
const productId = computed(() => String(route.params.id || ''));

const loading = ref(false);
const submitting = ref(false);
const currentProduct = ref<FailureModeProductItem | null>(null);
const ownerId = ref('');
const roleRows = ref<EditableRoleRow[]>([]);
const subsystemOptions = ref<VisibleSubsystemItem[]>([]);

const roleOptions = [
  { label: '特性SE', value: 'feature_se' },
  { label: '普通成员', value: 'member' },
];

const roleSummary = computed(() => {
  const grouped = new Map<string, { feature: number; member: number }>();
  for (const item of roleRows.value) {
    if (!item.subsystem) {
      continue;
    }
    const current = grouped.get(item.subsystem) || { feature: 0, member: 0 };
    if (item.role === 'feature_se') {
      current.feature += 1;
    } else {
      current.member += 1;
    }
    grouped.set(item.subsystem, current);
  }
  return [...grouped.entries()].map(([subsystem, value]) => ({
    subsystem,
    ...value,
  }));
});

function createRoleRow(): EditableRoleRow {
  return {
    tempKey: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    role: 'feature_se',
    subsystem: '',
    user_id: '',
  };
}

function dedupeSubsystemOptions(items: VisibleSubsystemItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (!item.value || seen.has(item.value)) {
      return false;
    }
    seen.add(item.value);
    return true;
  });
}

async function loadData() {
  if (!productId.value) {
    return;
  }
  loading.value = true;
  try {
    const products = await listProductsApi();
    currentProduct.value =
      products.find((item) => item.id === productId.value) || null;
    if (!currentProduct.value) {
      return;
    }

    const [roleAssignments, visibleSubsystems, dictOptions] = await Promise.all(
      [
        listProductRoleAssignmentsApi(productId.value),
        listVisibleSubsystemsApi(productId.value),
        getFailureModeDictOptionsApi(),
      ],
    );

    ownerId.value = currentProduct.value.owner_id || '';
    roleRows.value = roleAssignments
      .filter((item) => item.role === 'feature_se' || item.role === 'member')
      .map((item) => ({
        tempKey: item.id,
        role: item.role,
        subsystem: item.subsystem,
        user_id: item.user_id,
      }));

    const dictSubsystems = (dictOptions.subsystem || []).map((item) => ({
      label: item.label,
      value: item.value,
    }));
    subsystemOptions.value = dedupeSubsystemOptions([
      ...visibleSubsystems,
      ...dictSubsystems,
      ...roleRows.value
        .filter((item) => item.subsystem)
        .map((item) => ({ label: item.subsystem, value: item.subsystem })),
    ]);
  } finally {
    loading.value = false;
  }
}

function addRoleRow() {
  roleRows.value.push(createRoleRow());
}

function removeRoleRow(tempKey: string) {
  roleRows.value = roleRows.value.filter((item) => item.tempKey !== tempKey);
}

function buildPayload(): ProductRoleAssignmentSaveItem[] {
  return roleRows.value
    .map((item) => ({
      role: item.role,
      subsystem: item.subsystem.trim(),
      user_id: item.user_id,
    }))
    .filter((item) => item.subsystem && item.user_id);
}

async function handleSave() {
  if (!currentProduct.value) {
    return;
  }
  submitting.value = true;
  try {
    if ((ownerId.value || '') !== (currentProduct.value.owner_id || '')) {
      await updateProductOwnerApi(
        currentProduct.value.id,
        ownerId.value || undefined,
      );
    }
    await saveProductRoleAssignmentsApi(
      currentProduct.value.id,
      buildPayload(),
    );
    ElMessage.success('角色配置已保存');
    await loadData();
  } finally {
    submitting.value = false;
  }
}

function handleBack() {
  router.push('/failure-mode/roles');
}

void loadData();
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div class="flex min-h-0 flex-1 flex-col gap-4">
      <div
        class="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white p-5 shadow-sm"
      >
        <div class="flex flex-wrap items-center gap-3">
          <ElButton plain @click="handleBack">返回角色配置</ElButton>
          <span class="text-xl font-semibold text-gray-900">
            {{ currentProduct?.project_name || '角色配置详情' }}
          </span>
          <ElTag type="primary">产品级授权矩阵</ElTag>
        </div>
        <ElButton type="primary" :loading="submitting" @click="handleSave">
          保存配置
        </ElButton>
      </div>

      <div
        class="grid min-h-0 flex-1 gap-4 xl:grid-cols-[320px_minmax(0,1.4fr)_320px]"
      >
        <ElCard
          class="h-full"
          shadow="never"
          :body-style="{ height: '100%', overflow: 'auto', padding: '20px' }"
        >
          <template #header>
            <span class="font-medium">产品信息</span>
          </template>
          <div class="space-y-4">
            <div>
              <div class="mb-2 text-sm text-gray-500">产品名称</div>
              <div class="font-medium text-gray-900">
                {{ currentProduct?.project_name || '-' }}
              </div>
            </div>
            <div>
              <div class="mb-2 text-sm text-gray-500">主版本SE</div>
              <UserSelector
                v-model="ownerId"
                clearable
                display-mode="button"
                placeholder="请选择主版本SE"
              />
            </div>
          </div>
        </ElCard>

        <ElCard
          class="h-full"
          shadow="never"
          :body-style="{ height: '100%', overflow: 'hidden', padding: '20px' }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <span class="font-medium">子系统角色矩阵</span>
              <ElButton type="primary" plain @click="addRoleRow">
                新增一行
              </ElButton>
            </div>
          </template>
          <div
            v-if="roleRows.length === 0"
            class="rounded-xl border border-dashed p-10 text-center text-sm text-gray-500"
          >
            暂无角色授权，请新增矩阵行后保存
          </div>
          <div v-else class="h-full space-y-3 overflow-auto pr-1">
            <div
              v-for="item in roleRows"
              :key="item.tempKey"
              class="grid items-center gap-3 rounded-xl border p-3 lg:grid-cols-[160px_160px_minmax(0,1fr)_70px]"
            >
              <ElSelect
                v-model="item.subsystem"
                filterable
                placeholder="选择子系统"
              >
                <ElOption
                  v-for="option in subsystemOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </ElSelect>
              <ElSelect v-model="item.role" placeholder="选择角色">
                <ElOption
                  v-for="option in roleOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </ElSelect>
              <UserSelector
                v-model="item.user_id"
                clearable
                display-mode="button"
                placeholder="选择用户"
              />
              <ElButton type="danger" link @click="removeRoleRow(item.tempKey)">
                删除
              </ElButton>
            </div>
          </div>
        </ElCard>

        <ElCard
          class="h-full"
          shadow="never"
          :body-style="{ height: '100%', overflow: 'auto', padding: '20px' }"
        >
          <template #header>
            <span class="font-medium">授权影响预览</span>
          </template>
          <div class="space-y-3">
            <div class="rounded-lg bg-gray-50 p-3 text-sm text-gray-600">
              角色页是高复杂配置区，建议由管理员或版本SE集中维护，不建议在业务列表里做碎片化调整。
            </div>
            <div
              v-for="item in roleSummary"
              :key="item.subsystem"
              class="rounded-lg border p-3"
            >
              <div class="font-medium text-gray-900">{{ item.subsystem }}</div>
              <div class="mt-2 text-sm text-gray-600">
                特性SE：{{ item.feature }} 人
              </div>
              <div class="mt-1 text-sm text-gray-600">
                普通成员：{{ item.member }} 人
              </div>
            </div>
            <div v-if="roleSummary.length === 0" class="text-sm text-gray-500">
              暂无可预览的授权矩阵
            </div>
          </div>
        </ElCard>
      </div>
    </div>
  </Page>
</template>
