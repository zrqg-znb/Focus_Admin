<script lang="ts" setup>
import type { MasterResourceKind } from '../data';

import type {
  FailureModeDictOptions,
  HandlingMeasureItem,
  HuatuoDiagnosisItem,
  InterceptionStrategyItem,
  ObservationMethodItem,
  RelationItem,
  TestCaseItem,
} from '#/api/project-manager/failure_mode';

import { computed, nextTick, ref } from 'vue';

import { Link } from '@element-plus/icons-vue';
import { ElButton, ElMessage, ElTag } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createHandlingMeasureApi,
  createHuatuoDiagnosisApi,
  createInterceptionStrategyApi,
  createObservationMethodApi,
  createTestCaseApi,
  getHandlingMeasureDetailApi,
  getHuatuoDiagnosisDetailApi,
  getInterceptionStrategyDetailApi,
  getObservationMethodDetailApi,
  getTestCaseDetailApi,
  updateHandlingMeasureApi,
  updateHuatuoDiagnosisApi,
  updateInterceptionStrategyApi,
  updateObservationMethodApi,
  updateTestCaseApi,
} from '#/api/project-manager/failure_mode';
import { ZqDrawer } from '#/components/zq-drawer';

import {
  buildRelationItem,
  ensureOrderedRelationItems,
  getMasterResourceLabel,
  normalizeStringList,
  upsertRelationItem,
  useMasterFormSchema,
} from '../data';
import RelationSelectorDialog from './RelationSelectorDialog.vue';

defineOptions({ name: 'MasterDataDrawer' });

const props = withDefaults(
  defineProps<{
    allowNested?: boolean;
    dictOptions: FailureModeDictOptions;
  }>(),
  {
    allowNested: true,
  },
);

const emit = defineEmits<{
  success: [
    payload: {
      action: 'create' | 'edit';
      item: any;
      kind: MasterResourceKind;
      relationItem: RelationItem;
    },
  ];
}>();

const visible = ref(false);
const loading = ref(false);
const confirmLoading = ref(false);
const currentKind = ref<MasterResourceKind>('interception');
const mode = ref<'create' | 'edit'>('create');
const editingId = ref('');
const testCaseIds = ref<string[]>([]);
const testCaseItems = ref<RelationItem[]>([]);
const relationSelectorRef = ref<any>();
const nestedMasterDrawerRef = ref<any>();

const drawerTitle = computed(() => {
  const prefix = mode.value === 'create' ? '新增' : '编辑';
  return `${prefix}${getMasterResourceLabel(currentKind.value)}`;
});

const [Form, formApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: { class: 'w-full' },
  },
  schema: useMasterFormSchema('interception', props.dictOptions),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4 md:grid-cols-2',
});

function applySchema(kind: MasterResourceKind) {
  formApi.setState({ schema: useMasterFormSchema(kind, props.dictOptions) });
}

function getInitialValues(kind: MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      return { description: '', owner_ids: [] };
    }
    case 'interception': {
      return {
        interception_item: '',
        owner_ids: [],
        station: '',
        version_detection_html: '',
      };
    }
    case 'measure': {
      return {
        measure: '',
        measure_category: undefined,
        measure_detail_html: '',
        measure_effect: '',
        owner_ids: [],
      };
    }
    case 'observation': {
      return {
        log_id: '',
        log_keyword: '',
        log_path: '',
        monitor_type: undefined,
        owner_ids: [],
      };
    }
    default: {
      return {
        brief: '',
        cida_link: '',
        detail_html: '',
        owner_ids: [],
      };
    }
  }
}

function getDetailApi(kind: MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      return getHuatuoDiagnosisDetailApi;
    }
    case 'interception': {
      return getInterceptionStrategyDetailApi;
    }
    case 'measure': {
      return getHandlingMeasureDetailApi;
    }
    case 'observation': {
      return getObservationMethodDetailApi;
    }
    default: {
      return getTestCaseDetailApi;
    }
  }
}

function getCreateApi(kind: MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      return createHuatuoDiagnosisApi;
    }
    case 'interception': {
      return createInterceptionStrategyApi;
    }
    case 'measure': {
      return createHandlingMeasureApi;
    }
    case 'observation': {
      return createObservationMethodApi;
    }
    default: {
      return createTestCaseApi;
    }
  }
}

function getUpdateApi(kind: MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      return updateHuatuoDiagnosisApi;
    }
    case 'interception': {
      return updateInterceptionStrategyApi;
    }
    case 'measure': {
      return updateHandlingMeasureApi;
    }
    case 'observation': {
      return updateObservationMethodApi;
    }
    default: {
      return updateTestCaseApi;
    }
  }
}

function syncSelectedTestCaseItem(nextItem: RelationItem) {
  if (!testCaseIds.value.includes(nextItem.id)) {
    return;
  }
  testCaseItems.value = upsertRelationItem(testCaseItems.value, nextItem);
}

async function openCreate(kind: MasterResourceKind) {
  currentKind.value = kind;
  mode.value = 'create';
  editingId.value = '';
  loading.value = false;
  applySchema(kind);
  testCaseIds.value = [];
  testCaseItems.value = [];
  visible.value = true;
  await nextTick();
  await formApi.resetForm();
  formApi.setValues(getInitialValues(kind));
}

async function openEdit(
  kind: MasterResourceKind,
  record: string | { id: string },
) {
  currentKind.value = kind;
  mode.value = 'edit';
  editingId.value = typeof record === 'string' ? record : record.id;
  applySchema(kind);
  testCaseIds.value = [];
  testCaseItems.value = [];
  visible.value = true;
  await nextTick();
  loading.value = true;
  try {
    await formApi.resetForm();
    const detail = await getDetailApi(kind)(editingId.value);
    if (kind === 'interception') {
      const row = detail as InterceptionStrategyItem;
      formApi.setValues({
        interception_item: row.interception_item,
        owner_ids: row.owner_ids || [],
        station: row.station || '',
        version_detection_html: row.version_detection_html || '',
      });
      return;
    }
    if (kind === 'measure') {
      const row = detail as HandlingMeasureItem;
      formApi.setValues({
        measure: row.measure,
        measure_category: row.measure_category || undefined,
        measure_detail_html: row.measure_detail_html || '',
        measure_effect: row.measure_effect || '',
        owner_ids: row.owner_ids || [],
      });
      testCaseIds.value = normalizeStringList(row.test_case_ids || []);
      testCaseItems.value = ensureOrderedRelationItems(
        testCaseIds.value,
        row.test_case_items || [],
      );
      return;
    }
    if (kind === 'observation') {
      const row = detail as ObservationMethodItem;
      formApi.setValues({
        log_id: row.log_id || '',
        log_keyword: row.log_keyword || '',
        log_path: row.log_path || '',
        monitor_type: row.monitor_type || undefined,
        owner_ids: row.owner_ids || [],
      });
      return;
    }
    if (kind === 'huatuo') {
      const row = detail as HuatuoDiagnosisItem;
      formApi.setValues({
        description: row.description || '',
        owner_ids: row.owner_ids || [],
      });
      return;
    }
    const row = detail as TestCaseItem;
    formApi.setValues({
      brief: row.brief,
      cida_link: row.cida_link || '',
      detail_html: row.detail_html || '',
      owner_ids: row.owner_ids || [],
    });
  } finally {
    loading.value = false;
  }
}

function handleOpenRelationSelector() {
  relationSelectorRef.value?.open({
    kind: 'testCase',
    selectedIds: testCaseIds.value,
    selectedItems: testCaseItems.value,
  });
}

function handleRelationConfirm(payload: {
  ids: string[];
  items: RelationItem[];
}) {
  testCaseIds.value = normalizeStringList(payload.ids || []);
  testCaseItems.value = ensureOrderedRelationItems(
    testCaseIds.value,
    payload.items || [],
  );
}

function handleQuickCreate(kind: MasterResourceKind) {
  if (!props.allowNested) {
    return;
  }
  nestedMasterDrawerRef.value?.openCreate(kind);
}

function handleQuickEdit(payload: { id: string; kind: MasterResourceKind }) {
  if (!props.allowNested) {
    return;
  }
  nestedMasterDrawerRef.value?.openEdit(payload.kind, payload.id);
}

function handleNestedSuccess(payload: {
  action: 'create' | 'edit';
  item: any;
  kind: MasterResourceKind;
  relationItem: RelationItem;
}) {
  if (payload.kind !== 'testCase') {
    return;
  }
  const shouldSelect =
    payload.action === 'create' ||
    testCaseIds.value.includes(payload.relationItem.id);
  relationSelectorRef.value?.upsertSelection(
    payload.relationItem,
    shouldSelect,
  );
  relationSelectorRef.value?.reload();
  syncSelectedTestCaseItem(payload.relationItem);
}

async function handleConfirm() {
  const { valid } = await formApi.validate();
  if (!valid) {
    return;
  }

  confirmLoading.value = true;
  try {
    const values = await formApi.getValues<Record<string, any>>();
    const payload = { ...values };
    if (currentKind.value === 'measure') {
      payload.test_case_ids = [...testCaseIds.value];
    }

    let result: any;
    if (mode.value === 'create') {
      const requestApi = getCreateApi(currentKind.value) as (
        data: Record<string, any>,
      ) => Promise<any>;
      result = await requestApi(payload);
    } else {
      const requestApi = getUpdateApi(currentKind.value) as (
        id: string,
        data: Record<string, any>,
      ) => Promise<any>;
      result = await requestApi(editingId.value, payload);
    }

    ElMessage.success(mode.value === 'create' ? '创建成功' : '保存成功');
    visible.value = false;
    emit('success', {
      action: mode.value,
      item: result,
      kind: currentKind.value,
      relationItem: buildRelationItem(currentKind.value, result),
    });
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
    size="62%"
    @confirm="handleConfirm"
  >
    <div class="space-y-4 px-2 py-1">
      <div
        class="rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
      >
        <Form />
      </div>

      <div
        v-if="currentKind === 'measure'"
        class="rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
      >
        <div class="mb-4 flex items-center justify-between gap-3">
          <div>
            <div
              class="text-sm font-semibold text-[var(--el-text-color-primary)]"
            >
              关联测试用例
            </div>
            <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
              支持按关键词搜索、多选并直接快速新增或快编测试用例
            </div>
          </div>
          <ElButton
            :icon="Link"
            plain
            type="primary"
            @click="handleOpenRelationSelector"
          >
            选择测试用例
          </ElButton>
        </div>

        <div v-if="testCaseItems.length > 0" class="flex flex-wrap gap-2">
          <ElTag
            v-for="item in testCaseItems"
            :key="item.id"
            effect="light"
            type="info"
          >
            {{ item.label }}
          </ElTag>
        </div>
        <div
          v-else
          class="rounded-lg bg-[var(--el-fill-color-light)] px-4 py-6 text-sm text-[var(--el-text-color-secondary)]"
        >
          暂未关联测试用例。
        </div>
      </div>
    </div>
  </ZqDrawer>

  <RelationSelectorDialog
    ref="relationSelectorRef"
    @confirm="handleRelationConfirm"
    @quick-create="handleQuickCreate"
    @quick-edit="handleQuickEdit"
  />

  <MasterDataDrawer
    v-if="allowNested"
    ref="nestedMasterDrawerRef"
    :allow-nested="false"
    :dict-options="dictOptions"
    @success="handleNestedSuccess"
  />
</template>
