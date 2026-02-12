<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { IterationDashboardItem } from '#/api/project-manager/iteration';

import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElLink, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  getIterationOverviewApi,
  updateManualMetricApi,
} from '#/api/project-manager/iteration';

import { useDashboardColumns, useSearchFormSchema } from './data';

defineOptions({ name: 'IterationDashboard' });

const router = useRouter();

function onNameClick(row: IterationDashboardItem) {
  router.push(`/project-manager/iteration/detail/${row.project_id}`);
}

async function onEditClosed({ row, column }: any) {
  if (!row.iteration_id) return;
  const field = column.field;
  if (
    field === 'test_automation_rate' ||
    field === 'test_case_execution_rate'
  ) {
    try {
      await updateManualMetricApi(row.iteration_id, {
        [field]: row[field],
      });
      ElMessage.success('更新成功');
    } catch {
      // Revert change? For now just show error
      ElMessage.error('更新失败');
    }
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridEvents: {
    editClosed: onEditClosed,
  },
  gridOptions: {
    columns: useDashboardColumns(onNameClick),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: true },
    editConfig: {
      trigger: 'click',
      mode: 'cell',
      beforeEditMethod: ({ row }) => {
        if (!row.end_date) return true;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const end = new Date(row.end_date);
        if (end < today) {
          ElMessage.warning('该迭代已结束，无法修改指标');
          return false;
        }
        return true;
      },
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const data = await getIterationOverviewApi();
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
        <ElLink type="primary" @click="onNameClick(row)">
          {{ row.project_name }}
        </ElLink>
      </template>
    </Grid>
  </Page>
</template>
