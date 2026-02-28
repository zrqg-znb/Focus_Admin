<script lang="ts" setup>
import type { IterationDetailItem } from '#/api/project-manager/iteration';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElInputNumber, ElMessage, ElTag } from 'element-plus';

import {
  listProjectIterationsApi,
  refreshProjectIterationApi,
  updateManualMetricApi,
} from '#/api/project-manager/iteration';
import { getProjectApi } from '#/api/project-manager/project';
import { useZqTable } from '#/components/zq-table';

defineOptions({ name: 'IterationDetail' });

type EditableMetricField = 'test_automation_rate' | 'test_case_execution_rate';

interface IterationDetailRow extends IterationDetailItem {
  ar_set_a_rate: number;
  ar_set_c_rate: number;
  bug_fix_rate: number;
  code_coverage_rate: number;
  code_review_rate: number;
  dr_breakdown_rate: number;
  dr_set_a_rate: number;
  dr_set_c_rate: number;
  sr_breakdown_rate: number;
  test_automation_rate: number;
  test_case_execution_rate: number;
}

interface IterationQueryParams {
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
const editingCell = ref<null | { field: EditableMetricField; rowId: string }>(
  null,
);
const editingMetricValue = ref(0);

function formatRate(value: null | number | undefined) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return '-';
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function isIterationEnded(row: IterationDetailRow) {
  if (!row.end_date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const end = new Date(row.end_date);
  return end < today;
}

function withCenterAlign<T extends Record<string, any>>(columns: T[]): T[] {
  return columns.map((column) => {
    const nextColumn: Record<string, any> = {
      ...column,
      align: column.align ?? 'center',
      headerAlign: column.headerAlign ?? 'center',
    };
    if (Array.isArray(column.children)) {
      nextColumn.children = withCenterAlign(column.children);
    }
    return nextColumn as T;
  }) as T[];
}

function toDetailRows(items: IterationDetailItem[]) {
  return items.map((item) => {
    const metric = item.latest_metric;
    return {
      ...item,
      ar_set_a_rate: Number(metric?.ar_set_a_rate || 0),
      ar_set_c_rate: Number(metric?.ar_set_c_rate || 0),
      bug_fix_rate: Number(metric?.bug_fix_rate || 0),
      code_coverage_rate: Number(metric?.code_coverage_rate || 0),
      code_review_rate: Number(metric?.code_review_rate || 0),
      dr_breakdown_rate: Number(metric?.dr_breakdown_rate || 0),
      dr_set_a_rate: Number(metric?.dr_set_a_rate || 0),
      dr_set_c_rate: Number(metric?.dr_set_c_rate || 0),
      sr_breakdown_rate: Number(metric?.sr_breakdown_rate || 0),
      test_automation_rate: Number(metric?.test_automation_rate || 0),
      test_case_execution_rate: Number(metric?.test_case_execution_rate || 0),
    } as IterationDetailRow;
  });
}

async function fetchProjectInfo() {
  try {
    projectInfo.value = await getProjectApi(projectId);
  } catch (error) {
    console.error(error);
  }
}

async function handleRefresh() {
  try {
    loading.value = true;
    await refreshProjectIterationApi(projectId);
    ElMessage.success('刷新任务已提交，请稍后查看同步日志或刷新页面');
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

function handleBack() {
  router.back();
}

async function onManualMetricChange(
  row: IterationDetailRow,
  field: EditableMetricField,
  value: null | number | undefined,
) {
  if (value === null || value === undefined || !row.id) return;
  if (isIterationEnded(row)) {
    ElMessage.warning('该迭代已结束，无法修改指标');
    return;
  }

  const prev = row[field];
  row[field] = Number(value);
  row.latest_metric = {
    ...row.latest_metric,
    [field]: row[field],
  } as NonNullable<IterationDetailItem['latest_metric']>;

  try {
    await updateManualMetricApi(row.id, {
      [field]: row[field],
    });
    ElMessage.success('更新成功');
  } catch {
    row[field] = prev;
    row.latest_metric = {
      ...row.latest_metric,
      [field]: prev,
    } as NonNullable<IterationDetailItem['latest_metric']>;
    ElMessage.error('更新失败');
  }
}

function isEditingMetric(row: IterationDetailRow, field: EditableMetricField) {
  return (
    editingCell.value?.rowId === row.id && editingCell.value?.field === field
  );
}

function beginMetricEdit(row: IterationDetailRow, field: EditableMetricField) {
  if (!row.id || isIterationEnded(row)) {
    return;
  }
  editingCell.value = { rowId: row.id, field };
  editingMetricValue.value = Number(row[field] || 0);
}

async function commitMetricEdit(
  row: IterationDetailRow,
  field: EditableMetricField,
) {
  if (!isEditingMetric(row, field)) return;
  const nextValue = Number(editingMetricValue.value || 0);
  editingCell.value = null;
  await onManualMetricChange(row, field, nextValue);
}

function useColumns(): ZqTableGridOptions<IterationDetailRow>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<IterationDetailRow>['columns']
  > = [
    {
      key: 'name',
      dataKey: 'name',
      title: '迭代名称',
      width: 180,
      fixed: true,
      headerHelp: {
        definition: '项目内的迭代名称标识，用于区分不同迭代批次。',
      },
    },
    {
      key: 'code',
      dataKey: 'code',
      title: '编码',
      width: 120,
      headerHelp: {
        definition: '迭代在系统中的唯一编码，用于检索和关联数据。',
      },
    },
    {
      key: 'start_date',
      dataKey: 'start_date',
      title: '开始时间',
      width: 120,
      headerHelp: {
        definition: '迭代计划启动日期。',
      },
    },
    {
      key: 'end_date',
      dataKey: 'end_date',
      title: '结束时间',
      width: 120,
      headerHelp: {
        definition: '迭代计划完成日期，超期后通常视为已结束迭代。',
      },
    },
    {
      key: 'is_current',
      dataKey: 'is_current',
      title: '当前迭代',
      width: 110,
      headerHelp: {
        definition: '用于标识该迭代是否为当前正在执行的主迭代。',
      },
    },
    {
      key: 'is_healthy',
      dataKey: 'is_healthy',
      title: '健康状态',
      width: 110,
      headerHelp: {
        definition: '迭代综合状态评估结果，健康/风险用于提示进度与质量风险。',
      },
    },
    {
      key: 'entry_metrics',
      dataKey: 'entry_metrics',
      title: '迭代入口指标',
      width: 240,
      headerHelp: {
        definition: '进入迭代开发前应满足的准备类指标集合。',
      },
      children: [
        {
          key: 'dr_breakdown_rate',
          dataKey: 'dr_breakdown_rate',
          title: 'DR分解率',
          width: 120,
          headerHelp: {
            definition: '需求 DR 的分解完成程度。',
            formula: 'DR分解率 = 已分解DR数量 ÷ DR总数量',
          },
        },
        {
          key: 'sr_breakdown_rate',
          dataKey: 'sr_breakdown_rate',
          title: 'SR分解率',
          width: 120,
          headerHelp: {
            definition: '系统需求 SR 的分解完成程度。',
            formula: 'SR分解率 = 已分解SR数量 ÷ SR总数量',
          },
        },
      ],
    },
    {
      key: 'exit_metrics',
      dataKey: 'exit_metrics',
      title: '迭代出口指标',
      width: 1110,
      headerHelp: {
        definition: '迭代收敛阶段用于评估交付质量与完成度的指标集合。',
      },
      children: [
        {
          key: 'dr_set_a_rate',
          dataKey: 'dr_set_a_rate',
          title: 'DR置A率',
          width: 120,
          headerHelp: {
            definition: 'DR状态收敛到 A 的比例。',
            formula: 'DR置A率 = 状态为A的DR数量 ÷ DR总数量',
          },
        },
        {
          key: 'ar_set_a_rate',
          dataKey: 'ar_set_a_rate',
          title: 'AR置A率',
          width: 120,
          headerHelp: {
            definition: 'AR状态收敛到 A 的比例。',
            formula: 'AR置A率 = 状态为A的AR数量 ÷ AR总数量',
          },
        },
        {
          key: 'dr_set_c_rate',
          dataKey: 'dr_set_c_rate',
          title: 'DR置C率',
          width: 120,
          headerHelp: {
            definition: 'DR状态为 C 的比例，通常用于观察未闭环风险。',
            formula: 'DR置C率 = 状态为C的DR数量 ÷ DR总数量',
          },
        },
        {
          key: 'ar_set_c_rate',
          dataKey: 'ar_set_c_rate',
          title: 'AR置C率',
          width: 120,
          headerHelp: {
            definition: 'AR状态为 C 的比例，通常用于观察未闭环风险。',
            formula: 'AR置C率 = 状态为C的AR数量 ÷ AR总数量',
          },
        },
        {
          key: 'test_automation_rate',
          dataKey: 'test_automation_rate',
          title: '测试自动化率',
          width: 150,
          headerHelp: {
            definition: '本迭代测试执行中自动化用例覆盖水平。',
            formula: '测试自动化率 = 自动化执行用例数 ÷ 总执行用例数',
            editableHint: '支持双击单元格编辑（仅未结束迭代）',
          },
        },
        {
          key: 'test_case_execution_rate',
          dataKey: 'test_case_execution_rate',
          title: '用例执行率',
          width: 140,
          headerHelp: {
            definition: '本迭代测试计划用例的执行完成程度。',
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
            definition: '迭代内缺陷关闭和修复完成情况。',
            formula: '缺陷修复率 = 已修复缺陷数 ÷ 缺陷总数',
          },
        },
        {
          key: 'code_review_rate',
          dataKey: 'code_review_rate',
          title: '代码评审率',
          width: 120,
          headerHelp: {
            definition: '提交代码参与评审的覆盖程度。',
            formula: '代码评审率 = 已评审代码提交数 ÷ 代码提交总数',
          },
        },
        {
          key: 'code_coverage_rate',
          dataKey: 'code_coverage_rate',
          title: '代码覆盖率',
          width: 120,
          headerHelp: {
            definition: '自动化测试对代码行/分支的覆盖程度。',
            formula: '代码覆盖率 = 被覆盖代码量 ÷ 代码总量',
          },
        },
      ],
    },
  ];
  return withCenterAlign(columns);
}

const [Grid, gridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    columns: useColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page }: IterationQueryParams) => {
          const data = toDetailRows(await listProjectIterationsApi(projectId));
          const start = (page.currentPage - 1) * page.pageSize;
          const end = start + page.pageSize;
          return { items: data.slice(start, end), total: data.length };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: {
      custom: true,
      export: {
        filename: '迭代详情指标',
      },
      refresh: true,
      zoom: true,
    },
  } as ZqTableGridOptions<IterationDetailRow>,
});

onMounted(() => {
  fetchProjectInfo();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col">
      <div class="mb-4 flex items-center justify-between px-4">
        <div class="flex items-center gap-4">
          <ElButton @click="handleBack">返回</ElButton>
          <div class="text-lg font-bold">{{ projectInfo.name }} - 迭代详情</div>
        </div>
        <div class="flex items-center gap-2">
          <ElButton @click="gridApi.reload()">刷新列表</ElButton>
          <ElButton type="primary" :loading="loading" @click="handleRefresh">
            刷新数据
          </ElButton>
        </div>
      </div>
      <div class="min-h-0 flex-1 px-4 pb-4">
        <Grid class="h-full">
          <template #cell-is_current="{ row }">
            <ElTag :type="row.is_current ? 'success' : 'info'" size="small">
              {{ row.is_current ? '是' : '否' }}
            </ElTag>
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
      </div>
    </div>
  </Page>
</template>
