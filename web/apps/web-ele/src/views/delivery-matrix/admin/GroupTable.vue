<script lang="ts" setup>
import { useVbenDrawer } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getGroups, deleteGroup } from '#/api/delivery-matrix';
import { groupColumns } from '../data';
import GroupForm from './components/GroupForm.vue';
import { ElButton, ElMessage, ElMessageBox } from 'element-plus';
import { Plus } from '@vben/icons';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: GroupForm,
});

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: groupColumns,
    proxyConfig: {
      ajax: {
        query: async () => {
          return await getGroups();
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
  const data = { ...row, manager_ids: row.managers };
  formDrawerApi.setData(data).open();
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除项目群 ${row.name}?`, '提示', { type: 'warning' });
    await deleteGroup(row.id);
    ElMessage.success('删除成功');
    gridApi.query();
  } catch (e) {
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
          <Plus class="mr-1 size-4" /> 新增项目群
        </ElButton>
      </template>
      <template #action="{ row }">
        <ElButton link type="primary" @click="onEdit(row)">编辑</ElButton>
        <ElButton link type="danger" @click="onDelete(row)">删除</ElButton>
      </template>
    </Grid>
  </div>
</template>
