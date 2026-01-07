<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ProjectQualitySummary } from '#/api/project-manager/code_quality';

import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElLink } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getQualityOverviewApi } from '#/api/project-manager/code_quality';

import { useSearchFormSchema, useSummaryColumns } from './data';

defineOptions({ name: 'CodeQualityDashboard' });

const router = useRouter();

function onNameClick(row: ProjectQualitySummary) {
  router.push(`/project-manager/code-quality/detail/${row.project_id}`);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useSummaryColumns(onNameClick),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: true }, // Enable pager for manual pagination
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          // Frontend filtering since backend returns all
          const data = await getQualityOverviewApi();
          let filtered = data;
          if (formValues.keyword) {
            const k = formValues.keyword.toLowerCase();
            filtered = filtered.filter((i) =>
              i.project_name.toLowerCase().includes(k),
            );
          }
          if (formValues.domain) {
            filtered = filtered.filter((i) =>
              i.project_domain.includes(formValues.domain),
            );
          }
          if (formValues.type) {
            filtered = filtered.filter((i) =>
              i.project_type.includes(formValues.type),
            );
          }
          // Date filtering is tricky on aggregated data, skipping for now or exact match?
          // The aggregated data has "record_date".
          if (formValues.date) {
            filtered = filtered.filter(
              (i) => i.record_date === formValues.date,
            );
          }

          // Manual pagination
          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          const pageItems = filtered.slice(start, end);

          return { items: pageItems, total: filtered.length };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<ProjectQualitySummary>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #name_slot="{ row }">
        <ElLink type="primary" @click="onNameClick(row)">
          {{ row.project_name }}
        </ElLink>
      </template>
    </Grid>
  </Page>
</template>
