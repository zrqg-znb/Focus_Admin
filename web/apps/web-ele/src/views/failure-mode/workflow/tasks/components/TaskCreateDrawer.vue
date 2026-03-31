<script setup lang="ts">
import type {
  FailureModeProductItem,
  FailureModeRoleAssignmentItem,
  FailureModeTaskCreatePayload,
  VisibleSubsystemItem,
} from '#/api/failure_mode_workflow';

import { computed, reactive, ref } from 'vue';

import {
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
} from 'element-plus';

import {
  createTaskApi,
  listProductRoleAssignmentsApi,
  listProductsApi,
  listVisibleSubsystemsApi,
} from '#/api/failure_mode_workflow';
import { ZqDrawer } from '#/components/zq-drawer';

const emit = defineEmits(['success']);

const visible = ref(false);
const loading = ref(false);
const submitting = ref(false);
const products = ref<FailureModeProductItem[]>([]);
const subsystemOptions = ref<VisibleSubsystemItem[]>([]);
const roleAssignments = ref<FailureModeRoleAssignmentItem[]>([]);
const formRef = ref<InstanceType<typeof ElForm>>();

const formModel = reactive<FailureModeTaskCreatePayload>({
  name: '',
  task_type: 'CREATE',
  product_id: '',
  subsystem: '',
  assignee_id: '',
});

const assigneeOptions = computed(() => {
  const seen = new Set<string>();
  return roleAssignments.value
    .filter(
      (item) =>
        item.role === 'feature_se' && item.subsystem === formModel.subsystem,
    )
    .filter((item) => {
      if (seen.has(item.user_id)) {
        return false;
      }
      seen.add(item.user_id);
      return true;
    })
    .map((item) => ({
      label: item.user_info.name || item.user_info.username,
      value: item.user_id,
    }));
});

const rules = {
  name: [{ message: '请输入任务名称', required: true, trigger: 'blur' }],
  task_type: [{ message: '请选择任务类型', required: true, trigger: 'change' }],
  product_id: [
    { message: '请选择关联产品', required: true, trigger: 'change' },
  ],
  subsystem: [{ message: '请选择子系统', required: true, trigger: 'change' }],
  assignee_id: [
    { message: '请选择特性SE责任人', required: true, trigger: 'change' },
  ],
};

async function loadProducts() {
  products.value = (await listProductsApi()) as any;
}

async function loadProductContext() {
  if (!formModel.product_id) {
    subsystemOptions.value = [];
    roleAssignments.value = [];
    return;
  }
  loading.value = true;
  try {
    const [subsystems, assignments] = await Promise.all([
      listVisibleSubsystemsApi(formModel.product_id),
      listProductRoleAssignmentsApi(formModel.product_id),
    ]);
    subsystemOptions.value = subsystems;
    roleAssignments.value = assignments;
  } finally {
    loading.value = false;
  }
}

async function handleProductChange() {
  formModel.subsystem = '';
  formModel.assignee_id = '';
  await loadProductContext();
}

function handleSubsystemChange() {
  formModel.assignee_id = '';
}

async function open() {
  visible.value = true;
  submitting.value = false;
  loading.value = true;
  formModel.name = '';
  formModel.task_type = 'CREATE';
  formModel.product_id = '';
  formModel.subsystem = '';
  formModel.assignee_id = '';
  subsystemOptions.value = [];
  roleAssignments.value = [];
  try {
    await loadProducts();
  } finally {
    loading.value = false;
  }
}

async function handleConfirm() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) {
    return;
  }

  submitting.value = true;
  try {
    await createTaskApi({ ...formModel });
    ElMessage.success('创建任务成功');
    visible.value = false;
    emit('success');
  } catch (error: any) {
    ElMessage.error(error.message || '创建失败');
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
    size="50%"
    title="发起梳理任务"
    @confirm="handleConfirm"
  >
    <div class="rounded-xl border bg-white p-4">
      <ElForm
        ref="formRef"
        :model="formModel"
        :rules="rules"
        label-width="120px"
      >
        <ElFormItem label="任务名称" prop="name">
          <ElInput v-model="formModel.name" placeholder="请输入任务名称" />
        </ElFormItem>
        <ElFormItem label="任务类型" prop="task_type">
          <ElSelect v-model="formModel.task_type" class="w-full">
            <ElOption label="创建" value="CREATE" />
            <ElOption label="修订" value="REVISE" />
            <ElOption label="删除" value="DELETE" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="关联产品" prop="product_id">
          <ElSelect
            v-model="formModel.product_id"
            class="w-full"
            filterable
            @change="handleProductChange"
          >
            <ElOption
              v-for="item in products"
              :key="item.id"
              :label="item.project_name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="子系统" prop="subsystem">
          <ElSelect
            v-model="formModel.subsystem"
            class="w-full"
            filterable
            @change="handleSubsystemChange"
          >
            <ElOption
              v-for="item in subsystemOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="责任人" prop="assignee_id">
          <ElSelect v-model="formModel.assignee_id" class="w-full" filterable>
            <ElOption
              v-for="item in assigneeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
      </ElForm>
    </div>
  </ZqDrawer>
</template>
