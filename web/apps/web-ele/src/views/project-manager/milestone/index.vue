<template>
  <Page auto-content-height>
    <div class="flex h-full flex-col gap-4 p-4">
      <div class="bg-card rounded-lg p-4 shadow-sm">
        <Form />
      </div>

      <div
        class="bg-card flex flex-col gap-4 rounded-lg p-4 shadow-sm"
        v-loading="loading"
        style="min-height: 400px"
      >
        <div class="h-80 w-full shrink-0">
          <MilestoneGantt
            v-if="milestoneData.length > 0"
            :data="milestoneData"
          />
          <div
            v-else
            class="flex h-full items-center justify-center text-gray-400"
          >
            暂无数据
          </div>
        </div>

        <div class="flex-1 overflow-hidden">
          <Grid>
            <template #risk_action="{ row }">
              <ElButton link type="primary" @click="handleOpenRiskDrawer(row)">
                跟踪
              </ElButton>
            </template>
          </Grid>
        </div>
      </div>
    </div>

    <RiskLogDrawer ref="riskDrawerRef" />
  </Page>
</template>

<script setup lang="ts">
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { MilestoneBoardItem } from '#/api/project-manager/milestone';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { ElButton } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getMilestoneOverviewApi } from '#/api/project-manager/milestone';

import MilestoneGantt from './components/MilestoneGantt.vue';
import RiskLogDrawer from './components/RiskLogDrawer.vue';
import { useSearchFormSchema, useTableColumns } from './data';

defineOptions({ name: 'MilestoneDashboard' });

const loading = ref(false);
const milestoneData = ref<MilestoneBoardItem[]>([]);
const riskDrawerRef = ref();

function handleOpenRiskDrawer(row: MilestoneBoardItem) {
  riskDrawerRef.value?.open(row.project_id, row.project_name);
}

const [Form, formApi] = useVbenForm({
  schema: useSearchFormSchema(),
  handleSubmit: handleSearch,
  showCollapseButton: false,
  layout: 'inline',
  submitOnChange: true,
  submitButtonOptions: {
    content: '搜索',
  },
  resetButtonOptions: {
    content: '重置',
  },
});

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useTableColumns(),
    height: 'auto',
    pagerConfig: {
      enabled: true,
    },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          loading.value = true;
          try {
            // Merge form values from the separate form instance
            const values = await formApi.getValues();
            const data = await getMilestoneOverviewApi({
              ...values,
              ...formValues,
            });

            // Update the Gantt chart data with the full result set
            milestoneData.value = data;

            // Perform frontend pagination for the table
            const start = (page.currentPage - 1) * page.pageSize;
            const end = start + page.pageSize;
            const pageItems = data.slice(start, end);

            return { items: pageItems, total: data.length };
          } finally {
            loading.value = false;
          }
        },
      },
    },
    toolbarConfig: {
      refresh: { code: 'query' },
      zoom: true,
      custom: true,
    },
  } as VxeTableGridOptions<MilestoneBoardItem>,
});

async function handleSearch() {
  gridApi.reload();
}

onMounted(() => {
  // Initial load
  // gridApi.reload() is called automatically if autoLoad is true (default in adapter)
  // But we want to ensure it uses the form values if any defaults exist
});
</script>

<style scoped>
.bg-card {
  background-color: var(--el-bg-color);
}
</style>
