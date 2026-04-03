<script lang="ts" setup>
import type {
  FailureModeProductItem,
  FailureModeRoleAssignmentItem,
  ProductRoleAssignmentSaveItem,
  VisibleSubsystemItem,
} from '#/api/failure_mode_workflow';

import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElCard, ElMessage, ElOption, ElSelect } from 'element-plus';

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
const isEditing = ref(false);
const currentProduct = ref<FailureModeProductItem | null>(null);
const ownerId = ref('');
const roleAssignments = ref<FailureModeRoleAssignmentItem[]>([]);
const roleRows = ref<EditableRoleRow[]>([]);
const subsystemOptions = ref<VisibleSubsystemItem[]>([]);

const roleOptions = [
  { label: '特性SE', value: 'feature_se' },
  { label: '普通成员', value: 'member' },
];

function isEditableRoleAssignment(
  item: FailureModeRoleAssignmentItem,
): item is FailureModeRoleAssignmentItem & { role: EditableRoleRow['role'] } {
  return item.role === 'feature_se' || item.role === 'member';
}

const canManageRoles = computed(() =>
  Boolean(currentProduct.value?.can_manage_roles),
);

const roleMatrixRows = computed(() => {
  const grouped = new Map<
    string,
    {
      featureUsers: string[];
      memberUsers: string[];
    }
  >();
  for (const item of roleAssignments.value) {
    if (item.role !== 'feature_se' && item.role !== 'member') {
      continue;
    }
    const subsystem = item.subsystem || '未配置子系统';
    const current = grouped.get(subsystem) || {
      featureUsers: [],
      memberUsers: [],
    };
    const userName =
      item.user_info?.name || item.user_info?.username || item.user_id;
    if (item.role === 'feature_se') {
      current.featureUsers.push(userName);
    } else {
      current.memberUsers.push(userName);
    }
    grouped.set(subsystem, current);
  }
  return [...grouped.entries()].map(([subsystem, value]) => ({
    subsystem,
    featureUsers: value.featureUsers,
    memberUsers: value.memberUsers,
  }));
});

const roleSummary = computed(() => {
  return roleMatrixRows.value.map((item) => ({
    subsystem: item.subsystem,
    featureText: item.featureUsers.join(' / ') || '未配置',
    memberText: item.memberUsers.join(' / ') || '未配置',
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
    const products = await listProductsApi({ project_type: '平台项目' });
    currentProduct.value =
      products.find((item) => item.id === productId.value) || null;
    if (!currentProduct.value) {
      return;
    }

    const [assignmentRows, visibleSubsystems, dictOptions] = await Promise.all([
      listProductRoleAssignmentsApi(productId.value),
      listVisibleSubsystemsApi(productId.value),
      getFailureModeDictOptionsApi(),
    ]);

    ownerId.value = currentProduct.value.owner_id || '';
    roleAssignments.value = assignmentRows;
    roleRows.value = assignmentRows
      .filter((item) => isEditableRoleAssignment(item))
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

function handleStartEditing() {
  if (!canManageRoles.value) {
    return;
  }
  isEditing.value = true;
}

async function handleCancelEditing() {
  isEditing.value = false;
  await loadData();
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
    isEditing.value = false;
  } finally {
    submitting.value = false;
  }
}

function handleBack() {
  router.push('/failure-mode/config/roles');
}

void loadData();
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div v-loading="loading" class="flex min-h-0 flex-1 flex-col gap-4">
      <div
        class="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white p-5 shadow-sm"
      >
        <div class="flex flex-wrap items-center gap-3">
          <ElButton plain @click="handleBack">返回角色配置</ElButton>
          <span class="text-xl font-semibold text-gray-900">
            {{ currentProduct?.project_name || '角色配置详情' }}
          </span>
          <span class="text-sm text-gray-500">
            {{ canManageRoles ? '可编辑' : '只读查看' }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <ElButton
            v-if="canManageRoles && !isEditing"
            type="primary"
            @click="handleStartEditing"
          >
            进入编辑模式
          </ElButton>
          <ElButton
            v-if="canManageRoles && isEditing"
            @click="handleCancelEditing"
          >
            取消编辑
          </ElButton>
          <ElButton
            v-if="canManageRoles && isEditing"
            type="primary"
            :loading="submitting"
            @click="handleSave"
          >
            保存配置
          </ElButton>
        </div>
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
                v-if="canManageRoles && isEditing"
                v-model="ownerId"
                clearable
                display-mode="select"
                placeholder="请选择主版本SE"
              />
              <div v-else class="font-medium text-gray-900">
                {{
                  currentProduct?.owner_info?.name ||
                  currentProduct?.owner_info?.username ||
                  '未配置'
                }}
              </div>
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
              <ElButton
                v-if="canManageRoles && isEditing"
                type="primary"
                plain
                @click="addRoleRow"
              >
                新增一行
              </ElButton>
            </div>
          </template>
          <div v-if="!isEditing" class="h-full space-y-3 overflow-auto pr-1">
            <div
              v-for="item in roleSummary"
              :key="item.subsystem"
              class="rounded-xl border p-4"
            >
              <div class="font-medium text-gray-900">{{ item.subsystem }}</div>
              <div class="mt-3 text-sm text-gray-600">
                特性SE：{{ item.featureText }}
              </div>
              <div class="mt-1 text-sm text-gray-600">
                普通成员：{{ item.memberText }}
              </div>
            </div>
            <div
              v-if="roleSummary.length === 0"
              class="rounded-xl border border-dashed p-10 text-center text-sm text-gray-500"
            >
              当前范围内暂无角色授权配置
            </div>
          </div>
          <div
            v-else-if="roleRows.length === 0"
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
                display-mode="select"
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
              {{
                canManageRoles
                  ? '建议先在只读模式确认当前负责人，再进入编辑模式做集中调整。'
                  : '当前账号仅有查看权限，可在此核对各子系统 SE 与成员对应关系。'
              }}
            </div>
            <div
              v-for="item in roleSummary"
              :key="item.subsystem"
              class="rounded-lg border p-3"
            >
              <div class="font-medium text-gray-900">{{ item.subsystem }}</div>
              <div class="mt-2 text-sm text-gray-600">
                特性SE：{{ item.featureText }}
              </div>
              <div class="mt-1 text-sm text-gray-600">
                普通成员：{{ item.memberText }}
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
