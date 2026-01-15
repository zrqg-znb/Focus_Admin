<script setup lang="ts">
import type { VxeGridProps } from '#/adapter/vxe-table';
import type { ProjectConfigOut } from '#/api/integration-report';

import { onMounted } from 'vue';

import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '@vben/plugins/vxe-table';
import { ElMessage, ElSwitch, ElTag } from 'element-plus';

import {
  listIntegrationProjectsApi,
  toggleIntegrationSubscriptionApi,
} from '#/api/integration-report';

defineOptions({ name: 'DailyIntegrationSubscribe' });

const gridOptions: VxeGridProps<ProjectConfigOut> = {
  columns: [
    {
      field: 'subscribed',
      title: '订阅',
      width: 80,
      slots: { default: 'subscribed_default' },
    },
    { field: 'name', title: '配置名称', minWidth: 180 },
    { field: 'project_name', title: '所属项目', minWidth: 150 },
    {
      field: 'managers',
      title: '负责人',
      minWidth: 150,
      formatter: ({ row }) => row.managers || row.project_managers,
    },
    { field: 'latest_date', title: '最新数据', width: 120 },
    {
      field: 'status',
      title: '状态',
      width: 90,
      slots: { default: 'status_default' },
    },
  ],
  pagerConfig: {
    enabled: true,
  },
  height: 'auto',
  keepSource: true,
  proxyConfig: {
    ajax: {
      query: async ({ page }, formValues: any) => {
        const params = {
          page: page.currentPage,
          pageSize: page.pageSize,
          ...formValues,
        };
        const res = await listIntegrationProjectsApi(params);
        const k = formValues?.keyword?.toLowerCase().trim();
        if (!k) return { items: res.items, total: res.count };
        // 前端筛选（保持原有逻辑，但注意这会使得分页不准确）
        const filtered = res.items.filter(
          (i) =>
            i.name.toLowerCase().includes(k) || i.project_name.toLowerCase().includes(k),
        );
        return { items: filtered, total: filtered.length };
      },
    },
  },
  toolbarConfig: {
    refresh: true,
  },
};

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: [
      {
        fieldName: 'keyword',
        label: '搜索',
        component: 'Input',
        componentProps: {
          placeholder: '搜索配置名或项目名',
        },
      },
    ],
    submitOnChange: true,
  },
  gridOptions,
});

onMounted(() => {
  gridApi.reload();
});

async function toggle(row: ProjectConfigOut, val: boolean) {
  try {
    await toggleIntegrationSubscriptionApi(row.id, val);
    row.subscribed = val;
    ElMessage.success(val ? '订阅成功' : '已取消订阅');
  } catch (e) {
    row.subscribed = !val; // Revert
  }
}
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #subscribed_default="{ row }">
        <ElSwitch v-model="row.subscribed" size="small" @change="(v) => toggle(row, !!v)" />
      </template>

      <template #status_default="{ row }">
        <ElTag v-if="row.enabled" type="success" size="small">已启用</ElTag>
        <ElTag v-else type="warning" size="small">未启用</ElTag>
      </template>
    </Grid>
  </Page>
</template>
