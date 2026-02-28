<script lang="ts" setup>
import type { IterationDashboardItem } from '#/api/project-manager/iteration';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElInputNumber, ElLink, ElMessage, ElTag } from 'element-plus';

import {
  getIterationOverviewApi,
  updateManualMetricApi,
} from '#/api/project-manager/iteration';
import { useZqTable } from '#/components/zq-table';

import { useSearchFormSchema } from './data';

defineOptions({ name: 'IterationDashboard' });
type EditableMetricField = 'test_automation_rate' | 'test_case_execution_rate';
interface IterationQueryParams {
  form?: Record<string, any>;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const router = useRouter();
const editingCell = ref<null | { field: EditableMetricField; rowId: string }>(
  null,
);
const editingMetricValue = ref(0);

function onNameClick(row: IterationDashboardItem) {
  router.push(`/project-manager/iteration/detail/${row.project_id}`);
}
function formatRate(value: number) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return '-';
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}
function isIterationEnded(row: IterationDashboardItem) {
  if (!row.end_date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const end = new Date(row.end_date);
  return end < today;
}
async function onManualMetricChange(
  row: IterationDashboardItem,
  field: EditableMetricField,
  value: null | number | undefined,
) {
  if (value === null || value === undefined) return;
  if (!row.iteration_id) return;
  if (isIterationEnded(row)) {
    ElMessage.warning('该迭代已结束，无法修改指标');
    return;
  }

  const prev = row[field];
  row[field] = Number(value);
  try {
    await updateManualMetricApi(row.iteration_id, {
      [field]: row[field],
    });
    ElMessage.success('更新成功');
  } catch {
    row[field] = prev;
    ElMessage.error('更新失败');
  }
}

function isEditingMetric(
  row: IterationDashboardItem,
  field: EditableMetricField,
) {
  return (
    !!row.iteration_id &&
    editingCell.value?.rowId === row.iteration_id &&
    editingCell.value?.field === field
  );
}

function beginMetricEdit(
  row: IterationDashboardItem,
  field: EditableMetricField,
) {
  if (!row.iteration_id || isIterationEnded(row)) {
    return;
  }
  editingCell.value = { rowId: row.iteration_id, field };
  editingMetricValue.value = Number(row[field] || 0);
}

async function commitMetricEdit(
  row: IterationDashboardItem,
  field: EditableMetricField,
) {
  if (!isEditingMetric(row, field)) return;
  const nextValue = Number(editingMetricValue.value || 0);
  editingCell.value = null;
  await onManualMetricChange(row, field, nextValue);
}

function useColumns(): ZqTableGridOptions<IterationDashboardItem>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<IterationDashboardItem>['columns']
  > = [
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目名',
      width: 180,
      fixed: true,
      headerHelp: {
        definition: '项目名称，点击可跳转项目迭代详情页。',
      },
    },
    {
      key: 'project_domain',
      dataKey: 'project_domain',
      title: '领域',
      width: 100,
      headerHelp: {
        definition: '项目所属业务领域（如座舱、车控）。',
      },
    },
    {
      key: 'project_type',
      dataKey: 'project_type',
      title: '类型',
      width: 100,
      headerHelp: {
        definition: '项目类型标签，用于分类统计。',
      },
    },
    {
      key: 'current_iteration_name',
      dataKey: 'current_iteration_name',
      title: '当前迭代',
      width: 140,
      headerHelp: {
        definition: '项目当前生效迭代名称。',
      },
    },
    {
      key: 'is_healthy',
      dataKey: 'is_healthy',
      title: '健康状态',
      width: 110,
      headerHelp: {
        definition: '迭代综合状态评估结果（健康/风险）。',
      },
    },
    {
      key: 'dr_breakdown_rate',
      dataKey: 'dr_breakdown_rate',
      title: 'DR分解率',
      width: 120,
      headerHelp: {
        definition: 'DR需求分解完成程度。',
        formula: 'DR分解率 = 已分解DR数量 ÷ DR总数量',
      },
    },
    {
      key: 'sr_breakdown_rate',
      dataKey: 'sr_breakdown_rate',
      title: 'SR分解率',
      width: 120,
      headerHelp: {
        definition: 'SR需求分解完成程度。',
        formula: 'SR分解率 = 已分解SR数量 ÷ SR总数量',
      },
    },
    {
      key: 'dr_set_a_rate',
      dataKey: 'dr_set_a_rate',
      title: 'DR置A率',
      width: 120,
      headerHelp: {
        definition: 'DR状态置A的比例。',
        formula: 'DR置A率 = 状态为A的DR数量 ÷ DR总数量',
      },
    },
    {
      key: 'ar_set_a_rate',
      dataKey: 'ar_set_a_rate',
      title: 'AR置A率',
      width: 120,
      headerHelp: {
        definition: 'AR状态置A的比例。',
        formula: 'AR置A率 = 状态为A的AR数量 ÷ AR总数量',
      },
    },
    {
      key: 'dr_set_c_rate',
      dataKey: 'dr_set_c_rate',
      title: 'DR置C率',
      width: 120,
      headerHelp: {
        definition: 'DR状态置C的比例（风险观察指标）。',
        formula: 'DR置C率 = 状态为C的DR数量 ÷ DR总数量',
      },
    },
    {
      key: 'ar_set_c_rate',
      dataKey: 'ar_set_c_rate',
      title: 'AR置C率',
      width: 120,
      headerHelp: {
        definition: 'AR状态置C的比例（风险观察指标）。',
        formula: 'AR置C率 = 状态为C的AR数量 ÷ AR总数量',
      },
    },
    {
      key: 'test_automation_rate',
      dataKey: 'test_automation_rate',
      title: '迭代测试自动化率',
      width: 160,
      headerHelp: {
        definition: '本迭代自动化测试执行覆盖水平。',
        formula: '测试自动化率 = 自动化执行用例数 ÷ 总执行用例数',
        editableHint: '支持双击单元格编辑（仅未结束迭代）',
      },
    },
    {
      key: 'test_case_execution_rate',
      dataKey: 'test_case_execution_rate',
      title: '用例执行率',
      width: 130,
      headerHelp: {
        definition: '本迭代测试用例执行完成程度。',
        formula: '用例执行率 = 已执行用例数 ÷ 计划执行用例总数',
        editableHint: '支持双击单元格编辑（仅未结束迭代）',
      },
    },
    {
      key: 'bug_fix_rate',
      dataKey: 'bug_fix_rate',
      title: '缺陷修复率',
      width: 120,
      headerHelp: {
        definition: '迭代内缺陷修复完成程度。',
        formula: '缺陷修复率 = 已修复缺陷数 ÷ 缺陷总数',
      },
    },
    {
      key: 'code_review_rate',
      dataKey: 'code_review_rate',
      title: '代码评审率',
      width: 120,
      headerHelp: {
        definition: '代码提交参与评审覆盖程度。',
        formula: '代码评审率 = 已评审提交数 ÷ 提交总数',
      },
    },
    {
      key: 'code_coverage_rate',
      dataKey: 'code_coverage_rate',
      title: '代码覆盖率',
      width: 120,
      headerHelp: {
        definition: '自动化测试覆盖代码的比例。',
        formula: '代码覆盖率 = 被覆盖代码量 ÷ 代码总量',
      },
    },
    {
      key: 'quality_ut_file_coverage_rate',
      dataKey: 'quality_ut_file_coverage_rate',
      title: 'UT文件覆盖率',
      width: 130,
      headerHelp: {
        definition: '单元测试覆盖文件维度的比例。',
      },
    },
    {
      key: 'quality_ut_line_coverage_rate',
      dataKey: 'quality_ut_line_coverage_rate',
      title: 'UT行覆盖率',
      width: 130,
      headerHelp: {
        definition: '单元测试覆盖代码行维度的比例。',
      },
    },
    {
      key: 'quality_clean_code_rate',
      dataKey: 'quality_clean_code_rate',
      title: 'CleanCode达成率',
      width: 150,
      headerHelp: {
        definition: 'CleanCode指标达标情况（综合指标）。',
      },
    },
    {
      key: 'start_date',
      dataKey: 'start_date',
      title: '开始时间',
      width: 120,
      headerHelp: {
        definition: '当前迭代计划开始日期。',
      },
    },
    {
      key: 'end_date',
      dataKey: 'end_date',
      title: '结束时间',
      width: 120,
      headerHelp: {
        definition: '当前迭代计划结束日期。',
      },
    },
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
    showCollapseButton: false,
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: IterationQueryParams) => {
          const data = await getIterationOverviewApi();
          let filtered = data;
          if (form?.keyword) {
            const keyword = String(form.keyword).toLowerCase();
            filtered = filtered.filter((item) =>
              item.project_name.toLowerCase().includes(keyword),
            );
          }
          if (form?.domain) {
            filtered = filtered.filter((item) =>
              item.project_domain.includes(String(form.domain)),
            );
          }
          if (form?.type) {
            filtered = filtered.filter((item) =>
              item.project_type.includes(String(form.type)),
            );
          }
          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          return { items: filtered.slice(start, end), total: filtered.length };
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
  } as ZqTableGridOptions<IterationDashboardItem>,
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
      <template #cell-is_healthy="{ row }">
        <ElTag :type="row.is_healthy ? 'success' : 'danger'" size="small">
          {{ row.is_healthy ? '健康' : '风险' }}
        </ElTag>
      </template>

      <template #cell-dr_breakdown_rate="{ row }">
        {{ formatRate(row.dr_breakdown_rate) }}
      </template>
      <template #cell-sr_breakdown_rate="{ row }">
        {{ formatRate(row.sr_breakdown_rate) }}
      </template>
      <template #cell-dr_set_a_rate="{ row }">
        {{ formatRate(row.dr_set_a_rate) }}
      </template>
      <template #cell-ar_set_a_rate="{ row }">
        {{ formatRate(row.ar_set_a_rate) }}
      </template>
      <template #cell-dr_set_c_rate="{ row }">
        {{ formatRate(row.dr_set_c_rate) }}
      </template>
      <template #cell-ar_set_c_rate="{ row }">
        {{ formatRate(row.ar_set_c_rate) }}
      </template>
      <template #cell-bug_fix_rate="{ row }">
        {{ formatRate(row.bug_fix_rate) }}
      </template>
      <template #cell-code_review_rate="{ row }">
        {{ formatRate(row.code_review_rate) }}
      </template>
      <template #cell-code_coverage_rate="{ row }">
        {{ formatRate(row.code_coverage_rate) }}
      </template>
      <template #cell-quality_ut_file_coverage_rate="{ row }">
        {{ formatRate(row.quality_ut_file_coverage_rate) }}
      </template>
      <template #cell-quality_ut_line_coverage_rate="{ row }">
        {{ formatRate(row.quality_ut_line_coverage_rate) }}
      </template>
      <template #cell-quality_clean_code_rate="{ row }">
        {{ formatRate(row.quality_clean_code_rate) }}
      </template>

      <template #cell-test_automation_rate="{ row }">
        <ElInputNumber
          v-if="isEditingMetric(row, 'test_automation_rate')"
          :model-value="editingMetricValue"
          size="small"
          :controls="false"
          :step="0.01"
          :min="0"
          :max="1"
          @update:model-value="
            (value) => (editingMetricValue = Number(value || 0))
          "
          @blur="commitMetricEdit(row, 'test_automation_rate')"
          @change="
            (value) => {
              editingMetricValue = Number(value || 0);
              void commitMetricEdit(row, 'test_automation_rate');
            }
          "
        />
        <span
          v-else
          :class="isIterationEnded(row) ? '' : 'cursor-pointer'"
          @dblclick="beginMetricEdit(row, 'test_automation_rate')"
        >
          {{ formatRate(row.test_automation_rate) }}
        </span>
      </template>
      <template #cell-test_case_execution_rate="{ row }">
        <ElInputNumber
          v-if="isEditingMetric(row, 'test_case_execution_rate')"
          :model-value="editingMetricValue"
          size="small"
          :controls="false"
          :step="0.01"
          :min="0"
          :max="1"
          @update:model-value="
            (value) => (editingMetricValue = Number(value || 0))
          "
          @blur="commitMetricEdit(row, 'test_case_execution_rate')"
          @change="
            (value) => {
              editingMetricValue = Number(value || 0);
              void commitMetricEdit(row, 'test_case_execution_rate');
            }
          "
        />
        <span
          v-else
          :class="isIterationEnded(row) ? '' : 'cursor-pointer'"
          @dblclick="beginMetricEdit(row, 'test_case_execution_rate')"
        >
          {{ formatRate(row.test_case_execution_rate) }}
        </span>
      </template>
    </Grid>
  </Page>
</template>
