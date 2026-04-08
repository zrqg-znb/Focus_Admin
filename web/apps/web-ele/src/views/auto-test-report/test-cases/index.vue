<script lang="ts" setup>
import type { FormInstance } from 'element-plus';

import type {
  TestCaseItem,
  TestCasePayload,
  VehicleOption,
} from '#/api/auto-test-report';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElCascader,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElSwitch,
  ElTooltip,
} from 'element-plus';

import {
  batchDeleteTestCasesApi,
  createTestCaseApi,
  deleteTestCaseApi,
  downloadTestCaseExportUrl,
  downloadTestCaseTemplateUrl,
  importTestCasesExcelApi,
  listTestCasesApi,
  listVehicleOptionsApi,
  updateTestCaseApi,
} from '#/api/auto-test-report';
import { useZqTable } from '#/components/zq-table';

import TestCaseHistoryDrawer from '../components/test-case-history-drawer.vue';
import { useCaseColumns } from './data';

defineOptions({ name: 'AutoTestCaseList' });

const vehicleOptions = ref<VehicleOption[]>([]);
const cascaderOptions = ref<any[]>([]);
const selectedVehiclePaths = ref<string[][]>([]);
const vehicleKeyword = ref('');
const keyword = ref('');
const selectedIds = ref<string[]>([]);

const caseDialogVisible = ref(false);
const caseDialogMode = ref<'create' | 'edit'>('create');
const caseDialogSaving = ref(false);
const caseFormRef = ref<FormInstance>();
const caseForm = ref<TestCasePayload & { id?: string }>({
  vehicle_id: '',
  case_no: '',
  case_name: '',
  sort: 0,
  is_active: true,
});

const importLoading = ref(false);
const historyVisible = ref(false);
const historyTitle = ref('');
const currentCaseId = ref('');

const selectedVehicleIds = computed(() =>
  selectedVehiclePaths.value
    .map((item) => item[item.length - 1])
    .filter(Boolean),
);

const currentVehicleId = computed(
  () => selectedVehicleIds.value[0] || vehicleOptions.value[0]?.id || '',
);

const [Grid, gridApi] = useZqTable({
  tableTitle: '测试用例列表',
  gridOptions: {
    columns: useCaseColumns(),
    border: true,
    stripe: true,
    rowKey: 'id',
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          const items =
            (await listTestCasesApi({ keyword: keyword.value || undefined })) ||
            [];
          const filtered = items.filter((item) => {
            if (
              selectedVehicleIds.value.length > 0 &&
              !selectedVehicleIds.value.includes(item.vehicle_id)
            ) {
              return false;
            }
            if (vehicleKeyword.value.trim()) {
              const matcher = vehicleKeyword.value.trim().toLowerCase();
              const text =
                `${item.platform_name} ${item.vehicle_name} ${item.vehicle_code}`.toLowerCase();
              if (!text.includes(matcher)) {
                return false;
              }
            }
            return true;
          });
          const currentPage = Math.max(Number(page?.currentPage || 1), 1);
          const pageSize = Math.max(Number(page?.pageSize || 20), 1);
          const start = (currentPage - 1) * pageSize;
          const end = start + pageSize;
          return {
            items: filtered.slice(start, end),
            total: filtered.length,
          };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: { custom: true, refresh: true, search: false, zoom: true },
  },
  showSearchForm: false,
});

function rebuildCascaderOptions() {
  const platformMap = new Map<string, any>();
  for (const item of vehicleOptions.value) {
    if (!platformMap.has(item.platform_id)) {
      platformMap.set(item.platform_id, {
        value: item.platform_id,
        label: item.platform_name,
        children: [],
      });
    }
    platformMap.get(item.platform_id).children.push({
      value: item.id,
      label: `${item.name} (${item.vehicle_code})`,
    });
  }
  cascaderOptions.value = [...platformMap.values()];
}

async function reloadVehicleOptions() {
  vehicleOptions.value = (await listVehicleOptionsApi()) || [];
  rebuildCascaderOptions();
}

async function refreshGrid() {
  await gridApi.reload();
}

function openCreate() {
  caseDialogMode.value = 'create';
  caseForm.value = {
    vehicle_id: currentVehicleId.value,
    case_no: '',
    case_name: '',
    sort: 0,
    is_active: true,
  };
  caseDialogVisible.value = true;
}

function openEdit(row: TestCaseItem) {
  caseDialogMode.value = 'edit';
  caseForm.value = {
    id: row.id,
    vehicle_id: row.vehicle_id,
    case_no: row.case_no,
    case_name: row.case_name,
    sort: row.sort,
    is_active: row.is_active,
  };
  caseDialogVisible.value = true;
}

async function submitCase() {
  await caseFormRef.value?.validate();
  caseDialogSaving.value = true;
  try {
    if (caseDialogMode.value === 'create') {
      await createTestCaseApi(caseForm.value);
      ElMessage.success('用例创建成功');
    } else {
      await updateTestCaseApi(caseForm.value.id!, caseForm.value);
      ElMessage.success('用例更新成功');
    }
    caseDialogVisible.value = false;
    await refreshGrid();
  } finally {
    caseDialogSaving.value = false;
  }
}

async function removeCase(row: TestCaseItem) {
  await ElMessageBox.confirm(`确定删除用例 ${row.case_no} 吗？`, '提示', {
    type: 'warning',
  });
  await deleteTestCaseApi(row.id);
  ElMessage.success('删除成功');
  await refreshGrid();
}

async function removeSelected() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择用例');
    return;
  }
  await ElMessageBox.confirm(
    `确定批量删除 ${selectedIds.value.length} 条用例吗？`,
    '提示',
    { type: 'warning' },
  );
  await batchDeleteTestCasesApi(selectedIds.value);
  ElMessage.success('批量删除成功');
  selectedIds.value = [];
  await refreshGrid();
}

async function onImportFile(file?: File | null) {
  if (!currentVehicleId.value) {
    ElMessage.warning('请先通过级联选择一个车型');
    return false;
  }
  if (!file) {
    ElMessage.warning('请选择 Excel 文件');
    return false;
  }
  importLoading.value = true;
  try {
    const result = await importTestCasesExcelApi(currentVehicleId.value, file);
    ElMessage.success(
      `导入完成：新增 ${result.created_count}，更新 ${result.updated_count}，忽略 ${result.ignored_count}`,
    );
    if ((result.errors || []).length > 0) {
      await ElMessageBox.alert(
        result.errors
          .map((item) => `第 ${item.row_no} 行：${item.message}`)
          .join('<br/>'),
        '导入异常',
        {
          dangerouslyUseHTMLString: true,
        },
      );
    }
    await refreshGrid();
  } finally {
    importLoading.value = false;
  }
  return false;
}

function handleSelectionChange(rows: TestCaseItem[]) {
  selectedIds.value = rows.map((item) => item.id);
}

function openHistory(row: TestCaseItem) {
  currentCaseId.value = row.id;
  historyTitle.value = `${row.case_no} / ${row.case_name}`;
  historyVisible.value = true;
}

function downloadTemplate() {
  window.open(downloadTestCaseTemplateUrl(), '_blank');
}

function exportCases() {
  window.open(
    downloadTestCaseExportUrl({
      keyword: keyword.value || undefined,
      vehicle_id:
        selectedVehicleIds.value.length === 1
          ? selectedVehicleIds.value[0]
          : undefined,
    }),
    '_blank',
  );
}

onMounted(async () => {
  gridApi.setLoading(true);
  try {
    await reloadVehicleOptions();
    await refreshGrid();
  } finally {
    gridApi.setLoading(false);
  }
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col">
      <div
        class="mb-4 shrink-0 rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm"
      >
        <ElForm
          :inline="true"
          class="flex flex-wrap items-center gap-4"
          @submit.prevent
        >
          <ElFormItem label="MCU 平台 / 车型" class="!mb-0">
            <ElCascader
              v-model="selectedVehiclePaths"
              class="w-[320px]"
              clearable
              collapse-tags
              collapse-tags-tooltip
              filterable
              multiple
              placeholder="选择 MCU 平台 / 车型（支持多选）"
              :max-collapse-tags="1"
              :options="cascaderOptions"
              :props="{ multiple: true, emitPath: true, checkStrictly: false }"
              @change="refreshGrid"
            />
          </ElFormItem>
          <ElFormItem label="车型关键词" class="!mb-0">
            <ElInput
              v-model="vehicleKeyword"
              class="w-[200px]"
              clearable
              placeholder="按车型关键词筛选"
              @change="refreshGrid"
            />
          </ElFormItem>
          <ElFormItem label="用例搜索" class="!mb-0">
            <ElInput
              v-model="keyword"
              class="w-[200px]"
              clearable
              placeholder="按用例编号/名称筛选"
              @change="refreshGrid"
            />
          </ElFormItem>
        </ElForm>
      </div>

      <div class="min-h-0 flex-1">
        <Grid class="h-full" @selection-change="handleSelectionChange">
          <template #toolbar-actions>
            <div class="flex items-center gap-2">
              <ElButton type="primary" @click="openCreate">新增用例</ElButton>
              <ElButton type="danger" @click="removeSelected">
                批量删除
              </ElButton>
              <ElButton @click="downloadTemplate">导出模板</ElButton>
              <ElButton @click="exportCases">导出用例</ElButton>
              <ElButton
                :loading="importLoading"
                @click="$refs.excelInput?.click()"
              >
                导入Excel
              </ElButton>
              <input
                ref="excelInput"
                class="hidden"
                type="file"
                accept=".xlsx,.xls"
                @change="
                  (event) => onImportFile(event.target.files?.[0] || null)
                "
              />
            </div>
          </template>

          <template #cell-latest_execute_time="{ row }">
            {{ row.latest_execute_time || '-' }}
          </template>

          <template #cell-actions="{ row }">
            <div class="flex items-center justify-center gap-1">
              <ElTooltip content="历史执行记录">
                <ElButton link type="success" @click="openHistory(row)">
                  历史
                </ElButton>
              </ElTooltip>
              <ElTooltip content="编辑">
                <ElButton link type="primary" @click="openEdit(row)">
                  编辑
                </ElButton>
              </ElTooltip>
              <ElTooltip content="删除">
                <ElButton link type="danger" @click="removeCase(row)">
                  删除
                </ElButton>
              </ElTooltip>
            </div>
          </template>
        </Grid>
      </div>
    </div>

    <ElDialog
      v-model="caseDialogVisible"
      :title="caseDialogMode === 'create' ? '新增用例' : '编辑用例'"
      width="560px"
    >
      <ElForm ref="caseFormRef" :model="caseForm" label-width="110px">
        <ElFormItem label="归属车型" prop="vehicle_id" required>
          <el-select v-model="caseForm.vehicle_id" class="w-full" filterable>
            <el-option
              v-for="item in vehicleOptions"
              :key="item.id"
              :label="`${item.platform_name} / ${item.name}`"
              :value="item.id"
            />
          </el-select>
        </ElFormItem>
        <ElFormItem label="用例编号" prop="case_no" required>
          <ElInput v-model="caseForm.case_no" />
        </ElFormItem>
        <ElFormItem label="用例名称" prop="case_name" required>
          <ElInput v-model="caseForm.case_name" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="caseForm.sort" class="w-full" />
        </ElFormItem>
        <ElFormItem label="是否启用">
          <ElSwitch v-model="caseForm.is_active" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="caseDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="caseDialogSaving"
          @click="submitCase"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>

    <TestCaseHistoryDrawer
      v-model:visible="historyVisible"
      :case-id="currentCaseId"
      :title="historyTitle"
    />
  </Page>
</template>
