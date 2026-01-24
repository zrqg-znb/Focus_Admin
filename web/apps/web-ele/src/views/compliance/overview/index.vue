<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { DeptComplianceStat } from '#/api/compliance';

import { onMounted } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ElButton } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getDeptStats } from '#/api/compliance';

import { useOverviewColumns, useOverviewSearchFormSchema } from './data';

const router = useRouter();

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useOverviewSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useOverviewColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: false }, // Overview might not need pagination if data is small, but enabled is safer if backend supports it. Currently backend returns all list.
    proxyConfig: {
      ajax: {
        query: async (_, formValues) => {
          // Backend API currently returns all data, no pagination params support in python service yet? 
          // Python service: `get_department_stats` returns list.
          // We can implement client-side filtering if needed, or just return data.
          // Since backend doesn't take pagination, we just fetch all.
          // If formValues has dept_name, we might need to filter client side or update backend. 
          // For now, let's just return the full list and let VxeTable handle it or just display all.
          // Note: VxeTable proxy query expects specific return format or just data array.
          const data = await getDeptStats();
          // Simple client-side filtering for demo
          if (formValues.dept_name) {
             return data.filter(item => item.dept_name.includes(formValues.dept_name));
          }
          return data;
        },
      },
    },
    toolbarConfig: {
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<DeptComplianceStat>,
});

const handleViewDetail = (row: DeptComplianceStat) => {
  router.push({ 
    path: '/compliance/detail', 
    query: { deptId: row.dept_id, deptName: row.dept_name } 
  });
};
</script>

<template>
  <Page title="合规风险概览" auto-content-height>
    <Grid>
      <template #unresolved="{ row }">
        <span :class="{'text-red-500 font-bold': row.unresolved_count > 0}">
          {{ row.unresolved_count }}
        </span>
      </template>
      <template #action="{ row }">
        <ElButton type="primary" link @click="handleViewDetail(row)">
          查看详情
        </ElButton>
      </template>
    </Grid>
  </Page>
</template>
