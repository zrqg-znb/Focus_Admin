<script lang="ts" setup>
import type { MasterResourceKind } from '../data';

import type {
  FailureModeDictOptions,
  FailureModeItem,
  FailureModePayload,
  RelationItem,
} from '#/api/failure_mode';

import { computed, nextTick, ref } from 'vue';

import { Link } from '@element-plus/icons-vue';
import { ElButton, ElMessage, ElTag } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createFailureModeApi,
  getFailureModeDetailApi,
  updateFailureModeApi,
} from '#/api/failure_mode';
import { ZqDrawer } from '#/components/zq-drawer';

import {
  ensureOrderedRelationItems,
  getMasterResourceLabel,
  normalizeStringList,
  removeRelationItem,
  upsertRelationItem,
  useFailureModeFormSchema,
} from '../data';
import MasterDataDrawer from './MasterDataDrawer.vue';
import RelationSelectorDialog from './RelationSelectorDialog.vue';
import StringListEditor from './StringListEditor.vue';

defineOptions({ name: 'FailureModeDrawer' });

const props = defineProps<{
  dictOptions: FailureModeDictOptions;
}>();

const emit = defineEmits<{
  success: [item: FailureModeItem];
}>();

const visible = ref(false);
const loading = ref(false);
const confirmLoading = ref(false);
const mode = ref<'create' | 'edit'>('create');
const editingId = ref('');
const symptoms = ref<string[]>([]);
const relatedDtsNos = ref<string[]>([]);
const interceptionStrategyIds = ref<string[]>([]);
const interceptionStrategyItems = ref<RelationItem[]>([]);
const handlingMeasureIds = ref<string[]>([]);
const handlingMeasureItems = ref<RelationItem[]>([]);
const observationMethodIds = ref<string[]>([]);
const observationMethodItems = ref<RelationItem[]>([]);
const huatuoDiagnosisIds = ref<string[]>([]);
const huatuoDiagnosisItems = ref<RelationItem[]>([]);
const currentSelectorKind = ref<MasterResourceKind>('interception');
const relationSelectorRef = ref<any>();
const masterDrawerRef = ref<any>();

const drawerTitle = computed(() =>
  mode.value === 'create' ? '新增故障模式' : '编辑故障模式',
);

const relationCardConfigs = computed(() => [
  {
    kind: 'interception' as MasterResourceKind,
    ids: interceptionStrategyIds.value,
    items: interceptionStrategyItems.value,
    label: getMasterResourceLabel('interception'),
    description: '按关键词搜索产线拦截策略并多选关联。',
  },
  {
    kind: 'measure' as MasterResourceKind,
    ids: handlingMeasureIds.value,
    items: handlingMeasureItems.value,
    label: getMasterResourceLabel('measure'),
    description: '可直接快建故障处理措施，并带测试用例关联。',
  },
  {
    kind: 'observation' as MasterResourceKind,
    ids: observationMethodIds.value,
    items: observationMethodItems.value,
    label: getMasterResourceLabel('observation'),
    description: '维测手段支持日志 ID、关键词、路径等维度维护。',
  },
  {
    kind: 'huatuo' as MasterResourceKind,
    ids: huatuoDiagnosisIds.value,
    items: huatuoDiagnosisItems.value,
    label: getMasterResourceLabel('huatuo'),
    description: '诊断方案支持沉淀为全局主数据，复用到不同故障模式。',
  },
]);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: { class: 'w-full' },
    labelClass: 'whitespace-nowrap',
    labelWidth: 156,
  },
  schema: useFailureModeFormSchema(props.dictOptions),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-6 xl:grid-cols-2',
});

function applySchema() {
  formApi.setState({ schema: useFailureModeFormSchema(props.dictOptions) });
}

function getRelationState(kind: MasterResourceKind) {
  switch (kind) {
    case 'interception': {
      return {
        ids: interceptionStrategyIds,
        items: interceptionStrategyItems,
      };
    }
    case 'measure': {
      return {
        ids: handlingMeasureIds,
        items: handlingMeasureItems,
      };
    }
    case 'observation': {
      return {
        ids: observationMethodIds,
        items: observationMethodItems,
      };
    }
    default: {
      return {
        ids: huatuoDiagnosisIds,
        items: huatuoDiagnosisItems,
      };
    }
  }
}

function resetRelations() {
  interceptionStrategyIds.value = [];
  interceptionStrategyItems.value = [];
  handlingMeasureIds.value = [];
  handlingMeasureItems.value = [];
  observationMethodIds.value = [];
  observationMethodItems.value = [];
  huatuoDiagnosisIds.value = [];
  huatuoDiagnosisItems.value = [];
}

async function openCreate() {
  mode.value = 'create';
  editingId.value = '';
  symptoms.value = [];
  relatedDtsNos.value = [];
  resetRelations();
  applySchema();
  visible.value = true;
  await nextTick();
  await formApi.resetForm();
  formApi.setValues({
    author_ids: [],
    brief: '',
    chips: [],
    detectability: undefined,
    effect_html: '',
    fault_categories: [],
    functional_safety_level: undefined,
    module: undefined,
    occurrence_frequency: undefined,
    root_cause_html: '',
    severity: undefined,
    status: undefined,
    subsystem: undefined,
  });
}

async function openEdit(record: string | { id: string }) {
  mode.value = 'edit';
  editingId.value = typeof record === 'string' ? record : record.id;
  visible.value = true;
  await nextTick();
  loading.value = true;
  resetRelations();
  applySchema();
  try {
    await formApi.resetForm();
    const detail = await getFailureModeDetailApi(editingId.value);
    formApi.setValues({
      author_ids: detail.author_ids || [],
      brief: detail.brief,
      chips: detail.chips || [],
      detectability: detail.detectability || undefined,
      effect_html: detail.effect_html || '',
      fault_categories: detail.fault_categories || [],
      functional_safety_level: detail.functional_safety_level || undefined,
      module: detail.module || undefined,
      occurrence_frequency: detail.occurrence_frequency || undefined,
      root_cause_html: detail.root_cause_html || '',
      severity: detail.severity || undefined,
      status: detail.status || undefined,
      subsystem: detail.subsystem || undefined,
    });
    symptoms.value = normalizeStringList(detail.symptoms || []);
    relatedDtsNos.value = normalizeStringList(detail.related_dts_nos || []);
    interceptionStrategyIds.value = normalizeStringList(
      detail.interception_strategy_ids || [],
    );
    interceptionStrategyItems.value = ensureOrderedRelationItems(
      interceptionStrategyIds.value,
      detail.interception_strategy_items || [],
    );
    handlingMeasureIds.value = normalizeStringList(
      detail.handling_measure_ids || [],
    );
    handlingMeasureItems.value = ensureOrderedRelationItems(
      handlingMeasureIds.value,
      detail.handling_measure_items || [],
    );
    observationMethodIds.value = normalizeStringList(
      detail.observation_method_ids || [],
    );
    observationMethodItems.value = ensureOrderedRelationItems(
      observationMethodIds.value,
      detail.observation_method_items || [],
    );
    huatuoDiagnosisIds.value = normalizeStringList(
      detail.huatuo_diagnosis_ids || [],
    );
    huatuoDiagnosisItems.value = ensureOrderedRelationItems(
      huatuoDiagnosisIds.value,
      detail.huatuo_diagnosis_items || [],
    );
  } finally {
    loading.value = false;
  }
}

function openRelationSelector(kind: MasterResourceKind) {
  currentSelectorKind.value = kind;
  const relationState = getRelationState(kind);
  relationSelectorRef.value?.open({
    kind,
    selectedIds: relationState.ids.value,
    selectedItems: relationState.items.value,
  });
}

function removeRelationSelection(kind: MasterResourceKind, id: string) {
  const relationState = getRelationState(kind);
  relationState.ids.value = relationState.ids.value.filter(
    (item) => item !== id,
  );
  relationState.items.value = removeRelationItem(relationState.items.value, id);
}

function handleRelationConfirm(payload: {
  ids: string[];
  items: RelationItem[];
  kind: MasterResourceKind;
}) {
  const relationState = getRelationState(payload.kind);
  relationState.ids.value = normalizeStringList(payload.ids || []);
  relationState.items.value = ensureOrderedRelationItems(
    relationState.ids.value,
    payload.items || [],
  );
}

function handleQuickCreate(kind: MasterResourceKind) {
  masterDrawerRef.value?.openCreate(kind);
}

function handleQuickEdit(payload: { id: string; kind: MasterResourceKind }) {
  masterDrawerRef.value?.openEdit(payload.kind, payload.id);
}

function handleMasterDataSuccess(payload: {
  action: 'create' | 'edit';
  kind: MasterResourceKind;
  relationItem: RelationItem;
}) {
  const relationState = getRelationState(payload.kind);
  const shouldSelect =
    payload.action === 'create' ||
    relationState.ids.value.includes(payload.relationItem.id);
  relationSelectorRef.value?.upsertSelection(
    payload.relationItem,
    shouldSelect,
  );
  relationSelectorRef.value?.reload();
  if (relationState.ids.value.includes(payload.relationItem.id)) {
    relationState.items.value = upsertRelationItem(
      relationState.items.value,
      payload.relationItem,
    );
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
    const payload: FailureModePayload = {
      ...(values as FailureModePayload),
      handling_measure_ids: [...handlingMeasureIds.value],
      huatuo_diagnosis_ids: [...huatuoDiagnosisIds.value],
      interception_strategy_ids: [...interceptionStrategyIds.value],
      observation_method_ids: [...observationMethodIds.value],
      related_dts_nos: [...relatedDtsNos.value],
      symptoms: [...symptoms.value],
    };

    const result =
      mode.value === 'create'
        ? await createFailureModeApi(payload)
        : await updateFailureModeApi(editingId.value, payload);

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
    size="74%"
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
          v-model="symptoms"
          add-text="新增故障现象"
          item-label="故障现象"
          label="故障现象"
          placeholder="请输入一条故障现象描述"
        />
        <StringListEditor
          v-model="relatedDtsNos"
          add-text="新增问题单号"
          item-label="问题单号"
          label="关联问题单"
          placeholder="请输入 dts_no"
        />
      </div>

      <div
        class="rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
      >
        <div class="mb-4 flex items-center justify-between gap-3">
          <div>
            <div
              class="text-sm font-semibold text-[var(--el-text-color-primary)]"
            >
              关联主数据
            </div>
            <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
              故障模式通过全局主数据建立复用关系，支持搜索、多选和当前上下文快速新增。
            </div>
          </div>
          <ElTag type="info">
            已关联
            {{
              relationCardConfigs.reduce(
                (sum, item) => sum + item.ids.length,
                0,
              )
            }}
            项
          </ElTag>
        </div>

        <div class="grid gap-4 xl:grid-cols-2">
          <div
            v-for="card in relationCardConfigs"
            :key="card.kind"
            class="rounded-xl border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] p-4"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <div>
                <div
                  class="text-sm font-semibold text-[var(--el-text-color-primary)]"
                >
                  {{ card.label }}
                </div>
                <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
                  {{ card.description }}
                </div>
              </div>
              <ElButton
                :icon="Link"
                plain
                type="primary"
                @click="openRelationSelector(card.kind)"
              >
                选择
              </ElButton>
            </div>

            <div v-if="card.items.length > 0" class="flex flex-wrap gap-2">
              <ElTag
                v-for="item in card.items"
                :key="item.id"
                closable
                effect="light"
                type="info"
                @close="removeRelationSelection(card.kind, item.id)"
              >
                {{ item.label }}
              </ElTag>
            </div>
            <div
              v-else
              class="rounded-lg bg-[var(--el-fill-color-blank)] px-4 py-6 text-sm text-[var(--el-text-color-secondary)]"
            >
              暂未关联{{ card.label }}。
            </div>
          </div>
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
    ref="masterDrawerRef"
    :dict-options="dictOptions"
    @success="handleMasterDataSuccess"
  />
</template>
