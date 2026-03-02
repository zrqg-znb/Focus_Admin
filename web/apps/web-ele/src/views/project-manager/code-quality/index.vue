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
  createThresholdCellClassName,
  getMetricFieldName,
  getOverviewColumns,
  QUALITY_METRIC_COLUMNS,
  QUALITY_THRESHOLD_CONFIG,
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

function normalizeRows(rows: ProjectQualitySummary[] = []) {
  return rows
    .map((item) => {
      const { displayMap, numberMap, warningMap } = toMetricMaps(
        item.metric_values || [],
      );
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
        metric_num_map: numberMap,
      };
      for (const metric of QUALITY_METRIC_COLUMNS) {
        const field = getMetricFieldName(metric.key as QualityMetricKey);
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

function normalizeProjectType(value: string) {
  const text = String(value || '')
    .trim()
    .toLowerCase();
  if (!text) return '';
  if (text.includes('vehicle') || text.includes('车控')) return 'vehicle';
  if (text.includes('cockpit') || text.includes('座舱')) return 'cockpit';
  return text;
}

function filterRows(
  rows: CodeQualityOverviewRow[],
  formValues: Record<string, any>,
) {
  const projectName = String(formValues.project_name || '')
    .trim()
    .toLowerCase();
  const projectManager = String(formValues.project_manager || '')
    .trim()
    .toLowerCase();
  const projectType = normalizeProjectType(String(formValues.project_type || ''));
  const oemName = String(formValues.oem_name || '')
    .trim()
    .toLowerCase();
  const date = String(formValues.date || '').trim();

  let filtered = rows;
  if (projectName) {
    filtered = filtered.filter((item) =>
      item.project_name.toLowerCase().includes(projectName),
    );
  }
  if (projectManager) {
    filtered = filtered.filter((item) =>
      String(item.project_managers || '')
        .toLowerCase()
        .includes(projectManager),
    );
  }
  if (projectType) {
    filtered = filtered.filter(
      (item) => normalizeProjectType(item.project_type) === projectType,
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

const [Grid] = useZqTable({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
    showCollapseButton: false,
  },
  gridOptions: {
    border: true,
    stripe: true,
    columns: getOverviewColumns(),
    cellClassName: createThresholdCellClassName(() => QUALITY_THRESHOLD_CONFIG),
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
      <template #table-title>
        <span class="text-sm font-medium">代码质量概览</span>
      </template>

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
