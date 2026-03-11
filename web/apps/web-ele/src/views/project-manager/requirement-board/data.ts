import type { Column } from 'element-plus';

import type {
  RequirementBoardItem,
  RequirementBoardSummary,
  RequirementStatusSummary,
} from '#/api/project-manager/requirement_board';
import type { ZqTableGridOptions } from '#/components/zq-table';

export const CATEGORY_OPTIONS = [
  { label: 'AR', value: 'AR' },
  { label: 'DR', value: 'DR' },
  { label: 'SR', value: 'SR' },
];

export const DEFAULT_CATEGORIES = CATEGORY_OPTIONS.map((item) => item.value);

export const STATUS_META: Array<RequirementStatusSummary> = [
  { status_code: 'I', status_label: '初始化', count: 0 },
  { status_code: 'D', status_label: '已完成定义', count: 0 },
  { status_code: 'P', status_label: '正在工作', count: 0 },
  { status_code: 'C', status_label: '开发已完成', count: 0 },
  { status_code: 'A', status_label: '测试验收完成', count: 0 },
];

export function useRequirementColumns(): ZqTableGridOptions<RequirementBoardItem>['columns'] {
  const columns: Column<RequirementBoardItem>[] = [
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目名',
      width: 200,
      fixed: 'left',
    },
    {
      key: 'team_name',
      dataKey: 'team_name',
      title: '团队',
      width: 170,
      fixed: 'left',
    },
    {
      key: 'category',
      dataKey: 'category',
      title: '需求类型',
      width: 110,
    },
    {
      key: 'requirement_id',
      dataKey: 'requirement_id',
      title: '需求 ID',
      width: 180,
    },
    {
      key: 'title',
      dataKey: 'title',
      title: '标题',
      width: 260,
    },
    {
      key: 'status_code',
      dataKey: 'status_code',
      title: '状态',
      width: 160,
      fixed: 'right',
    },
    {
      key: 'planned_test_time',
      dataKey: 'planned_test_time',
      title: '计划测试时间',
      width: 170,
    },
    {
      key: 'due_date',
      dataKey: 'due_date',
      title: '到期时间',
      width: 170,
    },
    {
      key: 'workload_kloc',
      dataKey: 'workload_kloc',
      title: '代码量(KLOC)',
      width: 130,
    },
    {
      key: 'workload_man_day',
      dataKey: 'workload_man_day',
      title: '工作量(人天)',
      width: 130,
    },
    {
      key: 'develop_user',
      dataKey: 'develop_user',
      title: '开发人',
      width: 140,
    },
    {
      key: 'test_user',
      dataKey: 'test_user',
      title: '测试人',
      width: 140,
    },
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function formatMetric(value?: null | number, digits = 2) {
  const numeric = Number(value || 0);
  return numeric.toFixed(digits);
}

export function formatPercent(value?: null | number) {
  const numeric = Number(value || 0);
  return `${(numeric * 100).toFixed(1)}%`;
}

export function createEmptyRequirementSummary(): RequirementBoardSummary {
  return {
    total_count: 0,
    total_workload_man_day: 0,
    total_workload_kloc: 0,
    status_summary: STATUS_META.map((item) => ({ ...item })),
    type_summary: [],
    project_summary: [],
    team_summary: [],
  };
}
