<script lang="ts" setup>
import type { CodeQualityTreeRow, QualityMetricKey } from './data';

import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type {
  ModuleQualityDetail,
  QualityMetricValue,
  QualityTreeNode,
} from '#/api/project-manager/code_quality';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  getProjectQualityDetailsApi,
  refreshProjectQualityApi,
} from '#/api/project-manager/code_quality';
import { getProjectApi } from '#/api/project-manager/project';

import {
  getMetricFieldName,
  QUALITY_METRIC_COLUMNS,
  useDetailColumns,
  useDetailSearchFormSchema,
} from './data';

defineOptions({ name: 'CodeQualityDetail' });

const route = useRoute();
const router = useRouter();
const projectId = route.params.id as string;

const projectInfo = ref<any>({});
const loading = ref(false);
const detailsLoading = ref(false);
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

function mapNodeRows(nodes: QualityTreeNode[] = []): CodeQualityTreeRow[] {
  return nodes.map((node) => {
    const { displayMap, warningMap } = toMetricMaps(node.metric_values || []);
    const children = mapNodeRows(node.children || []);
    const row: CodeQualityTreeRow = {
      id: `node-${node.id}`,
      row_type: 'node',
      node_name: node.version_name || '-',
      oem_name: '-',
      module: '-',
      owner_names_text: '-',
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
        row_type: 'module',
        node_name: item.root_version_name || item.module || '-',
        oem_name: item.oem_name || '-',
        module: item.module || '-',
        owner_names_text:
          item.owner_names && item.owner_names.length > 0
            ? item.owner_names.join('、')
            : '-',
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
        children: mapNodeRows(nodeChildrenSource),
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

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useDetailSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    autoResize: true,
    border: true,
    columns: useDetailColumns(),
    height: '100%',
    keepSource: true,
    treeConfig: {
      transform: false,
      rowField: 'id',
      parentField: 'parent_id',
      childrenField: 'children',
      expandAll: true,
    },
    proxyConfig: {
      ajax: {
        query: async (_, formValues) => {
          return {
            items: filterTreeRows(treeRows.value, formValues),
          };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<CodeQualityTreeRow>,
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
    await gridApi.query();
  } catch (error) {
    console.error(error);
    ElMessage.error('获取代码质量详情失败');
  } finally {
    detailsLoading.value = false;
  }
}

async function handleRefresh() {
  try {
    loading.value = true;
    await refreshProjectQualityApi(projectId);
    ElMessage.success('刷新任务已提交，正在重新加载最新数据');
    await fetchDetails();
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

onMounted(async () => {
  await fetchProjectInfo();
  await fetchDetails();
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
            </div>
          </template>
        </Grid>
      </div>
    </div>
  </Page>
</template>
