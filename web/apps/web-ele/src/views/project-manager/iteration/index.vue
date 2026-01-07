<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { IterationDashboardItem } from '#/api/project-manager/iteration';

import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElLink } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getIterationOverviewApi } from '#/api/project-manager/iteration';

import { useDashboardColumns, useSearchFormSchema } from './data';

defineOptions({ name: 'IterationDashboard' });

const router = useRouter();

function onNameClick(row: IterationDashboardItem) {
  router.push(`/project-manager/iteration/detail/${row.project_id}`);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useDashboardColumns(onNameClick),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const data = await getIterationOverviewApi();
          let filtered = data;
          if (formValues.keyword) {
            const k = formValues.keyword.toLowerCase();
            filtered = filtered.filter(i => i.project_name.toLowerCase().includes(k));
          }
          if (formValues.domain) {
            filtered = filtered.filter(i => i.project_domain.includes(formValues.domain));
          }
          if (formValues.type) {
            filtered = filtered.filter(i => i.project_type.includes(formValues.type));
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
  } as VxeTableGridOptions<IterationDashboardItem>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #name_slot="{ row }">
        <ElLink type="primary" @click="onNameClick(row)">{{ row.project_name }}</ElLink>
      </template>
    </Grid>
  </Page>
</template>
