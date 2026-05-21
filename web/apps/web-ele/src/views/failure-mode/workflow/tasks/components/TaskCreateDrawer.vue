<script setup lang="ts">
import type {
  FailureModeProductItem,
  FailureModeTaskCreatePayload,
  ProductFailureModeItem,
  VisibleSubsystemItem,
} from '#/api/failure_mode_workflow';

import { computed, reactive, ref, watch } from 'vue';

import {
  ElAlert,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
} from 'element-plus';

import {
  createTaskApi,
  listProductFailureModesApi,
  listProductsApi,
  listVisibleSubsystemsApi,
} from '#/api/failure_mode_workflow';
import { ZqDrawer } from '#/components/zq-drawer';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

const emit = defineEmits(['success']);

const visible = ref(false);
const loading = ref(false);
const submitting = ref(false);
const products = ref<FailureModeProductItem[]>([]);
const subsystemOptions = ref<VisibleSubsystemItem[]>([]);
const baselinePreviewItems = ref<ProductFailureModeItem[]>([]);
const baselineLoading = ref(false);
const formRef = ref<InstanceType<typeof ElForm>>();

const formModel = reactive<FailureModeTaskCreatePayload>({
  name: '',
  task_type: 'CREATE',
  product_id: '',
  subsystem: '',
  assignee_id: '',
});

const requiresBaseline = computed(() =>
  ['DELETE', 'REVISE'].includes(formModel.task_type),
);

const scopeHasSelection = computed(() =>
  Boolean(formModel.product_id || formModel.subsystem),
);

const scopeIsComplete = computed(() =>
  Boolean(formModel.product_id && formModel.subsystem),
);

const baselinePreviewNames = computed(() =>
  baselinePreviewItems.value.slice(0, 6).map((item) => item.failure_mode_brief),
);

function validateTaskScope(
  _rule: any,
  _value: string,
  callback: (error?: Error) => void,
) {
  const productId = String(formModel.product_id || '').trim();
  const subsystem = String(formModel.subsystem || '').trim();
  if (productId && !subsystem) {
    callback(new Error('请选择子系统，或同时清空关联产品'));
    return;
  }
  if (!productId && subsystem) {
    callback(new Error('请选择关联产品，或同时清空子系统'));
    return;
  }
  callback();
}

const rules = {
  name: [{ message: '请输入任务名称', required: true, trigger: 'blur' }],
  task_type: [{ message: '请选择任务类型', required: true, trigger: 'change' }],
  product_id: [{ validator: validateTaskScope, trigger: 'change' }],
  assignee_id: [{ message: '请选择责任人', required: true, trigger: 'change' }],
};

async function loadProducts() {
  products.value = await listProductsApi();
}

async function loadProductContext() {
  if (!formModel.product_id) {
    subsystemOptions.value = [];
    baselinePreviewItems.value = [];
    return;
  }
  subsystemOptions.value = await listVisibleSubsystemsApi(formModel.product_id);
}

async function handleProductChange(value?: string) {
  void value;
  formModel.subsystem = '';
  baselinePreviewItems.value = [];
  await loadProductContext();
}

function handleSubsystemChange() {
  baselinePreviewItems.value = [];
}

async function loadBaselinePreview() {
  if (!requiresBaseline.value || !scopeIsComplete.value) {
    baselinePreviewItems.value = [];
    baselineLoading.value = false;
    return;
  }
  baselineLoading.value = true;
  try {
    const productId = String(formModel.product_id || '').trim();
    const subsystem = String(formModel.subsystem || '').trim();
    baselinePreviewItems.value = await listProductFailureModesApi(productId, {
      subsystem,
    });
  } finally {
    baselineLoading.value = false;
  }
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
  baselinePreviewItems.value = [];
  baselineLoading.value = false;
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
  if (
    requiresBaseline.value &&
    scopeIsComplete.value &&
    baselineLoading.value
  ) {
    ElMessage.warning('当前基线还在加载，请稍候再提交');
    return;
  }
  if (
    requiresBaseline.value &&
    scopeIsComplete.value &&
    baselinePreviewItems.value.length === 0
  ) {
    ElMessage.warning('当前产品子系统下暂无已生效基线，不能发起修订或删除任务');
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

watch(
  () => [formModel.task_type, formModel.product_id, formModel.subsystem],
  () => {
    void loadBaselinePreview();
  },
);

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
        <ElFormItem label="关联产品（可选）" prop="product_id">
          <ElSelect
            v-model="formModel.product_id"
            class="w-full"
            filterable
            clearable
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
        <ElFormItem label="子系统（可选）" prop="subsystem">
          <ElSelect
            v-model="formModel.subsystem"
            class="w-full"
            filterable
            clearable
            :disabled="!formModel.product_id"
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
          <UserSelector
            v-model="formModel.assignee_id"
            class="w-full"
            display-mode="select"
            :multiple="false"
            placeholder="请选择责任人"
          />
        </ElFormItem>
        <ElFormItem
          v-if="requiresBaseline && scopeHasSelection"
          label="当前基线"
        >
          <div
            class="w-full rounded-lg border border-dashed border-gray-300 bg-gray-50 p-3"
          >
            <ElAlert
              v-if="!scopeIsComplete"
              :closable="false"
              title="请先同时选择产品和子系统，才能查看当前基线；如果是公共任务，也可以直接留空范围继续创建"
              type="info"
            />
            <ElAlert
              v-else-if="baselineLoading"
              :closable="false"
              title="当前基线加载中，请稍候"
              type="info"
            />
            <ElAlert
              v-else-if="baselinePreviewItems.length === 0"
              :closable="false"
              title="当前产品 + 子系统下暂无已生效基线，不能发起此类任务"
              type="warning"
            />
            <template v-else>
              <div class="text-sm text-gray-700">
                当前已生效故障模式 {{ baselinePreviewItems.length }} 条
              </div>
              <div class="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
                <span
                  v-for="item in baselinePreviewNames"
                  :key="item"
                  class="rounded-full bg-white px-3 py-1"
                >
                  {{ item }}
                </span>
                <span
                  v-if="
                    baselinePreviewItems.length > baselinePreviewNames.length
                  "
                  class="rounded-full bg-white px-3 py-1"
                >
                  还有
                  {{
                    baselinePreviewItems.length - baselinePreviewNames.length
                  }}
                  条
                </span>
              </div>
            </template>
          </div>
        </ElFormItem>
        <ElFormItem v-else-if="requiresBaseline" label="当前基线">
          <div
            class="w-full rounded-lg border border-dashed border-gray-300 bg-gray-50 p-3 text-sm text-gray-500"
          >
            选择产品和子系统后可预览当前基线；留空则直接发起公共任务。
          </div>
        </ElFormItem>
      </ElForm>
    </div>
  </ZqDrawer>
</template>
