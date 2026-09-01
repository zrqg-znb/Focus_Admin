<script lang="ts" setup>
import type { FormInstance } from 'element-plus';

import type {
  TestCaseItem,
  TestCasePayload,
  VehicleOption,
} from '#/api/auto-test-report';

import { computed, onMounted, ref, watch } from 'vue';

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
  ElOption,
  ElSelect,
  ElSwitch,
  ElTooltip,
} from 'element-plus';

import {
  batchDeleteTestCasesApi,
  createTestCaseApi,
  deleteTestCaseApi,
  downloadTestCaseExportApi,
  downloadTestCaseTemplateApi,
  importFullTestCasesExcelApi,
  listTestCasesApi,
  listVehicleOptionsApi,
  updateTestCaseApi,
} from '#/api/auto-test-report';
import { useZqTable } from '#/components/zq-table';

import DomainSwitcher from '../components/domain-switcher.vue';
import TestCaseHistoryDrawer from '../components/test-case-history-drawer.vue';
import {
  AUTO_TEST_REPORT_VIU_CODES,
  isVehicleControlDomain,
  useAutoTestReportDomain,
} from '../shared/domain';
import TestCaseHeaderKeywordFilter from './components/TestCaseHeaderKeywordFilter.vue';
import { useCaseColumns } from './data';

defineOptions({ name: 'AutoTestCaseList' });

type TestCaseFormState = Omit<TestCasePayload, 'vehicle_id'> & {
  id?: string;
  vehicle_path: string[];
};

const { domain, domainMeta } = useAutoTestReportDomain();
const vehicleOptions = ref<VehicleOption[]>([]);
const cascaderOptions = ref<any[]>([]);
const selectedVehiclePaths = ref<string[][]>([]);
const selectedViuCode = ref('');
const vehicleKeyword = ref('');
const caseNoKeyword = ref('');
const caseNameKeyword = ref('');
const selectedIds = ref<string[]>([]);
const excelInputRef = ref<HTMLInputElement | null>(null);

const caseDialogVisible = ref(false);
const caseDialogMode = ref<'create' | 'edit'>('create');
const caseDialogSaving = ref(false);
const caseFormRef = ref<FormInstance>();
const caseForm = ref<TestCaseFormState>({
  case_no: '',
  case_name: '',
  viu_code: '',
  module: '',
  remark: '',
  sort: 0,
  is_active: true,
  vehicle_path: [],
});

const importLoading = ref(false);
const exportLoading = ref(false);
const templateLoading = ref(false);
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

const currentVehicle = computed(
  () =>
    vehicleOptions.value.find((item) => item.id === currentVehicleId.value) ||
    null,
);

const vehicleViuOptions = computed(() =>
  [...AUTO_TEST_REPORT_VIU_CODES].map((code) => ({
    label: code,
    value: code,
  })),
);

const currentVehicleViuCodes = computed(() => {
  if (domain.value !== 'vehicle') {
    return [];
  }
  return currentVehicle.value?.viu_codes?.length
    ? [...currentVehicle.value.viu_codes]
    : [];
});

const selectedVehicleViuOptions = computed(() =>
  currentVehicleViuCodes.value.map((code) => ({
    label: code,
    value: code,
  })),
);

const [Grid, gridApi] = useZqTable({
  tableTitle: '测试用例列表',
  gridOptions: {
    columns: useCaseColumns(domain.value),
    border: true,
    stripe: true,
    rowKey: 'id',
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
          const items =
            (await listTestCasesApi({
              domain: domain.value,
              case_no_keyword: caseNoKeyword.value || undefined,
              case_name_keyword: caseNameKeyword.value || undefined,
              viu_code:
                isVehicleControlDomain(domain.value)
                  ? selectedViuCode.value || undefined
                  : undefined,
            })) || [];
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
          const total = filtered.length;
          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          const pagedItems = filtered.slice(start, end);
          return { items: pagedItems, total };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: { custom: true, refresh: true, search: false, zoom: true },
  },
  showSearchForm: false,
});

function getVehiclePath(vehicleId: string) {
  const matchedVehicle = vehicleOptions.value.find((v) => v.id === vehicleId);
  return matchedVehicle ? [matchedVehicle.platform_id, matchedVehicle.id] : [];
}

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
  vehicleOptions.value = (await listVehicleOptionsApi(domain.value)) || [];
  rebuildCascaderOptions();

  const validVehicleIds = new Set(vehicleOptions.value.map((item) => item.id));
  selectedVehiclePaths.value = selectedVehiclePaths.value.filter((path) =>
    validVehicleIds.has(path[path.length - 1] || ''),
  );

  if (
    isVehicleControlDomain(domain.value) &&
    selectedViuCode.value &&
    !vehicleViuOptions.value.some(
      (item) => item.value === selectedViuCode.value,
    )
  ) {
    selectedViuCode.value = '';
  }
}

async function refreshGrid() {
  await gridApi.reload();
}

async function applyCaseHeaderFilter() {
  gridApi.pagination.currentPage = 1;
  await refreshGrid();
}

function openCreate() {
  caseDialogMode.value = 'create';

  const initialPath = getVehiclePath(currentVehicleId.value);
  if (
    isVehicleControlDomain(domain.value) &&
    selectedVehicleViuOptions.value.length === 0
  ) {
    ElMessage.warning('当前车型未配置可用 VIU 编号，请先维护车型配置');
    return;
  }

  caseForm.value = {
    vehicle_path: initialPath,
    case_no: '',
    case_name: '',
    module: '',
    viu_code:
      isVehicleControlDomain(domain.value)
        ? selectedVehicleViuOptions.value[0]?.value || ''
        : '',
    remark: '',
    sort: 0,
    is_active: true,
    id: undefined,
  };
  caseDialogVisible.value = true;
}

function openEdit(row: TestCaseItem) {
  caseDialogMode.value = 'edit';

  caseForm.value = {
    id: row.id,
    vehicle_path: getVehiclePath(row.vehicle_id),
    case_no: row.case_no,
    case_name: row.case_name,
    module: row.module || '',
    viu_code: row.viu_code || '',
    remark: row.remark || '',
    sort: row.sort,
    is_active: row.is_active,
  };
  caseDialogVisible.value = true;
}

async function submitCase() {
  await caseFormRef.value?.validate();
  caseDialogSaving.value = true;
  try {
    const cascaderValue = caseForm.value.vehicle_path || [];
    const actualVehicleId = cascaderValue[cascaderValue.length - 1] || '';

    if (!actualVehicleId) {
      ElMessage.warning(`请选择${domainMeta.value.selectorLabel}`);
      return;
    }
    if (isVehicleControlDomain(domain.value) && !caseForm.value.viu_code) {
      ElMessage.warning('请先选择 VIU 编号');
      return;
    }
    if (domain.value === 'cockpit_soc' && !caseForm.value.module.trim()) {
      ElMessage.warning('请先填写模块');
      return;
    }

    const payload: TestCasePayload = {
      vehicle_id: actualVehicleId,
      viu_code: isVehicleControlDomain(domain.value)
        ? caseForm.value.viu_code
        : '',
      module: domain.value === 'cockpit_soc' ? caseForm.value.module : '',
      case_no: caseForm.value.case_no,
      case_name: caseForm.value.case_name,
      remark: caseForm.value.remark,
      sort: caseForm.value.sort,
      is_active: caseForm.value.is_active,
    };

    if (caseDialogMode.value === 'create') {
      await createTestCaseApi(payload);
      ElMessage.success('用例创建成功');
    } else {
      await updateTestCaseApi(caseForm.value.id!, payload);
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
  if (!file) {
    ElMessage.warning('请选择 Excel 文件');
    return false;
  }
  importLoading.value = true;
  try {
    const result = await importFullTestCasesExcelApi(domain.value, file);
    ElMessage.success(
      `导入完成：平台新增 ${result.platform_created_count} / 更新 ${result.platform_updated_count}，车型新增 ${result.vehicle_created_count} / 更新 ${result.vehicle_updated_count}，用例新增 ${result.created_count} / 更新 ${result.updated_count} / 忽略 ${result.ignored_count}，纯配置行 ${result.configuration_row_count}`,
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
    await reloadVehicleOptions();
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
  historyTitle.value = `${row.case_no}${
    row.viu_code ? ` / ${row.viu_code}` : ''
  }${row.module ? ` / ${row.module}` : ''} / ${row.case_name}`;
  historyVisible.value = true;
}

function downloadBlob(data: any, fileName: string) {
  const blob = data instanceof Blob ? data : new Blob([data]);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.append(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

async function downloadTemplate() {
  templateLoading.value = true;
  try {
    const res = await downloadTestCaseTemplateApi(domain.value);
    downloadBlob(res, `auto_test_case_template_${domain.value}.xlsx`);
  } catch (error) {
    ElMessage.error('下载模板失败');
    console.error(error);
  } finally {
    templateLoading.value = false;
  }
}

async function exportCases() {
  exportLoading.value = true;
  try {
    const res = await downloadTestCaseExportApi({
      domain: domain.value,
      case_no_keyword: caseNoKeyword.value || undefined,
      case_name_keyword: caseNameKeyword.value || undefined,
      vehicle_id:
        selectedVehicleIds.value.length === 1
          ? selectedVehicleIds.value[0]
          : undefined,
      viu_code:
        isVehicleControlDomain(domain.value)
          ? selectedViuCode.value || undefined
          : undefined,
    });
    downloadBlob(res, `auto_test_cases_${domain.value}.xlsx`);
  } catch (error) {
    ElMessage.error('导出失败');
    console.error(error);
  } finally {
    exportLoading.value = false;
  }
}

function handleExcelInputChange(event: Event) {
  const target = event.target as HTMLInputElement | null;
  void onImportFile(target?.files?.[0] || null);
  if (target) {
    target.value = '';
  }
}

watch(
  domain,
  async () => {
    selectedVehiclePaths.value = [];
    selectedViuCode.value = '';
    selectedIds.value = [];
    vehicleKeyword.value = '';
    caseNoKeyword.value = '';
    caseNameKeyword.value = '';
    gridApi.setGridOptions({
      columns: useCaseColumns(domain.value),
    });
    await reloadVehicleOptions();
    await refreshGrid();
  },
  { immediate: false },
);

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
  <Page auto-content-height content-class="flex flex-col">
    <div class="mb-4 rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="text-base font-semibold">
            {{ domainMeta.platformPanelTitle }}
          </div>
          <div class="mt-1 text-sm text-gray-500">
            {{ domainMeta.platformPanelHint }}
          </div>
        </div>
        <DomainSwitcher />
      </div>
    </div>

    <div class="mb-4 shrink-0 rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm">
      <ElForm
        :inline="true"
        class="flex flex-wrap items-center gap-4"
        @submit.prevent
      >
        <ElFormItem :label="domainMeta.selectorLabel" class="!mb-0">
          <ElCascader
            v-model="selectedVehiclePaths"
            class="w-[420px]"
            clearable
            collapse-tags
            collapse-tags-tooltip
            filterable
            multiple
            :placeholder="`${domainMeta.selectorPlaceholder}（支持多选）`"
            :max-collapse-tags="1"
            :options="cascaderOptions"
            :props="{ multiple: true, emitPath: true, checkStrictly: false }"
            @change="refreshGrid"
          />
        </ElFormItem>
        <ElFormItem label="车型关键词" class="!mb-0">
          <ElInput
            v-model="vehicleKeyword"
            class="w-[220px]"
            clearable
            placeholder="按关键词筛选"
            @change="refreshGrid"
          />
        </ElFormItem>
        <ElFormItem v-if="isVehicleControlDomain(domain)" label="VIU编号" class="!mb-0">
          <ElSelect
            v-model="selectedViuCode"
            class="w-[180px]"
            clearable
            placeholder="全部 VIU 编号"
            @change="refreshGrid"
          >
            <ElOption
              v-for="item in vehicleViuOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem class="!mb-0">
          <ElButton type="primary" @click="refreshGrid">查询</ElButton>
        </ElFormItem>
      </ElForm>
    </div>

    <div class="min-h-0 flex-1">
      <Grid class="h-full" @selection-change="handleSelectionChange">
        <template #cell-responsible_users="{ row }">
          {{ row.responsible_users.map((user) => user.name).join('、') || '-' }}
        </template>
        <template #header-case_no>
          <TestCaseHeaderKeywordFilter
            v-model="caseNoKeyword"
            label="用例编号"
            placeholder="模糊搜索用例编号"
            @apply="applyCaseHeaderFilter"
            @clear="applyCaseHeaderFilter"
          />
        </template>
        <template #header-case_name>
          <TestCaseHeaderKeywordFilter
            v-model="caseNameKeyword"
            label="用例名称"
            placeholder="模糊搜索用例名称"
            @apply="applyCaseHeaderFilter"
            @clear="applyCaseHeaderFilter"
          />
        </template>
        <template #toolbar-actions>
          <div class="flex items-center gap-2">
            <ElButton type="primary" @click="openCreate">
              {{
                isVehicleControlDomain(domain)
                  ? domain === 'vehicle_io'
                    ? '新增车控IO用例'
                    : '新增车控用例'
                  : domain === 'cockpit_soc'
                    ? '新增座舱SOC用例'
                    : '新增座舱MCU用例'
              }}
            </ElButton>
            <ElButton type="danger" @click="removeSelected">批量删除</ElButton>
            <ElButton :loading="templateLoading" @click="downloadTemplate">
              下载模板
            </ElButton>
            <ElButton :loading="importLoading" @click="excelInputRef?.click()">
              导入 Excel
            </ElButton>
            <input
              ref="excelInputRef"
              class="hidden"
              type="file"
              accept=".xlsx,.xls"
              @change="handleExcelInputChange"
            />
            <ElButton :loading="exportLoading" @click="exportCases">
              导出用例
            </ElButton>
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

    <ElDialog
      v-model="caseDialogVisible"
      :title="
        caseDialogMode === 'create'
          ? isVehicleControlDomain(domain)
            ? domain === 'vehicle_io'
              ? '新增车控IO用例'
              : '新增车控用例'
            : domain === 'cockpit_soc'
              ? '新增座舱SOC用例'
              : '新增座舱MCU用例'
          : isVehicleControlDomain(domain)
            ? domain === 'vehicle_io'
              ? '编辑车控IO用例'
              : '编辑车控用例'
            : domain === 'cockpit_soc'
              ? '编辑座舱SOC用例'
              : '编辑座舱MCU用例'
      "
      width="560px"
    >
      <ElForm ref="caseFormRef" :model="caseForm" label-width="110px">
        <ElFormItem
          :label="domainMeta.selectorLabel"
          prop="vehicle_path"
          required
        >
          <ElCascader
            v-model="caseForm.vehicle_path"
            class="w-full"
            clearable
            filterable
            :placeholder="domainMeta.selectorPlaceholder"
            :options="cascaderOptions"
            :props="{ emitPath: true }"
            @change="caseForm.viu_code = ''"
          />
        </ElFormItem>
        <ElFormItem
          v-if="isVehicleControlDomain(domain)"
          label="VIU编号"
          prop="viu_code"
          required
        >
          <ElSelect
            v-model="caseForm.viu_code"
            class="w-full"
            clearable
            placeholder="选择 VIU 编号"
          >
            <ElOption
              v-for="item in selectedVehicleViuOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="用例编号" prop="case_no" required>
          <ElInput v-model="caseForm.case_no" />
        </ElFormItem>
        <ElFormItem label="用例名称" prop="case_name" required>
          <ElInput v-model="caseForm.case_name" />
        </ElFormItem>
        <ElFormItem
          v-if="domain === 'cockpit_soc'"
          label="模块"
          prop="module"
          required
        >
          <ElInput v-model="caseForm.module" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="caseForm.remark" type="textarea" :rows="3" />
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
