<script lang="ts" setup>
import type { FailureModeTabKey, MasterResourceKind } from './data';

import type {
  FailureModeItem,
  HandlingMeasureItem,
  HuatuoDiagnosisItem,
  InterceptionStrategyItem,
  ObservationMethodItem,
  TestCaseItem,
} from '#/api/project-manager/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElMessage,
  ElMessageBox,
  ElTabPane,
  ElTabs,
  ElTag,
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
  listFailureModesApi,
  listHandlingMeasuresApi,
  listHuatuoDiagnosesApi,
  listInterceptionStrategiesApi,
  listObservationMethodsApi,
  listTestCasesApi,
} from '#/api/project-manager/failure_mode';
import { useZqTable } from '#/components/zq-table';

import FailureModeDrawer from './components/FailureModeDrawer.vue';
import MasterDataDrawer from './components/MasterDataDrawer.vue';
import {
  createEmptyDictOptions,
  failureModeTabs,
  formatRelationLabels,
  formatTextList,
  formatUserNames,
  getMasterResourceLabel,
  replaceDictOptions,
  useFailureModeColumns,
  useFailureModeSearchSchema,
  useHandlingMeasureColumns,
  useHuatuoColumns,
  useInterceptionColumns,
  useKeywordSearchSchema,
  useObservationColumns,
  useTestCaseColumns,
} from './data';

defineOptions({ name: 'FailureModeAdmin' });

type MasterRow =
  | HandlingMeasureItem
  | HuatuoDiagnosisItem
  | InterceptionStrategyItem
  | ObservationMethodItem
  | TestCaseItem;

interface QueryContext {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const activeTab = ref<FailureModeTabKey>('failureMode');
const dictOptions = reactive(createEmptyDictOptions());
const failureModeDrawerRef = ref<any>();
const masterDrawerRef = ref<any>();

function createKeywordGrid<T extends Record<string, any>>(
  columns: ZqTableGridOptions<T>['columns'],
  request: (params: {
    keyword?: string;
    page?: number;
    pageSize?: number;
  }) => Promise<{ items: T[]; total: number }>,
) {
  return useZqTable<T>({
    gridOptions: {
      border: true,
      columns,
      proxyConfig: {
        autoLoad: true,
        ajax: {
          query: async ({ form, page }: QueryContext) => {
            return request({
              keyword: form?.keyword,
              page: page.currentPage,
              pageSize: page.pageSize,
            });
          },
        },
      },
      rowKey: 'id',
      stripe: true,
      toolbarConfig: {
        custom: true,
        refresh: true,
        search: true,
        zoom: true,
      },
      pagerConfig: {
        enabled: true,
        pageSize: 10,
        pageSizes: [10, 20, 50],
      },
    },
    formOptions: {
      schema: useKeywordSearchSchema(),
      showCollapseButton: false,
      submitOnChange: true,
    },
  });
}

const [FailureModeGrid, failureModeGridApi] = useZqTable<FailureModeItem>({
  gridOptions: {
    border: true,
    columns: useFailureModeColumns(),
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ form, page }: QueryContext) => {
          return listFailureModesApi({
            keyword: form?.keyword,
            module: form?.module,
            page: page.currentPage,
            pageSize: page.pageSize,
            status: form?.status,
            subsystem: form?.subsystem,
          });
        },
      },
    },
    rowKey: 'id',
    stripe: true,
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
    pagerConfig: {
      enabled: true,
      pageSize: 10,
      pageSizes: [10, 20, 50],
    },
  },
  formOptions: {
    schema: useFailureModeSearchSchema(dictOptions),
    showCollapseButton: false,
    submitOnChange: true,
  },
});

const [InterceptionGrid, interceptionGridApi] = createKeywordGrid(
  useInterceptionColumns(),
  listInterceptionStrategiesApi,
);
const [HandlingMeasureGrid, handlingMeasureGridApi] = createKeywordGrid(
  useHandlingMeasureColumns(),
  listHandlingMeasuresApi,
);
const [ObservationGrid, observationGridApi] = createKeywordGrid(
  useObservationColumns(),
  listObservationMethodsApi,
);
const [HuatuoGrid, huatuoGridApi] = createKeywordGrid(
  useHuatuoColumns(),
  listHuatuoDiagnosesApi,
);
const [TestCaseGrid, testCaseGridApi] = createKeywordGrid(
  useTestCaseColumns(),
  listTestCasesApi,
);

async function loadDictOptions() {
  const response = await getFailureModeDictOptionsApi();
  replaceDictOptions(dictOptions, response);
}

function reloadMasterGrid(kind: MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      huatuoGridApi.reload();
      break;
    }
    case 'interception': {
      interceptionGridApi.reload();
      break;
    }
    case 'measure': {
      handlingMeasureGridApi.reload();
      break;
    }
    case 'observation': {
      observationGridApi.reload();
      break;
    }
    default: {
      testCaseGridApi.reload();
    }
  }
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
  reloadMasterGrid(kind);
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
    failureModeGridApi.reload();
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error);
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
  failureModeGridApi.reload();
}

function handleMasterSaved(payload: { kind: MasterResourceKind }) {
  reloadMasterGrid(payload.kind);
}

onMounted(async () => {
  try {
    await loadDictOptions();
  } catch (error) {
    console.error(error);
    ElMessage.error('加载故障模式字典失败');
  }
});
</script>

<template>
  <Page auto-content-height>
    <FailureModeDrawer
      ref="failureModeDrawerRef"
      :dict-options="dictOptions"
      @success="handleFailureModeSaved"
    />
    <MasterDataDrawer
      ref="masterDrawerRef"
      :dict-options="dictOptions"
      @success="handleMasterSaved"
    />

    <div
      class="rounded-2xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)] p-4 shadow-sm"
    >
      <ElTabs v-model="activeTab" class="failure-mode-tabs">
        <ElTabPane
          v-for="tab in failureModeTabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
        >
          <FailureModeGrid
            v-if="tab.key === 'failureMode'"
            class="min-h-[600px]"
          >
            <template #toolbar-actions>
              <ElButton
                type="primary"
                @click="failureModeDrawerRef?.openCreate()"
              >
                新增故障模式
              </ElButton>
            </template>

            <template #cell-chips="{ row }">
              {{ formatTextList(row.chips) || '-' }}
            </template>
            <template #cell-fault_categories="{ row }">
              {{ formatTextList(row.fault_categories) || '-' }}
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
              <ElTag v-if="row.status" size="small" type="success">
                {{ row.status }}
              </ElTag>
              <span v-else>-</span>
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

          <InterceptionGrid
            v-else-if="tab.key === 'interception'"
            class="min-h-[600px]"
          >
            <template #toolbar-actions>
              <ElButton
                type="primary"
                @click="openMasterCreate('interception')"
              >
                新增产线拦截策略
              </ElButton>
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
                    @click="handleMasterAction('interception', 'edit', row)"
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
                    @click="handleMasterAction('interception', 'delete', row)"
                  >
                    <IconifyIcon icon="ep:delete" />
                  </ElButton>
                </ElTooltip>
              </div>
            </template>
          </InterceptionGrid>

          <HandlingMeasureGrid
            v-else-if="tab.key === 'measure'"
            class="min-h-[600px]"
          >
            <template #toolbar-actions>
              <ElButton type="primary" @click="openMasterCreate('measure')">
                新增故障处理措施
              </ElButton>
            </template>
            <template #cell-test_case_items="{ row }">
              {{ formatRelationLabels(row.test_case_items) || '-' }}
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

          <ObservationGrid
            v-else-if="tab.key === 'observation'"
            class="min-h-[600px]"
          >
            <template #toolbar-actions>
              <ElButton type="primary" @click="openMasterCreate('observation')">
                新增维测手段
              </ElButton>
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
                    @click="handleMasterAction('observation', 'edit', row)"
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
                    @click="handleMasterAction('observation', 'delete', row)"
                  >
                    <IconifyIcon icon="ep:delete" />
                  </ElButton>
                </ElTooltip>
              </div>
            </template>
          </ObservationGrid>

          <HuatuoGrid v-else-if="tab.key === 'huatuo'" class="min-h-[600px]">
            <template #toolbar-actions>
              <ElButton type="primary" @click="openMasterCreate('huatuo')">
                新增华佗诊断方案
              </ElButton>
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

          <TestCaseGrid v-else class="min-h-[600px]">
            <template #toolbar-actions>
              <ElButton type="primary" @click="openMasterCreate('testCase')">
                新增测试用例
              </ElButton>
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
        </ElTabPane>
      </ElTabs>
    </div>
  </Page>
</template>
