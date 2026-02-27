<script lang="ts" setup>
import type { CodeQualityTreeRow, QualityMetricKey } from './data';

import type {
  ModuleQualityDetail,
  QualityMetricValue,
  QualityTreeNode,
} from '#/api/project-manager/code_quality';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElDialog, ElMessage } from 'element-plus';

import {
  getProjectQualityDetailsApi,
  refreshProjectQualityApi,
  updateNodeOwnerApi,
} from '#/api/project-manager/code_quality';
import { getProjectApi } from '#/api/project-manager/project';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';
import { useZqTable } from '#/components/zq-table';

import CleanCodeRateCell from './components/CleanCodeRateCell.vue';
import {
  getMetricFieldName,
  QUALITY_METRIC_COLUMNS,
  useDetailSearchFormSchema,
} from './data';

defineOptions({ name: 'CodeQualityDetail' });
interface DetailQueryParams {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const route = useRoute();
const router = useRouter();
const projectId = route.params.id as string;

const projectInfo = ref<any>({});
const loading = ref(false);
const detailsLoading = ref(true);
const ownerDialogVisible = ref(false);
const ownerSaving = ref(false);
const ownerEditIds = ref<string[]>([]);
const ownerEditRow = ref<CodeQualityTreeRow | null>(null);
const treeRows = ref<CodeQualityTreeRow[]>([]);
const metricKeys = new Set<string>(
  QUALITY_METRIC_COLUMNS.map((item) => item.key),
);

const summary = computed(() => {
  const rows = treeRows.value;
  const moduleCount = rows.length;
  const totalNodeCount = rows.reduce(
    (sum, item) => sum + Number(item.total_node_count || 0),
    0,
  );
  const warningNodeCount = rows.reduce(
    (sum, item) => sum + Number(item.warning_node_count || 0),
    0,
  );
  const avgCleanCodeRate =
    moduleCount > 0
      ? rows.reduce((sum, item) => sum + Number(item.clean_code_rate || 0), 0) /
        moduleCount
      : 0;
  return {
    avgCleanCodeRate,
    moduleCount,
    totalNodeCount,
    warningNodeCount,
  };
});

function formatPercent(rate: null | number | undefined) {
  return `${((Number(rate || 0) || 0) * 100).toFixed(2)}%`;
}

function toMetricMaps(metricValues: QualityMetricValue[] = []) {
  const displayMap: Record<string, string> = {};
  const warningMap: Record<string, boolean> = {};

  for (const metric of metricValues) {
    const metricKey = String(metric.key || '');
    if (!metricKey || !metricKeys.has(metricKey)) {
      continue;
    }
    const field = getMetricFieldName(metricKey as QualityMetricKey);
    displayMap[field] = String(metric.display || '-');
    warningMap[metricKey] = Boolean(metric.is_warning);
  }
  return { displayMap, warningMap };
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
    const { displayMap, warningMap } = toMetricMaps(node.metric_values || []);
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
      children,
    };
    for (const metric of QUALITY_METRIC_COLUMNS) {
      const field = getMetricFieldName(metric.key);
      row[field] = displayMap[field] || '-';
    }
    return row;
  });
}

function normalizeTreeRows(details: ModuleQualityDetail[] = []) {
  return details
    .map((item) => {
      const { displayMap, warningMap } = toMetricMaps(item.metric_values || []);
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
        children: mapNodeRows(
          nodeChildrenSource,
          item.id,
          moduleOwnerIds,
          moduleOwnerNamesText,
        ),
      };
      for (const metric of QUALITY_METRIC_COLUMNS) {
        const field = getMetricFieldName(metric.key);
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

function rowContainsKeyword(row: CodeQualityTreeRow, keyword: string): boolean {
  const currentHit = [
    row.node_name,
    row.oem_name,
    row.module,
    row.owner_names_text,
    row.unachieved_clean_code_text,
    row.warning_metrics_text,
  ]
    .join('|')
    .toLowerCase()
    .includes(keyword);
  if (currentHit) return true;

  for (const child of row.children || []) {
    if (rowContainsKeyword(child, keyword)) {
      return true;
    }
  }
  return false;
}

function filterTreeRows(
  rows: CodeQualityTreeRow[],
  formValues: Record<string, any>,
) {
  const keyword = String(formValues.keyword || '')
    .trim()
    .toLowerCase();
  const oemName = String(formValues.oem_name || '')
    .trim()
    .toLowerCase();
  const moduleName = String(formValues.module || '')
    .trim()
    .toLowerCase();
  const warningOnly = String(formValues.warning_only || '');

  return rows.filter((row) => {
    if (keyword && !rowContainsKeyword(row, keyword)) {
      return false;
    }
    if (oemName && !row.oem_name.toLowerCase().includes(oemName)) {
      return false;
    }
    if (moduleName && !row.module.toLowerCase().includes(moduleName)) {
      return false;
    }

    if (warningOnly === 'yes') {
      return (
        Number(row.warning_count || 0) > 0 ||
        Number(row.warning_node_count || 0) > 0 ||
        row.unachieved_clean_code_text !== '-'
      );
    }
    if (warningOnly === 'no') {
      return (
        Number(row.warning_count || 0) === 0 &&
        Number(row.warning_node_count || 0) === 0 &&
        row.unachieved_clean_code_text === '-'
      );
    }
    return true;
  });
}

function useColumns(): ZqTableGridOptions<CodeQualityTreeRow>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<CodeQualityTreeRow>['columns']
  > = [
    {
      key: 'node_name',
      dataKey: 'node_name',
      title: '树节点',
      width: 260,
      fixed: true,
    },
    { key: 'oem_name', dataKey: 'oem_name', title: 'OEMName', width: 150 },
    {
      key: 'owner_names_text',
      dataKey: 'owner_names_text',
      title: '责任人',
      width: 240,
    },
    {
      key: 'record_date',
      dataKey: 'record_date',
      title: '更新日期',
      width: 120,
    },
    {
      key: 'clean_code_rate',
      dataKey: 'clean_code_rate',
      title: 'CleanCode达成率',
      width: 150,
    },
    ...QUALITY_METRIC_COLUMNS.map((metric) => ({
      key: getMetricFieldName(metric.key),
      dataKey: getMetricFieldName(metric.key),
      title: metric.title,
      width: 140,
    })),
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

const [Grid, gridApi] = useZqTable({
  formOptions: {
    schema: useDetailSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    border: true,
    stripe: true,
    columns: useColumns(),
    rowKey: 'id',
    defaultExpandAll: true,
    treeProps: {
      children: 'children',
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ form }: DetailQueryParams) => {
          const rows = await fetchDetails();
          const filteredRows = filterTreeRows(rows, form || {});
          return {
            items: filteredRows,
            total: filteredRows.length,
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

async function fetchProjectInfo() {
  try {
    projectInfo.value = await getProjectApi(projectId);
  } catch (error) {
    console.error(error);
  }
}

async function fetchDetails() {
  try {
    detailsLoading.value = true;
    const details = await getProjectQualityDetailsApi(projectId);
    treeRows.value = normalizeTreeRows(details || []);
    return treeRows.value;
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
  await Promise.all([fetchProjectInfo(), gridApi.reload()]);
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
            <div class="flex flex-wrap items-center gap-4 text-sm">
              <span>模块数：{{ summary.moduleCount }}</span>
              <span>节点总数：{{ summary.totalNodeCount }}</span>
              <span class="font-semibold text-red-500">
                预警节点：{{ summary.warningNodeCount }}
              </span>
              <span
                :class="
                  summary.avgCleanCodeRate < 1
                    ? 'font-semibold text-red-500'
                    : 'font-semibold text-green-600'
                "
              >
                平均CleanCode达成率：{{
                  formatPercent(summary.avgCleanCodeRate)
                }}
              </span>
              <span class="text-gray-500">责任人列支持右键编辑</span>
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
