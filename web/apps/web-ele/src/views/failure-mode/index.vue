<script lang="ts" setup>
import type { FailureModeTabKey, MasterResourceKind } from './data';

import type {
  FailureModeItem,
  HandlingMeasureItem,
  HuatuoDiagnosisItem,
  InterceptionStrategyItem,
  ObservationMethodItem,
  TestCaseItem,
} from '#/api/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { useDebounceFn } from '@vueuse/core';
import {
  ElButton,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTooltip,
} from 'element-plus';

import {
  deleteFailureModeApi,
  deleteHandlingMeasureApi,
  deleteHuatuoDiagnosisApi,
  deleteInterceptionStrategyApi,
  deleteObservationMethodApi,
  deleteTestCaseApi,
  getFailureModeDictOptionsApi,
  getFailureModeSubsystemConfigOptionsApi,
  listFailureModesApi,
  listHandlingMeasuresApi,
  listHuatuoDiagnosesApi,
  listInterceptionStrategiesApi,
  listObservationMethodsApi,
  listTestCasesApi,
} from '#/api/failure_mode';
import { useZqTable } from '#/components/zq-table';

import FailureModeDrawer from './components/FailureModeDrawer.vue';
import MasterDataDrawer from './components/MasterDataDrawer.vue';
import RelationInsightDrawer from './components/RelationInsightDrawer.vue';
import {
  createEmptyDictOptions,
  createEmptySubsystemConfigOptions,
  formatFailureModeSourceHint,
  formatFailureModeSourceLabel,
  formatRelationLabels,
  formatTextList,
  formatUserNames,
  getMasterResourceLabel,
  normalizeStringList,
  replaceDictOptions,
  replaceSubsystemConfigOptions,
  resolveSubsystemScopedOptions,
  useFailureModeColumns,
  useHandlingMeasureColumns,
  useHuatuoColumns,
  useInterceptionColumns,
  useObservationColumns,
  useTestCaseColumns,
} from './data';

defineOptions({ name: 'FailureManagementAdmin' });

type MasterRow =
  | HandlingMeasureItem
  | HuatuoDiagnosisItem
  | InterceptionStrategyItem
  | ObservationMethodItem
  | TestCaseItem;

interface GridQueryContext {
  page: {
    currentPage: number;
    pageSize: number;
  };
}

interface ReloadableGridApi {
  pagination: {
    currentPage: number;
    pageSize: number;
  };
  reload: (params?: Record<string, any>) => Promise<any>;
  setState: (stateOrFn: any) => void;
}

const activeTab = ref<FailureModeTabKey>('failureMode');
const dictOptions = reactive(createEmptyDictOptions());
const subsystemConfigOptions = reactive(createEmptySubsystemConfigOptions());
const failureModeDrawerRef = ref<any>();
const masterDrawerRef = ref<any>();
const relationInsightDrawerRef = ref<InstanceType<
  typeof RelationInsightDrawer
> | null>(null);

const failureModeFilters = reactive({
  author_keyword: '',
  keyword: '',
  module: [] as string[],
  status: [] as string[],
  subsystem: [] as string[],
});
const interceptionFilters = reactive({ keyword: '', owner_keyword: '' });
const handlingMeasureFilters = reactive({
  owner_keyword: '',
  keyword: '',
  measure_category: [] as string[],
});
const observationFilters = reactive({
  keyword: '',
  monitor_type: [] as string[],
  owner_keyword: '',
});
const huatuoFilters = reactive({ keyword: '', owner_keyword: '' });
const testCaseFilters = reactive({ keyword: '', owner_keyword: '' });

const failureModeSubsystemFilterOptions = computed(() => {
  return subsystemConfigOptions.subsystem_options.length > 0
    ? subsystemConfigOptions.subsystem_options
    : dictOptions.subsystem;
});

const failureModeModuleFilterOptions = computed(() => {
  const scoped = resolveSubsystemScopedOptions(
    subsystemConfigOptions,
    failureModeFilters.subsystem,
  );
  return scoped.moduleOptions.length > 0
    ? scoped.moduleOptions
    : dictOptions.module;
});

function createKeywordGrid<T extends Record<string, any>>(
  columns: ZqTableGridOptions<T>['columns'],
  request: (params: any) => Promise<{ items: T[]; total: number }>,
  getParams: () => Record<string, any>,
) {
  return useZqTable<T>({
    gridOptions: {
      border: true,
      columns,
      proxyConfig: {
        autoLoad: true,
        ajax: {
          query: async ({ page }: GridQueryContext) => {
            return request(buildPageQuery(page, getParams()));
          },
        },
      },
      rowKey: 'id',
      stripe: true,
      toolbarConfig: {
        custom: true,
        refresh: true,
        search: false,
        zoom: true,
      },
      pagerConfig: {
        enabled: true,
        pageSize: 10,
        pageSizes: [10, 20, 50],
      },
    },
  });
}

const [FailureModeGrid, failureModeGridApi] = useZqTable<FailureModeItem>({
  gridOptions: {
    border: true,
    columns: useFailureModeColumns(false),
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page }: GridQueryContext) => {
          return listFailureModesApi(
            buildPageQuery(page, {
              author_keyword: normalizeQueryValue(
                failureModeFilters.author_keyword,
              ),
              keyword: normalizeQueryValue(failureModeFilters.keyword),
              module: normalizeStringList(failureModeFilters.module),
              status: normalizeStringList(failureModeFilters.status),
              subsystem: normalizeStringList(failureModeFilters.subsystem),
            }),
          );
        },
      },
    },
    rowKey: 'id',
    stripe: true,
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: false,
      zoom: true,
    },
    pagerConfig: {
      enabled: true,
      pageSize: 10,
      pageSizes: [10, 20, 50],
    },
  },
});

const [InterceptionGrid, interceptionGridApi] = createKeywordGrid(
  useInterceptionColumns(),
  listInterceptionStrategiesApi,
  () => ({
    keyword: normalizeQueryValue(interceptionFilters.keyword),
    owner_keyword: normalizeQueryValue(interceptionFilters.owner_keyword),
  }),
);
const [HandlingMeasureGrid, handlingMeasureGridApi] = createKeywordGrid(
  useHandlingMeasureColumns(),
  listHandlingMeasuresApi,
  () => ({
    keyword: normalizeQueryValue(handlingMeasureFilters.keyword),
    measure_category: normalizeStringList(
      handlingMeasureFilters.measure_category,
    ),
    owner_keyword: normalizeQueryValue(handlingMeasureFilters.owner_keyword),
  }),
);
const [ObservationGrid, observationGridApi] = createKeywordGrid(
  useObservationColumns(),
  listObservationMethodsApi,
  () => ({
    keyword: normalizeQueryValue(observationFilters.keyword),
    monitor_type: normalizeStringList(observationFilters.monitor_type),
    owner_keyword: normalizeQueryValue(observationFilters.owner_keyword),
  }),
);
const [HuatuoGrid, huatuoGridApi] = createKeywordGrid(
  useHuatuoColumns(),
  listHuatuoDiagnosesApi,
  () => ({
    keyword: normalizeQueryValue(huatuoFilters.keyword),
    owner_keyword: normalizeQueryValue(huatuoFilters.owner_keyword),
  }),
);
const [TestCaseGrid, testCaseGridApi] = createKeywordGrid(
  useTestCaseColumns(),
  listTestCasesApi,
  () => ({
    keyword: normalizeQueryValue(testCaseFilters.keyword),
    owner_keyword: normalizeQueryValue(testCaseFilters.owner_keyword),
  }),
);

function normalizeQueryValue(value: unknown) {
  const text = String(value ?? '').trim();
  return text || undefined;
}

function buildPageQuery(
  page: GridQueryContext['page'],
  extraParams: Record<string, any> = {},
) {
  const merged = {
    ...extraParams,
    page: page.currentPage,
    pageSize: page.pageSize,
  };
  return Object.fromEntries(
    Object.entries(merged).filter(([, value]) => {
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      if (typeof value === 'string') {
        return value !== '';
      }
      return value !== undefined && value !== null;
    }),
  );
}

async function reloadGridAtFirstPage(
  api: ReloadableGridApi,
  params: Record<string, any> = {},
) {
  api.pagination.currentPage = 1;
  api.setState((prev: any) => {
    const gridOptions = prev.gridOptions || {};
    const pagerConfig = prev.gridOptions?.pagerConfig || {};
    return {
      gridOptions: {
        ...gridOptions,
        pagerConfig: {
          ...pagerConfig,
          currentPage: 1,
        },
      },
    };
  });
  await api.reload(params);
}

const scheduleFailureModeReload = useDebounceFn(() => {
  void reloadGridAtFirstPage(failureModeGridApi);
}, 250);
const scheduleInterceptionReload = useDebounceFn(() => {
  void reloadGridAtFirstPage(interceptionGridApi);
}, 250);
const scheduleHandlingMeasureReload = useDebounceFn(() => {
  void reloadGridAtFirstPage(handlingMeasureGridApi);
}, 250);
const scheduleObservationReload = useDebounceFn(() => {
  void reloadGridAtFirstPage(observationGridApi);
}, 250);
const scheduleHuatuoReload = useDebounceFn(() => {
  void reloadGridAtFirstPage(huatuoGridApi);
}, 250);
const scheduleTestCaseReload = useDebounceFn(() => {
  void reloadGridAtFirstPage(testCaseGridApi);
}, 250);

function commitFailureModeFilters() {
  scheduleFailureModeReload();
}

function commitInterceptionFilters() {
  scheduleInterceptionReload();
}

function commitHandlingMeasureFilters() {
  scheduleHandlingMeasureReload();
}

function commitObservationFilters() {
  scheduleObservationReload();
}

function commitHuatuoFilters() {
  scheduleHuatuoReload();
}

function commitTestCaseFilters() {
  scheduleTestCaseReload();
}

function handleVisibleChange(visible: boolean, commit: () => void) {
  if (!visible) {
    commit();
  }
}

function handleFailureModeDictVisibleChange(visible: boolean) {
  handleVisibleChange(visible, commitFailureModeFilters);
}

function handleHandlingMeasureDictVisibleChange(visible: boolean) {
  handleVisibleChange(visible, commitHandlingMeasureFilters);
}

function handleObservationDictVisibleChange(visible: boolean) {
  handleVisibleChange(visible, commitObservationFilters);
}

async function loadBaseOptions() {
  const [dictResponse, linkedOptions] = await Promise.all([
    getFailureModeDictOptionsApi(),
    getFailureModeSubsystemConfigOptionsApi(),
  ]);
  replaceDictOptions(dictOptions, dictResponse);
  replaceSubsystemConfigOptions(subsystemConfigOptions, linkedOptions);
}

async function reloadMasterGrid(kind: FailureModeTabKey | MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      await huatuoGridApi.reload();
      break;
    }
    case 'interception': {
      await interceptionGridApi.reload();
      break;
    }
    case 'measure': {
      await handlingMeasureGridApi.reload();
      break;
    }
    case 'observation': {
      await observationGridApi.reload();
      break;
    }
    default: {
      await testCaseGridApi.reload();
    }
  }
}

async function reloadActiveGrid(tab: FailureModeTabKey = activeTab.value) {
  if (tab === 'failureMode') {
    await failureModeGridApi.reload();
    return;
  }
  await reloadMasterGrid(tab);
}

function openMasterCreate(kind: MasterResourceKind) {
  masterDrawerRef.value?.openCreate(kind);
}

function openMasterEdit(kind: MasterResourceKind, row: MasterRow) {
  masterDrawerRef.value?.openEdit(kind, row.id);
}

async function deleteMaster(kind: MasterResourceKind, id: string) {
  const label = getMasterResourceLabel(kind);
  await ElMessageBox.confirm(`确认删除该${label}吗？`, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  });

  switch (kind) {
    case 'huatuo': {
      await deleteHuatuoDiagnosisApi(id);
      break;
    }
    case 'interception': {
      await deleteInterceptionStrategyApi(id);
      break;
    }
    case 'measure': {
      await deleteHandlingMeasureApi(id);
      break;
    }
    case 'observation': {
      await deleteObservationMethodApi(id);
      break;
    }
    default: {
      await deleteTestCaseApi(id);
    }
  }

  ElMessage.success('删除成功');
  await reloadMasterGrid(kind);
}

async function handleFailureModeAction(
  action: 'delete' | 'edit',
  row: FailureModeItem,
) {
  try {
    if (action === 'edit') {
      failureModeDrawerRef.value?.openEdit(row.id);
      return;
    }
    await ElMessageBox.confirm('确认删除该故障模式吗？', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    });
    await deleteFailureModeApi(row.id);
    ElMessage.success('删除成功');
    await failureModeGridApi.reload();
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error);
      const hasApiResponse = Boolean((error as any)?.response);
      if (!hasApiResponse) {
        ElMessage.error((error as any)?.message || '删除失败');
      }
    }
  }
}

async function handleMasterAction(
  kind: MasterResourceKind,
  action: 'delete' | 'edit',
  row: MasterRow,
) {
  try {
    if (action === 'edit') {
      openMasterEdit(kind, row);
      return;
    }
    await deleteMaster(kind, row.id);
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error);
    }
  }
}

async function handleFailureModeSaved() {
  await Promise.all([failureModeGridApi.reload(), loadBaseOptions()]);
}

async function handleMasterSaved(payload: { kind: MasterResourceKind }) {
  await reloadMasterGrid(payload.kind);
}

function handleOpenFailureModeInsight(row: FailureModeItem) {
  relationInsightDrawerRef.value?.openFailureMode(row.id);
}

function handleOpenInterceptionInsight(row: InterceptionStrategyItem) {
  relationInsightDrawerRef.value?.openInterception(row.id);
}

function handleOpenHandlingMeasureInsight(row: HandlingMeasureItem) {
  relationInsightDrawerRef.value?.openHandlingMeasure(row.id);
}

function handleOpenObservationMethodInsight(row: ObservationMethodItem) {
  relationInsightDrawerRef.value?.openObservationMethod(row.id);
}

function handleOpenHuatuoDiagnosisInsight(row: HuatuoDiagnosisItem) {
  relationInsightDrawerRef.value?.openHuatuoDiagnosis(row.id);
}

function handleOpenTestCaseInsight(row: TestCaseItem) {
  relationInsightDrawerRef.value?.openTestCase(row.id);
}

function formatObservationInsightLabel(row: ObservationMethodItem) {
  return (
    row.log_keyword ||
    row.log_id ||
    row.monitor_type ||
    row.log_path ||
    row.display_name ||
    '-'
  );
}

watch(
  () => [...failureModeFilters.subsystem],
  () => {
    const allowedSet = new Set(
      failureModeModuleFilterOptions.value.map((item) => item.value),
    );
    const nextModules = normalizeStringList(failureModeFilters.module).filter(
      (item) => allowedSet.size === 0 || allowedSet.has(item),
    );
    if (nextModules.join('|') !== failureModeFilters.module.join('|')) {
      failureModeFilters.module = nextModules;
    }
  },
);

watch(
  () => activeTab.value,
  async (tab) => {
    await nextTick();
    await reloadActiveGrid(tab);
  },
);

onMounted(async () => {
  void loadBaseOptions().catch((error) => {
    console.error(error);
    ElMessage.error('加载故障管理基础选项失败');
  });
});
</script>

<template>
  <Page auto-content-height>
    <FailureModeDrawer
      ref="failureModeDrawerRef"
      :dict-options="dictOptions"
      :subsystem-config-options="subsystemConfigOptions"
      @success="handleFailureModeSaved"
    />
    <MasterDataDrawer
      ref="masterDrawerRef"
      :dict-options="dictOptions"
      @success="handleMasterSaved"
    />
    <RelationInsightDrawer ref="relationInsightDrawerRef" />

    <div class="flex h-full flex-col">
      <section
        class="border-border bg-card relative flex h-full min-h-0 flex-col rounded-lg border p-4 shadow-sm"
      >
        <ElTabs
          v-model="activeTab"
          class="failure-mode-tabs flex h-full min-h-0 flex-col"
        >
          <ElTabPane label="故障模式" name="failureMode">
            <FailureModeGrid class="h-full">
              <template #toolbar-actions>
                <ElButton
                  type="primary"
                  @click="failureModeDrawerRef?.openCreate()"
                >
                  新增故障模式
                </ElButton>
              </template>

              <template #header-brief>
                <div class="failure-mode-header-filter" @click.stop>
                  <span class="failure-mode-header-filter__label">
                    故障模式 brief
                  </span>
                  <ElInput
                    v-model="failureModeFilters.keyword"
                    class="failure-mode-header-filter__input"
                    clearable
                    placeholder="请输入关键词"
                    size="small"
                    @change="commitFailureModeFilters"
                    @clear="commitFailureModeFilters"
                    @keyup.enter="commitFailureModeFilters"
                  />
                </div>
              </template>

              <template #header-author-info>
                <div class="failure-mode-header-filter" @click.stop>
                  <span class="failure-mode-header-filter__label">作者</span>
                  <ElInput
                    v-model="failureModeFilters.author_keyword"
                    class="failure-mode-header-filter__input"
                    clearable
                    placeholder="关键词搜索"
                    size="small"
                    @change="commitFailureModeFilters"
                    @clear="commitFailureModeFilters"
                    @keyup.enter="commitFailureModeFilters"
                  />
                </div>
              </template>

              <template #header-subsystem>
                <div class="failure-mode-header-filter" @click.stop>
                  <span class="failure-mode-header-filter__label">子系统</span>
                  <ElSelect
                    v-model="failureModeFilters.subsystem"
                    class="failure-mode-header-filter__select"
                    clearable
                    collapse-tags
                    collapse-tags-tooltip
                    filterable
                    multiple
                    placeholder="全部，可多选"
                    size="small"
                    @clear="commitFailureModeFilters"
                    @visible-change="handleFailureModeDictVisibleChange"
                  >
                    <ElOption
                      v-for="item in failureModeSubsystemFilterOptions"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </ElSelect>
                </div>
              </template>

              <template #header-module>
                <div class="failure-mode-header-filter" @click.stop>
                  <span class="failure-mode-header-filter__label">模块</span>
                  <ElSelect
                    v-model="failureModeFilters.module"
                    class="failure-mode-header-filter__select"
                    clearable
                    collapse-tags
                    collapse-tags-tooltip
                    filterable
                    multiple
                    placeholder="全部，可多选"
                    size="small"
                    @clear="commitFailureModeFilters"
                    @visible-change="handleFailureModeDictVisibleChange"
                  >
                    <ElOption
                      v-for="item in failureModeModuleFilterOptions"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </ElSelect>
                </div>
              </template>

              <template #header-status>
                <div class="failure-mode-header-filter" @click.stop>
                  <span class="failure-mode-header-filter__label">状态</span>
                  <ElSelect
                    v-model="failureModeFilters.status"
                    class="failure-mode-header-filter__select"
                    clearable
                    collapse-tags
                    collapse-tags-tooltip
                    filterable
                    multiple
                    placeholder="全部，可多选"
                    size="small"
                    @clear="commitFailureModeFilters"
                    @visible-change="handleFailureModeDictVisibleChange"
                  >
                    <ElOption
                      v-for="item in dictOptions.status"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </ElSelect>
                </div>
              </template>

              <template #cell-chips="{ row }">
                {{ formatTextList(row.chips) || '-' }}
              </template>
              <template #cell-brief="{ row }">
                <button
                  class="failure-mode-link-cell"
                  type="button"
                  @click="handleOpenFailureModeInsight(row)"
                >
                  <span class="failure-mode-link-cell__text">
                    {{ row.brief }}
                  </span>
                </button>
              </template>
              <template #cell-fault_categories="{ row }">
                {{ formatTextList(row.fault_categories) || '-' }}
              </template>
              <template #cell-symptoms="{ row }">
                {{ formatTextList(row.symptoms) || '-' }}
              </template>
              <template #cell-author_info="{ row }">
                {{ formatUserNames(row.author_info) || '-' }}
              </template>
              <template #cell-related_dts_nos="{ row }">
                {{ formatTextList(row.related_dts_nos) || '-' }}
              </template>
              <template #cell-handling_measure_items="{ row }">
                {{ formatRelationLabels(row.handling_measure_items) || '-' }}
              </template>
              <template #cell-status="{ row }">
                {{ row.status || '-' }}
              </template>
              <template #cell-source_task_no="{ row }">
                <div class="text-sm text-gray-700">
                  {{ formatFailureModeSourceLabel(row) }}
                </div>
                <div
                  v-if="formatFailureModeSourceHint(row)"
                  class="mt-1 text-xs text-gray-500"
                >
                  {{ formatFailureModeSourceHint(row) }}
                </div>
              </template>
              <template #cell-actions="{ row }">
                <div class="flex justify-center gap-1">
                  <ElTooltip content="编辑" placement="top">
                    <ElButton
                      circle
                      link
                      size="small"
                      type="primary"
                      @click="handleFailureModeAction('edit', row)"
                    >
                      <IconifyIcon icon="ep:edit" />
                    </ElButton>
                  </ElTooltip>
                  <ElTooltip content="删除" placement="top">
                    <ElButton
                      circle
                      link
                      size="small"
                      type="danger"
                      @click="handleFailureModeAction('delete', row)"
                    >
                      <IconifyIcon icon="ep:delete" />
                    </ElButton>
                  </ElTooltip>
                </div>
              </template>
            </FailureModeGrid>
          </ElTabPane>

          <ElTabPane label="产线拦截策略" lazy name="interception">
            <section class="flex h-full min-h-0 flex-col">
              <div class="min-h-0 flex-1">
                <InterceptionGrid class="h-full">
                  <template #toolbar-actions>
                    <ElButton
                      type="primary"
                      @click="openMasterCreate('interception')"
                    >
                      新增产线拦截策略
                    </ElButton>
                  </template>

                  <template #header-interception_item>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        产线拦截项
                      </span>
                      <ElInput
                        v-model="interceptionFilters.keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="输入关键词"
                        size="small"
                        @change="commitInterceptionFilters"
                        @clear="commitInterceptionFilters"
                        @keyup.enter="commitInterceptionFilters"
                      />
                    </div>
                  </template>

                  <template #header-owner-info>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        设计责任人
                      </span>
                      <ElInput
                        v-model="interceptionFilters.owner_keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="关键词搜索"
                        size="small"
                        @change="commitInterceptionFilters"
                        @clear="commitInterceptionFilters"
                        @keyup.enter="commitInterceptionFilters"
                      />
                    </div>
                  </template>

                  <template #cell-owner_info="{ row }">
                    {{ formatUserNames(row.owner_info) || '-' }}
                  </template>
                  <template #cell-interception_item="{ row }">
                    <button
                      class="failure-mode-link-cell"
                      type="button"
                      @click="handleOpenInterceptionInsight(row)"
                    >
                      <span class="failure-mode-link-cell__text">
                        {{ row.interception_item }}
                      </span>
                    </button>
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="
                            handleMasterAction('interception', 'edit', row)
                          "
                        >
                          <IconifyIcon icon="ep:edit" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="删除" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="danger"
                          @click="
                            handleMasterAction('interception', 'delete', row)
                          "
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </InterceptionGrid>
              </div>
            </section>
          </ElTabPane>

          <ElTabPane label="故障处理措施" lazy name="measure">
            <section class="flex h-full min-h-0 flex-col">
              <div class="min-h-0 flex-1">
                <HandlingMeasureGrid class="h-full">
                  <template #toolbar-actions>
                    <ElButton
                      type="primary"
                      @click="openMasterCreate('measure')"
                    >
                      新增故障处理措施
                    </ElButton>
                  </template>

                  <template #header-measure>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        处理措施
                      </span>
                      <ElInput
                        v-model="handlingMeasureFilters.keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="输入关键词"
                        size="small"
                        @change="commitHandlingMeasureFilters"
                        @clear="commitHandlingMeasureFilters"
                        @keyup.enter="commitHandlingMeasureFilters"
                      />
                    </div>
                  </template>

                  <template #header-measure_category>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        措施类别
                      </span>
                      <ElSelect
                        v-model="handlingMeasureFilters.measure_category"
                        class="failure-mode-header-filter__select"
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        multiple
                        placeholder="全部，可多选"
                        size="small"
                        @clear="commitHandlingMeasureFilters"
                        @visible-change="handleHandlingMeasureDictVisibleChange"
                      >
                        <ElOption
                          v-for="item in dictOptions.measure_category"
                          :key="item.value"
                          :label="item.label"
                          :value="item.value"
                        />
                      </ElSelect>
                    </div>
                  </template>

                  <template #header-owner-info>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        设计责任人
                      </span>
                      <ElInput
                        v-model="handlingMeasureFilters.owner_keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="关键词搜索"
                        size="small"
                        @change="commitHandlingMeasureFilters"
                        @clear="commitHandlingMeasureFilters"
                        @keyup.enter="commitHandlingMeasureFilters"
                      />
                    </div>
                  </template>

                  <template #cell-test_case_items="{ row }">
                    {{ formatRelationLabels(row.test_case_items) || '-' }}
                  </template>
                  <template #cell-measure="{ row }">
                    <button
                      class="failure-mode-link-cell"
                      type="button"
                      @click="handleOpenHandlingMeasureInsight(row)"
                    >
                      <span class="failure-mode-link-cell__text">
                        {{ row.measure }}
                      </span>
                    </button>
                  </template>
                  <template #cell-owner_info="{ row }">
                    {{ formatUserNames(row.owner_info) || '-' }}
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="handleMasterAction('measure', 'edit', row)"
                        >
                          <IconifyIcon icon="ep:edit" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="删除" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="danger"
                          @click="handleMasterAction('measure', 'delete', row)"
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </HandlingMeasureGrid>
              </div>
            </section>
          </ElTabPane>

          <ElTabPane label="维测手段" lazy name="observation">
            <section class="flex h-full min-h-0 flex-col">
              <div class="min-h-0 flex-1">
                <ObservationGrid class="h-full">
                  <template #toolbar-actions>
                    <ElButton
                      type="primary"
                      @click="openMasterCreate('observation')"
                    >
                      新增维测手段
                    </ElButton>
                  </template>

                  <template #header-log_keyword>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        日志关键词
                      </span>
                      <ElInput
                        v-model="observationFilters.keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="输入关键词"
                        size="small"
                        @change="commitObservationFilters"
                        @clear="commitObservationFilters"
                        @keyup.enter="commitObservationFilters"
                      />
                    </div>
                  </template>

                  <template #header-monitor_type>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        维测类型
                      </span>
                      <ElSelect
                        v-model="observationFilters.monitor_type"
                        class="failure-mode-header-filter__select"
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        multiple
                        placeholder="全部，可多选"
                        size="small"
                        @clear="commitObservationFilters"
                        @visible-change="handleObservationDictVisibleChange"
                      >
                        <ElOption
                          v-for="item in dictOptions.monitor_type"
                          :key="item.value"
                          :label="item.label"
                          :value="item.value"
                        />
                      </ElSelect>
                    </div>
                  </template>

                  <template #header-owner-info>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        设计责任人
                      </span>
                      <ElInput
                        v-model="observationFilters.owner_keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="关键词搜索"
                        size="small"
                        @change="commitObservationFilters"
                        @clear="commitObservationFilters"
                        @keyup.enter="commitObservationFilters"
                      />
                    </div>
                  </template>

                  <template #cell-owner_info="{ row }">
                    {{ formatUserNames(row.owner_info) || '-' }}
                  </template>
                  <template #cell-log_keyword="{ row }">
                    <button
                      class="failure-mode-link-cell"
                      type="button"
                      @click="handleOpenObservationMethodInsight(row)"
                    >
                      <span class="failure-mode-link-cell__text">
                        {{ formatObservationInsightLabel(row) }}
                      </span>
                    </button>
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="
                            handleMasterAction('observation', 'edit', row)
                          "
                        >
                          <IconifyIcon icon="ep:edit" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="删除" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="danger"
                          @click="
                            handleMasterAction('observation', 'delete', row)
                          "
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </ObservationGrid>
              </div>
            </section>
          </ElTabPane>

          <ElTabPane label="华佗诊断方案" lazy name="huatuo">
            <section class="flex h-full min-h-0 flex-col">
              <div class="min-h-0 flex-1">
                <HuatuoGrid class="h-full">
                  <template #toolbar-actions>
                    <ElButton
                      type="primary"
                      @click="openMasterCreate('huatuo')"
                    >
                      新增华佗诊断方案
                    </ElButton>
                  </template>

                  <template #header-huatuo-description>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        诊断方案描述
                      </span>
                      <ElInput
                        v-model="huatuoFilters.keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="输入关键词"
                        size="small"
                        @change="commitHuatuoFilters"
                        @clear="commitHuatuoFilters"
                        @keyup.enter="commitHuatuoFilters"
                      />
                    </div>
                  </template>

                  <template #header-owner-info>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        设计责任人
                      </span>
                      <ElInput
                        v-model="huatuoFilters.owner_keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="关键词搜索"
                        size="small"
                        @change="commitHuatuoFilters"
                        @clear="commitHuatuoFilters"
                        @keyup.enter="commitHuatuoFilters"
                      />
                    </div>
                  </template>

                  <template #cell-owner_info="{ row }">
                    {{ formatUserNames(row.owner_info) || '-' }}
                  </template>
                  <template #cell-description="{ row }">
                    <button
                      class="failure-mode-link-cell"
                      type="button"
                      @click="handleOpenHuatuoDiagnosisInsight(row)"
                    >
                      <span class="failure-mode-link-cell__text">
                        {{ row.description }}
                      </span>
                    </button>
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="handleMasterAction('huatuo', 'edit', row)"
                        >
                          <IconifyIcon icon="ep:edit" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="删除" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="danger"
                          @click="handleMasterAction('huatuo', 'delete', row)"
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </HuatuoGrid>
              </div>
            </section>
          </ElTabPane>

          <ElTabPane label="测试用例" lazy name="testCase">
            <section class="flex h-full min-h-0 flex-col">
              <div class="min-h-0 flex-1">
                <TestCaseGrid class="h-full">
                  <template #toolbar-actions>
                    <ElButton
                      type="primary"
                      @click="openMasterCreate('testCase')"
                    >
                      新增测试用例
                    </ElButton>
                  </template>

                  <template #header-test-case-brief>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        测试用例 brief
                      </span>
                      <ElInput
                        v-model="testCaseFilters.keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="输入关键词"
                        size="small"
                        @change="commitTestCaseFilters"
                        @clear="commitTestCaseFilters"
                        @keyup.enter="commitTestCaseFilters"
                      />
                    </div>
                  </template>

                  <template #header-owner-info>
                    <div class="failure-mode-header-filter" @click.stop>
                      <span class="failure-mode-header-filter__label">
                        设计责任人
                      </span>
                      <ElInput
                        v-model="testCaseFilters.owner_keyword"
                        class="failure-mode-header-filter__input"
                        clearable
                        placeholder="关键词搜索"
                        size="small"
                        @change="commitTestCaseFilters"
                        @clear="commitTestCaseFilters"
                        @keyup.enter="commitTestCaseFilters"
                      />
                    </div>
                  </template>

                  <template #cell-owner_info="{ row }">
                    {{ formatUserNames(row.owner_info) || '-' }}
                  </template>
                  <template #cell-brief="{ row }">
                    <button
                      class="failure-mode-link-cell"
                      type="button"
                      @click="handleOpenTestCaseInsight(row)"
                    >
                      <span class="failure-mode-link-cell__text">
                        {{ row.brief }}
                      </span>
                    </button>
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="handleMasterAction('testCase', 'edit', row)"
                        >
                          <IconifyIcon icon="ep:edit" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="删除" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="danger"
                          @click="handleMasterAction('testCase', 'delete', row)"
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </TestCaseGrid>
              </div>
            </section>
          </ElTabPane>
        </ElTabs>
      </section>
    </div>
  </Page>
</template>

<style scoped>
.failure-mode-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
}

.failure-mode-tabs :deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
}

.failure-mode-header-filter {
  display: flex;
  width: 100%;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.failure-mode-header-filter__label {
  width: 100%;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  text-align: center;
  white-space: nowrap;
}

.failure-mode-header-filter__input,
.failure-mode-header-filter__select {
  width: 100%;
  min-width: 0;
}

.failure-mode-link-cell {
  display: block;
  width: 100%;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  cursor: pointer;
}

.failure-mode-link-cell__text {
  width: 100%;
  overflow: hidden;
  color: var(--el-color-primary);
  font-weight: 600;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.failure-mode-link-cell:hover .failure-mode-link-cell__text {
  color: var(--el-color-primary-light-3);
}
</style>
