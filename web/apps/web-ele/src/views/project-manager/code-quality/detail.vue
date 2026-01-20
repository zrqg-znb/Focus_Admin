<script lang="ts" setup>
import type { VxeTableDefines, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ModuleQualityDetail } from '#/api/project-manager/code_quality';

import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  getProjectQualityDetailsApi,
  refreshProjectQualityApi,
} from '#/api/project-manager/code_quality';
import { getProjectApi } from '#/api/project-manager/project';

import { useDetailColumns } from './data';

defineOptions({ name: 'CodeQualityDetail' });

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
    await refreshProjectQualityApi(projectId);
    ElMessage.success('刷新任务已提交，请稍后查看同步日志或刷新页面');
    // gridApi.reload(); // 不再立即刷新表格，因为是异步的
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleBack() {
  router.back();
}

// Span Method Logic
const spanMethod: VxeTableDefines.SpanMethod<ModuleQualityDetail> = ({
  row,
  rowIndex,
  column,
  visibleData,
}) => {
  if (column.field === 'oem_name') {
    const prevRow = visibleData[rowIndex - 1];
    if (prevRow && prevRow.oem_name === row.oem_name) {
      return { rowspan: 0, colspan: 0 };
    } else {
      let rowspan = 1;
      for (let i = rowIndex + 1; i < visibleData.length; i++) {
        if (visibleData[i].oem_name === row.oem_name) {
          rowspan++;
        } else {
          break;
        }
      }
      return { rowspan, colspan: 1 };
    }
  }
  return { rowspan: 1, colspan: 1 };
};

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useDetailColumns(),
    height: 'auto',
    pagerConfig: { enabled: true },
    spanMethod,
    proxyConfig: {
      ajax: {
        query: async ({ page }) => {
          const data = await getProjectQualityDetailsApi(projectId);
          // Sort by oem_name to ensure merging works
          data.sort((a, b) => a.oem_name.localeCompare(b.oem_name));
          
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
  } as VxeTableGridOptions<ModuleQualityDetail>,
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
        <div class="text-lg font-bold">{{ projectInfo.name }} - 代码质量详情</div>
      </div>
      <ElButton type="primary" :loading="loading" @click="handleRefresh">
        刷新数据
      </ElButton>
    </div>
    <Grid />
  </Page>
</template>
