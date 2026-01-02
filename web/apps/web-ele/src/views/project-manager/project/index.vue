<script lang="ts" setup>
import { Page, useVbenDrawer } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getProjectList, deleteProject } from '#/api/project-manager/project';
import { useColumns, useSearchFormSchema } from './data';
import ProjectDrawer from './modules/project-drawer.vue';
import { ElButton, ElMessage, ElMessageBox, ElTag } from 'element-plus';
import { Plus } from '@vben/icons';

defineOptions({ name: 'ProjectList' });

const [Drawer, drawerApi] = useVbenDrawer({
  connectedComponent: ProjectDrawer,
});

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getProjectList({
            page: page.currentPage,
            pageSize: page.pageSize,
            ...formValues,
          });
        },
      },
    },
    toolbarConfig: {
      custom: true,
      export: false,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  },
});

function onCreate() {
  drawerApi.setData({}).open();
}

function onEdit(row: any) {
  drawerApi.setData(row).open();
}

function onDelete(row: any) {
  ElMessageBox.confirm(
    `确认删除项目 "${row.name}" 吗？`,
    '删除确认',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await deleteProject(row.id);
      ElMessage.success('删除成功');
      gridApi.query();
    } catch (error) {
      console.error(error);
    }
  });
}

function refreshGrid() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <Drawer @success="refreshGrid" />
    <Grid>
      <template #table-title>
        <ElButton type="primary" @click="onCreate">
          <Plus class="size-5" />
          新增项目
        </ElButton>
      </template>

      <template #managers="{ row }">
        <div class="flex flex-wrap gap-1">
          <ElTag v-for="m in row.managers" :key="m.id" size="small" type="info">
            {{ m.name }}
          </ElTag>
        </div>
      </template>

      <template #enable_milestone="{ row }">
        <ElTag :type="row.enable_milestone ? 'success' : 'danger'" size="small">
          {{ row.enable_milestone ? '开启' : '关闭' }}
        </ElTag>
      </template>

      <template #enable_iteration="{ row }">
        <ElTag :type="row.enable_iteration ? 'success' : 'danger'" size="small">
          {{ row.enable_iteration ? '开启' : '关闭' }}
        </ElTag>
      </template>

      <template #enable_quality="{ row }">
        <ElTag :type="row.enable_quality ? 'success' : 'danger'" size="small">
          {{ row.enable_quality ? '开启' : '关闭' }}
        </ElTag>
      </template>

      <template #status="{ row }">
        <ElTag :type="row.is_closed ? 'info' : 'success'" effect="plain">
          {{ row.is_closed ? '已结项' : '进行中' }}
        </ElTag>
      </template>

      <template #action="{ row }">
        <ElButton type="primary" link size="small" @click="onEdit(row)">
          编辑
        </ElButton>
        <ElButton type="danger" link size="small" @click="onDelete(row)">
          删除
        </ElButton>
      </template>
    </Grid>
  </Page>
</template>
