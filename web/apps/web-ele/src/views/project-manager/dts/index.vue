<script lang="ts" setup>
import type { DtsProjectOverview } from '#/api/project-manager/dts';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElLink, ElMessage, ElTag } from 'element-plus';

import { getDtsOverviewApi, syncDtsApi } from '#/api/project-manager/dts';
import { useZqTable } from '#/components/zq-table';

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

const [Grid, gridApi] = useZqTable({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
    showCollapseButton: false,
  },
  gridOptions: {
    columns: useDashboardColumns(),
    border: true,
    stripe: true,
    pagerConfig: { enabled: true, pageSize: 20 },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }) => {
          const data = await getDtsOverviewApi();
          let filtered = data;
          if (form?.keyword) {
            const keyword = String(form.keyword).toLowerCase();
            filtered = filtered.filter((item) =>
              item.project_name.toLowerCase().includes(keyword),
            );
          }

          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          return { items: filtered.slice(start, end), total: filtered.length };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
  } as ZqTableGridOptions<DtsProjectOverview>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid class="h-full">
      <template #cell-project_name="{ row }">
        <ElLink type="primary" @click="onNameClick(row)">
          {{ row.project_name }}
        </ElLink>
      </template>
      <template #cell-has_data_today="{ row }">
        <ElTag :type="row.has_data_today ? 'success' : 'info'">
          {{ row.has_data_today ? '已同步' : '未同步' }}
        </ElTag>
      </template>
      <template #cell-actions="{ row }">
        <ElButton type="primary" link size="small" @click="handleSync(row)">
          同步
        </ElButton>
      </template>
    </Grid>
  </Page>
</template>
