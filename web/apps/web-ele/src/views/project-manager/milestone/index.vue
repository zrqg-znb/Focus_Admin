<script setup lang="ts">
import type { MilestoneBoardItem } from '#/api/project-manager/milestone';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { ElButton, ElTooltip } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { listHardwareConfigOptionsApi } from '#/api/project-manager/hardware';
import { getMilestoneOverviewApi } from '#/api/project-manager/milestone';
import { useZqTable } from '#/components/zq-table';

import MilestoneGantt from './components/MilestoneGantt.vue';
import RiskLogDrawer from './components/RiskLogDrawer.vue';
import { useSearchFormSchema, useTableColumns } from './data';

import './theme.css';

defineOptions({ name: 'MilestoneDashboard' });
interface MilestoneQueryParams {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

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

function isNextQG(row: MilestoneBoardItem, column: string) {
  if (!row.next_qg || row.next_qg.length === 0) return false;
  const qg = getQGName(String(column));
  return row.next_qg.includes(qg);
}
function getQGDisplayValue(row: MilestoneBoardItem, field: string) {
  const value = row[field as keyof MilestoneBoardItem];
  return value ? String(value) : '-';
}
function formatManagerNames(row: MilestoneBoardItem) {
  if (!Array.isArray(row.manager_names) || row.manager_names.length === 0) {
    return '-';
  }
  return row.manager_names.join(', ');
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

async function loadSupportingPlatformOptions() {
  const options = await listHardwareConfigOptionsApi();
  formApi.updateSchema([
    {
      fieldName: 'supporting_platform_filters',
      componentProps: {
        options: [
          {
            label: 'CDC 平台版本',
            value: 'cdc',
            children: (options.cdc_platforms || []).map((item) => ({
              label: item.name,
              value: item.id,
            })),
          },
          {
            label: '智慧屏版本',
            value: 'smart_screen',
            children: (options.smart_screen_versions || []).map((item) => ({
              label: item.name,
              value: item.id,
            })),
          },
          {
            label: 'IDVP 软件平台版本',
            value: 'idvp',
            children: (options.idvp_platforms || []).map((item) => ({
              label: item.name,
              value: item.id,
            })),
          },
        ],
      },
    },
  ]);
}

onMounted(() => {
  loadSupportingPlatformOptions();
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
          const values = await formApi.getValues();
          const data = await getMilestoneOverviewApi({
            ...values,
            ...form,
            sort_field: currentSort.value?.field,
            sort_order: currentSort.value?.order,
          });

          const clonedData = data.map((item) => ({ ...item }));
          milestoneData.value = clonedData;

          const currentPage = page?.currentPage || 1;
          const pageSize =
            page?.pageSize ?? (clonedData.length > 0 ? clonedData.length : 20);
          const start = (currentPage - 1) * pageSize;
          const end = start + pageSize;

          return {
            items: clonedData.slice(start, end),
            total: clonedData.length,
          };
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
const pageLoading = computed(() => gridApi.loading.value);
async function handleSearch() {
  await gridApi.reload();
}
</script>

<template>
  <Page auto-content-height>
    <div class="milestone-board-theme flex h-full min-h-0 flex-col gap-4 p-4">
      <div class="bg-card rounded-lg p-4 shadow-sm">
        <Form />
      </div>

      <div
        class="bg-card flex min-h-0 flex-1 flex-col gap-4 rounded-lg p-4 shadow-sm"
        v-loading="pageLoading"
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
            <template #header-qg3_date>
              <div class="flex items-center gap-1">
                <span>QG3</span>
                <ElButton
                  link
                  type="primary"
                  class="!p-0"
                  @click.stop="toggleQGSort('qg3_date')"
                >
                  <IconifyIcon
                    icon="lucide:arrow-up"
                    :class="
                      isSortActive('qg3_date')
                        ? 'text-[var(--el-color-primary)]'
                        : 'text-gray-400'
                    "
                  />
                </ElButton>
              </div>
            </template>
            <template #header-qg4_date>
              <div class="flex items-center gap-1">
                <span>QG4</span>
                <ElButton
                  link
                  type="primary"
                  class="!p-0"
                  @click.stop="toggleQGSort('qg4_date')"
                >
                  <IconifyIcon
                    icon="lucide:arrow-up"
                    :class="
                      isSortActive('qg4_date')
                        ? 'text-[var(--el-color-primary)]'
                        : 'text-gray-400'
                    "
                  />
                </ElButton>
              </div>
            </template>
            <template #header-qg5_date>
              <div class="flex items-center gap-1">
                <span>QG5</span>
                <ElButton
                  link
                  type="primary"
                  class="!p-0"
                  @click.stop="toggleQGSort('qg5_date')"
                >
                  <IconifyIcon
                    icon="lucide:arrow-up"
                    :class="
                      isSortActive('qg5_date')
                        ? 'text-[var(--el-color-primary)]'
                        : 'text-gray-400'
                    "
                  />
                </ElButton>
              </div>
            </template>

            <template #cell-manager_names="{ row }">
              {{ formatManagerNames(row) }}
            </template>

            <template #cell-qg1_date="{ row }">
              <div class="flex items-center gap-1">
                <span
                  :style="isNextQG(row, 'qg1_date') ? 'font-weight: 700' : ''"
                >
                  {{ getQGDisplayValue(row, 'qg1_date') }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, 'qg1_date')"
                  :content="getRisk(row, 'qg1_date')?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, 'qg1_date')"
                    :class="getRiskClass(row, 'qg1_date')"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>
            <template #cell-qg2_date="{ row }">
              <div class="flex items-center gap-1">
                <span
                  :style="isNextQG(row, 'qg2_date') ? 'font-weight: 700' : ''"
                >
                  {{ getQGDisplayValue(row, 'qg2_date') }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, 'qg2_date')"
                  :content="getRisk(row, 'qg2_date')?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, 'qg2_date')"
                    :class="getRiskClass(row, 'qg2_date')"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>
            <template #cell-qg3_date="{ row }">
              <div class="flex items-center gap-1">
                <span
                  :style="isNextQG(row, 'qg3_date') ? 'font-weight: 700' : ''"
                >
                  {{ getQGDisplayValue(row, 'qg3_date') }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, 'qg3_date')"
                  :content="getRisk(row, 'qg3_date')?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, 'qg3_date')"
                    :class="getRiskClass(row, 'qg3_date')"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>
            <template #cell-qg4_date="{ row }">
              <div class="flex items-center gap-1">
                <span
                  :style="isNextQG(row, 'qg4_date') ? 'font-weight: 700' : ''"
                >
                  {{ getQGDisplayValue(row, 'qg4_date') }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, 'qg4_date')"
                  :content="getRisk(row, 'qg4_date')?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, 'qg4_date')"
                    :class="getRiskClass(row, 'qg4_date')"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>
            <template #cell-qg5_date="{ row }">
              <div class="flex items-center gap-1">
                <span
                  :style="isNextQG(row, 'qg5_date') ? 'font-weight: 700' : ''"
                >
                  {{ getQGDisplayValue(row, 'qg5_date') }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, 'qg5_date')"
                  :content="getRisk(row, 'qg5_date')?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, 'qg5_date')"
                    :class="getRiskClass(row, 'qg5_date')"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>
            <template #cell-qg6_date="{ row }">
              <div class="flex items-center gap-1">
                <span
                  :style="isNextQG(row, 'qg6_date') ? 'font-weight: 700' : ''"
                >
                  {{ getQGDisplayValue(row, 'qg6_date') }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, 'qg6_date')"
                  :content="getRisk(row, 'qg6_date')?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, 'qg6_date')"
                    :class="getRiskClass(row, 'qg6_date')"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>
            <template #cell-qg7_date="{ row }">
              <div class="flex items-center gap-1">
                <span
                  :style="isNextQG(row, 'qg7_date') ? 'font-weight: 700' : ''"
                >
                  {{ getQGDisplayValue(row, 'qg7_date') }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, 'qg7_date')"
                  :content="getRisk(row, 'qg7_date')?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, 'qg7_date')"
                    :class="getRiskClass(row, 'qg7_date')"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>
            <template #cell-qg8_date="{ row }">
              <div class="flex items-center gap-1">
                <span
                  :style="isNextQG(row, 'qg8_date') ? 'font-weight: 700' : ''"
                >
                  {{ getQGDisplayValue(row, 'qg8_date') }}
                </span>
                <ElTooltip
                  v-if="getRisk(row, 'qg8_date')"
                  :content="getRisk(row, 'qg8_date')?.description"
                  placement="top"
                >
                  <IconifyIcon
                    :icon="getRiskIcon(row, 'qg8_date')"
                    :class="getRiskClass(row, 'qg8_date')"
                    class="cursor-help"
                  />
                </ElTooltip>
              </div>
            </template>

            <template #cell-risk_action="{ row }">
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
