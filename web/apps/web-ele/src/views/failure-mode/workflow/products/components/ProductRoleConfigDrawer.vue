<script setup lang="ts">
import type {
  FailureModeProductItem,
  FailureModeRoleAssignmentItem,
  ProductRoleAssignmentSaveItem,
  VisibleSubsystemItem,
} from '#/api/failure_mode_workflow';

import { computed, ref } from 'vue';

import { ElButton, ElMessage, ElOption, ElSelect } from 'element-plus';

import { getFailureModeDictOptionsApi } from '#/api/failure_mode';
import {
  listProductRoleAssignmentsApi,
  listVisibleSubsystemsApi,
  saveProductRoleAssignmentsApi,
  updateProductOwnerApi,
} from '#/api/failure_mode_workflow';
import { ZqDrawer } from '#/components/zq-drawer';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

interface EditableRoleRow {
  role: 'feature_se' | 'member';
  subsystem: string;
  tempKey: string;
  user_id: string;
}

const emit = defineEmits<{
  success: [];
}>();

const visible = ref(false);
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

function isEditableRoleAssignment(
  item: FailureModeRoleAssignmentItem,
): item is FailureModeRoleAssignmentItem & { role: EditableRoleRow['role'] } {
  return item.role === 'feature_se' || item.role === 'member';
}

const drawerTitle = computed(() => {
  const productName = currentProduct.value?.project_name || '';
  return productName ? `${productName} 角色配置` : '产品角色配置';
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

async function loadData(product: FailureModeProductItem) {
  loading.value = true;
  try {
    const [roleAssignments, visibleSubsystems, dictOptions] = await Promise.all(
      [
        listProductRoleAssignmentsApi(product.id),
        listVisibleSubsystemsApi(product.id),
        getFailureModeDictOptionsApi(),
      ],
    );
    ownerId.value = product.owner_id || '';
    roleRows.value = roleAssignments
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

async function open(product: FailureModeProductItem) {
  currentProduct.value = product;
  roleRows.value = [];
  ownerId.value = product.owner_id || '';
  visible.value = true;
  await loadData(product);
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

async function handleConfirm() {
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
    visible.value = false;
    emit('success');
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败');
  } finally {
    submitting.value = false;
  }
}

defineExpose({ open });
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :confirm-loading="submitting"
    :loading="loading"
    :title="drawerTitle"
    size="70%"
    @confirm="handleConfirm"
  >
    <div class="space-y-4">
      <div class="rounded-xl border bg-white p-4">
        <div class="mb-3 text-sm font-medium text-gray-700">主版本SE</div>
        <UserSelector
          v-model="ownerId"
          clearable
          display-mode="select"
          placeholder="请选择主版本SE"
        />
      </div>

      <div class="rounded-xl border bg-white p-4">
        <div class="mb-3 flex items-center justify-between">
          <div class="text-sm font-medium text-gray-700">子系统角色配置</div>
          <ElButton type="primary" plain @click="addRoleRow">新增一行</ElButton>
        </div>

        <div
          v-if="roleRows.length === 0"
          class="rounded-lg border border-dashed p-6 text-center text-sm text-gray-500"
        >
          暂无子系统角色配置，请新增后保存
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="item in roleRows"
            :key="item.tempKey"
            class="grid grid-cols-[160px_180px_minmax(0,1fr)_80px] items-center gap-3 rounded-lg border p-3"
          >
            <ElSelect v-model="item.subsystem" placeholder="选择子系统">
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
      </div>
    </div>
  </ZqDrawer>
</template>
