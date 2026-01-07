<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { ProjectOut } from '#/api/project-manager/project';

import { ref } from 'vue';

import { Page, useVbenDrawer } from '@vben/common-ui';

import { ElButton, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteProjectApi,
  listProjectsApi,
} from '#/api/project-manager/project';

import { useColumns, useSearchFormSchema } from './data';
import Form from './modules/form.vue';
import NewProjectDialog from './modules/NewProjectDialog.vue';

defineOptions({ name: 'ProjectList' });

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const createDialogVisible = ref(false);

function onActionClick({ code, row }: OnActionClickParams<ProjectOut>) {
  if (code === 'edit') {
    formDrawerApi.setData(row).open();
    return;
  }
  if (code === 'delete') {
    deleteProjectApi(row.id).then(() => {
      ElMessage.success('删除成功');
      refreshGrid();
    });
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            ...formValues,
          };
          return await listProjectsApi(params);
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<ProjectOut>,
});

function refreshGrid() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="refreshGrid" />

    <Grid>
      <template #table-title>
        <ElButton type="primary" @click="createDialogVisible = true">
          新增项目
        </ElButton>
      </template>
    </Grid>

    <NewProjectDialog v-model="createDialogVisible" @created="refreshGrid" />
  </Page>
</template>
