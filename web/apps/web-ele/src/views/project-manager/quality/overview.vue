<script lang="ts" setup>
import { useRouter } from 'vue-router';
import { Page, useVbenDrawer } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getQualityOverview } from '#/api/project-manager/quality';
import { ElButton, ElTag } from 'element-plus';
import { ArrowRight, Plus } from '@vben/icons';
import ModuleDrawer from './modules/module-drawer.vue';

defineOptions({ name: 'QualityOverview' });

const router = useRouter();

const [Drawer, drawerApi] = useVbenDrawer({
  connectedComponent: ModuleDrawer,
});

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: [
      { field: 'project_name', title: '项目名称', minWidth: 150 },
      { field: 'module_count', title: '模块数', width: 100 },
      { field: 'total_loc', title: '总代码行数', width: 120 },
      {
        field: 'avg_duplication_rate',
        title: '平均重复率',
        width: 120,
        formatter: ({ cellValue }) => `${cellValue}%`
      },
      {
        field: 'total_dangerous_func_count',
        title: '危险函数',
        width: 100,
        slots: { default: 'dangerous' }
      },
      {
        field: 'action',
        title: '操作',
        width: 200,
        fixed: 'right',
        slots: { default: 'action' }
      },
    ],
    height: 'auto',
    pagerConfig: { enabled: false },
    proxyConfig: {
      ajax: {
        query: async () => {
          const data = await getQualityOverview();
          return { items: data, total: data.length };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      zoom: true,
    },
  },
});

function onConfigModules(row: any) {
  drawerApi.setData({ project_id: row.project_id }).open();
}

function onDetail(row: any) {
  router.push(`/project-manager/quality/detail/${row.project_id}`);
}

function refreshGrid() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <Drawer @success="refreshGrid" />
    <Grid>
      <template #dangerous="{ row }">
        <span :class="row.total_dangerous_func_count > 0 ? 'text-red-500 font-bold' : ''">
          {{ row.total_dangerous_func_count }}
        </span>
      </template>
      <template #action="{ row }">
        <ElButton link type="primary" @click="onConfigModules(row)">
          <Plus class="size-4 mr-1" /> 配置模块
        </ElButton>
        <ElButton link type="primary" @click="onDetail(row)">
          详情 <ArrowRight class="size-4 ml-1" />
        </ElButton>
      </template>
    </Grid>
  </Page>
</template>
