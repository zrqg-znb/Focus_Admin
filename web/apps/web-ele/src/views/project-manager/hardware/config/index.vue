<script lang="ts" setup>
import type {
  HardwarePoint,
  PlatformConfig,
  ViuHardwarePlatform,
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
  ElOption,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTooltip,
} from 'element-plus';

import {
  createCdcPlatformApi,
  createHardwarePointApi,
  createIdvpPlatformApi,
  createSmartScreenVersionApi,
  createViuPlatformApi,
  deleteCdcPlatformApi,
  deleteHardwarePointApi,
  deleteIdvpPlatformApi,
  deleteSmartScreenVersionApi,
  deleteViuPlatformApi,
  listCdcPlatformsApi,
  listHardwarePointsApi,
  listIdvpPlatformsApi,
  listSmartScreenVersionsApi,
  listViuPlatformsApi,
  updateCdcPlatformApi,
  updateHardwarePointApi,
  updateIdvpPlatformApi,
  updateSmartScreenVersionApi,
  updateViuPlatformApi,
} from '#/api/project-manager/hardware';
import { useZqTable } from '#/components/zq-table';

import {
  usePlatformColumns,
  usePointColumns,
  useSearchFormSchema,
  useViuPlatformColumns,
} from './data';

defineOptions({ name: 'HardwareConfigAdmin' });

const activeTab = ref<'cdc' | 'idvp' | 'points' | 'smart' | 'viu'>('points');

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

const viuPlatforms = ref<ViuHardwarePlatform[]>([]);
const viuConfigInput = ref('');

type PlatformType = 'cdc' | 'idvp' | 'smart' | 'viu';

const configDialogVisible = ref(false);
const configDialogMode = ref<'create' | 'edit'>('create');
const configDialogType = ref<PlatformType>('cdc');
const configDialogSaving = ref(false);
const configForm = ref<{
  configs: string[];
  id?: string;
  name: string;
  remark: string;
}>({
  configs: [],
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

async function ensureViuPlatformsLoaded() {
  const data = await listViuPlatformsApi();
  viuPlatforms.value = data || [];
}

async function openPointCreate() {
  await ensureViuPlatformsLoaded();
  pointDialogMode.value = 'create';
  pointForm.value = { code: '', boards: [], remark: '' };
  pointDialogVisible.value = true;
}

async function openPointEdit(row: HardwarePoint) {
  await ensureViuPlatformsLoaded();
  pointDialogMode.value = 'edit';
  pointForm.value = {
    id: row.id,
    code: row.code,
    boards: Array.isArray(row.boards) ? [...row.boards] : [],
    remark: row.remark || '',
  };
  pointDialogVisible.value = true;
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
    await openPointEdit(row);
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
  configForm.value = { configs: [], name: '', remark: '' };
  viuConfigInput.value = '';
  configDialogVisible.value = true;
}

function openConfigEdit(
  type: PlatformType,
  row: PlatformConfig | ViuHardwarePlatform,
) {
  configDialogType.value = type;
  configDialogMode.value = 'edit';
  configForm.value = {
    configs:
      type === 'viu' && Array.isArray((row as ViuHardwarePlatform).configs)
        ? [...(row as ViuHardwarePlatform).configs]
        : [],
    id: row.id,
    name: row.name,
    remark: row.remark || '',
  };
  viuConfigInput.value = '';
  configDialogVisible.value = true;
}

function addViuConfig() {
  const value = viuConfigInput.value.trim();
  if (!value) return;
  if (!configForm.value.configs.includes(value)) {
    configForm.value.configs.push(value);
  }
  viuConfigInput.value = '';
}

function removeViuConfig(config: string) {
  configForm.value.configs = configForm.value.configs.filter(
    (item) => item !== config,
  );
}

async function queryPlatformList(type: PlatformType) {
  if (type === 'viu') {
    const data = (await listViuPlatformsApi()) || [];
    viuPlatforms.value = data;
    return data;
  }
  if (type === 'idvp') return (await listIdvpPlatformsApi()) || [];
  if (type === 'cdc') return (await listCdcPlatformsApi()) || [];
  return (await listSmartScreenVersionsApi()) || [];
}

async function reloadPlatformGrid(type: PlatformType) {
  switch (type) {
    case 'cdc': {
      await cdcGridApi.reload();

      break;
    }
    case 'idvp': {
      await idvpGridApi.reload();

      break;
    }
    case 'viu': {
      await viuGridApi.reload();

      break;
    }
    default: {
      await smartGridApi.reload();
    }
  }
}

async function submitConfigDialog() {
  const configName = configForm.value.name.trim();
  if (!configName) {
    ElMessage.warning('请输入配置名称');
    return;
  }
  configDialogSaving.value = true;
  try {
    const payload = {
      name: configName,
      remark: configForm.value.remark || undefined,
    };
    switch (configDialogType.value) {
      case 'cdc': {
        if (configDialogMode.value === 'create') {
          await createCdcPlatformApi(payload);
        } else if (configForm.value.id) {
          await updateCdcPlatformApi(configForm.value.id, payload);
        }

        break;
      }
      case 'idvp': {
        if (configDialogMode.value === 'create') {
          await createIdvpPlatformApi(payload);
        } else if (configForm.value.id) {
          await updateIdvpPlatformApi(configForm.value.id, payload);
        }

        break;
      }
      case 'viu': {
        if (configForm.value.configs.length === 0) {
          ElMessage.warning('请至少添加一个典配类型');
          return;
        }
        const viuPayload = {
          ...payload,
          configs: configForm.value.configs || [],
        };
        if (configDialogMode.value === 'create') {
          await createViuPlatformApi(viuPayload);
        } else if (configForm.value.id) {
          await updateViuPlatformApi(configForm.value.id, viuPayload);
        }

        break;
      }
      default: {
        if (configDialogMode.value === 'create') {
          await createSmartScreenVersionApi(payload);
        } else if (configForm.value.id) {
          await updateSmartScreenVersionApi(configForm.value.id, payload);
        }
      }
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

async function deletePlatform(
  type: PlatformType,
  row: PlatformConfig | ViuHardwarePlatform,
) {
  try {
    switch (type) {
      case 'cdc': {
        await deleteCdcPlatformApi(row.id);

        break;
      }
      case 'idvp': {
        await deleteIdvpPlatformApi(row.id);

        break;
      }
      case 'viu': {
        await deleteViuPlatformApi(row.id);

        break;
      }
      default: {
        await deleteSmartScreenVersionApi(row.id);
      }
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
  row: PlatformConfig | ViuHardwarePlatform,
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
    columns: useViuPlatformColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: ZqQueryParams) => {
          const data = (await queryPlatformList(
            'viu',
          )) as ViuHardwarePlatform[];
          const keyword = String(form?.keyword || '').toLowerCase();
          const filtered = keyword
            ? data.filter(
                (item) =>
                  item.name.toLowerCase().includes(keyword) ||
                  (item.configs || []).some((config) =>
                    config.toLowerCase().includes(keyword),
                  ) ||
                  (item.remark || '').toLowerCase().includes(keyword),
              )
            : data;
          return toPagedResult(filtered, page);
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: baseToolbarConfig,
  } as ZqTableGridOptions<ViuHardwarePlatform>,
});

const [IdvpGrid, idvpGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  formOptions: baseFormOptions,
  gridOptions: {
    columns: usePlatformColumns('IDVP 软件平台'),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: ZqQueryParams) => {
          const data = (await queryPlatformList('idvp')) as PlatformConfig[];
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
    if (tab === 'idvp') {
      await idvpGridApi.reload();
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
                  维护车控场景下的硬件点位与 VIU 单板映射，供项目阶段配置引用。
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

          <ElTabPane label="VIU 硬件平台配置" name="viu">
            <section
              class="bg-background flex h-full min-h-0 flex-col rounded-lg"
            >
              <header class="mb-4 shrink-0">
                <h3 class="text-foreground text-base font-semibold">
                  VIU 硬件平台配置
                </h3>
                <p class="text-muted-foreground mt-1 text-sm">
                  维护 VIU 单板型号及其典配列表，供硬件点位与项目阶段联动选择。
                </p>
              </header>
              <div class="min-h-0 flex-1">
                <ViuGrid class="hardware-points-grid h-full">
                  <template #table-title>
                    <ElButton type="primary" @click="openConfigCreate('viu')">
                      新增 VIU 硬件平台
                    </ElButton>
                  </template>
                  <template #cell-configs="{ row }">
                    {{ (row.configs || []).join('、') || '-' }}
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

          <ElTabPane label="IDVP 软件平台配置" name="idvp">
            <section
              class="bg-background flex h-full min-h-0 flex-col rounded-lg"
            >
              <header class="mb-4 shrink-0">
                <h3 class="text-foreground text-base font-semibold">
                  IDVP 软件平台配置
                </h3>
                <p class="text-muted-foreground mt-1 text-sm">
                  维护车控项目可选 IDVP 软件平台版本，项目启用典配时进行绑定。
                </p>
              </header>
              <div class="min-h-0 flex-1">
                <IdvpGrid class="hardware-points-grid h-full">
                  <template #table-title>
                    <ElButton type="primary" @click="openConfigCreate('idvp')">
                      新增 IDVP 软件平台
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
                          @click="onPlatformActionClick('idvp', 'edit', row)"
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
                          @click="onPlatformActionClick('idvp', 'delete', row)"
                        >
                          <IconifyIcon icon="ep:delete" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </template>
                </IdvpGrid>
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
        <ElFormItem label="单板列表">
          <div class="w-full">
            <ElSelect
              v-model="pointForm.boards"
              multiple
              filterable
              clearable
              class="w-full"
              placeholder="请选择 VIU 硬件单板型号"
            >
              <ElOption
                v-for="platform in viuPlatforms"
                :key="platform.id"
                :label="platform.name"
                :value="platform.name"
              />
            </ElSelect>
            <div
              v-if="viuPlatforms.length === 0"
              class="text-muted-foreground mt-2 text-sm"
            >
              暂无 VIU 硬件平台数据，请先在“VIU 硬件平台配置”中新增。
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
          ? 'VIU 硬件平台'
          : configDialogType === 'idvp'
            ? 'IDVP 软件平台'
            : configDialogType === 'cdc'
              ? 'CDC 平台'
              : '智慧屏版本'
      }`"
    >
      <ElForm label-width="120px">
        <ElFormItem label="名称">
          <ElInput v-model="configForm.name" />
        </ElFormItem>
        <ElFormItem v-if="configDialogType === 'viu'" label="典配列表">
          <div class="w-full">
            <div class="mb-2 flex gap-2">
              <ElInput
                v-model="viuConfigInput"
                placeholder="输入典配类型，如：标准版"
                @keyup.enter="addViuConfig"
              />
              <ElButton @click="addViuConfig">添加</ElButton>
            </div>
            <div class="flex flex-wrap gap-2">
              <ElTag
                v-for="config in configForm.configs"
                :key="config"
                closable
                @close="removeViuConfig(config)"
              >
                {{ config }}
              </ElTag>
              <div
                v-if="configForm.configs.length === 0"
                class="text-muted-foreground text-sm"
              >
                暂无典配类型
              </div>
            </div>
          </div>
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
