<script lang="ts" setup>
import { useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { ElButton, ElMessage, ElMessageBox } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteDomain as deleteDomainApi,
  getDomains as getDomainsApi,
} from '#/api/delivery-matrix';

import { domainColumns } from '../data';
import DomainForm from './components/DomainForm.vue';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: DomainForm,
});

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: domainColumns,
    proxyConfig: {
      ajax: {
        query: async () => {
          return await getDomainsApi();
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
  // Pass interface_people_ids which are needed for the form select
  const data = { ...row, interface_people_ids: row.interface_people };
  formDrawerApi.setData(data).open();
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除领域 ${row.name}?`, '提示', {
      type: 'warning',
    });
    await deleteDomainApi(row.id);
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
          <Plus class="mr-1 size-4" /> 新增领域
        </ElButton>
      </template>
      <template #action="{ row }">
        <ElButton link type="primary" @click="onEdit(row)">编辑</ElButton>
        <ElButton link type="danger" @click="onDelete(row)">删除</ElButton>
      </template>
    </Grid>
  </div>
</template>
