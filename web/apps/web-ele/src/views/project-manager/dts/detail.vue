<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { DtsDefect, DtsTeam } from '#/api/project-manager/dts';

import { nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElMessage, ElTabPane, ElTabs } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  getDtsDashboardApi,
  getDtsDetailsApi,
  syncDtsApi,
} from '#/api/project-manager/dts';
import { getProjectApi } from '#/api/project-manager/project';

import { useDefectListColumns, useDetailColumns } from './data';

defineOptions({ name: 'DtsDetail' });

const route = useRoute();
const router = useRouter();
const projectId = route.params.id as string;
const projectInfo = ref<any>({});
const loading = ref(false);
const activeTab = ref('dashboard');

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
    ElMessage.success('同步任务已提交，请稍后查看同步日志或刷新页面');
    await nextTick();
    if (activeTab.value === 'dashboard') {
      gridApi.query();
    } else {
      detailGridApi.query();
    }
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

const [DetailGrid, detailGridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useDefectListColumns(),
    height: 'auto',
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }) => {
          const res = await getDtsDetailsApi(
            projectId,
            page.currentPage,
            page.pageSize,
          );
          return {
            items: res.dataList,
            total: res.pageResult.total,
          };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      zoom: true,
    },
  } as VxeTableGridOptions<DtsDefect>,
});

onMounted(() => {
  fetchProjectInfo();
  gridApi.query();
});

watch(
  () => activeTab.value,
  async (tab) => {
    await nextTick();
    if (tab === 'dashboard') {
      gridApi.query();
    } else {
      detailGridApi.query();
    }
  },
);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full flex-col">
      <div class="mb-4 flex items-center justify-between px-4">
        <div class="flex items-center gap-4">
          <ElButton @click="handleBack">返回</ElButton>
          <div class="text-lg font-bold">
            {{ projectInfo.name }} - 问题单详情
          </div>
        </div>
        <ElButton type="primary" :loading="loading" @click="handleRefresh">
          同步数据
        </ElButton>
      </div>
      <div class="flex-1 overflow-hidden px-4">
        <div class="flex h-full flex-col">
          <ElTabs v-model="activeTab">
            <ElTabPane label="问题单数据" name="dashboard" />
            <ElTabPane label="问题单详情" name="detail" />
          </ElTabs>
          <div class="flex-1 overflow-hidden">
            <div v-show="activeTab === 'dashboard'" class="h-full">
              <Grid />
            </div>
            <div v-show="activeTab === 'detail'" class="h-full">
              <DetailGrid />
            </div>
          </div>
        </div>
      </div>
    </div>
  </Page>
</template>
