<script lang="ts" setup>
import type { CodeQualityOverviewRow, QualityMetricKey } from './data';

import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type {
  ProjectQualitySummary,
  QualityMetricValue,
} from '#/api/project-manager/code_quality';

import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElLink } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getQualityOverviewApi } from '#/api/project-manager/code_quality';

import {
  getMetricFieldName,
  QUALITY_METRIC_COLUMNS,
  useSearchFormSchema,
  useSummaryColumns,
} from './data';

defineOptions({ name: 'CodeQualityDashboard' });

const router = useRouter();
const metricKeys = new Set<string>(
  QUALITY_METRIC_COLUMNS.map((item) => item.key),
);

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

function projectSpanMethod({ column, row, rowIndex, visibleData }: any) {
  if (column.field !== 'project_name') {
    return { colspan: 1, rowspan: 1 };
  }

  const prevRow = visibleData[rowIndex - 1];
  if (prevRow && prevRow.project_id === row.project_id) {
    return { colspan: 0, rowspan: 0 };
  }

  let rowspan = 1;
  for (let index = rowIndex + 1; index < visibleData.length; index += 1) {
    if (visibleData[index].project_id === row.project_id) {
      rowspan += 1;
    } else {
      break;
    }
  }
  return { colspan: 1, rowspan };
}

const [Grid] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    border: true,
    columns: useSummaryColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const rows = normalizeRows(await getQualityOverviewApi());
          const filtered = filterRows(rows, formValues);

          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          return {
            items: filtered.slice(start, end),
            total: filtered.length,
          };
        },
      },
    },
    spanMethod: projectSpanMethod,
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<CodeQualityOverviewRow>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #name_slot="{ row }">
        <ElLink type="primary" @click="onNameClick(row)">
          {{ row.project_name }}
        </ElLink>
      </template>
    </Grid>
  </Page>
</template>
