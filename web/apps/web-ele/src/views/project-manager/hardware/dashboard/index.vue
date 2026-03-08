<script lang="ts" setup>
import type { PhaseBoardRow } from './data';

import type {
  ProjectFilterParams,
  ProjectOut,
} from '#/api/project-manager/project';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { nextTick, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { Download } from '@element-plus/icons-vue';
import { ElButton, ElMessage, ElTabPane, ElTabs } from 'element-plus';
import * as XLSX from 'xlsx';

import { listProjectsApi } from '#/api/project-manager/project';
import { useZqTable } from '#/components/zq-table';

import {
  useCockpitColumns,
  useCockpitSearchFormSchema,
  useVehicleColumns,
  useVehicleSearchFormSchema,
} from './data';

defineOptions({ name: 'HardwareConfigDashboard' });

type HardwareScenario = 'cockpit' | 'vehicle';
type VehiclePointKey = 'viu0' | 'viu1' | 'viu2' | 'viu3';

const VEHICLE_POINT_KEYS: VehiclePointKey[] = ['viu0', 'viu1', 'viu2', 'viu3'];
const activeView = ref<HardwareScenario>('vehicle');
const currentVehicleRows = ref<PhaseBoardRow[]>([]);
const vehicleFormValues = ref<Record<string, any>>({});
const cockpitFormValues = ref<Record<string, any>>({});
const exportLoading = ref(false);

const VEHICLE_EXPORT_COLUMNS = [
  { label: '项目', prop: 'project_name' },
  { label: '阶段', prop: 'stage_name' },
  { label: '阶段起止', prop: 'stage_range' },
  { label: 'IDVP 软件平台', prop: 'idvp_platform_name' },
  { label: 'viu0', prop: 'viu0' },
  { label: 'viu1', prop: 'viu1' },
  { label: 'viu2', prop: 'viu2' },
  { label: 'viu3', prop: 'viu3' },
] as const;

const COCKPIT_EXPORT_COLUMNS = [
  { label: '项目', prop: 'project_name' },
  { label: 'CDC 平台版本', prop: 'cdc_platform_name' },
  { label: '智慧屏版本', prop: 'smart_screen_display' },
] as const;

function getVehiclePointText(row: PhaseBoardRow, point: string) {
  const item = (row.vehicle_hardware || []).find(
    (hardware) => hardware.point.toLowerCase() === point.toLowerCase(),
  );
  if (!item) return '-';
  const board = item.board || '-';
  const configType = item.config_type || '-';
  if (!item.bomid) return `${board} / ${configType}`;
  return `${board} / ${configType} / BOMID: ${item.bomid}`;
}

function formatStageRange(stageStart?: string, stageEnd?: string) {
  if (!stageStart && !stageEnd) {
    return '-';
  }
  return `${stageStart || '-'} ~ ${stageEnd || '-'}`;
}

function formatSmartScreenDisplay(
  smartScreenVersionNames?: string[],
  smartScreenVersionName?: string,
) {
  return smartScreenVersionNames?.join(' / ') || smartScreenVersionName || '-';
}

function toPhaseRows(projects: ProjectOut[]): PhaseBoardRow[] {
  const rows: PhaseBoardRow[] = [];
  for (const project of projects) {
    const phaseConfigs = project.phase_configs || [];
    for (const phase of phaseConfigs) {
      const baseRow: PhaseBoardRow = {
        project_id: project.id,
        project_name: project.name,
        project_code: project.code,
        domain: project.domain,
        stage_name: phase.stage_name,
        stage_start: phase.stage_start,
        stage_end: phase.stage_end,
        stage_range: formatStageRange(phase.stage_start, phase.stage_end),
        scenario:
          phase.scenario ||
          (project.domain.includes('座舱') ? 'cockpit' : 'vehicle'),
        idvp_platform_name: project.idvp_platform_name || '-',
        vehicle_hardware: phase.vehicle_hardware || [],
        cdc_platform_name: phase.cdc_platform_name || '-',
        smart_screen_version_name: phase.smart_screen_version_name,
        smart_screen_version_names: phase.smart_screen_version_names || [],
        smart_screen_display: formatSmartScreenDisplay(
          phase.smart_screen_version_names || [],
          phase.smart_screen_version_name,
        ),
      };

      VEHICLE_POINT_KEYS.forEach((point) => {
        baseRow[point] = getVehiclePointText(baseRow, point);
      });

      rows.push(baseRow);
    }
  }
  return rows;
}

function filterRows(
  rows: PhaseBoardRow[],
  formValues: Record<string, any>,
  scenario: HardwareScenario,
) {
  const projectKeyword = String(formValues.project_keyword || '')
    .trim()
    .toLowerCase();
  const idvpPlatformKeyword = String(formValues.idvp_platform_keyword || '')
    .trim()
    .toLowerCase();
  const cdcPlatformKeyword = String(formValues.cdc_platform_keyword || '')
    .trim()
    .toLowerCase();
  const smartScreenKeyword = String(formValues.smart_screen_keyword || '')
    .trim()
    .toLowerCase();

  let filtered = rows.filter((item) => item.scenario === scenario);
  if (projectKeyword) {
    filtered = filtered.filter((item) =>
      item.project_name.toLowerCase().includes(projectKeyword),
    );
  }
  if (scenario === 'vehicle' && idvpPlatformKeyword) {
    filtered = filtered.filter((item) =>
      String(item.idvp_platform_name || '')
        .toLowerCase()
        .includes(idvpPlatformKeyword),
    );
  }
  if (scenario === 'cockpit' && cdcPlatformKeyword) {
    filtered = filtered.filter((item) =>
      String(item.cdc_platform_name || '')
        .toLowerCase()
        .includes(cdcPlatformKeyword),
    );
  }
  if (scenario === 'cockpit' && smartScreenKeyword) {
    filtered = filtered.filter((item) =>
      String(item.smart_screen_display || '')
        .toLowerCase()
        .includes(smartScreenKeyword),
    );
  }
  return filtered;
}

function buildScenarioQueryParams(
  formValues: Record<string, any>,
  scenario: HardwareScenario,
  page: number,
  pageSize: number,
): ProjectFilterParams {
  const params: ProjectFilterParams = {
    hardware_scenario: scenario,
    keyword: String(formValues.project_keyword || '').trim() || undefined,
    enable_hardware_config: true,
    page,
    pageSize,
  };

  if (scenario === 'vehicle') {
    params.idvp_platform_keyword =
      String(formValues.idvp_platform_keyword || '').trim() || undefined;
  } else {
    params.cdc_platform_keyword =
      String(formValues.cdc_platform_keyword || '').trim() || undefined;
    params.smart_screen_keyword =
      String(formValues.smart_screen_keyword || '').trim() || undefined;
  }

  return params;
}

async function fetchScenarioProjects(
  formValues: Record<string, any>,
  scenario: HardwareScenario,
  page = 1,
  pageSize = 1000,
) {
  return await listProjectsApi(
    buildScenarioQueryParams(formValues, scenario, page, pageSize),
  );
}

async function fetchAllScenarioProjects(
  formValues: Record<string, any>,
  scenario: HardwareScenario,
) {
  const allItems: ProjectOut[] = [];
  const pageSize = 200;
  let page = 1;
  let total = 0;

  while (true) {
    const data = await fetchScenarioProjects(
      formValues,
      scenario,
      page,
      pageSize,
    );
    const currentItems = data.items || [];
    total = Number(data.total || 0);
    allItems.push(...currentItems);
    if (currentItems.length === 0 || allItems.length >= total) {
      break;
    }
    page += 1;
    if (page > 500) {
      throw new Error('导出页数超过安全上限，请缩小筛选范围后重试');
    }
  }

  return allItems;
}

async function loadRowsByScenario(
  page: { currentPage: number; pageSize: number },
  rawFormValues: Record<string, any>,
  scenario: HardwareScenario,
) {
  const formValues = { ...rawFormValues };
  if (scenario === 'vehicle') {
    vehicleFormValues.value = formValues;
  } else {
    cockpitFormValues.value = formValues;
  }

  const projects = await fetchAllScenarioProjects(formValues, scenario);
  const rows = toPhaseRows(projects);
  const scenarioRows = filterRows(rows, formValues, scenario);
  const currentPage = page?.currentPage || 1;
  const pageSize = page?.pageSize || 20;
  const start = (currentPage - 1) * pageSize;
  const end = start + pageSize;
  const pageRows = scenarioRows.slice(start, end);

  if (scenario === 'vehicle') {
    currentVehicleRows.value = pageRows;
  }

  return {
    items: pageRows,
    total: scenarioRows.length,
  };
}

async function fetchAllRowsByScenario(
  formValues: Record<string, any>,
  scenario: HardwareScenario,
) {
  const projects = await fetchAllScenarioProjects(formValues, scenario);
  return filterRows(toPhaseRows(projects), formValues, scenario);
}

function normalizeExportValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return value;
}

function buildSheetData(
  rows: PhaseBoardRow[],
  columns: ReadonlyArray<{ label: string; prop: keyof PhaseBoardRow }>,
) {
  return [
    columns.map((column) => column.label),
    ...rows.map((row) =>
      columns.map((column) => normalizeExportValue(row[column.prop])),
    ),
  ];
}

function vehicleProjectSpanMethod({ column, row, rowIndex }: any) {
  const columnField = String(
    column.property || column.prop || column.field || '',
  );
  if (columnField !== 'project_name') {
    return { rowspan: 1, colspan: 1 };
  }

  const rows = currentVehicleRows.value;
  const prevRow = rows[rowIndex - 1];
  if (prevRow && prevRow.project_id === row.project_id) {
    return { rowspan: 0, colspan: 0 };
  }

  let rowspan = 1;
  for (let index = rowIndex + 1; index < rows.length; index += 1) {
    const currentRow = rows[index];
    if (currentRow && currentRow.project_id === row.project_id) {
      rowspan += 1;
    } else {
      break;
    }
  }
  return { rowspan, colspan: 1 };
}

async function handleExportAllSheets() {
  if (exportLoading.value) {
    return;
  }

  exportLoading.value = true;
  try {
    const xlsx = (XLSX as any)?.utils ? (XLSX as any) : (XLSX as any)?.default;
    if (!xlsx?.utils) {
      throw new TypeError('xlsx utils unavailable');
    }
    const writeFile = xlsx.writeFileXLSX || xlsx.writeFile;
    if (typeof writeFile !== 'function') {
      throw new TypeError('xlsx writeFile unavailable');
    }

    const [vehicleRows, cockpitRows] = await Promise.all([
      fetchAllRowsByScenario(vehicleFormValues.value, 'vehicle'),
      fetchAllRowsByScenario(cockpitFormValues.value, 'cockpit'),
    ]);

    if (vehicleRows.length === 0 && cockpitRows.length === 0) {
      ElMessage.warning('暂无可导出数据');
      return;
    }

    const workbook = xlsx.utils.book_new();
    const vehicleSheet = xlsx.utils.aoa_to_sheet(
      buildSheetData(vehicleRows, VEHICLE_EXPORT_COLUMNS),
    );
    const cockpitSheet = xlsx.utils.aoa_to_sheet(
      buildSheetData(cockpitRows, COCKPIT_EXPORT_COLUMNS),
    );

    xlsx.utils.book_append_sheet(workbook, vehicleSheet, '车控');
    xlsx.utils.book_append_sheet(workbook, cockpitSheet, '座舱');

    const stamp = new Date().toISOString().slice(0, 10);
    writeFile(workbook, `硬件配套看板-${stamp}.xlsx`);
    ElMessage.success('导出成功');
  } catch (error) {
    console.error('[hardware dashboard export failed]', error);
    ElMessage.error('导出失败，请检查筛选条件或数据后重试');
  } finally {
    exportLoading.value = false;
  }
}

const [VehicleGrid, vehicleGridApi] = useZqTable({
  separator: false,
  formOptions: {
    schema: useVehicleSearchFormSchema(),
    showCollapseButton: false,
    submitOnChange: true,
  },
  gridOptions: {
    border: true,
    stripe: true,
    columns: useVehicleColumns(),
    rowKey: 'project_id',
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }) => {
          return await loadRowsByScenario(page, form || {}, 'vehicle');
        },
      },
    },
    spanMethod: vehicleProjectSpanMethod,
  } as ZqTableGridOptions<PhaseBoardRow>,
});

const [CockpitGrid, cockpitGridApi] = useZqTable({
  separator: false,
  formOptions: {
    schema: useCockpitSearchFormSchema(),
    showCollapseButton: false,
    submitOnChange: true,
  },
  gridOptions: {
    border: true,
    stripe: true,
    columns: useCockpitColumns(),
    rowKey: 'project_id',
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page, form }) =>
          await loadRowsByScenario(page, form || {}, 'cockpit'),
      },
    },
  } as ZqTableGridOptions<PhaseBoardRow>,
});

watch(
  () => activeView.value,
  async (value) => {
    await nextTick();
    await (value === 'vehicle'
      ? vehicleGridApi.reload()
      : cockpitGridApi.reload());
  },
);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col">
      <section
        class="border-border bg-card flex min-h-0 flex-1 flex-col rounded-xl border p-4 shadow-sm"
      >
        <ElTabs
          v-model="activeView"
          class="hardware-dashboard-tabs flex h-full min-h-0 flex-col"
        >
          <ElTabPane label="车控视图" name="vehicle">
            <section
              class="border-border bg-background flex h-full min-h-0 flex-col rounded-lg border p-3"
            >
              <div class="min-h-0 flex-1">
                <VehicleGrid class="h-full">
                  <template #toolbar-tools>
                    <ElButton
                      :icon="Download"
                      :loading="exportLoading"
                      type="primary"
                      @click="handleExportAllSheets"
                    >
                      全量导出
                    </ElButton>
                  </template>
                </VehicleGrid>
              </div>
            </section>
          </ElTabPane>

          <ElTabPane label="座舱视图" name="cockpit">
            <section
              class="border-border bg-background flex h-full min-h-0 flex-col rounded-lg border p-3"
            >
              <div class="min-h-0 flex-1">
                <CockpitGrid class="h-full">
                  <template #toolbar-tools>
                    <ElButton
                      :icon="Download"
                      :loading="exportLoading"
                      type="primary"
                      @click="handleExportAllSheets"
                    >
                      全量导出
                    </ElButton>
                  </template>
                </CockpitGrid>
              </div>
            </section>
          </ElTabPane>
        </ElTabs>
      </section>
    </div>
  </Page>
</template>

<style scoped>
.hardware-dashboard-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.hardware-dashboard-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.hardware-dashboard-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
}

.hardware-dashboard-tabs :deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
}
</style>
