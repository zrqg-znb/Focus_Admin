<script setup lang="ts">
import type { MilestoneBoardItem } from '#/api/project-manager/milestone';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { ElButton, ElTooltip } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getMilestoneOverviewApi } from '#/api/project-manager/milestone';
import { useZqTable } from '#/components/zq-table';

import MilestoneGantt from './components/MilestoneGantt.vue';
import RiskLogDrawer from './components/RiskLogDrawer.vue';
import { useSearchFormSchema, useTableColumns } from './data';

defineOptions({ name: 'MilestoneDashboard' });
interface MilestoneQueryParams {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const loading = ref(false);
const milestoneData = ref<MilestoneBoardItem[]>([]);
const riskDrawerRef = ref();
const QG_SORT_FIELDS = new Set(['qg3_date', 'qg4_date', 'qg5_date']);
type QGSortField = 'qg3_date' | 'qg4_date' | 'qg5_date';
const currentSort = ref<null | { field: QGSortField; order: 'asc' }>(null);

function isSortActive(field: string) {
  return (
    currentSort.value?.field === field && currentSort.value.order === 'asc'
  );
}

async function toggleQGSort(field: string) {
  if (!QG_SORT_FIELDS.has(field)) {
    return;
  }

  currentSort.value = isSortActive(field)
    ? null
    : { field: field as QGSortField, order: 'asc' };

  await gridApi.reload();
}

function handleOpenRiskDrawer(row: MilestoneBoardItem) {
  riskDrawerRef.value?.open(row.project_id, row.project_name);
}

function getQGName(field: string) {
  return field.replace('_date', '').toUpperCase();
}
function getColumnField(column: Record<string, any>) {
  return String(column.field || column.prop || column.dataKey || '');
}

function getRisk(row: MilestoneBoardItem, field: string) {
  if (!row.risks) return undefined;
  const qg = getQGName(field);
  return row.risks[qg];
}

function getRiskIcon(row: MilestoneBoardItem, field: string) {
  const risk = getRisk(row, field);
  if (!risk) return '';
  return 'lucide:alert-triangle';
}

function getRiskClass(row: MilestoneBoardItem, field: string) {
  const risk = getRisk(row, field);
  if (!risk) return '';
  return risk.level === 'high' ? 'text-red-500' : 'text-yellow-500';
}

function isNextQG(row: MilestoneBoardItem, column: any) {
  if (!row.next_qg || row.next_qg.length === 0) return false;
  const qg = getQGName(getColumnField(column));
  return row.next_qg.includes(qg);
}
const [Form, formApi] = useVbenForm({
  schema: useSearchFormSchema(),
  showCollapseButton: false,
  layout: 'inline',
  submitOnChange: true,
  handleSubmit: handleSearch,
  submitButtonOptions: {
    content: '搜索',
  },
  resetButtonOptions: {
    content: '重置',
  },
});
const [Grid, gridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    columns: useTableColumns(),
    border: true,
    stripe: true,
    pagerConfig: {
      enabled: true,
      pageSize: 20,
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: MilestoneQueryParams) => {
          loading.value = true;
          try {
            const values = await formApi.getValues();
            const data = await getMilestoneOverviewApi({
              ...values,
              ...form,
              sort_field: currentSort.value?.field,
              sort_order: currentSort.value?.order,
            });

            // Update the Gantt chart data with the full result set (sorted by backend)
            milestoneData.value = data;

            const currentPage = page?.currentPage || 1;
            const pageSize =
              page?.pageSize ?? (data.length > 0 ? data.length : 20);
            const start = (currentPage - 1) * pageSize;
            const end = start + pageSize;
            const pageItems = data.slice(start, end);

            return { items: pageItems, total: data.length };
          } finally {
            loading.value = false;
          }
        },
      },
    },
    toolbarConfig: {
      refresh: true,
      search: true,
      zoom: true,
      custom: true,
    },
  } as ZqTableGridOptions<MilestoneBoardItem>,
});
async function handleSearch() {
  await gridApi.reload();
}
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col gap-4 p-4">
      <div class="bg-card rounded-lg p-4 shadow-sm">
        <Form />
      </div>

      <div
        class="bg-card flex min-h-0 flex-1 flex-col gap-4 rounded-lg p-4 shadow-sm"
        v-loading="loading"
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

        <div class="min-h-0 flex-1 overflow-hidden">
          <Grid class="h-full">
            <template #qg_sort_header="{ column }">
              <div class="flex items-center gap-1">
                <span>{{ column.title }}</span>
                <ElButton
                  link
                  type="primary"
                  class="!p-0"
                  @click.stop="toggleQGSort(getColumnField(column))"
                >
                  <IconifyIcon
                    icon="lucide:arrow-up"
                    :class="
                      isSortActive(getColumnField(column))
                        ? 'text-[var(--el-color-primary)]'
                        : 'text-gray-400'
                    "
                  />
                </ElButton>
              </div>
            </template>
            <template #qg_cell="{ row, column }">
              <div class="flex items-center gap-1">
                <span :style="isNextQG(row, column) ? 'font-weight: 700' : ''">
                  {{ row[getColumnField(column)] }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, getColumnField(column))"
                  :content="getRisk(row, getColumnField(column))?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, getColumnField(column))"
                    :class="getRiskClass(row, getColumnField(column))"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>
            <template #risk_action="{ row }">
              <ElTooltip content="风险跟踪" placement="top">
                <ElButton
                  circle
                  link
                  size="small"
                  type="primary"
                  @click="handleOpenRiskDrawer(row)"
                >
                  <IconifyIcon icon="lucide:list-checks" />
                </ElButton>
              </ElTooltip>
            </template>
          </Grid>
        </div>
      </div>
    </div>

    <RiskLogDrawer ref="riskDrawerRef" />
  </Page>
</template>

<style scoped>
.bg-card {
  background-color: var(--el-bg-color);
}
</style>
