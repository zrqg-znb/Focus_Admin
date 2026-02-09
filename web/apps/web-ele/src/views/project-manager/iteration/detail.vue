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
  updateManualMetricApi
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

async function onEditClosed({ row, column }: any) {
  // row here is IterationDetailItem
  // But our edit fields are nested in latest_metric: 'latest_metric.test_automation_rate'
  // VxeTable handles nested fields edit by updating the nested object directly.
  
  if (!row.id || !row.latest_metric) return;
  const iterationId = row.id; // Iteration ID is the row ID for detail view
  
  const fieldPath = column.field; 
  // fieldPath is 'latest_metric.test_automation_rate'
  
  // Extract the actual field name
  let fieldName = '';
  let value = null;
  
  if (fieldPath === 'latest_metric.test_automation_rate') {
    fieldName = 'test_automation_rate';
    value = row.latest_metric.test_automation_rate;
  } else if (fieldPath === 'latest_metric.test_case_execution_rate') {
    fieldName = 'test_case_execution_rate';
    value = row.latest_metric.test_case_execution_rate;
  } else {
    return;
  }
  
  try {
    await updateManualMetricApi(iterationId, {
      [fieldName]: value
    });
    ElMessage.success('更新成功');
  } catch (e) {
    ElMessage.error('更新失败');
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useDetailColumns(),
    height: 'auto',
    pagerConfig: { enabled: true },
    editConfig: {
      trigger: 'click',
      mode: 'cell',
      beforeEditMethod: ({ row }) => {
         if (!row.end_date) return true;
         const today = new Date();
         today.setHours(0,0,0,0);
         const end = new Date(row.end_date);
         if (end < today) {
             ElMessage.warning('该迭代已结束，无法修改指标');
             return false;
         }
         return true;
      }
    },
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
    <Grid @edit-closed="onEditClosed" />
  </Page>
</template>
