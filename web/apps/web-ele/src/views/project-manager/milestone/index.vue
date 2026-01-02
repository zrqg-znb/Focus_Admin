<script lang="ts" setup>
import { Page, useVbenModal } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getMilestoneOverview } from '#/api/project-manager/milestone';
import { useColumns, useSearchFormSchema } from './data';
import MilestoneModal from './modules/milestone-modal.vue';
import { ElButton } from 'element-plus';
import { Edit } from '@vben/icons';

defineOptions({ name: 'MilestoneBoard' });

const [Modal, modalApi] = useVbenModal({
  connectedComponent: MilestoneModal,
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
          // 里程碑看板通常数据量不大，且后端接口是 Overview，可能没有分页
          // 如果需要分页，需调整 API 接口
          const data = await getMilestoneOverview(formValues);
          return { items: data, total: data.length };
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

function onEdit(row: any) {
  modalApi.setData(row).open();
}

function refreshGrid() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <Modal @success="refreshGrid" />
    <Grid>
      <template #action="{ row }">
        <ElButton type="primary" link size="small" @click="onEdit(row)">
          <Edit class="mr-1 size-4" />
          配置
        </ElButton>
      </template>
    </Grid>
  </Page>
</template>
