<script setup lang="ts">
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { EmailDeliveryRow } from '#/api/integration-report';

import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '@vben/plugins/vxe-table';

import { listEmailDeliveriesApi } from '#/api/integration-report';
import { useSearchFormSchema, useColumns } from './data';

defineOptions({ name: 'EmailDeliveryLogs' });

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(),
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
          return await listEmailDeliveriesApi(params);
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<EmailDeliveryRow>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid />
  </Page>
</template>