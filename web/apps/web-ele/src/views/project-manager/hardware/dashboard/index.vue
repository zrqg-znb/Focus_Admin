<script lang="ts" setup>
import type { PhaseBoardRow } from './data';

import type { ProjectOut } from '#/api/project-manager/project';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { nextTick, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { ElTabPane, ElTabs } from 'element-plus';

import { listProjectsApi } from '#/api/project-manager/project';
import { useZqTable } from '#/components/zq-table';

import {
  useCockpitColumns,
  useCockpitSearchFormSchema,
  useVehicleColumns,
  useVehicleSearchFormSchema,
} from './data';

defineOptions({ name: 'HardwareConfigDashboard' });

const activeView = ref<'cockpit' | 'vehicle'>('vehicle');
const currentVehicleRows = ref<PhaseBoardRow[]>([]);

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

function toPhaseRows(projects: ProjectOut[]): PhaseBoardRow[] {
  const rows: PhaseBoardRow[] = [];
  for (const project of projects) {
    const phaseConfigs = project.phase_configs || [];
    for (const phase of phaseConfigs) {
      rows.push({
        project_id: project.id,
        project_name: project.name,
        project_code: project.code,
        domain: project.domain,
        stage_name: phase.stage_name,
        stage_start: phase.stage_start,
        stage_end: phase.stage_end,
        scenario:
          phase.scenario ||
          (project.domain.includes('座舱') ? 'cockpit' : 'vehicle'),
        idvp_platform_name: project.idvp_platform_name,
        vehicle_hardware: phase.vehicle_hardware || [],
        cdc_platform_name: phase.cdc_platform_name,
        smart_screen_version_name: phase.smart_screen_version_name,
        smart_screen_version_names: phase.smart_screen_version_names || [],
      });
    }
  }
  return rows;
}

function filterRows(
  rows: PhaseBoardRow[],
  formValues: Record<string, any>,
  scenario: 'cockpit' | 'vehicle',
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
      String(
        (item.smart_screen_version_names || []).join(' / ') ||
          item.smart_screen_version_name ||
          '',
      )
        .toLowerCase()
        .includes(smartScreenKeyword),
    );
  }
  return filtered;
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

async function loadRowsByScenario(
  page: { currentPage: number; pageSize: number },
  formValues: Record<string, any>,
  scenario: 'cockpit' | 'vehicle',
) {
  const projectKeyword = String(formValues.project_keyword || '').trim();
  const data = await listProjectsApi({
    hardware_scenario: scenario,
    keyword: projectKeyword || undefined,
    page: 1,
    pageSize: 1000,
    enable_hardware_config: true,
  });
  const rows = toPhaseRows(data.items || []);
  const scenarioRows = filterRows(rows, formValues, scenario);
  const currentPage = page?.currentPage || 1;
  const pageSize = page?.pageSize || 20;
  const start = (currentPage - 1) * pageSize;
  const end = start + pageSize;
  return {
    items: scenarioRows.slice(start, end),
    total: scenarioRows.length,
  };
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
          const result = await loadRowsByScenario(page, form || {}, 'vehicle');
          currentVehicleRows.value = result.items || [];
          return result;
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
                  <template #cell-stage_start="{ row }">
                    {{
                      !row.stage_start && !row.stage_end
                        ? '-'
                        : `${row.stage_start || '-'} ~ ${row.stage_end || '-'}`
                    }}
                  </template>
                  <template #cell-viu0="{ row }">
                    {{ getVehiclePointText(row, 'viu0') }}
                  </template>
                  <template #cell-viu1="{ row }">
                    {{ getVehiclePointText(row, 'viu1') }}
                  </template>
                  <template #cell-viu2="{ row }">
                    {{ getVehiclePointText(row, 'viu2') }}
                  </template>
                  <template #cell-viu3="{ row }">
                    {{ getVehiclePointText(row, 'viu3') }}
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
                <CockpitGrid class="h-full" />
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
