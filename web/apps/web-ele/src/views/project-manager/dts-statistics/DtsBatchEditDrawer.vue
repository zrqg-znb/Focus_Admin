<script lang="ts" setup>
import type { DtsFormFieldConfig } from './data';

import type {
  DtsBatchExtensionPatchPayload,
  DtsBatchSaveResponse,
  DtsDictOptions,
} from '#/api/project-manager/dts-statistics';

import { computed, reactive, ref, watch } from 'vue';

import {
  ElButton,
  ElCheckbox,
  ElEmpty,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTabPane,
  ElTabs,
} from 'element-plus';

import { batchSaveDtsExtension } from '#/api/project-manager/dts-statistics';
import { ZqDrawer } from '#/components/zq-drawer';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import {
  DTS_DEV_FORM_FIELDS,
  DTS_QA_FORM_FIELDS,
  DTS_TEST_FORM_FIELDS,
  fetchDtsDictOptionsCached,
  getDtsDictOptionsByKey,
  normalizeDtsStringListValue,
} from './data';

type EditTab = 'dev' | 'qa' | 'test';

const props = withDefaults(
  defineProps<{
    modelValue?: boolean;
    selectedDtsBizNos?: string[];
  }>(),
  {
    modelValue: false,
    selectedDtsBizNos: () => [],
  },
);

const emit = defineEmits<{
  success: [response: DtsBatchSaveResponse];
  'update:modelValue': [value: boolean];
}>();

const LINE_SPLIT_FIELDS = new Set(['dev_improvements', 'test_improvements']);

const FIELD_GROUPS: Record<EditTab, DtsFormFieldConfig[]> = {
  qa: DTS_QA_FORM_FIELDS,
  dev: DTS_DEV_FORM_FIELDS,
  test: DTS_TEST_FORM_FIELDS,
};

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const activeTab = ref<EditTab>('qa');
const confirmLoading = ref(false);
const dictOptions = ref<DtsDictOptions | null>(null);
const enabledFields = ref<string[]>([]);
const formValues = reactive<Record<string, any>>({});

function createEmptyFieldValue(field: DtsFormFieldConfig) {
  if (field.component === 'ApiSelect' && field.multiple) {
    return [];
  }
  if (field.component === 'Textarea' || field.component === 'Input') {
    return '';
  }
  return undefined;
}

function resetFormState() {
  enabledFields.value = [];
  Object.values(FIELD_GROUPS)
    .flat()
    .forEach((field) => {
      formValues[field.fieldName] = createEmptyFieldValue(field);
    });
}

function isFieldEnabled(fieldName: string) {
  return enabledFields.value.includes(fieldName);
}

function toggleField(fieldName: string, checked: boolean | number | string) {
  const enabled = Boolean(checked);
  const next = new Set(enabledFields.value);
  if (enabled) {
    next.add(fieldName);
  } else {
    next.delete(fieldName);
  }
  enabledFields.value = [...next];
}

function getSelectOptions(field: DtsFormFieldConfig) {
  if (!field.dictKey) {
    return [];
  }
  return getDtsDictOptionsByKey(dictOptions.value, field.dictKey);
}

function normalizeScalarValue(value: unknown) {
  const text = String(value ?? '').trim();
  return text || null;
}

function normalizeFieldValue(field: DtsFormFieldConfig) {
  const raw = formValues[field.fieldName];
  if (field.component === 'UserSelector') {
    return normalizeScalarValue(raw);
  }
  if (field.component === 'ApiSelect') {
    if (field.multiple) {
      return normalizeDtsStringListValue(raw);
    }
    return normalizeScalarValue(raw);
  }
  if (LINE_SPLIT_FIELDS.has(field.fieldName)) {
    return normalizeDtsStringListValue(raw);
  }
  return normalizeScalarValue(raw);
}

function buildSubmitData(): DtsBatchExtensionPatchPayload {
  const data: DtsBatchExtensionPatchPayload = {};
  Object.values(FIELD_GROUPS)
    .flat()
    .forEach((field) => {
      if (!isFieldEnabled(field.fieldName)) {
        return;
      }
      (data as Record<string, any>)[field.fieldName] =
        normalizeFieldValue(field);
    });
  return data;
}

async function ensureDictOptionsLoaded() {
  if (dictOptions.value) {
    return;
  }
  try {
    dictOptions.value = await fetchDtsDictOptionsCached();
  } catch (error) {
    console.error(error);
    dictOptions.value = null;
  }
}

const selectedCount = computed(() => props.selectedDtsBizNos.length);
const enabledFieldCount = computed(() => enabledFields.value.length);
const confirmDisabled = computed(
  () => selectedCount.value <= 0 || enabledFieldCount.value <= 0,
);
const drawerTitle = computed(
  () =>
    `批量填报${selectedCount.value > 0 ? `（已选 ${selectedCount.value} 条）` : ''}`,
);

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) {
      confirmLoading.value = false;
      return;
    }
    activeTab.value = 'qa';
    resetFormState();
    await ensureDictOptionsLoaded();
  },
  { immediate: true },
);

async function handleConfirm() {
  if (selectedCount.value <= 0) {
    ElMessage.warning('请先选择要批量填报的 DTS');
    return;
  }
  if (enabledFieldCount.value <= 0) {
    ElMessage.warning('请至少启用一个字段后再提交');
    return;
  }

  confirmLoading.value = true;
  try {
    const response = await batchSaveDtsExtension({
      defectNos: [...props.selectedDtsBizNos],
      fieldMask: [...enabledFields.value],
      data: buildSubmitData(),
    });
    emit('success', response);
  } catch (error) {
    console.error(error);
    ElMessage.error('批量保存失败，请稍后重试');
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
    size="42%"
    @confirm="handleConfirm"
  >
    <template #footer>
      <ElButton @click="visible = false">取消</ElButton>
      <ElButton
        type="primary"
        :disabled="confirmDisabled"
        :loading="confirmLoading"
        @click="handleConfirm"
      >
        确认批量保存
      </ElButton>
    </template>

    <div class="dts-batch-edit">
      <div class="dts-batch-edit__summary">
        <div class="dts-batch-edit__summary-item">
          <span class="dts-batch-edit__summary-label">作用范围</span>
          <strong>{{ selectedCount }}</strong>
          <span>条已选 DTS</span>
        </div>
        <div class="dts-batch-edit__summary-item">
          <span class="dts-batch-edit__summary-label">本次生效字段</span>
          <strong>{{ enabledFieldCount }}</strong>
          <span>项</span>
        </div>
      </div>

      <ElTabs v-model="activeTab" class="dts-batch-edit__tabs">
        <ElTabPane label="QA填报" name="qa">
          <div class="dts-batch-edit__panel">
            <div
              v-for="field in FIELD_GROUPS.qa"
              :key="field.fieldName"
              class="dts-batch-edit__row"
              :class="{ 'is-enabled': isFieldEnabled(field.fieldName) }"
            >
              <div class="dts-batch-edit__head">
                <ElCheckbox
                  :model-value="isFieldEnabled(field.fieldName)"
                  @change="toggleField(field.fieldName, $event)"
                >
                  应用该字段
                </ElCheckbox>
                <span class="dts-batch-edit__label">{{ field.label }}</span>
              </div>
              <div class="dts-batch-edit__control">
                <ElInput
                  v-if="field.component === 'Input'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :placeholder="field.placeholder"
                  clearable
                />
                <ElInput
                  v-else-if="field.component === 'Textarea'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :placeholder="field.placeholder"
                  type="textarea"
                  :rows="field.rows || 3"
                />
                <ElSelect
                  v-else-if="field.component === 'ApiSelect'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :multiple="Boolean(field.multiple)"
                  :placeholder="field.placeholder"
                  clearable
                  filterable
                  collapse-tags
                  collapse-tags-tooltip
                  class="w-full"
                >
                  <ElOption
                    v-for="option in getSelectOptions(field)"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </ElSelect>
                <UserSelector
                  v-else
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  display-mode="select"
                  :multiple="false"
                  :placeholder="field.placeholder"
                />
              </div>
            </div>
          </div>
        </ElTabPane>

        <ElTabPane label="开发填报" name="dev">
          <div class="dts-batch-edit__panel">
            <div
              v-for="field in FIELD_GROUPS.dev"
              :key="field.fieldName"
              class="dts-batch-edit__row"
              :class="{ 'is-enabled': isFieldEnabled(field.fieldName) }"
            >
              <div class="dts-batch-edit__head">
                <ElCheckbox
                  :model-value="isFieldEnabled(field.fieldName)"
                  @change="toggleField(field.fieldName, $event)"
                >
                  应用该字段
                </ElCheckbox>
                <span class="dts-batch-edit__label">{{ field.label }}</span>
              </div>
              <div class="dts-batch-edit__control">
                <ElInput
                  v-if="field.component === 'Input'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :placeholder="field.placeholder"
                  clearable
                />
                <ElInput
                  v-else-if="field.component === 'Textarea'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :placeholder="field.placeholder"
                  type="textarea"
                  :rows="field.rows || 3"
                />
                <ElSelect
                  v-else-if="field.component === 'ApiSelect'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :multiple="Boolean(field.multiple)"
                  :placeholder="field.placeholder"
                  clearable
                  filterable
                  collapse-tags
                  collapse-tags-tooltip
                  class="w-full"
                >
                  <ElOption
                    v-for="option in getSelectOptions(field)"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </ElSelect>
                <UserSelector
                  v-else
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  display-mode="select"
                  :multiple="false"
                  :placeholder="field.placeholder"
                />
              </div>
            </div>
          </div>
        </ElTabPane>

        <ElTabPane label="测试填报" name="test">
          <div class="dts-batch-edit__panel">
            <div
              v-for="field in FIELD_GROUPS.test"
              :key="field.fieldName"
              class="dts-batch-edit__row"
              :class="{ 'is-enabled': isFieldEnabled(field.fieldName) }"
            >
              <div class="dts-batch-edit__head">
                <ElCheckbox
                  :model-value="isFieldEnabled(field.fieldName)"
                  @change="toggleField(field.fieldName, $event)"
                >
                  应用该字段
                </ElCheckbox>
                <span class="dts-batch-edit__label">{{ field.label }}</span>
              </div>
              <div class="dts-batch-edit__control">
                <ElInput
                  v-if="field.component === 'Input'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :placeholder="field.placeholder"
                  clearable
                />
                <ElInput
                  v-else-if="field.component === 'Textarea'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :placeholder="field.placeholder"
                  type="textarea"
                  :rows="field.rows || 3"
                />
                <ElSelect
                  v-else-if="field.component === 'ApiSelect'"
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  :multiple="Boolean(field.multiple)"
                  :placeholder="field.placeholder"
                  clearable
                  filterable
                  collapse-tags
                  collapse-tags-tooltip
                  class="w-full"
                >
                  <ElOption
                    v-for="option in getSelectOptions(field)"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </ElSelect>
                <UserSelector
                  v-else
                  v-model="formValues[field.fieldName]"
                  :disabled="!isFieldEnabled(field.fieldName)"
                  display-mode="select"
                  :multiple="false"
                  :placeholder="field.placeholder"
                />
              </div>
            </div>
          </div>
        </ElTabPane>
      </ElTabs>

      <ElEmpty
        v-if="selectedCount <= 0"
        description="请先在列表中选择要批量填报的 DTS"
      />
    </div>
  </ZqDrawer>
</template>

<style scoped>
.dts-batch-edit {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 0 8px 8px;
}

.dts-batch-edit__summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.dts-batch-edit__summary-item {
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  padding: 12px 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f7fb 100%);
  color: #334155;
}

.dts-batch-edit__summary-label {
  display: block;
  margin-bottom: 4px;
  color: #64748b;
  font-size: 12px;
}

.dts-batch-edit__tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.dts-batch-edit__panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dts-batch-edit__row {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  background: #ffffff;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.dts-batch-edit__row.is-enabled {
  border-color: #93c5fd;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.08);
}

.dts-batch-edit__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.dts-batch-edit__label {
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
}

.dts-batch-edit__control {
  padding-left: 24px;
}

.dts-batch-edit__control :deep(.el-select),
.dts-batch-edit__control :deep(.el-input),
.dts-batch-edit__control :deep(.w-full) {
  width: 100%;
}
</style>
