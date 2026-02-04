<script setup lang="ts">
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listProjectsApi } from '#/api/code_scan';
import { useColumns } from './data';
import { ElButton, ElMessage, ElTag } from 'element-plus';
import { useRouter } from 'vue-router';
import { useClipboard } from '@vueuse/core';

const router = useRouter();
const { copy } = useClipboard();

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

const [Grid] = useVbenVxeGrid({ gridOptions });

function handleViewResults(row: any) {
  router.push({
    name: 'CodeScanResults',
    query: { projectId: row.id }
  });
}

function copyProjectKey(key: string) {
    copy(key);
    ElMessage.success('Project Key 已复制');
}
</script>

<template>
  <Page title="Code Scan 项目管理">
    <Grid>
      <template #project_key="{ row }">
          <div class="flex items-center gap-2">
              <span>{{ row.project_key }}</span>
              <ElButton size="small" link @click="copyProjectKey(row.project_key)">复制</ElButton>
          </div>
      </template>
      <template #action="{ row }">
        <ElButton type="primary" link @click="handleViewResults(row)">查看结果</ElButton>
      </template>
    </Grid>
  </Page>
</template>
