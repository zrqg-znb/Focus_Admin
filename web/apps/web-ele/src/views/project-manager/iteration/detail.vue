<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { IterationDetailItem } from '#/api/project-manager/iteration';

import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  listProjectIterationsApi,
  refreshProjectIterationApi,
} from '#/api/project-manager/iteration';
import { getProjectApi } from '#/api/project-manager/project';

import { useDetailColumns } from './data';

defineOptions({ name: 'IterationDetail' });

const route = useRoute();
const router = useRouter();
const projectId = route.params.id as string;
const projectInfo = ref<any>({});
const loading = ref(false);

async function fetchProjectInfo() {
  try {
    projectInfo.value = await getProjectApi(projectId);
  } catch (error) {
    console.error(error);
  }
}

async function handleRefresh() {
  try {
    loading.value = true;
    await refreshProjectIterationApi(projectId);
    ElMessage.success('刷新成功');
    gridApi.reload();
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleBack() {
  router.back();
}

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useDetailColumns(),
    height: 'auto',
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }) => {
          const data = await listProjectIterationsApi(projectId);
          
          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          const pageItems = data.slice(start, end);
          
          return { items: pageItems, total: data.length };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      zoom: true,
    },
  } as VxeTableGridOptions<IterationDetailItem>,
});

onMounted(() => {
  fetchProjectInfo();
});
</script>

<template>
  <Page auto-content-height>
    <div class="mb-4 flex items-center justify-between px-4">
      <div class="flex items-center gap-4">
        <ElButton @click="handleBack">返回</ElButton>
        <div class="text-lg font-bold">{{ projectInfo.name }} - 迭代详情</div>
      </div>
      <ElButton type="primary" :loading="loading" @click="handleRefresh">
        刷新数据
      </ElButton>
    </div>
    <Grid />
  </Page>
</template>
