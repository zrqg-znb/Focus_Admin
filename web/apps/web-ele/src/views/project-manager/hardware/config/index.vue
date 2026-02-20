<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type {
  HardwarePoint,
  PlatformConfig,
} from '#/api/project-manager/hardware';

import { nextTick, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
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

import { useColumns, useSearchFormSchema } from './data';

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

const viuPlatforms = ref<PlatformConfig[]>([]);
const cdcPlatforms = ref<PlatformConfig[]>([]);
const smartScreenVersions = ref<PlatformConfig[]>([]);
const configDialogVisible = ref(false);
const configDialogMode = ref<'create' | 'edit'>('create');
const configDialogType = ref<'cdc' | 'smart' | 'viu'>('cdc');
const configDialogSaving = ref(false);
const configForm = ref<{ id?: string; name: string; remark: string }>({
  name: '',
  remark: '',
});

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

async function onPointActionClick({
  code,
  row,
}: OnActionClickParams<HardwarePoint>) {
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

async function loadPlatformData() {
  try {
    const [viu, cdc, smart] = await Promise.all([
      listViuPlatformsApi(),
      listCdcPlatformsApi(),
      listSmartScreenVersionsApi(),
    ]);
    viuPlatforms.value = viu || [];
    cdcPlatforms.value = cdc || [];
    smartScreenVersions.value = smart || [];
  } catch (error) {
    console.error(error);
    ElMessage.error('获取平台配置失败');
  }
}

function openConfigCreate(type: 'cdc' | 'smart' | 'viu') {
  configDialogType.value = type;
  configDialogMode.value = 'create';
  configForm.value = { name: '', remark: '' };
  configDialogVisible.value = true;
}

function openConfigEdit(type: 'cdc' | 'smart' | 'viu', row: PlatformConfig) {
  configDialogType.value = type;
  configDialogMode.value = 'edit';
  configForm.value = {
    id: row.id,
    name: row.name,
    remark: row.remark || '',
  };
  configDialogVisible.value = true;
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
    await loadPlatformData();
  } finally {
    configDialogSaving.value = false;
  }
}

async function deletePlatform(
  type: 'cdc' | 'smart' | 'viu',
  row: PlatformConfig,
) {
  try {
    if (type === 'viu') {
      await deleteViuPlatformApi(row.id);
    } else if (type === 'cdc') {
      await deleteCdcPlatformApi(row.id);
    } else {
      await deleteSmartScreenVersionApi(row.id);
    }
    ElMessage.success('删除成功');
    await loadPlatformData();
  } catch (error) {
    console.error(error);
    ElMessage.error('删除失败');
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    autoResize: true,
    columns: useColumns(onPointActionClick),
    border: true,
    height: '100%',
    keepSource: true,
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const data = await listHardwarePointsApi();
          const keyword = (formValues.keyword || '').toLowerCase();
          const filtered = keyword
            ? data.filter(
                (item) =>
                  item.code.toLowerCase().includes(keyword) ||
                  (item.boards || []).some((itemBoard) =>
                    itemBoard.toLowerCase().includes(keyword),
                  ),
              )
            : data;

          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          return {
            items: filtered.slice(start, end),
            total: filtered.length,
          };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<HardwarePoint>,
});

watch(
  () => activeTab.value,
  async (tab) => {
    if (tab === 'points') {
      await nextTick();
      (gridApi.grid as any)?.recalculate?.();
      await gridApi.reload();
    }
  },
);

loadPlatformData();
</script>

<template>
  <Page auto-content-height class="hardware-config-page">
    <section class="tabs-card">
      <ElTabs v-model="activeTab" class="hardware-tabs">
        <ElTabPane label="硬件点位配置" name="points">
          <section class="config-card">
            <header class="card-header">
              <div>
                <h3 class="card-title">硬件点位管理</h3>
                <p class="card-desc">
                  维护车控场景下的硬件点位与板子型号映射，供项目阶段配置引用。
                </p>
              </div>
            </header>
            <div class="points-pane">
              <Grid class="points-grid">
                <template #table-title>
                  <ElButton type="primary" @click="openPointCreate">
                    新增点位
                  </ElButton>
                </template>
              </Grid>
            </div>
          </section>
        </ElTabPane>

        <ElTabPane label="VIU 平台配置" name="viu">
          <section class="config-card">
            <header class="card-header">
              <div>
                <h3 class="card-title">VIU 平台配置</h3>
                <p class="card-desc">
                  维护车控项目可选的 VIU 平台选项，项目启用典配时进行绑定。
                </p>
              </div>
            </header>
            <div class="card-action">
              <ElButton type="primary" @click="openConfigCreate('viu')">
                新增 VIU 平台
              </ElButton>
            </div>
            <ElTable :data="viuPlatforms" border class="config-table">
              <ElTableColumn prop="name" label="VIU 平台" min-width="220" />
              <ElTableColumn prop="remark" label="备注" min-width="220" />
              <ElTableColumn label="操作" width="180">
                <template #default="{ row }">
                  <ElButton
                    type="primary"
                    link
                    @click="openConfigEdit('viu', row)"
                  >
                    编辑
                  </ElButton>
                  <ElButton
                    type="danger"
                    link
                    @click="deletePlatform('viu', row)"
                  >
                    删除
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
          </section>
        </ElTabPane>

        <ElTabPane label="CDC 平台配置" name="cdc">
          <section class="config-card">
            <header class="card-header">
              <div>
                <h3 class="card-title">CDC 平台配置</h3>
                <p class="card-desc">
                  维护座舱场景可选的 CDC 平台，供项目阶段典配配置选择。
                </p>
              </div>
            </header>
            <div class="card-action">
              <ElButton type="primary" @click="openConfigCreate('cdc')">
                新增 CDC 平台
              </ElButton>
            </div>
            <ElTable :data="cdcPlatforms" border class="config-table">
              <ElTableColumn prop="name" label="CDC 平台" min-width="220" />
              <ElTableColumn prop="remark" label="备注" min-width="220" />
              <ElTableColumn label="操作" width="180">
                <template #default="{ row }">
                  <ElButton
                    type="primary"
                    link
                    @click="openConfigEdit('cdc', row)"
                  >
                    编辑
                  </ElButton>
                  <ElButton
                    type="danger"
                    link
                    @click="deletePlatform('cdc', row)"
                  >
                    删除
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
          </section>
        </ElTabPane>

        <ElTabPane label="智慧屏版本配置" name="smart">
          <section class="config-card">
            <header class="card-header">
              <div>
                <h3 class="card-title">智慧屏版本配置</h3>
                <p class="card-desc">
                  维护座舱项目可选的智慧屏版本，与 CDC 平台共同组成典配信息。
                </p>
              </div>
            </header>
            <div class="card-action">
              <ElButton type="primary" @click="openConfigCreate('smart')">
                新增智慧屏版本
              </ElButton>
            </div>
            <ElTable :data="smartScreenVersions" border class="config-table">
              <ElTableColumn prop="name" label="智慧屏版本" min-width="220" />
              <ElTableColumn prop="remark" label="备注" min-width="220" />
              <ElTableColumn label="操作" width="180">
                <template #default="{ row }">
                  <ElButton
                    type="primary"
                    link
                    @click="openConfigEdit('smart', row)"
                  >
                    编辑
                  </ElButton>
                  <ElButton
                    type="danger"
                    link
                    @click="deletePlatform('smart', row)"
                  >
                    删除
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
          </section>
        </ElTabPane>
      </ElTabs>
    </section>

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
.hardware-config-page {
  min-height: calc(100vh - 160px);
}

.tabs-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
  background: var(--el-bg-color-overlay);
  padding: 12px;
  box-shadow: 0 10px 24px rgb(15 23 42 / 4%);
}

.hardware-tabs {
  width: 100%;
}

.hardware-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 4px 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.hardware-tabs :deep(.el-tabs__content) {
  padding-top: 12px;
}

.hardware-tabs :deep(.el-tab-pane) {
  width: 100%;
}

.config-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background: linear-gradient(
    180deg,
    var(--el-bg-color-overlay) 0%,
    var(--el-fill-color-extra-light) 100%
  );
  padding: 16px;
  box-shadow: 0 8px 20px rgb(15 23 42 / 4%);
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.card-title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 600;
  line-height: 24px;
}

.card-desc {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.card-action {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-end;
}

.points-pane {
  width: 100%;
  min-height: 0;
  height: clamp(460px, calc(100vh - 340px), 780px);
  overflow: hidden;
}

.config-table {
  width: 100%;
}

.config-table :deep(.el-table) {
  width: 100%;
  border-radius: 10px;
  overflow: hidden;
}

.points-pane :deep(.points-grid) {
  height: 100%;
  width: 100%;
  display: block;
}

.points-pane :deep(.points-grid > .vxe-grid) {
  height: 100% !important;
  width: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.points-pane :deep(.points-grid .vxe-grid--toolbar-wrapper),
.points-pane :deep(.points-grid .vxe-grid--form-wrapper) {
  width: 100%;
}

.points-pane :deep(.points-grid .vxe-grid--layout-wrapper),
.points-pane :deep(.points-grid .vxe-grid--layout-body-wrapper),
.points-pane :deep(.points-grid .vxe-grid--layout-body-content-wrapper) {
  width: 100%;
  min-height: 0;
}

.points-pane :deep(.points-grid .vxe-grid--layout-wrapper) {
  flex: 1;
}

.points-pane :deep(.points-grid .vxe-table),
.points-pane :deep(.points-grid .vxe-table--main-wrapper),
.points-pane :deep(.points-grid .vxe-table--render-default),
.points-pane :deep(.points-grid .vxe-table--body-wrapper) {
  width: 100% !important;
  min-height: 0;
}

@media (max-width: 768px) {
  .tabs-card {
    padding: 8px;
  }

  .config-card {
    padding: 12px;
  }

  .card-action {
    justify-content: flex-start;
  }

  .points-pane {
    height: clamp(340px, calc(100vh - 280px), 600px);
  }
}
</style>
