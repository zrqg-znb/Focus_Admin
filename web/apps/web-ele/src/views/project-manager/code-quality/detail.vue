<script lang="ts" setup>
import type { CodeQualityTreeRow, QualityMetricKey } from './data';

import type {
  ModuleQualityDetail,
  QualityMetricValue,
  QualityTreeNode,
} from '#/api/project-manager/code_quality';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import dayjs from 'dayjs';
import { ElButton, ElDatePicker, ElDialog, ElMessage } from 'element-plus';

import {
  getProjectQualityDetailsApi,
  getProjectQualityRecordDatesApi,
  refreshProjectQualityApi,
  updateNodeOwnerApi,
} from '#/api/project-manager/code_quality';
import { getProjectApi } from '#/api/project-manager/project';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';
import { useZqTable } from '#/components/zq-table';

import CleanCodeRateCell from './components/CleanCodeRateCell.vue';
import {
  createThresholdCellClassName,
  getDetailColumns,
  getMetricFieldName,
  QUALITY_METRIC_COLUMNS,
  QUALITY_THRESHOLD_CONFIG,
} from './data';

defineOptions({ name: 'CodeQualityDetail' });

const route = useRoute();
const router = useRouter();
const projectId = route.params.id as string;

const projectInfo = ref<any>({});
const selectedDate = ref('');
const availableDates = ref<string[]>([]);
const loading = ref(false);
const detailsLoading = ref(true);
const ownerDialogVisible = ref(false);
const ownerSaving = ref(false);
const ownerEditIds = ref<string[]>([]);
const ownerEditRow = ref<CodeQualityTreeRow | null>(null);
const metricKeys = new Set<string>(
  QUALITY_METRIC_COLUMNS.map((item) => item.key),
);

function toCompactDate(isoDate: string) {
  return String(isoDate || '').replaceAll('-', '');
}

function toIsoDate(compactDate: string) {
  const text = String(compactDate || '').trim();
  if (!/^\d{8}$/.test(text)) return '';
  return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
}

function hasAvailableDate(isoDate: string) {
  return availableDates.value.includes(isoDate);
}

function isDateDisabled(value: Date) {
  const isoDate = dayjs(value).format('YYYY-MM-DD');
  return !hasAvailableDate(isoDate);
}

function getDateCellStatus(cell: any) {
  if (!cell || cell.type !== 'normal' || !cell.dayjs) {
    return 'other';
  }
  const isoDate = cell.dayjs.format('YYYY-MM-DD');
  return hasAvailableDate(isoDate) ? 'available' : 'empty';
}

function toMetricMaps(metricValues: QualityMetricValue[] = []) {
  const displayMap: Record<string, string> = {};
  const numberMap: Record<string, null | number> = {};
  const warningMap: Record<string, boolean> = {};

  for (const metric of metricValues) {
    const metricKey = String(metric.key || '');
    if (!metricKey || !metricKeys.has(metricKey)) {
      continue;
    }
    const field = getMetricFieldName(metricKey as QualityMetricKey);
    displayMap[field] = String(metric.display || '-');
    numberMap[metricKey] =
      metric.num === null || metric.num === undefined
        ? null
        : Number(metric.num);
    warningMap[metricKey] = Boolean(metric.is_warning);
  }
  return { displayMap, numberMap, warningMap };
}

function countDescendantNodes(nodes: QualityTreeNode[] = []): number {
  let total = 0;
  for (const node of nodes) {
    total += 1;
    total += countDescendantNodes(node.children || []);
  }
  return total;
}

function countDescendantWarnings(nodes: QualityTreeNode[] = []): number {
  let total = 0;
  for (const node of nodes) {
    if (Number(node.warning_count || 0) > 0) {
      total += 1;
    }
    total += countDescendantWarnings(node.children || []);
  }
  return total;
}

function mapNodeRows(
  nodes: QualityTreeNode[] = [],
  moduleId: string,
  fallbackOwnerIds: string[] = [],
  fallbackOwnerNamesText = '-',
): CodeQualityTreeRow[] {
  return nodes.map((node) => {
    const { displayMap, numberMap, warningMap } = toMetricMaps(
      node.metric_values || [],
    );
    const nodeOwnerIds =
      node.owner_ids && node.owner_ids.length > 0
        ? node.owner_ids
        : fallbackOwnerIds;
    const nodeOwnerNames =
      node.owner_names && node.owner_names.length > 0
        ? node.owner_names.join('、')
        : fallbackOwnerNamesText;
    const children = mapNodeRows(
      node.children || [],
      moduleId,
      fallbackOwnerIds,
      fallbackOwnerNamesText,
    );
    const row: CodeQualityTreeRow = {
      id: `node-${node.id}`,
      module_id: moduleId,
      node_key: node.node_key || '',
      owner_editable: true,
      owner_ids: [...nodeOwnerIds],
      row_type: 'node',
      node_name: node.version_name || '-',
      oem_name: '-',
      module: '-',
      owner_names_text: nodeOwnerNames || '-',
      record_date: '-',
      clean_code_rate: Number(node.clean_code_rate || 0),
      warning_count: Number(node.warning_count || 0),
      warning_node_count: countDescendantWarnings(node.children || []),
      total_node_count: countDescendantNodes(node.children || []),
      unachieved_clean_code_text:
        node.unachieved_clean_code && node.unachieved_clean_code.length > 0
          ? node.unachieved_clean_code.join('；')
          : '-',
      warning_metrics_text:
        node.warning_metrics && node.warning_metrics.length > 0
          ? node.warning_metrics.join('、')
          : '-',
      metric_warning_map: warningMap,
      metric_num_map: numberMap,
      children,
    };
    for (const metric of QUALITY_METRIC_COLUMNS) {
      const field = getMetricFieldName(metric.key as QualityMetricKey);
      row[field] = displayMap[field] || '-';
    }
    return row;
  });
}

function normalizeTreeRows(details: ModuleQualityDetail[] = []) {
  return details
    .map((item) => {
      const { displayMap, numberMap, warningMap } = toMetricMaps(
        item.metric_values || [],
      );
      const moduleOwnerIds = item.owner_ids || [];
      const moduleOwnerNamesText =
        item.owner_names && item.owner_names.length > 0
          ? item.owner_names.join('、')
          : '-';
      let nodeChildrenSource = item.nodes || [];
      if (
        nodeChildrenSource.length === 1 &&
        item.root_version_name &&
        nodeChildrenSource[0]?.version_name === item.root_version_name
      ) {
        nodeChildrenSource = nodeChildrenSource[0]?.children || [];
      }

      const row: CodeQualityTreeRow = {
        id: `module-${item.id}`,
        module_id: item.id,
        node_key: item.root_version_name || item.module || '',
        owner_editable: false,
        owner_ids: [...moduleOwnerIds],
        row_type: 'module',
        node_name: item.root_version_name || item.module || '-',
        oem_name: item.oem_name || '-',
        module: item.module || '-',
        owner_names_text: moduleOwnerNamesText,
        record_date: item.record_date || '-',
        clean_code_rate: Number(item.clean_code_rate || 0),
        warning_count: Number(item.warning_count || 0),
        warning_node_count: Number(item.warning_node_count || 0),
        total_node_count: Number(item.total_node_count || 0),
        unachieved_clean_code_text:
          item.unachieved_clean_code && item.unachieved_clean_code.length > 0
            ? item.unachieved_clean_code.join('；')
            : '-',
        warning_metrics_text:
          item.warning_metrics && item.warning_metrics.length > 0
            ? item.warning_metrics.join('、')
            : '-',
        metric_warning_map: warningMap,
        metric_num_map: numberMap,
        children: mapNodeRows(
          nodeChildrenSource,
          item.id,
          moduleOwnerIds,
          moduleOwnerNamesText,
        ),
      };
      for (const metric of QUALITY_METRIC_COLUMNS) {
        const field = getMetricFieldName(metric.key as QualityMetricKey);
        row[field] = displayMap[field] || '-';
      }
      return row;
    })
    .sort((first, second) => {
      const oemCompare = first.oem_name.localeCompare(second.oem_name, 'zh-CN');
      if (oemCompare !== 0) return oemCompare;
      return first.module.localeCompare(second.module, 'zh-CN');
    });
}

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    border: true,
    stripe: true,
    columns: getDetailColumns(),
    cellClassName: createThresholdCellClassName(() => QUALITY_THRESHOLD_CONFIG),
    rowKey: 'id',
    defaultExpandAll: true,
    treeProps: {
      children: 'children',
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async () => {
          const rows = await fetchDetails(selectedDate.value);
          return {
            items: rows,
            total: rows.length,
          };
        },
      },
    },
    pagerConfig: { enabled: false },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
  } as ZqTableGridOptions<CodeQualityTreeRow>,
});

async function loadAvailableDates(showMessage = true) {
  try {
    const compactDates = await getProjectQualityRecordDatesApi(projectId);
    const normalizedDates = [
      ...new Set(
        (compactDates || []).map((item) => toIsoDate(item)).filter(Boolean),
      ),
    ].sort((first, second) => second.localeCompare(first));

    availableDates.value = normalizedDates;

    if (normalizedDates.length === 0) {
      selectedDate.value = '';
      if (showMessage) {
        ElMessage.warning('数据湖暂无代码质量数据，请稍后重试');
      }
      return;
    }

    if (selectedDate.value && !hasAvailableDate(selectedDate.value)) {
      selectedDate.value = '';
    }
  } catch (error) {
    console.error(error);
    ElMessage.error('获取可用日期失败');
  }
}

async function handleDateFilterChange(value?: string) {
  const nextDate = String(value || selectedDate.value || '').trim();
  if (!nextDate) {
    selectedDate.value = '';
    await gridApi.reload();
    return;
  }
  if (!hasAvailableDate(nextDate)) {
    ElMessage.warning(
      `数据湖 ${toCompactDate(nextDate)} 没有数据，请选择可用日期`,
    );
    selectedDate.value = '';
    return;
  }
  await gridApi.reload();
}

async function fetchProjectInfo() {
  try {
    projectInfo.value = await getProjectApi(projectId);
  } catch (error) {
    console.error(error);
  }
}

async function fetchDetails(recordDate = '') {
  try {
    detailsLoading.value = true;
    const queryDate = String(recordDate || '').trim();
    const details = await getProjectQualityDetailsApi(projectId, {
      record_date: queryDate ? toCompactDate(queryDate) : undefined,
    });
    return normalizeTreeRows(details || []);
  } catch (error) {
    console.error(error);
    ElMessage.error('获取代码质量详情失败');
    return [];
  } finally {
    detailsLoading.value = false;
  }
}

async function handleRefresh() {
  try {
    loading.value = true;
    await refreshProjectQualityApi(projectId);
    await loadAvailableDates(false);
    ElMessage.success('刷新任务已提交，正在重新加载最新数据');
    await gridApi.reload();
  } catch (error) {
    console.error(error);
    ElMessage.error('刷新失败');
  } finally {
    loading.value = false;
  }
}

function handleBack() {
  router.back();
}

async function handleOwnerChange(row: CodeQualityTreeRow, ownerIds: string[]) {
  if (!row.owner_editable || !row.module_id || !row.node_key) {
    return;
  }
  try {
    await updateNodeOwnerApi({
      module_id: row.module_id,
      node_key: row.node_key,
      owner_ids: ownerIds || [],
    });
    ElMessage.success('节点责任人更新成功');
    await gridApi.reload();
  } catch (error) {
    console.error(error);
    ElMessage.error('节点责任人更新失败');
  }
}

function openOwnerDialog(row: CodeQualityTreeRow) {
  if (!row.owner_editable) {
    return;
  }
  ownerEditRow.value = row;
  ownerEditIds.value = [...(row.owner_ids || [])];
  ownerDialogVisible.value = true;
}

async function saveOwnerDialog() {
  if (!ownerEditRow.value) {
    return;
  }
  ownerSaving.value = true;
  try {
    await handleOwnerChange(ownerEditRow.value, ownerEditIds.value || []);
    ownerDialogVisible.value = false;
  } finally {
    ownerSaving.value = false;
  }
}

onMounted(async () => {
  await fetchProjectInfo();
  await loadAvailableDates();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full flex-col">
      <div class="mb-4 flex items-center justify-between px-4">
        <div class="flex items-center gap-4">
          <ElButton @click="handleBack">返回</ElButton>
          <div class="text-lg font-bold">
            {{ projectInfo.name }} - 代码质量详情
          </div>
        </div>
        <ElButton type="primary" :loading="loading" @click="handleRefresh">
          刷新数据
        </ElButton>
      </div>

      <div
        v-loading="detailsLoading"
        class="min-h-0 flex-1 overflow-hidden px-4"
        element-loading-text="正在加载代码质量详情..."
      >
        <Grid class="h-full">
          <template #table-title>
            <div class="flex flex-wrap items-center gap-2 text-sm">
              <span class="font-medium">日期筛选</span>
              <ElDatePicker
                v-model="selectedDate"
                type="date"
                clearable
                :editable="false"
                value-format="YYYY-MM-DD"
                placeholder="选择记录日期"
                popper-class="cq-quality-date-picker"
                :disabled-date="isDateDisabled"
                @change="handleDateFilterChange"
              >
                <template #default="cell">
                  <div
                    class="cq-date-cell"
                    :class="`cq-date-cell--${getDateCellStatus(cell)}`"
                  >
                    <span>{{ cell.text }}</span>
                    <span
                      v-if="getDateCellStatus(cell) !== 'other'"
                      class="cq-date-cell-dot"
                    ></span>
                  </div>
                </template>
              </ElDatePicker>
              <span class="cq-date-hint">
                绿色点：有数据可选；红色点：数据湖无数据不可选
              </span>
            </div>
          </template>
          <template #cell-clean_code_rate="{ row }">
            <CleanCodeRateCell
              :rate="Number(row.clean_code_rate || 0)"
              :reason-text="row.unachieved_clean_code_text"
            />
          </template>
          <template #cell-owner_names_text="{ row }">
            <span
              :class="row.owner_editable ? 'cursor-context-menu' : ''"
              @click="row.owner_editable && openOwnerDialog(row)"
              @contextmenu.prevent="row.owner_editable && openOwnerDialog(row)"
            >
              {{ row.owner_names_text || '-' }}
            </span>
          </template>
        </Grid>
      </div>
    </div>

    <ElDialog
      v-model="ownerDialogVisible"
      :append-to-body="true"
      :close-on-click-modal="false"
      title="编辑节点责任人"
      width="520px"
    >
      <div class="mb-3 text-sm">
        <span class="text-gray-500">节点：</span>
        <span class="font-medium">{{ ownerEditRow?.node_name || '-' }}</span>
      </div>
      <UserSelector
        v-model="ownerEditIds"
        :multiple="true"
        placeholder="请选择节点责任人"
      />
      <template #footer>
        <ElButton @click="ownerDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="ownerSaving"
          @click="saveOwnerDialog"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style>
.cq-date-hint {
  color: #6b7280;
  font-size: 12px;
}

.cq-quality-date-picker .cq-date-cell {
  align-items: center;
  display: flex;
  height: 100%;
  justify-content: center;
  position: relative;
  width: 100%;
}

.cq-quality-date-picker .cq-date-cell-dot {
  border-radius: 50%;
  bottom: 2px;
  height: 5px;
  position: absolute;
  width: 5px;
}

.cq-quality-date-picker .cq-date-cell--available .cq-date-cell-dot {
  background: #67c23a;
}

.cq-quality-date-picker .cq-date-cell--empty {
  color: #c0c4cc;
}

.cq-quality-date-picker .cq-date-cell--empty .cq-date-cell-dot {
  background: #f56c6c;
}

.cq-quality-date-picker td.is-disabled .cq-date-cell {
  cursor: not-allowed;
  opacity: 0.88;
}
</style>
