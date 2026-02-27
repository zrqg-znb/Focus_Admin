<script lang="ts" setup>
import type { CodeQualityOverviewRow, QualityMetricKey } from './data';

import type {
  ProjectQualitySummary,
  QualityMetricValue,
} from '#/api/project-manager/code_quality';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElLink } from 'element-plus';

import { getQualityOverviewApi } from '#/api/project-manager/code_quality';
import { useZqTable } from '#/components/zq-table';

import CleanCodeRateCell from './components/CleanCodeRateCell.vue';
import {
  getMetricFieldName,
  QUALITY_METRIC_COLUMNS,
  useSearchFormSchema,
} from './data';

defineOptions({ name: 'CodeQualityDashboard' });
interface QualityQueryParams {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const router = useRouter();
const metricKeys = new Set<string>(
  QUALITY_METRIC_COLUMNS.map((item) => item.key),
);
const currentPageRows = ref<CodeQualityOverviewRow[]>([]);

function onNameClick(row: CodeQualityOverviewRow) {
  router.push(`/project-manager/code-quality/detail/${row.project_id}`);
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
function normalizeRows(rows: ProjectQualitySummary[] = []) {
  return rows
    .map((item) => {
      const { displayMap, warningMap } = toMetricMaps(item.metric_values || []);
      const row: CodeQualityOverviewRow = {
        project_id: item.project_id,
        project_name: item.project_name || '-',
        project_domain: item.project_domain || '-',
        project_type: item.project_type || '-',
        project_managers: item.project_managers || '-',
        record_date: item.record_date || '-',
        oem_name: item.oem_name || '-',
        module_count: Number(item.module_count || 0),
        clean_code_pass_modules: Number(item.clean_code_pass_modules || 0),
        total_node_count: Number(item.total_node_count || 0),
        warning_node_count: Number(item.warning_node_count || 0),
        warning_count: Number(item.warning_count || 0),
        clean_code_achieve_rate: Number(item.clean_code_achieve_rate || 0),
        avg_duplication_rate: Number(item.avg_duplication_rate || 0),
        total_loc: Number(item.total_loc || 0),
        warning_metrics_text:
          item.warning_metrics && item.warning_metrics.length > 0
            ? item.warning_metrics.join('、')
            : '-',
        unachieved_clean_code_text:
          item.unachieved_clean_code && item.unachieved_clean_code.length > 0
            ? item.unachieved_clean_code.join('；')
            : '-',
        metric_warning_map: warningMap,
      };
      for (const metric of QUALITY_METRIC_COLUMNS) {
        const field = getMetricFieldName(metric.key);
        row[field] = displayMap[field] || '-';
      }
      return row;
    })
    .sort((first, second) => {
      const projectCompare = first.project_name.localeCompare(
        second.project_name,
        'zh-CN',
      );
      if (projectCompare !== 0) return projectCompare;
      return first.oem_name.localeCompare(second.oem_name, 'zh-CN');
    });
}
function filterRows(
  rows: CodeQualityOverviewRow[],
  formValues: Record<string, any>,
) {
  const keyword = String(formValues.keyword || '')
    .trim()
    .toLowerCase();
  const oemName = String(formValues.oem_name || '')
    .trim()
    .toLowerCase();
  const date = String(formValues.date || '').trim();

  let filtered = rows;
  if (keyword) {
    filtered = filtered.filter((item) =>
      [item.project_name, item.oem_name, item.project_managers]
        .join('|')
        .toLowerCase()
        .includes(keyword),
    );
  }
  if (oemName) {
    filtered = filtered.filter((item) =>
      item.oem_name.toLowerCase().includes(oemName),
    );
  }
  if (date) {
    filtered = filtered.filter((item) => item.record_date === date);
  }
  return filtered;
}
function projectSpanMethod({ row, column, rowIndex }: any) {
  const prop = String(column.property || column.prop || '');
  if (prop !== 'project_name') {
    return [1, 1];
  }
  const rows = currentPageRows.value;
  const prevRow = rows[rowIndex - 1];
  if (prevRow && prevRow.project_id === row.project_id) {
    return [0, 0];
  }

  let rowspan = 1;
  for (let index = rowIndex + 1; index < rows.length; index += 1) {
    if (rows[index]?.project_id === row.project_id) {
      rowspan += 1;
    } else {
      break;
    }
  }
  return [rowspan, 1];
}
function useColumns(): ZqTableGridOptions<CodeQualityOverviewRow>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<CodeQualityOverviewRow>['columns']
  > = [
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目名',
      width: 180,
      fixed: true,
    },
    {
      key: 'oem_name',
      dataKey: 'oem_name',
      title: 'OEMName',
      width: 140,
      fixed: true,
    },
    {
      key: 'project_managers',
      dataKey: 'project_managers',
      title: '项目经理',
      width: 150,
    },
    {
      key: 'record_date',
      dataKey: 'record_date',
      title: '更新日期',
      width: 120,
    },
    {
      key: 'clean_code_achieve_rate',
      dataKey: 'clean_code_achieve_rate',
      title: 'CleanCode达成率',
      width: 150,
    },
    {
      key: 'avg_duplication_rate',
      dataKey: 'avg_duplication_rate',
      title: '平均重复率',
      width: 120,
    },
    { key: 'total_loc', dataKey: 'total_loc', title: '总代码规模', width: 140 },
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

const [Grid] = useZqTable({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
    showCollapseButton: false,
  },
  gridOptions: {
    border: true,
    stripe: true,
    columns: useColumns(),
    spanMethod: projectSpanMethod,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: QualityQueryParams) => {
          const rows = normalizeRows(await getQualityOverviewApi());
          const filtered = filterRows(rows, form || {});

          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          currentPageRows.value = filtered.slice(start, end);
          return {
            items: currentPageRows.value,
            total: filtered.length,
          };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
  } as ZqTableGridOptions<CodeQualityOverviewRow>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid class="h-full">
      <template #cell-project_name="{ row }">
        <ElLink type="primary" @click="onNameClick(row)">
          {{ row.project_name }}
        </ElLink>
      </template>
      <template #cell-clean_code_achieve_rate="{ row }">
        <CleanCodeRateCell
          :rate="Number(row.clean_code_achieve_rate || 0)"
          :reason-text="row.unachieved_clean_code_text"
        />
      </template>
      <template #cell-avg_duplication_rate="{ row }">
        {{ Number(row.avg_duplication_rate || 0).toFixed(2) }}%
      </template>
      <template #cell-total_loc="{ row }">
        {{ Number(row.total_loc || 0).toLocaleString() }}
      </template>
    </Grid>
  </Page>
</template>
