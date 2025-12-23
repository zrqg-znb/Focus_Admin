<script lang="ts" setup>
import type { OnActionClickParams, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { OperationLog } from '#/api/core/operation-log';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { ElButton, ElMessage, ElMessageBox } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { batchDeleteOperationLogApi, deleteOperationLogApi, getOperationLogDetailApi, getOperationLogListApi } from '#/api/core/operation-log';

import { useColumns, useSearchFormSchema } from './data';
import DetailDrawer from './modules/detail-drawer.vue';

defineOptions({ name: 'SystemOperationLog' });

const selectedRows = ref<OperationLog[]>([]);
const detailDrawerRef = ref();
const currentLog = ref<OperationLog>();

async function onDetail(row: OperationLog) {
  try {
    const log = await getOperationLogDetailApi(row.id);
    currentLog.value = log;
    detailDrawerRef.value?.open();
  } catch (error) {
    ElMessage.error($t('operationLog.getDetailError'));
    console.error($t('operationLog.getDetailError'), error);
  }
}

function onDelete(row: OperationLog) {
  ElMessageBox.confirm(
    $t('operationLog.deleteConfirm', [row.request_username]),
    $t('common.delete'),
    { confirmButtonText: $t('common.confirm'), cancelButtonText: $t('common.cancel'), type: 'warning' },
  )
    .then(async () => {
      try {
        await deleteOperationLogApi(row.id);
        ElMessage.success($t('operationLog.deleteSuccess'));
        refreshGrid();
      } catch {
        ElMessage.error($t('operationLog.deleteError'));
      }
    })
    .catch(() => {});
}

function onBatchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning($t('operationLog.selectLogsToDelete'));
    return;
  }
  const names = selectedRows.value.map((row) => row.request_username).join('、');
  const confirmMessage = $t('operationLog.batchDeleteConfirm', [selectedRows.value.length, names]);
  ElMessageBox.confirm(confirmMessage, $t('operationLog.batchDeleteTitle'), {
    confirmButtonText: $t('common.confirm'),
    cancelButtonText: $t('common.cancel'),
    type: 'warning',
  })
    .then(async () => {
      try {
        const ids = selectedRows.value.map((row) => row.id);
        await batchDeleteOperationLogApi(ids);
        ElMessage.success($t('operationLog.deleteSuccess'));
        selectedRows.value = [];
        refreshGrid();
      } catch {
        ElMessage.error($t('operationLog.deleteError'));
      }
    })
    .catch(() => {});
}

function onActionClick({ code, row }: OnActionClickParams<OperationLog>) {
  switch (code) {
    case 'delete':
      onDelete(row);
      break;
    case 'detail':
      onDetail(row);
      break;
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: { schema: useSearchFormSchema(), submitOnChange: true },
  gridEvents: {
    checkboxAll: ({ records }: { records: OperationLog[] }) => { selectedRows.value = records },
    checkboxChange: ({ records }: { records: OperationLog[] }) => { selectedRows.value = records },
  },
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    keepSource: true,
    proxyConfig: { ajax: { query: async ({ page }, formValues) => {
      const params = { page: page.currentPage, pageSize: page.pageSize, ...formValues };
      return await getOperationLogListApi(params);
    } } },
    checkboxConfig: { reserve: true, trigger: 'default' },
    toolbarConfig: { custom: true, export: false, refresh: { code: 'query' }, search: true, zoom: true },
  } as VxeTableGridOptions<OperationLog>,
});

function refreshGrid() { gridApi.query() }
</script>

<template>
  <Page auto-content-height>
    <DetailDrawer ref="detailDrawerRef" :log="currentLog" />
    <Grid>
      <template #table-title>
        <ElButton type="danger" plain @click="onBatchDelete">
          {{ $t('operationLog.batchDelete') }}
          {{ selectedRows.length > 0 ? `(${selectedRows.length})` : '' }}
        </ElButton>
      </template>
    </Grid>
  </Page>
  </template>

