<script lang="ts" setup>
import type {
  FailureModeSubsystemConfigItem,
  FailureModeSubsystemConfigPayload,
} from '#/api/failure_mode';

import { computed, nextTick, ref } from 'vue';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createFailureModeSubsystemConfigApi,
  getFailureModeSubsystemConfigDetailApi,
  updateFailureModeSubsystemConfigApi,
} from '#/api/failure_mode';
import { ZqDrawer } from '#/components/zq-drawer';

import { useSubsystemConfigFormSchema } from '../data';
import StringListEditor from './StringListEditor.vue';

defineOptions({ name: 'SubsystemConfigDrawer' });

const emit = defineEmits<{
  success: [item: FailureModeSubsystemConfigItem];
}>();

const visible = ref(false);
const loading = ref(false);
const confirmLoading = ref(false);
const mode = ref<'create' | 'edit'>('create');
const editingId = ref('');
const moduleOptions = ref<string[]>([]);
const chipOptions = ref<string[]>([]);

const drawerTitle = computed(() =>
  mode.value === 'create' ? '新增子系统配置' : '编辑子系统配置',
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: { class: 'w-full' },
    labelClass: 'whitespace-nowrap',
    labelWidth: 120,
  },
  schema: useSubsystemConfigFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-6',
});

async function openCreate() {
  mode.value = 'create';
  editingId.value = '';
  loading.value = false;
  moduleOptions.value = [];
  chipOptions.value = [];
  visible.value = true;
  await nextTick();
  await formApi.resetForm();
  formApi.setValues({ subsystem: '' });
}

async function openEdit(record: string | { id: string }) {
  mode.value = 'edit';
  editingId.value = typeof record === 'string' ? record : record.id;
  visible.value = true;
  await nextTick();
  loading.value = true;
  try {
    await formApi.resetForm();
    const detail = await getFailureModeSubsystemConfigDetailApi(
      editingId.value,
    );
    formApi.setValues({ subsystem: detail.subsystem });
    moduleOptions.value = [...(detail.module_options || [])];
    chipOptions.value = [...(detail.chip_options || [])];
  } finally {
    loading.value = false;
  }
}

async function handleConfirm() {
  const { valid } = await formApi.validate();
  if (!valid) {
    return;
  }

  confirmLoading.value = true;
  try {
    const values = await formApi.getValues<Record<string, any>>();
    const payload: FailureModeSubsystemConfigPayload = {
      subsystem: String(values.subsystem || '').trim(),
      module_options: [...moduleOptions.value],
      chip_options: [...chipOptions.value],
    };
    const result =
      mode.value === 'create'
        ? await createFailureModeSubsystemConfigApi(payload)
        : await updateFailureModeSubsystemConfigApi(editingId.value, payload);
    ElMessage.success(mode.value === 'create' ? '创建成功' : '保存成功');
    visible.value = false;
    emit('success', result);
  } finally {
    confirmLoading.value = false;
  }
}

defineExpose({
  openCreate,
  openEdit,
});
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :confirm-loading="confirmLoading"
    :loading="loading"
    :title="drawerTitle"
    size="52%"
    @confirm="handleConfirm"
  >
    <div class="space-y-4 px-2 py-1">
      <div
        class="rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
      >
        <Form />
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <StringListEditor
          v-model="moduleOptions"
          add-text="新增模块选项"
          item-label="模块选项"
          label="模块选项"
          placeholder="请输入模块名称"
        />
        <StringListEditor
          v-model="chipOptions"
          add-text="新增芯片选项"
          item-label="芯片选项"
          label="芯片选项"
          placeholder="请输入芯片名称"
        />
      </div>
    </div>
  </ZqDrawer>
</template>
