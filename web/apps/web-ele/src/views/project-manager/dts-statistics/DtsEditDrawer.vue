<script lang="ts" setup>
import type {
  DtsExtensionSavePayload,
  DtsMergedDefect,
} from '#/api/project-manager/dts-statistics';

import { computed, ref, watch } from 'vue';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { saveDtsExtension } from '#/api/project-manager/dts-statistics';
import { ZqDrawer } from '#/components/zq-drawer';

import { useDevFormSchema, useQaFormSchema, useTestFormSchema } from './data';

type EditType = 'dev' | 'qa' | 'test';

const props = withDefaults(
  defineProps<{
    editType?: EditType;
    modelValue?: boolean;
    row?: DtsMergedDefect | null;
  }>(),
  {
    editType: 'qa',
    modelValue: false,
    row: null,
  },
);

const emit = defineEmits<{
  success: [];
  'update:modelValue': [value: boolean];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const confirmLoading = ref(false);

const [QaForm, qaFormApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: { class: 'w-full' },
  },
  schema: useQaFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

const [DevForm, devFormApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: { class: 'w-full' },
  },
  schema: useDevFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

const [TestForm, testFormApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: { class: 'w-full' },
  },
  schema: useTestFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

const activeFormApi = computed(() => {
  if (props.editType === 'dev') return devFormApi;
  if (props.editType === 'test') return testFormApi;
  return qaFormApi;
});

const activeFormComponent = computed(() => {
  if (props.editType === 'dev') return DevForm;
  if (props.editType === 'test') return TestForm;
  return QaForm;
});

const drawerTitle = computed(() => {
  const defectNo = props.row?.defectNo || '';
  const prefixMap: Record<EditType, string> = {
    dev: '开发填报',
    qa: 'QA填报',
    test: '测试填报',
  };
  const prefix = prefixMap[props.editType];
  return defectNo ? `${prefix} - ${defectNo}` : prefix;
});

function syncFormValues() {
  const row = props.row;
  if (!row) {
    qaFormApi.resetForm();
    devFormApi.resetForm();
    testFormApi.resetForm();
    return;
  }
  qaFormApi.setValues(row);
  devFormApi.setValues(row);
  testFormApi.setValues(row);
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      syncFormValues();
    } else {
      confirmLoading.value = false;
    }
  },
);

watch(
  () => props.row,
  () => {
    if (props.modelValue) {
      syncFormValues();
    }
  },
  { deep: true },
);

async function handleConfirm() {
  const defectNo = props.row?.defectNo;
  if (!defectNo) {
    ElMessage.warning('未获取到 defectNo，无法保存');
    return;
  }

  const { valid } = await activeFormApi.value.validate();
  if (!valid) {
    return;
  }

  confirmLoading.value = true;
  try {
    const values =
      await activeFormApi.value.getValues<DtsExtensionSavePayload>();
    await saveDtsExtension(defectNo, values);
    ElMessage.success('保存成功');
    visible.value = false;
    emit('success');
  } catch (error) {
    console.error(error);
  } finally {
    confirmLoading.value = false;
  }
}
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :confirm-loading="confirmLoading"
    :title="drawerTitle"
    @confirm="handleConfirm"
  >
    <component :is="activeFormComponent" class="mx-4" />
  </ZqDrawer>
</template>
