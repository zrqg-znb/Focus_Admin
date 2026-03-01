<script lang="ts" setup>
import type { DtsTeamTableRow } from './data';

import type { DtsDefect, DtsTeam } from '#/api/project-manager/dts';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElMessage, ElTabPane, ElTabs } from 'element-plus';

import {
  getDtsDashboardApi,
  getDtsDetailsApi,
  syncDtsApi,
} from '#/api/project-manager/dts';
import { getProjectApi } from '#/api/project-manager/project';
import { useZqTable } from '#/components/zq-table';

import { useDefectListColumns, useDetailColumns } from './data';

defineOptions({ name: 'DtsDetail' });

const route = useRoute();
const router = useRouter();
const projectId = route.params.id as string;
const projectInfo = ref<any>({});
const loading = ref(false);
const activeTab = ref('dashboard');

function mapTeamRows(items: DtsTeam[]): DtsTeamTableRow[] {
  return items.map((item) => {
    const latest = item.latest_data;
    return {
      ...item,
      di: latest?.di ?? null,
      target_di: latest?.target_di ?? null,
      today_in_di: latest?.today_in_di ?? null,
      today_out_di: latest?.today_out_di ?? null,
      solve_rate: latest?.solve_rate ?? null,
      critical_solve_rate: latest?.critical_solve_rate ?? null,
      fatal_num: latest?.fatal_num ?? null,
      major_num: latest?.major_num ?? null,
      minor_num: latest?.minor_num ?? null,
      suggestion_num: latest?.suggestion_num ?? null,
      children: mapTeamRows(item.children || []),
    };
  });
}

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
      gridApi.reload();
    } else {
      detailGridApi.reload();
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

const [Grid, gridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    columns: useDetailColumns(),
    border: true,
    stripe: true,
    rowKey: 'id',
    treeProps: { children: 'children' },
    defaultExpandAll: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async () => {
          const data = await getDtsDashboardApi(projectId);
          const treeRows = mapTeamRows(data.root_teams || []);
          return { items: treeRows, total: treeRows.length };
        },
      },
    },
    pagerConfig: { enabled: false },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  } as ZqTableGridOptions<DtsTeamTableRow>,
});

const [DetailGrid, detailGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    columns: useDefectListColumns(),
    border: true,
    stripe: true,
    pagerConfig: { enabled: true, pageSize: 20 },
    proxyConfig: {
      autoLoad: false,
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
      refresh: true,
      zoom: true,
    },
  } as ZqTableGridOptions<DtsDefect>,
});

onMounted(() => {
  fetchProjectInfo();
  gridApi.reload();
});

watch(
  () => activeTab.value,
  async (tab) => {
    await nextTick();
    if (tab === 'dashboard') {
      gridApi.reload();
    } else {
      detailGridApi.reload();
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
