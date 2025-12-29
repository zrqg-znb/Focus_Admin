<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PerformanceDashboardItem } from '#/api/core/performance';

import { ref } from 'vue';
import { Page } from '@vben/common-ui';
import { ElButton, ElDialog, ElTag } from 'element-plus';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getDashboardDataApi } from '#/api/core/performance';

import { getStatusType, useColumns, useSearchFormSchema } from './data';
import TrendChart from './components/TrendChart.vue';

defineOptions({ name: 'PerformanceDashboard' });

const trendVisible = ref(false);
const currentIndicatorId = ref('');
const currentIndicatorName = ref('');
const currentBaselineValue = ref<number | undefined>(undefined);

const [Grid] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: true,
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            ...formValues,
          };
          return await getDashboardDataApi(params);
        },
      },
    },
    toolbarConfig: {
      custom: true,
      export: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<PerformanceDashboardItem>,
});

function showTrend(row: PerformanceDashboardItem) {
    currentIndicatorId.value = row.id;
    currentIndicatorName.value = row.name;
    currentBaselineValue.value = row.baseline_value;
    trendVisible.value = true;
}
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #fluctuation="{ row }">
        <ElTag :type="getStatusType(row)" v-if="row.fluctuation_value !== null">
           {{ row.fluctuation_value?.toFixed(2) }}
        </ElTag>
      </template>
      
      <template #action="{ row }">
        <ElButton type="primary" size="small" @click="showTrend(row)">趋势</ElButton>
      </template>
    </Grid>

    <ElDialog 
      v-model="trendVisible" 
      :title="`趋势图 - ${currentIndicatorName}`" 
      width="800px" 
      destroy-on-close
    >
        <TrendChart 
          :indicator-id="currentIndicatorId" 
          :baseline-value="currentBaselineValue"
          v-if="trendVisible" 
        />
    </ElDialog>
  </Page>
</template>
