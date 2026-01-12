<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { DtsProjectOverview } from '#/api/project-manager/dts';

import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElLink, ElMessage, ElTag } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getDtsOverviewApi, syncDtsApi } from '#/api/project-manager/dts';

import { useDashboardColumns, useSearchFormSchema } from './data';

defineOptions({ name: 'DtsDashboard' });

const router = useRouter();

function onNameClick(row: DtsProjectOverview) {
  router.push(`/project-manager/dts/detail/${row.project_id}`);
}

async function handleSync(row: DtsProjectOverview) {
  try {
    const res = await syncDtsApi(row.project_id);
    if (res.success) {
      ElMessage.success('同步成功');
      gridApi.reload();
    } else {
      ElMessage.error(res.message || '同步失败');
    }
  } catch (error) {
    console.error(error);
  }
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
          const data = await getDtsOverviewApi();
          let filtered = data;
          if (formValues.keyword) {
            const k = formValues.keyword.toLowerCase();
            filtered = filtered.filter(i => i.project_name.toLowerCase().includes(k));
          }
          
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
  } as VxeTableGridOptions<DtsProjectOverview>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #name_slot="{ row }">
        <ElLink type="primary" @click="onNameClick(row)">{{ row.project_name }}</ElLink>
      </template>
      <template #status_slot="{ row }">
        <ElTag :type="row.has_data_today ? 'success' : 'info'">
          {{ row.has_data_today ? '已同步' : '未同步' }}
        </ElTag>
      </template>
      <template #action_slot="{ row }">
        <ElButton type="primary" link size="small" @click="handleSync(row)">同步</ElButton>
      </template>
    </Grid>
  </Page>
</template>
