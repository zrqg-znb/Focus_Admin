<script lang="ts" setup>
import type { MasterResourceKind } from '../data';

import type {
  FailureModeDictOptions,
  FailureModeItem,
  FailureModePayload,
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
  getMasterResourceLabel,
  normalizeStringList,
  resolveSubsystemScopedOptions,
  upsertRelationItem,
  useFailureModeFormSchema,
} from '../data';
import MasterDataDrawer from './MasterDataDrawer.vue';
import RelationSelectorDialog from './RelationSelectorDialog.vue';
import StringListEditor from './StringListEditor.vue';

defineOptions({ name: 'FailureModeDrawer' });

const props = defineProps<{
  createHandler?: (payload: FailureModePayload) => Promise<FailureModeItem>;
  dictOptions: FailureModeDictOptions;
  hideStatusField?: boolean;
  subsystemConfigOptions: FailureModeSubsystemConfigOptions;
}>();
const emit = defineEmits<{
  success: [item: FailureModeItem];
}>();
const HANDLING_CATEGORIES = ['检测', '预防', '自愈'];
const OBSERVATION_TYPES = ['流水日志', 'DMD 点位', 'FMP 点位'];

const visible = ref(false);
const loading = ref(false);
const confirmLoading = ref(false);
const mode = ref<'create' | 'edit'>('create');
const editingId = ref('');
const selectedSubsystem = ref<string>();
const relatedDtsNos = ref<string[]>([]);
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

const drawerTitle = computed(() =>
  mode.value === 'create' ? '新增故障模式' : '编辑故障模式',
);

const handlingCategoryOptions = computed(() => {
  const allowSet = new Set(HANDLING_CATEGORIES);
  return props.dictOptions.measure_category.filter((item) =>
    allowSet.has(item.value),
  );
});

const observationTypeOptions = computed(() => {
  const allowSet = new Set(OBSERVATION_TYPES);
  return props.dictOptions.monitor_type.filter((item) =>
    allowSet.has(item.value),
  );
});

const relationCardConfigs = computed(() => [
  {
    kind: 'interception' as MasterResourceKind,
    ids: interceptionStrategyIds.value,
    items: interceptionStrategyItems.value,
    label: getMasterResourceLabel('interception'),
    description: interceptionRequired.value
      ? '已开启必配，支持搜索并多选关联产线拦截策略。'
      : '关闭后视为无需配置，并自动清空关联。',
    enabled: interceptionRequired.value,
  },
  {
    kind: 'measure' as MasterResourceKind,
    ids: handlingMeasureIds.value,
    items: handlingMeasureItems.value,
    label: getMasterResourceLabel('measure'),
    description:
      requiredHandlingMeasureCategories.value.length > 0
        ? `当前必配类别：${requiredHandlingMeasureCategories.value.join('、')}。`
        : '请先勾选需要的措施类别，再绑定对应措施。',
    enabled: requiredHandlingMeasureCategories.value.length > 0,
  },
  {
    kind: 'observation' as MasterResourceKind,
    ids: observationMethodIds.value,
    items: observationMethodItems.value,
    label: getMasterResourceLabel('observation'),
    description:
      requiredObservationMethodTypes.value.length > 0
        ? `当前必配类型：${requiredObservationMethodTypes.value.join('、')}。`
        : '请先勾选需要的维测类型，再绑定对应维测手段。',
    enabled: requiredObservationMethodTypes.value.length > 0,
  },
  {
    kind: 'huatuo' as MasterResourceKind,
    ids: huatuoDiagnosisIds.value,
    items: huatuoDiagnosisItems.value,
    label: getMasterResourceLabel('huatuo'),
    description: huatuoRequired.value
      ? '已开启必配，支持沉淀并复用华佗诊断方案。'
      : '关闭后视为无需配置，并自动清空关联。',
    enabled: huatuoRequired.value,
  },
]);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: { class: 'w-full' },
    labelClass: 'whitespace-nowrap',
    labelWidth: 156,
  },
  schema: useFailureModeFormSchema(
    props.dictOptions,
    props.subsystemConfigOptions,
    selectedSubsystem.value,
    undefined,
    {
      hideStatusField: props.hideStatusField,
    },
  ),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-6 xl:grid-cols-2',
});

function applySchema() {
  formApi.setState({
    schema: useFailureModeFormSchema(
      props.dictOptions,
      props.subsystemConfigOptions,
      selectedSubsystem.value,
      (value) => {
        void handleSubsystemChange(value);
      },
      {
        hideStatusField: props.hideStatusField,
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
    formApi.setValues(nextValues);
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
  relatedDtsNos.value = [];
  interceptionRequired.value = false;
  huatuoRequired.value = false;
  requiredHandlingMeasureCategories.value = [];
  requiredObservationMethodTypes.value = [];
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
    symptoms: [],
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
  try {
    await formApi.resetForm();
    const detail = await getFailureModeDetailApi(editingId.value);
    selectedSubsystem.value = detail.subsystem || undefined;
    applySchema();
    formApi.setValues({
      author_ids: detail.author_ids || [],
      brief: detail.brief,
      chips: detail.chips || [],
      detectability: detail.detectability || undefined,
      effect_html: detail.effect_html || '',
      fault_categories: detail.fault_categories || [],
      symptoms: detail.symptoms || [],
      functional_safety_level: detail.functional_safety_level || undefined,
      module: detail.module || undefined,
      occurrence_frequency: detail.occurrence_frequency || undefined,
      root_cause_html: detail.root_cause_html || '',
      severity: detail.severity || undefined,
      status: detail.status || undefined,
      subsystem: detail.subsystem || undefined,
    });
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
  } finally {
    loading.value = false;
  }
}

function openRelationSelector(kind: MasterResourceKind) {
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
    const payload: FailureModePayload = {
      ...(values as FailureModePayload),
      handling_measure_ids: [...handlingMeasureIds.value],
      huatuo_diagnosis_ids: [...huatuoDiagnosisIds.value],
      interception_required: interceptionRequired.value,
      huatuo_required: huatuoRequired.value,
      interception_strategy_ids: [...interceptionStrategyIds.value],
      observation_method_ids: [...observationMethodIds.value],
      related_dts_nos: [...relatedDtsNos.value],
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
      result = await updateFailureModeApi(editingId.value, payload);
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
});
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :confirm-loading="confirmLoading"
    :loading="loading"
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

      <div
        class="grid gap-4 xl:h-[460px] xl:min-h-0 xl:grid-cols-[1.15fr_0.85fr] xl:items-stretch"
      >
        <div
          class="failure-mode-statistics-panel rounded-xl border border-[var(--el-border-color-light)] p-4 shadow-sm xl:h-full xl:min-h-0 xl:overflow-y-auto"
        >
          <div class="mb-4 flex items-start justify-between gap-3">
            <div>
              <div
                class="text-sm font-semibold text-[var(--el-text-color-primary)]"
              >
                统计配置
              </div>
              <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
                先声明哪些维度为必配，再维护对应关联，用于后续统计看板准确判断“已配置
                / 待补充 / 无需配置”。
              </div>
            </div>
            <ElTag type="primary">统计字段</ElTag>
          </div>

          <div class="grid gap-4 xl:grid-cols-2">
            <div class="failure-mode-switch-card">
              <div>
                <div class="failure-mode-switch-card__title">
                  产线拦截策略必配
                </div>
                <div class="failure-mode-switch-card__desc">
                  关闭时自动清空当前关联，并统计为“无需配置”。
                </div>
              </div>
              <ElSwitch v-model="interceptionRequired" />
            </div>
            <div class="failure-mode-switch-card">
              <div>
                <div class="failure-mode-switch-card__title">华佗诊断必配</div>
                <div class="failure-mode-switch-card__desc">
                  关闭时自动清空当前关联，并统计为“无需配置”。
                </div>
              </div>
              <ElSwitch v-model="huatuoRequired" />
            </div>
          </div>

          <div class="mt-4 grid gap-4 xl:grid-cols-2">
            <div class="failure-mode-check-card">
              <div class="failure-mode-check-card__title">
                故障处理措施必配类别
              </div>
              <div class="failure-mode-check-card__desc">
                勾选后仅允许绑定对应类别的故障处理措施。
              </div>
              <ElCheckboxGroup
                v-model="requiredHandlingMeasureCategories"
                class="mt-3 flex flex-wrap gap-3"
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
            </div>
            <div class="failure-mode-check-card">
              <div class="failure-mode-check-card__title">维测手段必配类型</div>
              <div class="failure-mode-check-card__desc">
                勾选后仅允许绑定对应类型的维测手段。
              </div>
              <ElCheckboxGroup
                v-model="requiredObservationMethodTypes"
                class="mt-3 flex flex-wrap gap-3"
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
            </div>
          </div>
        </div>

        <StringListEditor
          v-model="relatedDtsNos"
          add-text="新增问题单号"
          add-button-placement="footer"
          class="xl:h-full xl:min-h-0"
          description="顶部固定展示当前问题单数量，中间区域独立滚动维护，底部统一新增，避免表单随内容无限增高。"
          item-label="问题单号"
          label="关联问题单"
          placeholder="请输入 dts_no"
          scrollable
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
              按照当前“必配”定义进行绑定，后续统计页会直接复用这些关联关系做完成率聚合。
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
            :class="{ 'opacity-65': !card.enabled }"
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
              {{
                card.enabled
                  ? `暂未关联${card.label}。`
                  : `当前${card.label}为无需配置。`
              }}
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
    :dict-options="props.dictOptions"
    @success="handleMasterDataSuccess"
  />
</template>

<style scoped>
.failure-mode-statistics-panel {
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--el-color-primary-light-9) 86%, white),
    color-mix(in srgb, var(--el-color-primary-light-8) 28%, white)
  );
}

.failure-mode-switch-card,
.failure-mode-check-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  padding: 16px;
}

.failure-mode-switch-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.failure-mode-switch-card__title,
.failure-mode-check-card__title {
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
}

.failure-mode-switch-card__desc,
.failure-mode-check-card__desc {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
