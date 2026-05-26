<script lang="ts" setup>
import type { MasterResourceKind } from '../data';

import type {
  FailureModeDictOptions,
  FailureModeItem,
  FailureModePayload,
  FailureModeScopeBinding,
  FailureModeSubsystemConfigOptions,
  RelationItem,
} from '#/api/failure_mode';

import { computed, nextTick, ref, watch } from 'vue';

import { Link } from '@element-plus/icons-vue';
import {
  ElButton,
  ElCheckbox,
  ElCheckboxGroup,
  ElMessage,
  ElSwitch,
  ElTag,
} from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createFailureModeApi,
  getFailureModeDetailApi,
  updateFailureModeApi,
} from '#/api/failure_mode';
import { ZqDrawer } from '#/components/zq-drawer';

import {
  ensureOrderedRelationItems,
  filterRelationItemsBySubtitle,
  normalizeStringList,
  resolveSubsystemScopedOptions,
  upsertRelationItem,
  useFailureModeFormSchema,
} from '../data';
import MasterDataDrawer from './MasterDataDrawer.vue';
import RelationSelectorDialog from './RelationSelectorDialog.vue';
import ScopeBindingEditor from './ScopeBindingEditor.vue';
import StringListEditor from './StringListEditor.vue';

defineOptions({ name: 'FailureModeDrawer' });

const props = defineProps<{
  createHandler?: (payload: FailureModePayload) => Promise<FailureModeItem>;
  dictOptions: FailureModeDictOptions;
  hideStatusField?: boolean;
  subsystemConfigOptions: FailureModeSubsystemConfigOptions;
  updateHandler?: (
    id: string,
    payload: FailureModePayload,
  ) => Promise<FailureModeItem>;
}>();
const emit = defineEmits<{
  success: [item: FailureModeItem];
}>();

const visible = ref(false);
const loading = ref(false);
const confirmLoading = ref(false);
const mode = ref<'create' | 'edit' | 'view'>('create');
const editingId = ref('');
const selectedSubsystem = ref<string>();
const relatedDtsNos = ref<string[]>([]);
const scopeBindings = ref<FailureModeScopeBinding[]>([]);
const interceptionRequired = ref(false);
const huatuoRequired = ref(false);
const requiredHandlingMeasureCategories = ref<string[]>([]);
const requiredObservationMethodTypes = ref<string[]>([]);
const interceptionStrategyIds = ref<string[]>([]);
const interceptionStrategyItems = ref<RelationItem[]>([]);
const handlingMeasureIds = ref<string[]>([]);
const handlingMeasureItems = ref<RelationItem[]>([]);
const observationMethodIds = ref<string[]>([]);
const observationMethodItems = ref<RelationItem[]>([]);
const huatuoDiagnosisIds = ref<string[]>([]);
const huatuoDiagnosisItems = ref<RelationItem[]>([]);
const relationSelectorRef = ref<any>();
const masterDrawerRef = ref<any>();
type FailureModeFormValues = {
  author_ids: string[];
  brief: string;
  chips: string[];
  detectability?: string;
  effect_html: string;
  fault_categories: string[];
  functional_safety_level?: string;
  module?: string;
  occurrence_frequency?: string;
  root_cause_html: string;
  severity?: string;
  status?: string;
  subsystem?: string;
  symptoms: string[];
};

const formValueFallbacks = ref<{
  chips: string[];
  fault_categories: string[];
  symptoms: string[];
}>({
  chips: [],
  fault_categories: [],
  symptoms: [],
});

const drawerTitle = computed(() => {
  if (mode.value === 'create') {
    return '新增故障模式';
  }
  if (mode.value === 'view') {
    return '故障模式详情';
  }
  return '编辑故障模式';
});
const isReadonly = computed(() => mode.value === 'view');

function getFormCommonConfig() {
  return {
    colon: true,
    componentProps: { class: 'w-full' },
    disabled: isReadonly.value,
    labelClass: 'whitespace-nowrap',
    labelWidth: 156,
  };
}

const handlingCategoryOptions = computed(() => {
  return props.dictOptions.measure_category;
});

const observationTypeOptions = computed(() => {
  return props.dictOptions.monitor_type;
});

const selectedRelationCount = computed(() => {
  return (
    interceptionStrategyIds.value.length +
    handlingMeasureIds.value.length +
    observationMethodIds.value.length +
    huatuoDiagnosisIds.value.length
  );
});

function createDefaultFormValues(
  detail: Partial<FailureModeItem> = {},
): FailureModeFormValues {
  return {
    author_ids: detail.author_ids || [],
    brief: detail.brief || '',
    chips: normalizeStringList(detail.chips || []),
    detectability: detail.detectability || undefined,
    effect_html: detail.effect_html || '',
    fault_categories: normalizeStringList(detail.fault_categories || []),
    functional_safety_level: detail.functional_safety_level || undefined,
    module: detail.module || undefined,
    occurrence_frequency: detail.occurrence_frequency || undefined,
    root_cause_html: detail.root_cause_html || '',
    severity: detail.severity || undefined,
    status: detail.status || undefined,
    subsystem: detail.subsystem || undefined,
    symptoms: normalizeStringList(detail.symptoms || []),
  };
}

const [Form, formApi] = useVbenForm({
  commonConfig: getFormCommonConfig(),
  schema: useFailureModeFormSchema(
    props.dictOptions,
    props.subsystemConfigOptions,
    selectedSubsystem.value,
    undefined,
    {
      hideStatusField: props.hideStatusField,
      valueFallbacks: formValueFallbacks.value,
    },
  ),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-6 xl:grid-cols-2',
});

function applySchema() {
  formApi.setState({
    commonConfig: getFormCommonConfig(),
    schema: useFailureModeFormSchema(
      props.dictOptions,
      props.subsystemConfigOptions,
      selectedSubsystem.value,
      (value) => {
        void handleSubsystemChange(value);
      },
      {
        hideStatusField: props.hideStatusField,
        valueFallbacks: formValueFallbacks.value,
      },
    ),
  });
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

async function clearInitialValidationState() {
  await nextTick();
  await nextTick();
  await formApi.resetValidate?.();
}

function normalizeScopeBindingsForSubmit(
  values: FailureModeScopeBinding[] = [],
  selectedSubsystem?: string,
) {
  const items: FailureModeScopeBinding[] = [];
  const seen = new Set<string>();
  const normalizedSubsystem = String(selectedSubsystem || '').trim();
  let hasIncomplete = false;

  values.forEach((item) => {
    const productId = String(item.product_id || '').trim();
    const productName = String(item.product_name || '').trim();

    if (!productId) {
      return;
    }
    if (!normalizedSubsystem) {
      hasIncomplete = true;
      return;
    }

    const key = productId;
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    items.push({
      product_id: productId,
      subsystem: normalizedSubsystem,
      product_name: productName || null,
    });
  });

  return {
    hasIncomplete,
    items,
  };
}

function isRelationKindEnabled(kind: MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      return huatuoRequired.value;
    }
    case 'interception': {
      return interceptionRequired.value;
    }
    case 'measure': {
      return requiredHandlingMeasureCategories.value.length > 0;
    }
    case 'observation': {
      return requiredObservationMethodTypes.value.length > 0;
    }
    default: {
      return true;
    }
  }
}

function isRelationItemAllowed(kind: MasterResourceKind, item: RelationItem) {
  if (kind === 'measure') {
    return requiredHandlingMeasureCategories.value.includes(
      item.subtitle || '',
    );
  }
  if (kind === 'observation') {
    return requiredObservationMethodTypes.value.includes(item.subtitle || '');
  }
  return isRelationKindEnabled(kind);
}

function syncMeasureRelationsByCategory() {
  const next = filterRelationItemsBySubtitle(
    handlingMeasureIds.value,
    handlingMeasureItems.value,
    requiredHandlingMeasureCategories.value,
  );
  handlingMeasureIds.value = next.ids;
  handlingMeasureItems.value = next.items;
}

function syncObservationRelationsByType() {
  const next = filterRelationItemsBySubtitle(
    observationMethodIds.value,
    observationMethodItems.value,
    requiredObservationMethodTypes.value,
  );
  observationMethodIds.value = next.ids;
  observationMethodItems.value = next.items;
}

function getRelationSelectorExtraFilters(kind: MasterResourceKind) {
  if (kind === 'measure') {
    return {
      measure_category: [...requiredHandlingMeasureCategories.value],
    };
  }
  if (kind === 'observation') {
    return {
      monitor_type: [...requiredObservationMethodTypes.value],
    };
  }
  return {};
}

async function syncScopedFieldValues() {
  const scoped = resolveSubsystemScopedOptions(
    props.subsystemConfigOptions,
    selectedSubsystem.value,
  );
  const values = await formApi.getValues<Record<string, any>>();
  const nextValues: Record<string, any> = {};

  const moduleSet = new Set(
    (scoped.moduleOptions || []).map((item) => item.value),
  );
  const chipSet = new Set((scoped.chipOptions || []).map((item) => item.value));

  const currentModule = String(values.module || '').trim();
  if (currentModule && moduleSet.size > 0 && !moduleSet.has(currentModule)) {
    nextValues.module = undefined;
  }

  const nextChips = normalizeStringList(values.chips || []).filter((chip) => {
    return chipSet.size === 0 || chipSet.has(chip);
  });
  if (nextChips.length !== normalizeStringList(values.chips || []).length) {
    nextValues.chips = nextChips;
  }

  if (Object.keys(nextValues).length > 0) {
    await formApi.setValues(nextValues);
  }
}

async function handleSubsystemChange(value?: string) {
  selectedSubsystem.value = value;
  applySchema();
  await nextTick();
  await syncScopedFieldValues();
}

async function openCreate() {
  mode.value = 'create';
  editingId.value = '';
  selectedSubsystem.value = undefined;
  formValueFallbacks.value = {
    chips: [],
    fault_categories: [],
    symptoms: [],
  };
  relatedDtsNos.value = [];
  scopeBindings.value = [];
  interceptionRequired.value = false;
  huatuoRequired.value = false;
  requiredHandlingMeasureCategories.value = [];
  requiredObservationMethodTypes.value = [];
  resetRelations();
  applySchema();
  loading.value = false;
  visible.value = true;
  await nextTick();
  await formApi.resetForm({ values: createDefaultFormValues() });
  await clearInitialValidationState();
}

async function applyFailureModeDetail(detail: FailureModeItem) {
  const chips = normalizeStringList(detail.chips || []);
  const faultCategories = normalizeStringList(detail.fault_categories || []);
  const symptoms = normalizeStringList(detail.symptoms || []);
  formValueFallbacks.value = {
    chips,
    fault_categories: faultCategories,
    symptoms,
  };
  selectedSubsystem.value = detail.subsystem || undefined;
  scopeBindings.value = detail.scope_bindings || [];
  relatedDtsNos.value = normalizeStringList(detail.related_dts_nos || []);
  interceptionRequired.value = Boolean(detail.interception_required);
  huatuoRequired.value = Boolean(detail.huatuo_required);
  requiredHandlingMeasureCategories.value = normalizeStringList(
    detail.required_handling_measure_categories || [],
  );
  requiredObservationMethodTypes.value = normalizeStringList(
    detail.required_observation_method_types || [],
  );
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
  applySchema();
  await nextTick();
  await formApi.resetForm({ values: createDefaultFormValues(detail) });
  await clearInitialValidationState();
}

async function openEdit(record: FailureModeItem | string | { id: string }) {
  mode.value = 'edit';
  editingId.value = typeof record === 'string' ? record : record.id;
  loading.value = true;
  visible.value = true;
  await nextTick();
  resetRelations();
  try {
    const detail =
      typeof record === 'object' && 'brief' in record
        ? record
        : await getFailureModeDetailApi(editingId.value);
    await applyFailureModeDetail(detail as FailureModeItem);
  } finally {
    loading.value = false;
    await clearInitialValidationState();
  }
}

async function openView(record: FailureModeItem | string | { id: string }) {
  mode.value = 'view';
  editingId.value = typeof record === 'string' ? record : record.id;
  loading.value = true;
  visible.value = true;
  await nextTick();
  resetRelations();
  try {
    const detail =
      typeof record === 'object' && 'brief' in record
        ? record
        : await getFailureModeDetailApi(editingId.value);
    await applyFailureModeDetail(detail as FailureModeItem);
  } finally {
    loading.value = false;
    await clearInitialValidationState();
  }
}

function openRelationSelector(kind: MasterResourceKind) {
  if (isReadonly.value) {
    return;
  }
  if (!isRelationKindEnabled(kind)) {
    const tips = {
      huatuo: '请先开启华佗诊断必配开关。',
      interception: '请先开启产线拦截策略必配开关。',
      measure: '请先勾选至少一个故障处理措施类别。',
      observation: '请先勾选至少一个维测手段类型。',
    };
    ElMessage.warning(tips[kind as keyof typeof tips] || '请先完成前置配置');
    return;
  }

  const relationState = getRelationState(kind);
  relationSelectorRef.value?.open({
    kind,
    selectedIds: relationState.ids.value,
    selectedItems: relationState.items.value,
    extraFilters: getRelationSelectorExtraFilters(kind),
  });
}

function removeRelationSelection(kind: MasterResourceKind, id: string) {
  if (isReadonly.value) {
    return;
  }
  const relationState = getRelationState(kind);
  relationState.ids.value = relationState.ids.value.filter(
    (item) => item !== id,
  );
  relationState.items.value = relationState.items.value.filter(
    (item) => item.id !== id,
  );
}

function handleRelationConfirm(payload: {
  ids: string[];
  items: RelationItem[];
  kind: MasterResourceKind;
}) {
  const relationState = getRelationState(payload.kind);
  let nextIds = normalizeStringList(payload.ids || []);
  let nextItems = ensureOrderedRelationItems(nextIds, payload.items || []);
  if (payload.kind === 'measure') {
    const filtered = filterRelationItemsBySubtitle(
      nextIds,
      nextItems,
      requiredHandlingMeasureCategories.value,
    );
    nextIds = filtered.ids;
    nextItems = filtered.items;
  }
  if (payload.kind === 'observation') {
    const filtered = filterRelationItemsBySubtitle(
      nextIds,
      nextItems,
      requiredObservationMethodTypes.value,
    );
    nextIds = filtered.ids;
    nextItems = filtered.items;
  }
  relationState.ids.value = nextIds;
  relationState.items.value = nextItems;
}

function handleQuickCreate(kind: MasterResourceKind) {
  if (isReadonly.value) {
    return;
  }
  masterDrawerRef.value?.openCreate(kind);
}

function handleQuickEdit(payload: { id: string; kind: MasterResourceKind }) {
  if (isReadonly.value) {
    return;
  }
  masterDrawerRef.value?.openEdit(payload.kind, payload.id);
}

function handleViewRelation(kind: MasterResourceKind, id: string) {
  masterDrawerRef.value?.openView(kind, id);
}

function handleMasterDataSuccess(payload: {
  action: 'create' | 'edit';
  kind: MasterResourceKind;
  relationItem: RelationItem;
}) {
  const relationState = getRelationState(payload.kind);
  const shouldSelect =
    isRelationItemAllowed(payload.kind, payload.relationItem) &&
    (payload.action === 'create' ||
      relationState.ids.value.includes(payload.relationItem.id));
  relationSelectorRef.value?.upsertSelection(
    payload.relationItem,
    shouldSelect,
  );
  relationSelectorRef.value?.reload();
  if (!shouldSelect) {
    relationState.ids.value = relationState.ids.value.filter(
      (item) => item !== payload.relationItem.id,
    );
    relationState.items.value = relationState.items.value.filter(
      (item) => item.id !== payload.relationItem.id,
    );
    return;
  }
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
    const normalizedScopeBindings = normalizeScopeBindingsForSubmit(
      scopeBindings.value,
      String(values.subsystem || '').trim(),
    );
    if (normalizedScopeBindings.hasIncomplete) {
      ElMessage.warning('已关联产品时，请先选择故障模式子系统。');
      return;
    }
    const payload: FailureModePayload = {
      ...(values as FailureModePayload),
      handling_measure_ids: [...handlingMeasureIds.value],
      huatuo_diagnosis_ids: [...huatuoDiagnosisIds.value],
      interception_required: interceptionRequired.value,
      huatuo_required: huatuoRequired.value,
      interception_strategy_ids: [...interceptionStrategyIds.value],
      observation_method_ids: [...observationMethodIds.value],
      related_dts_nos: [...relatedDtsNos.value],
      scope_bindings: normalizedScopeBindings.items,
      required_handling_measure_categories: [
        ...requiredHandlingMeasureCategories.value,
      ],
      required_observation_method_types: [
        ...requiredObservationMethodTypes.value,
      ],
    };

    let result: FailureModeItem;
    if (mode.value === 'create') {
      result = props.createHandler
        ? await props.createHandler(payload)
        : await createFailureModeApi(payload);
    } else {
      result = props.updateHandler
        ? await props.updateHandler(editingId.value, payload)
        : await updateFailureModeApi(editingId.value, payload);
    }

    ElMessage.success(mode.value === 'create' ? '创建成功' : '保存成功');
    visible.value = false;
    emit('success', result);
  } finally {
    confirmLoading.value = false;
  }
}

watch(interceptionRequired, (value) => {
  if (!value) {
    interceptionStrategyIds.value = [];
    interceptionStrategyItems.value = [];
  }
});

watch(huatuoRequired, (value) => {
  if (!value) {
    huatuoDiagnosisIds.value = [];
    huatuoDiagnosisItems.value = [];
  }
});

watch(
  requiredHandlingMeasureCategories,
  () => {
    syncMeasureRelationsByCategory();
  },
  { deep: true },
);

watch(
  requiredObservationMethodTypes,
  () => {
    syncObservationRelationsByType();
  },
  { deep: true },
);

watch(
  () => [props.dictOptions, props.subsystemConfigOptions],
  async () => {
    if (!visible.value) {
      return;
    }
    applySchema();
    await nextTick();
  },
  { deep: true },
);

defineExpose({
  openCreate,
  openEdit,
  openView,
});
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :cancel-text="isReadonly ? '关闭' : '取消'"
    :confirm-loading="confirmLoading"
    :loading="loading"
    :show-confirm-button="!isReadonly"
    :title="drawerTitle"
    size="78%"
    @confirm="handleConfirm"
  >
    <div class="space-y-4 px-2 py-1">
      <div
        class="rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
      >
        <Form />
      </div>

      <div class="space-y-4">
        <ScopeBindingEditor
          v-model="scopeBindings"
          body-max-height="360px"
          :disabled="isReadonly"
          label="关联产品"
          description="选择需要关联的产品，子系统统一取当前故障模式的子系统字段；保存后会自动同步到对应产品基线。"
        />

        <StringListEditor
          v-model="relatedDtsNos"
          add-text="新增问题单号"
          add-button-placement="footer"
          description="问题单作为补充线索单独维护，独立放在上方，避免与主数据关系配置互相挤压。"
          :disabled="isReadonly"
          item-label="问题单号"
          label="关联问题单"
          placeholder="请输入 dts_no"
          scrollable
        />

        <div
          class="rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
        >
          <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div
                class="text-sm font-semibold text-[var(--el-text-color-primary)]"
              >
                关联能力配置
              </div>
              <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
                每张卡同时维护“是否必配”和“已绑定项”，查看态下可继续点开只读主数据详情。
              </div>
            </div>
            <ElTag type="info">已关联 {{ selectedRelationCount }} 项</ElTag>
          </div>

          <div class="grid gap-4 xl:grid-cols-2">
            <section class="failure-mode-relation-card">
              <div class="failure-mode-relation-card__header">
                <div>
                  <div class="failure-mode-relation-card__title">
                    产线拦截策略
                  </div>
                  <div class="failure-mode-relation-card__desc">
                    开启必配后，可直接在当前卡片中维护关联的拦截策略。
                  </div>
                </div>
                <ElSwitch
                  v-model="interceptionRequired"
                  :disabled="isReadonly"
                />
              </div>

              <div class="failure-mode-relation-card__toolbar">
                <ElTag :type="interceptionRequired ? 'success' : 'info'" round>
                  {{ interceptionRequired ? '必配' : '不涉及' }}
                </ElTag>
                <ElButton
                  v-if="!isReadonly"
                  :icon="Link"
                  plain
                  type="primary"
                  @click="openRelationSelector('interception')"
                >
                  选择拦截策略
                </ElButton>
              </div>

              <div
                v-if="interceptionStrategyItems.length > 0"
                class="failure-mode-relation-card__content"
              >
                <template v-if="isReadonly">
                  <button
                    v-for="item in interceptionStrategyItems"
                    :key="item.id"
                    class="failure-mode-relation-card__link-tag"
                    type="button"
                    @click="handleViewRelation('interception', item.id)"
                  >
                    {{ item.label }}
                  </button>
                </template>
                <template v-else>
                  <ElTag
                    v-for="item in interceptionStrategyItems"
                    :key="item.id"
                    closable
                    effect="light"
                    type="info"
                    @close="removeRelationSelection('interception', item.id)"
                  >
                    {{ item.label }}
                  </ElTag>
                </template>
              </div>
              <div v-else class="failure-mode-relation-card__empty">
                {{
                  interceptionRequired
                    ? '暂未关联产线拦截策略。'
                    : '当前产线拦截策略不涉及。'
                }}
              </div>
            </section>

            <section class="failure-mode-relation-card">
              <div class="failure-mode-relation-card__header">
                <div>
                  <div class="failure-mode-relation-card__title">
                    故障处理措施
                  </div>
                  <div class="failure-mode-relation-card__desc">
                    先勾选必配类别，再绑定对应措施；查看态下可继续打开措施和其测试用例详情。
                  </div>
                </div>
                <ElTag type="primary" round>
                  {{ requiredHandlingMeasureCategories.length || 0 }} 个类别
                </ElTag>
              </div>

              <ElCheckboxGroup
                v-model="requiredHandlingMeasureCategories"
                class="failure-mode-relation-card__checks"
                :disabled="isReadonly"
              >
                <ElCheckbox
                  v-for="item in handlingCategoryOptions"
                  :key="item.value"
                  :label="item.value"
                  :value="item.value"
                  border
                >
                  {{ item.label }}
                </ElCheckbox>
              </ElCheckboxGroup>

              <div class="failure-mode-relation-card__toolbar">
                <ElTag
                  :type="
                    requiredHandlingMeasureCategories.length > 0
                      ? 'success'
                      : 'info'
                  "
                  round
                >
                  {{
                    requiredHandlingMeasureCategories.length > 0
                      ? `必配：${requiredHandlingMeasureCategories.join('、')}`
                      : '当前不涉及'
                  }}
                </ElTag>
                <ElButton
                  v-if="!isReadonly"
                  :icon="Link"
                  plain
                  type="primary"
                  @click="openRelationSelector('measure')"
                >
                  选择处理措施
                </ElButton>
              </div>

              <div
                v-if="handlingMeasureItems.length > 0"
                class="failure-mode-relation-card__content"
              >
                <template v-if="isReadonly">
                  <button
                    v-for="item in handlingMeasureItems"
                    :key="item.id"
                    class="failure-mode-relation-card__link-tag"
                    type="button"
                    @click="handleViewRelation('measure', item.id)"
                  >
                    <span>{{ item.label }}</span>
                    <small v-if="item.subtitle">{{ item.subtitle }}</small>
                  </button>
                </template>
                <template v-else>
                  <ElTag
                    v-for="item in handlingMeasureItems"
                    :key="item.id"
                    closable
                    effect="light"
                    type="info"
                    @close="removeRelationSelection('measure', item.id)"
                  >
                    {{ item.label }}
                    <span v-if="item.subtitle"> · {{ item.subtitle }}</span>
                  </ElTag>
                </template>
              </div>
              <div v-else class="failure-mode-relation-card__empty">
                {{
                  requiredHandlingMeasureCategories.length > 0
                    ? '暂未关联故障处理措施。'
                    : '请先勾选需要的措施类别。'
                }}
              </div>
            </section>

            <section class="failure-mode-relation-card">
              <div class="failure-mode-relation-card__header">
                <div>
                  <div class="failure-mode-relation-card__title">维测手段</div>
                  <div class="failure-mode-relation-card__desc">
                    先勾选必配类型，再绑定对应维测手段。
                  </div>
                </div>
                <ElTag type="primary" round>
                  {{ requiredObservationMethodTypes.length || 0 }} 个类型
                </ElTag>
              </div>

              <ElCheckboxGroup
                v-model="requiredObservationMethodTypes"
                class="failure-mode-relation-card__checks"
                :disabled="isReadonly"
              >
                <ElCheckbox
                  v-for="item in observationTypeOptions"
                  :key="item.value"
                  :label="item.value"
                  :value="item.value"
                  border
                >
                  {{ item.label }}
                </ElCheckbox>
              </ElCheckboxGroup>

              <div class="failure-mode-relation-card__toolbar">
                <ElTag
                  :type="
                    requiredObservationMethodTypes.length > 0
                      ? 'success'
                      : 'info'
                  "
                  round
                >
                  {{
                    requiredObservationMethodTypes.length > 0
                      ? `必配：${requiredObservationMethodTypes.join('、')}`
                      : '当前不涉及'
                  }}
                </ElTag>
                <ElButton
                  v-if="!isReadonly"
                  :icon="Link"
                  plain
                  type="primary"
                  @click="openRelationSelector('observation')"
                >
                  选择维测手段
                </ElButton>
              </div>

              <div
                v-if="observationMethodItems.length > 0"
                class="failure-mode-relation-card__content"
              >
                <template v-if="isReadonly">
                  <button
                    v-for="item in observationMethodItems"
                    :key="item.id"
                    class="failure-mode-relation-card__link-tag"
                    type="button"
                    @click="handleViewRelation('observation', item.id)"
                  >
                    <span>{{ item.label }}</span>
                    <small v-if="item.subtitle">{{ item.subtitle }}</small>
                  </button>
                </template>
                <template v-else>
                  <ElTag
                    v-for="item in observationMethodItems"
                    :key="item.id"
                    closable
                    effect="light"
                    type="info"
                    @close="removeRelationSelection('observation', item.id)"
                  >
                    {{ item.label }}
                    <span v-if="item.subtitle"> · {{ item.subtitle }}</span>
                  </ElTag>
                </template>
              </div>
              <div v-else class="failure-mode-relation-card__empty">
                {{
                  requiredObservationMethodTypes.length > 0
                    ? '暂未关联维测手段。'
                    : '请先勾选需要的维测类型。'
                }}
              </div>
            </section>

            <section class="failure-mode-relation-card">
              <div class="failure-mode-relation-card__header">
                <div>
                  <div class="failure-mode-relation-card__title">
                    华佗诊断方案
                  </div>
                  <div class="failure-mode-relation-card__desc">
                    开启后可直接维护关联的华佗诊断方案。
                  </div>
                </div>
                <ElSwitch v-model="huatuoRequired" :disabled="isReadonly" />
              </div>

              <div class="failure-mode-relation-card__toolbar">
                <ElTag :type="huatuoRequired ? 'success' : 'info'" round>
                  {{ huatuoRequired ? '必配' : '不涉及' }}
                </ElTag>
                <ElButton
                  v-if="!isReadonly"
                  :icon="Link"
                  plain
                  type="primary"
                  @click="openRelationSelector('huatuo')"
                >
                  选择华佗方案
                </ElButton>
              </div>

              <div
                v-if="huatuoDiagnosisItems.length > 0"
                class="failure-mode-relation-card__content"
              >
                <template v-if="isReadonly">
                  <button
                    v-for="item in huatuoDiagnosisItems"
                    :key="item.id"
                    class="failure-mode-relation-card__link-tag"
                    type="button"
                    @click="handleViewRelation('huatuo', item.id)"
                  >
                    {{ item.label }}
                  </button>
                </template>
                <template v-else>
                  <ElTag
                    v-for="item in huatuoDiagnosisItems"
                    :key="item.id"
                    closable
                    effect="light"
                    type="info"
                    @close="removeRelationSelection('huatuo', item.id)"
                  >
                    {{ item.label }}
                  </ElTag>
                </template>
              </div>
              <div v-else class="failure-mode-relation-card__empty">
                {{
                  huatuoRequired
                    ? '暂未关联华佗诊断方案。'
                    : '当前华佗诊断方案不涉及。'
                }}
              </div>
            </section>
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
    :dict-options="props.dictOptions"
    @success="handleMasterDataSuccess"
  />
</template>

<style scoped>
.failure-mode-relation-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 16px;
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--el-color-primary-light-9) 90%, white),
    #ffffff
  );
  padding: 16px;
}

.failure-mode-relation-card__header,
.failure-mode-relation-card__toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.failure-mode-relation-card__toolbar {
  align-items: center;
  margin-top: 14px;
}

.failure-mode-relation-card__title {
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 600;
}

.failure-mode-relation-card__desc {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.failure-mode-relation-card__checks {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
}

.failure-mode-relation-card__content {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.failure-mode-relation-card__empty {
  margin-top: 14px;
  border-radius: 12px;
  background: var(--el-fill-color-light);
  padding: 14px 16px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.failure-mode-relation-card__link-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  border-radius: 999px;
  background: color-mix(in srgb, var(--el-color-primary-light-9) 82%, white);
  color: var(--el-color-primary);
  cursor: pointer;
  padding: 8px 12px;
  text-align: left;
}

.failure-mode-relation-card__link-tag small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.failure-mode-relation-card__link-tag:hover {
  background: color-mix(in srgb, var(--el-color-primary-light-8) 74%, white);
}
</style>
