<script lang="ts" setup>
import { useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { ElButton, ElMessage, ElMessageBox } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteComponent, getComponents } from '#/api/delivery-matrix';

import { componentColumns } from '../data';
import ComponentForm from './components/ComponentForm.vue';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: ComponentForm,
});

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: componentColumns,
    proxyConfig: {
      ajax: {
        query: async () => {
          return await getComponents();
        },
      },
    },
    toolbarConfig: { search: false, refresh: { code: 'query' } },
  },
});

function onCreate() {
  formDrawerApi.setData({}).open();
}

function onEdit(row: any) {
  const data = {
    ...row,
    manager_ids: row.managers,
    linked_project_id: row.linked_project,
  };
  formDrawerApi.setData(data).open();
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除组件 ${row.name}?`, '提示', {
      type: 'warning',
    });
    await deleteComponent(row.id);
    ElMessage.success('删除成功');
    gridApi.query();
  } catch {
    // cancelled
  }
}
</script>

<template>
  <div class="h-full">
    <FormDrawer @success="gridApi.query()" />
    <Grid>
      <template #toolbar-tools>
        <ElButton type="primary" @click="onCreate">
          <Plus class="mr-1 size-4" /> 新增组件
        </ElButton>
      </template>
      <template #action="{ row }">
        <ElButton link type="primary" @click="onEdit(row)">编辑</ElButton>
        <ElButton link type="danger" @click="onDelete(row)">删除</ElButton>
      </template>
    </Grid>
  </div>
</template>
