<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { DtsTeam } from '#/api/project-manager/dts';

import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getDtsDashboardApi, syncDtsApi } from '#/api/project-manager/dts';
import { getProjectApi } from '#/api/project-manager/project';

import { useDetailColumns } from './data';

defineOptions({ name: 'DtsDetail' });

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
    await syncDtsApi(projectId);
    ElMessage.success('同步成功');
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
    treeConfig: {
      transform: false,
      rowField: 'id',
      parentField: 'parent_id',
      childrenField: 'children',
      expandAll: true,
    },
    proxyConfig: {
      ajax: {
        query: async () => {
          const data = await getDtsDashboardApi(projectId);
          return { items: data.root_teams || [] };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      zoom: true,
    },
  } as VxeTableGridOptions<DtsTeam>,
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
        <div class="text-lg font-bold">{{ projectInfo.name }} - 问题单详情</div>
      </div>
      <ElButton type="primary" :loading="loading" @click="handleRefresh">
        同步数据
      </ElButton>
    </div>
    <Grid />
  </Page>
</template>
