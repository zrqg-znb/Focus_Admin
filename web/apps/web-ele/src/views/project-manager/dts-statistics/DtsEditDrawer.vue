<script lang="ts" setup>
import type {
  DtsExtensionSavePayload,
  DtsMergedDefect,
} from '#/api/project-manager/dts-statistics';

import { computed, ref, watch } from 'vue';

import { ElMessage, ElTabPane, ElTabs } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { saveDtsExtension } from '#/api/project-manager/dts-statistics';
import { ZqDrawer } from '#/components/zq-drawer';

import { useDevFormSchema, useQaFormSchema, useTestFormSchema } from './data';

type EditTab = 'dev' | 'qa' | 'test';

const props = withDefaults(
  defineProps<{
    initialTab?: EditTab;
    modelValue?: boolean;
    row?: DtsMergedDefect | null;
  }>(),
  {
    modelValue: false,
    row: null,
    initialTab: 'qa',
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

const activeTab = ref<EditTab>('qa');
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

const drawerTitle = computed(() => {
  const defectNo = props.row?.defectNo || '';
  const prefix = '问题单填报';
  return defectNo ? `${prefix} - ${defectNo}` : prefix;
});

function normalizeStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    const result: string[] = [];
    const seen = new Set<string>();
    value.forEach((item) => {
      const text = String(item || '').trim();
      if (!text || seen.has(text)) {
        return;
      }
      seen.add(text);
      result.push(text);
    });
    return result;
  }

  const text = String(value || '').trim();
  if (!text) {
    return [];
  }

  const parts = text.split(/\r?\n|,|，/g);
  const result: string[] = [];
  const seen = new Set<string>();
  parts.forEach((part) => {
    const item = String(part || '').trim();
    if (!item || seen.has(item)) {
      return;
    }
    seen.add(item);
    result.push(item);
  });
  return result;
}

function joinLines(value: unknown): string {
  if (!Array.isArray(value)) {
    return String(value || '').trim();
  }
  return value
    .map((item) => String(item || '').trim())
    .filter(Boolean)
    .join('\n');
}

function syncFormValues() {
  const row = props.row;
  if (!row) {
    qaFormApi.resetForm();
    devFormApi.resetForm();
    testFormApi.resetForm();
    return;
  }
  qaFormApi.setValues(row);
  devFormApi.setValues({
    ...row,
    dev_improvements: joinLines(row.dev_improvements),
  });
  testFormApi.setValues({
    ...row,
    test_improvements: joinLines(row.test_improvements),
  });
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      activeTab.value = props.initialTab || 'qa';
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

async function validateAllForms() {
  const qaResult = await qaFormApi.validate();
  if (!qaResult.valid) {
    activeTab.value = 'qa';
    return false;
  }
  const devResult = await devFormApi.validate();
  if (!devResult.valid) {
    activeTab.value = 'dev';
    return false;
  }
  const testResult = await testFormApi.validate();
  if (!testResult.valid) {
    activeTab.value = 'test';
    return false;
  }
  return true;
}

async function handleConfirm() {
  const defectNo = props.row?.defectNo;
  if (!defectNo) {
    ElMessage.warning('未获取到 defectNo，无法保存');
    return;
  }

  const ok = await validateAllForms();
  if (!ok) {
    return;
  }

  confirmLoading.value = true;
  try {
    const qaValues = await qaFormApi.getValues<Record<string, any>>();
    const devValues = await devFormApi.getValues<Record<string, any>>();
    const testValues = await testFormApi.getValues<Record<string, any>>();

    const payload: DtsExtensionSavePayload = {
      ...qaValues,
      ...devValues,
      ...testValues,
      dev_sub_category: normalizeStringList(devValues.dev_sub_category),
      dev_improvements: normalizeStringList(devValues.dev_improvements),
      test_miss_reason: normalizeStringList(testValues.test_miss_reason),
      test_improvements: normalizeStringList(testValues.test_improvements),
    };

    await saveDtsExtension(defectNo, payload);
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
    <div class="mx-4 pb-2">
      <ElTabs v-model="activeTab" class="dts-edit-tabs">
        <ElTabPane label="QA填报" name="qa">
          <QaForm />
        </ElTabPane>
        <ElTabPane label="开发填报" name="dev">
          <DevForm />
        </ElTabPane>
        <ElTabPane label="测试填报" name="test">
          <TestForm />
        </ElTabPane>
      </ElTabs>
    </div>
  </ZqDrawer>
</template>
