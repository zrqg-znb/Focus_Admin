<script lang="ts" setup>
import type {
  HardwarePoint,
  PlatformConfig,
} from '#/api/project-manager/hardware';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { nextTick, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTooltip,
} from 'element-plus';

import {
  createCdcPlatformApi,
  createHardwarePointApi,
  createSmartScreenVersionApi,
  createViuPlatformApi,
  deleteCdcPlatformApi,
  deleteHardwarePointApi,
  deleteSmartScreenVersionApi,
  deleteViuPlatformApi,
  listCdcPlatformsApi,
  listHardwarePointsApi,
  listSmartScreenVersionsApi,
  listViuPlatformsApi,
  updateCdcPlatformApi,
  updateHardwarePointApi,
  updateSmartScreenVersionApi,
  updateViuPlatformApi,
} from '#/api/project-manager/hardware';
import { useZqTable } from '#/components/zq-table';

import {
  usePlatformColumns,
  usePointColumns,
  useSearchFormSchema,
} from './data';

defineOptions({ name: 'HardwareConfigAdmin' });

const activeTab = ref<'cdc' | 'points' | 'smart' | 'viu'>('points');

const pointDialogVisible = ref(false);
const pointDialogMode = ref<'create' | 'edit'>('create');
const pointDialogSaving = ref(false);
const pointForm = ref<{
  boards: string[];
  code: string;
  id?: string;
  remark: string;
}>({
  code: '',
  boards: [],
  remark: '',
});
const boardInput = ref('');

type PlatformType = 'cdc' | 'smart' | 'viu';

const configDialogVisible = ref(false);
const configDialogMode = ref<'create' | 'edit'>('create');
const configDialogType = ref<PlatformType>('cdc');
const configDialogSaving = ref(false);
const configForm = ref<{ id?: string; name: string; remark: string }>({
  name: '',
  remark: '',
});
interface ZqQueryParams {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

function openPointCreate() {
  pointDialogMode.value = 'create';
  pointForm.value = { code: '', boards: [], remark: '' };
  boardInput.value = '';
  pointDialogVisible.value = true;
}

function openPointEdit(row: HardwarePoint) {
  pointDialogMode.value = 'edit';
  pointForm.value = {
    id: row.id,
    code: row.code,
    boards: Array.isArray(row.boards) ? [...row.boards] : [],
    remark: row.remark || '',
  };
  boardInput.value = '';
  pointDialogVisible.value = true;
}

function addBoard() {
  const value = boardInput.value.trim();
  if (!value) return;
  if (!pointForm.value.boards.includes(value)) {
    pointForm.value.boards.push(value);
  }
  boardInput.value = '';
}

function removeBoard(board: string) {
  pointForm.value.boards = pointForm.value.boards.filter(
    (item) => item !== board,
  );
}

async function submitPointDialog() {
  if (!pointForm.value.code) {
    ElMessage.warning('请输入硬件点位');
    return;
  }
  pointDialogSaving.value = true;
  try {
    if (pointDialogMode.value === 'create') {
      await createHardwarePointApi({
        code: pointForm.value.code,
        boards: pointForm.value.boards,
        remark: pointForm.value.remark || undefined,
      });
      ElMessage.success('创建成功');
    } else if (pointForm.value.id) {
      await updateHardwarePointApi(pointForm.value.id, {
        code: pointForm.value.code,
        boards: pointForm.value.boards,
        remark: pointForm.value.remark || undefined,
      });
      ElMessage.success('更新成功');
    }
    pointDialogVisible.value = false;
    await gridApi.reload();
  } finally {
    pointDialogSaving.value = false;
  }
}

async function onPointActionClick(code: 'delete' | 'edit', row: HardwarePoint) {
  if (code === 'edit') {
    openPointEdit(row);
    return;
  }
  if (code === 'delete') {
    try {
      await deleteHardwarePointApi(row.id);
      ElMessage.success('删除成功');
      await gridApi.reload();
    } catch (error) {
      console.error(error);
      ElMessage.error('删除失败');
    }
  }
}

function openConfigCreate(type: PlatformType) {
  configDialogType.value = type;
  configDialogMode.value = 'create';
  configForm.value = { name: '', remark: '' };
  configDialogVisible.value = true;
}

function openConfigEdit(type: PlatformType, row: PlatformConfig) {
  configDialogType.value = type;
  configDialogMode.value = 'edit';
  configForm.value = {
    id: row.id,
    name: row.name,
    remark: row.remark || '',
  };
  configDialogVisible.value = true;
}

async function queryPlatformList(type: PlatformType) {
  if (type === 'viu') return (await listViuPlatformsApi()) || [];
  if (type === 'cdc') return (await listCdcPlatformsApi()) || [];
  return (await listSmartScreenVersionsApi()) || [];
}

async function reloadPlatformGrid(type: PlatformType) {
  if (type === 'viu') {
    await viuGridApi.reload();
  } else if (type === 'cdc') {
    await cdcGridApi.reload();
  } else {
    await smartGridApi.reload();
  }
}

async function submitConfigDialog() {
  if (!configForm.value.name) {
    ElMessage.warning('请输入配置名称');
    return;
  }
  configDialogSaving.value = true;
  try {
    const payload = {
      name: configForm.value.name,
      remark: configForm.value.remark || undefined,
    };
    if (configDialogType.value === 'viu') {
      if (configDialogMode.value === 'create') {
        await createViuPlatformApi(payload);
      } else if (configForm.value.id) {
        await updateViuPlatformApi(configForm.value.id, payload);
      }
    } else if (configDialogType.value === 'cdc') {
      if (configDialogMode.value === 'create') {
        await createCdcPlatformApi(payload);
      } else if (configForm.value.id) {
        await updateCdcPlatformApi(configForm.value.id, payload);
      }
    } else if (configDialogMode.value === 'create') {
      await createSmartScreenVersionApi(payload);
    } else if (configForm.value.id) {
      await updateSmartScreenVersionApi(configForm.value.id, payload);
    }
    ElMessage.success(
      configDialogMode.value === 'create' ? '创建成功' : '更新成功',
    );
    configDialogVisible.value = false;
    await reloadPlatformGrid(configDialogType.value);
  } finally {
    configDialogSaving.value = false;
  }
}

async function deletePlatform(type: PlatformType, row: PlatformConfig) {
  try {
    if (type === 'viu') {
      await deleteViuPlatformApi(row.id);
    } else if (type === 'cdc') {
      await deleteCdcPlatformApi(row.id);
    } else {
      await deleteSmartScreenVersionApi(row.id);
    }
    ElMessage.success('删除成功');
    await reloadPlatformGrid(type);
  } catch (error) {
    console.error(error);
    ElMessage.error('删除失败');
  }
}

async function onPlatformActionClick(
  type: PlatformType,
  code: 'delete' | 'edit',
  row: PlatformConfig,
) {
  if (code === 'edit') {
    openConfigEdit(type, row);
    return;
  }
  if (code === 'delete') {
    await deletePlatform(type, row);
  }
}

function toPagedResult<T>(items: T[], page: ZqQueryParams['page']) {
  const start = (page.currentPage - 1) * page.pageSize;
  const end = start + page.pageSize;
  return {
    items: items.slice(start, end),
    total: items.length,
  };
}

const baseToolbarConfig = {
  custom: true,
  refresh: true,
  search: true,
  zoom: true,
};
const baseFormOptions = {
  schema: useSearchFormSchema(),
  showCollapseButton: false,
  submitOnChange: true,
};

const [Grid, gridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  formOptions: baseFormOptions,
  gridOptions: {
    columns: usePointColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: ZqQueryParams) => {
          const data = await listHardwarePointsApi();
          const keyword = String(form?.keyword || '').toLowerCase();
          const filtered = keyword
            ? data.filter(
                (item) =>
                  item.code.toLowerCase().includes(keyword) ||
                  (item.boards || []).some((itemBoard) =>
                    itemBoard.toLowerCase().includes(keyword),
                  ),
              )
            : data;
          return toPagedResult(filtered, page);
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: baseToolbarConfig,
  } as ZqTableGridOptions<HardwarePoint>,
});

const [ViuGrid, viuGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  formOptions: baseFormOptions,
  gridOptions: {
    columns: usePlatformColumns('VIU 平台'),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: ZqQueryParams) => {
          const data = await queryPlatformList('viu');
          const keyword = String(form?.keyword || '').toLowerCase();
          const filtered = keyword
            ? data.filter(
                (item) =>
                  item.name.toLowerCase().includes(keyword) ||
                  (item.remark || '').toLowerCase().includes(keyword),
              )
            : data;
          return toPagedResult(filtered, page);
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: baseToolbarConfig,
  } as ZqTableGridOptions<PlatformConfig>,
});

const [CdcGrid, cdcGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  formOptions: baseFormOptions,
  gridOptions: {
    columns: usePlatformColumns('CDC 平台'),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: ZqQueryParams) => {
          const data = await queryPlatformList('cdc');
          const keyword = String(form?.keyword || '').toLowerCase();
          const filtered = keyword
            ? data.filter(
                (item) =>
                  item.name.toLowerCase().includes(keyword) ||
                  (item.remark || '').toLowerCase().includes(keyword),
              )
            : data;
          return toPagedResult(filtered, page);
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: baseToolbarConfig,
  } as ZqTableGridOptions<PlatformConfig>,
});

const [SmartGrid, smartGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  formOptions: baseFormOptions,
  gridOptions: {
    columns: usePlatformColumns('智慧屏版本'),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: ZqQueryParams) => {
          const data = await queryPlatformList('smart');
          const keyword = String(form?.keyword || '').toLowerCase();
          const filtered = keyword
            ? data.filter(
                (item) =>
                  item.name.toLowerCase().includes(keyword) ||
                  (item.remark || '').toLowerCase().includes(keyword),
              )
            : data;
          return toPagedResult(filtered, page);
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: baseToolbarConfig,
  } as ZqTableGridOptions<PlatformConfig>,
});

watch(
  () => activeTab.value,
  async (tab) => {
    await nextTick();
    if (tab === 'points') {
      await gridApi.reload();
      return;
    }
    if (tab === 'viu') {
      await viuGridApi.reload();
      return;
    }
    if (tab === 'cdc') {
      await cdcGridApi.reload();
      return;
    }
    await smartGridApi.reload();
  },
);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full flex-col">
      <section
        class="border-border bg-card flex h-full min-h-0 flex-col rounded-lg border p-4 shadow-sm"
      >
        <ElTabs
          v-model="activeTab"
          class="hardware-tabs flex h-full min-h-0 flex-col"
        >
          <ElTabPane label="硬件点位配置" name="points">
            <section
              class="bg-background flex h-full min-h-0 flex-col rounded-lg"
            >
              <header class="mb-4 shrink-0">
                <h3 class="text-foreground text-base font-semibold">
                  硬件点位管理
                </h3>
                <p class="text-muted-foreground mt-1 text-sm">
                  维护车控场景下的硬件点位与板子型号映射，供项目阶段配置引用。
                </p>
              </header>
              <div class="min-h-0 flex-1">
                <Grid class="hardware-points-grid h-full">
                  <template #table-title>
                    <ElButton type="primary" @click="openPointCreate">
                      新增点位
                    </ElButton>
                  </template>
                  <template #cell-boards="{ row }">
                    {{ (row.boards || []).join('、') || '-' }}
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex items-center justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="onPointActionClick('edit', row)"
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
                          @click="onPointActionClick('delete', row)"
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </Grid>
              </div>
            </section>
          </ElTabPane>

          <ElTabPane label="VIU 平台配置" name="viu">
            <section
              class="bg-background flex h-full min-h-0 flex-col rounded-lg"
            >
              <header class="mb-4 shrink-0">
                <h3 class="text-foreground text-base font-semibold">
                  VIU 平台配置
                </h3>
                <p class="text-muted-foreground mt-1 text-sm">
                  维护车控项目可选的 VIU 平台选项，项目启用典配时进行绑定。
                </p>
              </header>
              <div class="min-h-0 flex-1">
                <ViuGrid class="hardware-points-grid h-full">
                  <template #table-title>
                    <ElButton type="primary" @click="openConfigCreate('viu')">
                      新增 VIU 平台
                    </ElButton>
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex items-center justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="onPlatformActionClick('viu', 'edit', row)"
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
                          @click="onPlatformActionClick('viu', 'delete', row)"
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </ViuGrid>
              </div>
            </section>
          </ElTabPane>

          <ElTabPane label="CDC 平台配置" name="cdc">
            <section
              class="bg-background flex h-full min-h-0 flex-col rounded-lg"
            >
              <header class="mb-4 shrink-0">
                <h3 class="text-foreground text-base font-semibold">
                  CDC 平台配置
                </h3>
                <p class="text-muted-foreground mt-1 text-sm">
                  维护座舱场景可选的 CDC 平台，供项目阶段典配配置选择。
                </p>
              </header>
              <div class="min-h-0 flex-1">
                <CdcGrid class="hardware-points-grid h-full">
                  <template #table-title>
                    <ElButton type="primary" @click="openConfigCreate('cdc')">
                      新增 CDC 平台
                    </ElButton>
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex items-center justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="onPlatformActionClick('cdc', 'edit', row)"
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
                          @click="onPlatformActionClick('cdc', 'delete', row)"
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </CdcGrid>
              </div>
            </section>
          </ElTabPane>

          <ElTabPane label="智慧屏版本配置" name="smart">
            <section
              class="bg-background flex h-full min-h-0 flex-col rounded-lg"
            >
              <header class="mb-4 shrink-0">
                <h3 class="text-foreground text-base font-semibold">
                  智慧屏版本配置
                </h3>
                <p class="text-muted-foreground mt-1 text-sm">
                  维护座舱项目可选的智慧屏版本，与 CDC 平台共同组成典配信息。
                </p>
              </header>
              <div class="min-h-0 flex-1">
                <SmartGrid class="hardware-points-grid h-full">
                  <template #table-title>
                    <ElButton type="primary" @click="openConfigCreate('smart')">
                      新增智慧屏版本
                    </ElButton>
                  </template>
                  <template #cell-actions="{ row }">
                    <div class="flex items-center justify-center gap-1">
                      <ElTooltip content="编辑" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="onPlatformActionClick('smart', 'edit', row)"
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
                          @click="onPlatformActionClick('smart', 'delete', row)"
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </SmartGrid>
              </div>
            </section>
          </ElTabPane>
        </ElTabs>
      </section>
    </div>

    <ElDialog
      v-model="pointDialogVisible"
      :title="pointDialogMode === 'create' ? '新增点位' : '编辑点位'"
    >
      <ElForm label-width="120px">
        <ElFormItem label="硬件点位">
          <ElInput v-model="pointForm.code" placeholder="如：viu0" />
        </ElFormItem>
        <ElFormItem label="板子列表">
          <div class="w-full">
            <div class="mb-2 flex gap-2">
              <ElInput
                v-model="boardInput"
                placeholder="输入板子型号，如：VIU270"
                @keyup.enter="addBoard"
              />
              <ElButton @click="addBoard">添加</ElButton>
            </div>
            <div class="flex flex-wrap gap-2">
              <ElTag
                v-for="board in pointForm.boards"
                :key="board"
                closable
                @close="removeBoard(board)"
              >
                {{ board }}
              </ElTag>
              <div
                v-if="pointForm.boards.length === 0"
                class="text-muted-foreground text-sm"
              >
                暂无板子配置
              </div>
            </div>
          </div>
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="pointForm.remark" placeholder="备注（可选）" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="pointDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="pointDialogSaving"
          @click="submitPointDialog"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="configDialogVisible"
      :title="`${configDialogMode === 'create' ? '新增' : '编辑'}${
        configDialogType === 'viu'
          ? 'VIU 平台'
          : configDialogType === 'cdc'
            ? 'CDC 平台'
            : '智慧屏版本'
      }`"
    >
      <ElForm label-width="120px">
        <ElFormItem label="名称">
          <ElInput v-model="configForm.name" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="configForm.remark" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="configDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="configDialogSaving"
          @click="submitConfigDialog"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style scoped>
.hardware-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
}

.hardware-tabs :deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
}
</style>
