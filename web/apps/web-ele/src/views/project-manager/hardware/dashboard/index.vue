<script lang="ts" setup>
import type { PhaseBoardRow } from './data';

import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ProjectOut } from '#/api/project-manager/project';

import { Page } from '@vben/common-ui';

import { ElTag } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listProjectsApi } from '#/api/project-manager/project';

import { useColumns, useSearchFormSchema } from './data';

defineOptions({ name: 'HardwareConfigDashboard' });

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
        viu_platform_name: project.viu_platform_name,
        vehicle_hardware: phase.vehicle_hardware || [],
        cdc_platform_name: phase.cdc_platform_name,
        smart_screen_version_name: phase.smart_screen_version_name,
      });
    }
  }
  return rows;
}

const [Grid] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const data = await listProjectsApi({
            page: 1,
            pageSize: 1000,
            enable_hardware_config: true,
          });
          const keyword = (formValues.keyword || '').toLowerCase();
          const domain = (formValues.domain || '').toLowerCase();
          const stage = (formValues.stage || '').toLowerCase();

          let rows = toPhaseRows(data.items || []);
          if (keyword) {
            rows = rows.filter(
              (item) =>
                item.project_name.toLowerCase().includes(keyword) ||
                (item.project_code || '').toLowerCase().includes(keyword),
            );
          }
          if (domain) {
            rows = rows.filter((item) =>
              item.domain.toLowerCase().includes(domain),
            );
          }
          if (stage) {
            rows = rows.filter((item) =>
              item.stage_name.toLowerCase().includes(stage),
            );
          }

          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          return {
            items: rows.slice(start, end),
            total: rows.length,
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
  } as VxeTableGridOptions<PhaseBoardRow>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #config_combo="{ row }">
        <div v-if="row.scenario === 'vehicle'" class="flex flex-wrap gap-2">
          <ElTag size="small" type="success">
            VIU平台: {{ row.viu_platform_name || '-' }}
          </ElTag>
          <ElTag
            v-for="item in row.vehicle_hardware || []"
            :key="`${item.point}-${item.board}-${item.bomid || ''}`"
            size="small"
            type="info"
          >
            {{ item.point }}: {{ item.board }} / BOMID: {{ item.bomid || '-' }}
          </ElTag>
          <span
            v-if="!row.vehicle_hardware || row.vehicle_hardware.length === 0"
            class="text-muted-foreground text-sm"
          >
            暂无硬件组合
          </span>
        </div>
        <div v-else class="flex flex-wrap gap-2">
          <ElTag size="small" type="success">
            CDC: {{ row.cdc_platform_name || '-' }}
          </ElTag>
          <ElTag size="small" type="warning">
            智慧屏: {{ row.smart_screen_version_name || '-' }}
          </ElTag>
        </div>
      </template>
    </Grid>
  </Page>
</template>
