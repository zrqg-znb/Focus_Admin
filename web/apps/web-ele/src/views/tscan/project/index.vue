<script setup lang="ts">
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listProjectsApi, runScanTaskApi } from '#/api/tscan';
import { useColumns } from './data';
import { ElButton, ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';

const router = useRouter();

const gridOptions: any = {
  columns: useColumns(),
  proxyConfig: {
    ajax: {
      query: async () => {
        const res = await listProjectsApi();
        return { items: res };
      },
    },
  },
};

const [Grid, gridApi] = useVbenVxeGrid({ gridOptions });

async function handleRun(row: any) {
  try {
    await runScanTaskApi(row.id);
    ElMessage.success('任务已启动');
    gridApi.reload();
  } catch (error) {
    ElMessage.error('启动失败');
  }
}

function handleViewResults(row: any) {
  router.push({
    name: 'TScanResults',
    query: { projectId: row.id }
  });
}
</script>

<template>
  <Page title="TScan 项目管理">
    <Grid>
      <template #action="{ row }">
        <ElButton type="primary" link @click="handleRun(row)">启动扫描</ElButton>
        <ElButton type="primary" link @click="handleViewResults(row)">查看结果</ElButton>
      </template>
    </Grid>
  </Page>
</template>
