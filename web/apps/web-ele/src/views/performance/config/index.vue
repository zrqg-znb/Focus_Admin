<script lang="ts" setup>
import type { OnActionClickParams, VxeTableGridOptions } from '#/adapter/vxe-table';
import type {
  PerformanceChipType,
  PerformanceIndicator,
  PerformanceTreeNode,
} from '#/api/core/performance';

import { computed, onMounted, ref, watch } from 'vue';
import { Page, useVbenDrawer } from '@vben/common-ui';
import {
  ElButton,
  ElDialog,
  ElInput,
  ElLink,
  ElOption,
  ElProgress,
  ElSelect,
  ElSkeleton,
  ElSkeletonItem,
  ElTree,
  ElUpload,
  ElForm,
  ElFormItem,
} from 'element-plus';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Upload, Edit, Trash2 } from '@vben/icons';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteIndicatorApi,
  getChipTypesApi,
  getIndicatorListApi,
  getIndicatorTreeApi,
  getIndicatorImportTaskApi,
  startIndicatorImportTaskApi,
  batchDeleteIndicatorsApi,
  batchUpdateIndicatorsApi,
} from '#/api/core/performance';

import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';
import { useColumns } from './data';
import Form from './modules/form.vue';

defineOptions({ name: 'PerformanceConfig' });

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const importDialogVisible = ref(false);
const importing = ref(false);
const importPercent = ref(0);
const importStage = ref<'uploading' | 'processing'>('uploading');
const importTaskId = ref('');
const importMessage = ref('');
let importTimer: any = null;

const treeLoading = ref(false);
const treeData = ref<PerformanceTreeNode[]>([]);

const selectedCategory = ref<'vehicle' | 'cockpit'>('vehicle');
const selectedProject = ref<string>('');
const selectedModule = ref<string>('');

const chipTypeOptions = ref<PerformanceChipType[]>([]);
const selectedChipType = ref<string>('');
const keyword = ref('');

const initialized = ref(false);
const chipTypeUpdating = ref(false);
const pageInitializing = ref(true);
const gridLoading = ref(false);

const selectedRows = ref<PerformanceIndicator[]>([]);
const batchEditVisible = ref(false);
const batchEditField = ref('');
const batchEditValue = ref('');
const batchEditLoading = ref(false);

const batchEditFieldOptions = [
  { label: '模块', value: 'module' },
  { label: '项目', value: 'project' },
  { label: '芯片类型', value: 'chip_type' },
  { label: '基线值', value: 'baseline_value' },
  { label: '基线单位', value: 'baseline_unit' },
  { label: '浮动范围', value: 'fluctuation_range' },
  { label: '浮动方向', value: 'fluctuation_direction' },
  { label: '责任人', value: 'owner_id' },
];

const currentFilters = computed(() => ({
  category: selectedCategory.value,
  project: selectedProject.value,
  module: selectedModule.value,
  chip_type: selectedChipType.value,
  search: keyword.value,
}));

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: true,
    },
    checkboxConfig: {
      reserve: true,
      highlight: true,
      range: true,
    },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          gridLoading.value = true;
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            ...currentFilters.value,
          };
          try {
            return await getIndicatorListApi(params);
          } finally {
            gridLoading.value = false;
          }
        },
      },
    },
    toolbarConfig: {
      custom: true,
      export: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<PerformanceIndicator>,
  gridEvents: {
    checkboxChange: handleSelectionChange,
    checkboxAll: handleSelectionChange,
  },
});

function handleSelectionChange(params: any) {
  // Try to get from event params
  if (params && (params.records || params.reserves)) {
    const records = params.records || [];
    const reserves = params.reserves || [];
    selectedRows.value = [...records, ...reserves];
    return;
  }
  // Fallback to API
  const grid = gridApi.grid;
  if (grid) {
    selectedRows.value = [
      ...grid.getCheckboxRecords(),
      ...grid.getCheckboxReserveRecords(),
    ];
  } else {
    selectedRows.value = [];
  }
}

function clearSelection() {
  selectedRows.value = [];
  const grid = gridApi.grid;
  grid?.clearCheckboxRow?.();
  grid?.clearCheckboxReserve?.();
}

function handleBatchDelete() {
  if (selectedRows.value.length === 0) return;
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 个指标吗？`,
    '批量删除',
    {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    },
  ).then(async () => {
    try {
      const ids = selectedRows.value.map((r) => r.id);
      const count = await batchDeleteIndicatorsApi(ids);
      ElMessage.success(`成功删除 ${count} 个指标`);
      clearSelection();
      gridApi.query();
    } catch (error) {
      // handled
    }
  });
}

function handleBatchEdit() {
  if (selectedRows.value.length === 0) return;
  batchEditField.value = '';
  batchEditValue.value = '';
  batchEditVisible.value = true;
}

async function confirmBatchEdit() {
  if (!batchEditField.value) {
    ElMessage.warning('请选择要修改的字段');
    return;
  }

  batchEditLoading.value = true;
  try {
    const ids = selectedRows.value.map((r) => r.id);
    const count = await batchUpdateIndicatorsApi(ids, batchEditField.value, batchEditValue.value);
    ElMessage.success(`成功更新 ${count} 个指标`);
    batchEditVisible.value = false;
    clearSelection();
    gridApi.query();
  } catch (error) {
    // handled
  } finally {
    batchEditLoading.value = false;
  }
}

function onActionClick({ code, row }: OnActionClickParams<PerformanceIndicator>) {
  if (code === 'edit') {
    openEdit(row);
  } else if (code === 'delete') {
    handleDelete(row);
  }
}

function openCreate() {
  formDrawerApi
    .setData({
      category: selectedCategory.value,
      project: selectedProject.value,
      module: selectedModule.value,
      chip_type: selectedChipType.value,
      value_type: 'avg',
      baseline_value: 0,
      baseline_unit: '',
      fluctuation_range: 0,
      fluctuation_direction: 'none',
    } as any)
    .open();
}

function openEdit(row: PerformanceIndicator) {
  formDrawerApi.setData(row).open();
}

async function handleDelete(row: PerformanceIndicator) {
  try {
    await deleteIndicatorApi(row.id);
    ElMessage.success('删除成功');
    gridApi.query();
  } catch (error) {
    // Error handled by global interceptor usually
  }
}

function parseNodeKey(key: string) {
  const parts = key.split(':');
  if (parts.length === 1) {
    return { category: parts[0] as 'vehicle' | 'cockpit' };
  }
  if (parts.length === 2) {
    return { category: parts[0] as 'vehicle' | 'cockpit', project: parts[1] };
  }
  return {
    category: parts[0] as 'vehicle' | 'cockpit',
    project: parts[1],
    module: parts.slice(2).join(':'),
  };
}

async function loadTree() {
  treeLoading.value = true;
  try {
    treeData.value = await getIndicatorTreeApi();
    if (!selectedProject.value) {
      const firstCategory = treeData.value[0];
      const firstProject = firstCategory?.children?.[0];
      const firstModule = firstProject?.children?.[0];
      if (firstCategory?.key) selectedCategory.value = firstCategory.key as any;
      if (firstProject?.label) selectedProject.value = firstProject.label;
      if (firstModule?.label) selectedModule.value = firstModule.label;
    }
  } finally {
    treeLoading.value = false;
  }
}

async function loadChipTypes() {
  chipTypeOptions.value = await getChipTypesApi({
    category: selectedCategory.value,
    project: selectedProject.value,
    module: selectedModule.value,
  });
  const nextVal = chipTypeOptions.value[0]?.chip_type || '';
  if (!chipTypeOptions.value.some((i) => i.chip_type === selectedChipType.value)) {
    chipTypeUpdating.value = true;
    selectedChipType.value = nextVal;
    chipTypeUpdating.value = false;
  }
}

function handleNodeClick(node: any) {
  const parsed = parseNodeKey(node.key);
  selectedCategory.value = parsed.category || selectedCategory.value;
  selectedProject.value = parsed.project || selectedProject.value;
  selectedModule.value = parsed.module || selectedModule.value;
}

async function handleImportRequest(options: any) {
  if (importing.value) return;
  try {
    importing.value = true;
    importPercent.value = 0;
    importStage.value = 'uploading';
    importMessage.value = '正在上传文件';
    const startResp = await startIndicatorImportTaskApi(options.file, {
      timeout: 15 * 60 * 1000,
      onUploadProgress: (evt: any) => {
        const total = evt?.total || 0;
        const loaded = evt?.loaded || 0;
        if (!total) return;
        importPercent.value = Math.min(90, Math.floor((loaded / total) * 90));
      },
    });
    importTaskId.value = startResp.task_id;
    importStage.value = 'processing';
    importMessage.value = '上传完成，等待解析';

    if (importTimer) clearInterval(importTimer);
    importTimer = setInterval(async () => {
      if (!importTaskId.value) return;
      try {
        const task = await getIndicatorImportTaskApi(importTaskId.value);
        importMessage.value = task.message || importMessage.value;
        const p = Number(task.progress ?? 0);
        importPercent.value = Math.max(importPercent.value, Math.min(100, p));
        if (task.status === 'success') {
          clearInterval(importTimer);
          importTimer = null;
          importing.value = false;
          importPercent.value = 100;
          ElMessage.success(`导入成功：${task.success_count}条，失败${task.error_count}条`);
          importDialogVisible.value = false;
          await loadTree();
          gridApi.query();
        }
        if (task.status === 'failed') {
          clearInterval(importTimer);
          importTimer = null;
          importing.value = false;
          importPercent.value = 100;
          ElMessage.error(task.message || '导入失败');
        }
      } catch (e) {
      }
    }, 800);
  } catch (error) {
    // 错误提示由全局拦截器统一处理
  } finally {
    if (!importTaskId.value) importing.value = false;
  }
}

function downloadTemplate() {
    const csvContent = "Code,Category,Name,Module,Project,Chip Type,Value Type,Baseline Value,Baseline Unit,Fluctuation Range,Fluctuation Direction,Owner\nTEST_001,vehicle,示例指标1,load,ProjA,ChipA,avg,100,ms,10,down,UserA";
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", "performance_indicator_template.csv");
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

watch(
  () => [selectedCategory.value, selectedProject.value, selectedModule.value] as const,
  async () => {
    if (!initialized.value) return;
    clearSelection();
    await loadChipTypes();
    gridApi.query();
  },
);

watch(
  () => selectedChipType.value,
  () => {
    if (!initialized.value) return;
    if (chipTypeUpdating.value) return;
    clearSelection();
    gridApi.query();
  },
);

watch(
  () => importDialogVisible.value,
  (open) => {
    if (open) {
      importPercent.value = 0;
      importing.value = false;
      importTaskId.value = '';
      importStage.value = 'uploading';
      importMessage.value = '';
      if (importTimer) {
        clearInterval(importTimer);
        importTimer = null;
      }
    } else {
      if (importTimer) {
        clearInterval(importTimer);
        importTimer = null;
      }
    }
  },
);

onMounted(async () => {
  await loadTree();
  await loadChipTypes();
  initialized.value = true;
  await gridApi.query();
  pageInitializing.value = false;
});
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="gridApi.query()" />

    <ElSkeleton :loading="pageInitializing" animated>
      <template #template>
        <div class="flex h-full gap-4">
          <div class="w-[280px] shrink-0 overflow-hidden rounded bg-[var(--el-bg-color)] p-3">
            <ElSkeletonItem variant="text" class="mb-3 w-24" />
            <div class="space-y-2">
              <ElSkeletonItem v-for="i in 8" :key="i" variant="text" class="w-full" />
            </div>
          </div>
          <div class="min-w-0 flex-1 rounded bg-[var(--el-bg-color)] p-3">
            <div class="mb-3 flex items-center gap-2">
              <ElSkeletonItem variant="rect" class="h-8 w-[240px]" />
              <ElSkeletonItem variant="rect" class="h-8 w-[200px]" />
              <div class="flex-1" />
              <ElSkeletonItem variant="rect" class="h-8 w-24" />
              <ElSkeletonItem variant="rect" class="h-8 w-20" />
            </div>
            <div class="space-y-2">
              <ElSkeletonItem v-for="i in 10" :key="i" variant="rect" class="h-9 w-full" />
            </div>
          </div>
        </div>
      </template>

      <template #default>
        <div class="flex h-full gap-4">
          <div class="w-[280px] shrink-0 overflow-hidden rounded bg-[var(--el-bg-color)] p-3">
            <div class="mb-2 text-sm font-medium">指标项目分类</div>
            <div class="h-[calc(100%-28px)] overflow-auto">
              <ElTree
                :data="treeData"
                :props="{ children: 'children', label: 'label' }"
                node-key="key"
                highlight-current
                @node-click="handleNodeClick"
              />
            </div>
          </div>

          <div class="min-w-0 flex-1" v-loading="gridLoading">
            <Grid>
              <template #toolbar-actions>
                <div class="flex flex-1 items-center gap-2">
                  <ElInput
                    v-model="keyword"
                    class="w-[240px]"
                    clearable
                    placeholder="搜索指标名称"
                    @keyup.enter="gridApi.query()"
                  />
                  <ElSelect
                    v-model="selectedChipType"
                    class="w-[200px]"
                    clearable
                    placeholder="芯片类型"
                  >
                    <ElOption
                      v-for="item in chipTypeOptions"
                      :key="item.chip_type"
                      :label="item.chip_type"
                      :value="item.chip_type"
                    />
                  </ElSelect>

                  <div class="flex-1" />

                  <ElButton
                    type="danger"
                    plain
                    :disabled="selectedRows.length === 0"
                    @click="handleBatchDelete"
                  >
                    <Trash2 class="mr-1 size-4" /> 批量删除
                  </ElButton>
                  <ElButton
                    type="primary"
                    plain
                    :disabled="selectedRows.length === 0"
                    @click="handleBatchEdit"
                  >
                    <Edit class="mr-1 size-4" /> 批量编辑
                  </ElButton>

                  <ElButton type="primary" @click="openCreate">
                    <Plus class="mr-1 size-4" /> 新增指标
                  </ElButton>
                  <ElButton type="success" @click="importDialogVisible = true">
                    <Upload class="mr-1 size-4" /> 导入
                  </ElButton>
                </div>
              </template>
            </Grid>
          </div>
        </div>
      </template>
    </ElSkeleton>

    <!-- Import Dialog -->
    <ElDialog
      v-model="batchEditVisible"
      title="批量编辑"
      width="400px"
      destroy-on-close
    >
      <ElForm label-position="top">
        <ElFormItem label="选择字段">
          <ElSelect v-model="batchEditField" placeholder="请选择要修改的字段" class="w-full">
            <ElOption
              v-for="opt in batchEditFieldOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="新值">
           <ElSelect v-if="batchEditField === 'fluctuation_direction'" v-model="batchEditValue" class="w-full">
             <ElOption label="向上" value="up" />
             <ElOption label="向下" value="down" />
             <ElOption label="无" value="none" />
           </ElSelect>
           <UserSelector
             v-else-if="batchEditField === 'owner_id'"
             v-model="batchEditValue"
             placeholder="请选择责任人"
             :multiple="false"
             class="w-full"
           />
           <ElInput v-else v-model="batchEditValue" placeholder="请输入新值" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="batchEditVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="batchEditLoading" @click="confirmBatchEdit">
          确定更新
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="importDialogVisible"
      title="导入指标"
      width="420px"
      :close-on-click-modal="!importing"
      :close-on-press-escape="!importing"
      :show-close="!importing"
    >
        <div class="mb-4 text-right">
            <ElLink type="primary" :underline="false" @click="downloadTemplate">下载模板 CSV</ElLink>
        </div>
        <div v-if="importing" class="mb-3">
          <div class="mb-2 text-sm text-[var(--el-text-color-secondary)]">
            {{ importStage === 'uploading' ? '正在上传文件，请勿关闭弹窗' : '正在解析并导入，请勿关闭弹窗' }}
          </div>
          <div v-if="importMessage" class="mb-2 text-xs text-[var(--el-text-color-secondary)]">
            {{ importMessage }}
          </div>
          <ElProgress :percentage="importPercent" :stroke-width="10" />
        </div>
        <ElUpload
          class="upload-demo"
          drag
          action="#"
          :http-request="handleImportRequest"
          :show-file-list="false"
          accept=".xlsx,.csv"
          :disabled="importing"
        >
          <div class="el-upload__text">
            将文件拖到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
             <div class="el-upload__tip">
                支持 .xlsx 或 .csv 文件
             </div>
          </template>
        </ElUpload>
    </ElDialog>
  </Page>
</template>
