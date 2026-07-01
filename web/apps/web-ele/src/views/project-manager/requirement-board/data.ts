import type {
  RequirementBoardItem,
  RequirementBoardSummary,
  RequirementStatusSummary,
  RequirementTimeField,
} from '#/api/project-manager/requirement_board';
import type { ZqTableGridOptions } from '#/components/zq-table';

export interface RequirementStatusMeta extends RequirementStatusSummary {
  accent: string;
  badgeClass: string;
  description: string;
  shortHint: string;
}

export const CATEGORY_OPTIONS = [
  { label: 'AR', value: 'AR' },
  { label: 'DR', value: 'DR' },
  { label: 'SR', value: 'SR' },
];

export const VERIFICATION_POLICY_OPTIONS = [
  { label: '测试验证', value: '10000001' },
  { label: '设计评审', value: '10000002' },
  { label: '由下级分解需求验证', value: '10000006' },
  { label: '开发自验证', value: '10000009' },
  { label: '协同第三方验证', value: '10000010' },
  { label: '免验证', value: '10000011' },
];

export const DEFAULT_CATEGORIES = CATEGORY_OPTIONS.map((item) => item.value);

export const TIME_FIELD_OPTIONS: Array<{
  label: string;
  value: RequirementTimeField;
}> = [
  { label: '测试完成时间', value: 'accepted_time' },
  { label: '开发完成时间', value: 'completed_time' },
  { label: '计划完成时间', value: 'due_date' },
  { label: '计划转测时间', value: 'planned_test_time' },
];

export const DEFAULT_TIME_FIELD: RequirementTimeField = 'accepted_time';

export const SCHEDULE_STATE_OPTIONS = [
  { label: 'I · Initial', value: 'I' },
  { label: 'D · Defined', value: 'D' },
  { label: 'P · In-Progress', value: 'P' },
  { label: 'C · Completed', value: 'C' },
  { label: 'A · Accepted', value: 'A' },
];

export const DELAY_STATUS_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '正常', value: 'normal' },
  { label: '延期', value: 'delayed' },
];

export const STATUS_META: RequirementStatusMeta[] = [
  {
    status_code: 'I',
    status_label: '初始化',
    count: 0,
    count_rate: 0,
    workload_man_day: 0,
    workload_kloc: 0,
    accent: '#b91c1c',
    badgeClass: 'requirement-status-badge--i',
    description: '需求刚创建或进入初始化阶段，尚未完成定义。',
    shortHint: '待定义',
  },
  {
    status_code: 'D',
    status_label: '已定义完成',
    count: 0,
    count_rate: 0,
    workload_man_day: 0,
    workload_kloc: 0,
    accent: '#1d4ed8',
    badgeClass: 'requirement-status-badge--d',
    description: '需求已定义完成，等待进入开发或排期推进。',
    shortHint: '待开发',
  },
  {
    status_code: 'P',
    status_label: '开发中',
    count: 0,
    count_rate: 0,
    workload_man_day: 0,
    workload_kloc: 0,
    accent: '#4338ca',
    badgeClass: 'requirement-status-badge--p',
    description: '需求正在开发处理中，尚未达到转测状态。',
    shortHint: '推进中',
  },
  {
    status_code: 'C',
    status_label: '已开发完成（转测）',
    count: 0,
    count_rate: 0,
    workload_man_day: 0,
    workload_kloc: 0,
    accent: '#c2410c',
    badgeClass: 'requirement-status-badge--c',
    description: '需求已开发完成并转测，等待测试验收。',
    shortHint: '待验收',
  },
  {
    status_code: 'A',
    status_label: '测试完成（已置 A）',
    count: 0,
    count_rate: 0,
    workload_man_day: 0,
    workload_kloc: 0,
    accent: '#15803d',
    badgeClass: 'requirement-status-badge--a',
    description: '需求已测试完成并置 A，可视为验收完成。',
    shortHint: '已完成',
  },
];

export const STATUS_META_MAP = Object.fromEntries(
  STATUS_META.map((item) => [item.status_code, item]),
);

const filterHeaderSlot = { header: 'requirement-filter-header' };

export function useRequirementColumns(): ZqTableGridOptions<RequirementBoardItem>['columns'] {
  const columns = [
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目名',
      width: 220,
      fixed: true as const,
      slots: filterHeaderSlot,
    },
    {
      key: 'team_name',
      dataKey: 'team_name',
      title: '团队',
      width: 190,
      fixed: true as const,
      slots: filterHeaderSlot,
    },
    {
      key: 'responsible_pl_group_name',
      dataKey: 'responsible_pl_group_name',
      title: '责任PL组',
      width: 180,
      fixed: true as const,
      slots: filterHeaderSlot,
    },
    {
      key: 'status_code',
      dataKey: 'status_code',
      title: '状态',
      width: 200,
      fixed: true as const,
      slots: filterHeaderSlot,
    },
    {
      key: 'category',
      dataKey: 'category',
      title: '需求类型',
      width: 160,
      slots: filterHeaderSlot,
    },
    {
      key: 'verification_policy_label',
      dataKey: 'verification_policy_label',
      title: '验证策略',
      width: 200,
      slots: filterHeaderSlot,
    },
    {
      key: 'requirement_id',
      dataKey: 'requirement_id',
      title: '需求 ID',
      width: 210,
      slots: filterHeaderSlot,
    },
    {
      key: 'title',
      dataKey: 'title',
      title: '需求标题',
      width: 320,
      slots: filterHeaderSlot,
    },
    {
      key: 'planned_test_time',
      dataKey: 'planned_test_time',
      title: '计划转测时间',
      width: 250,
      slots: filterHeaderSlot,
    },
    {
      key: 'due_date',
      dataKey: 'due_date',
      title: '计划完成时间',
      width: 250,
      slots: filterHeaderSlot,
    },
    {
      key: 'completed_time',
      dataKey: 'completed_time',
      title: '开发完成时间',
      width: 250,
      slots: filterHeaderSlot,
    },
    {
      key: 'accepted_time',
      dataKey: 'accepted_time',
      title: '测试完成时间',
      width: 250,
      slots: filterHeaderSlot,
    },
    {
      key: 'is_dev_delayed',
      dataKey: 'is_dev_delayed',
      title: '开发延期',
      width: 150,
      slots: filterHeaderSlot,
    },
    {
      key: 'is_test_delayed',
      dataKey: 'is_test_delayed',
      title: '测试延期',
      width: 150,
      slots: filterHeaderSlot,
    },
    {
      key: 'workload_man_day',
      dataKey: 'workload_man_day',
      title: '工作量(人天)',
      width: 132,
    },
    {
      key: 'workload_kloc',
      dataKey: 'workload_kloc',
      title: '代码量(KLOC)',
      width: 132,
    },
    {
      key: 'develop_user_display',
      dataKey: 'develop_user_display',
      title: '开发责任人',
      width: 260,
      slots: filterHeaderSlot,
    },
    {
      key: 'test_user_display',
      dataKey: 'test_user_display',
      title: '测试责任人',
      width: 260,
      slots: filterHeaderSlot,
    },
  ];

  return columns.map((column) => {
    return {
      align: 'center' as const,
      headerAlign: 'center' as const,
      ...column,
    };
  });
}

export function formatMetric(value?: null | number, digits = 2) {
  const numeric = Number(value || 0);
  return numeric.toFixed(digits);
}

export function formatPercent(value?: null | number) {
  const numeric = Number(value || 0);
  return `${(numeric * 100).toFixed(1)}%`;
}

export function formatDateTime(value?: null | string) {
  return value || '--';
}

export function createEmptyRequirementSummary(): RequirementBoardSummary {
  return {
    total_count: 0,
    total_workload_man_day: 0,
    total_workload_kloc: 0,
    status_summary: STATUS_META.map((item) => ({
      status_code: item.status_code,
      status_label: item.status_label,
      count: 0,
      count_rate: 0,
      workload_man_day: 0,
      workload_kloc: 0,
    })),
    type_summary: [],
    project_summary: [],
    team_summary: [],
    pl_group_summary: [],
    user_summary: { develop_users: [], test_users: [] },
    dispatch_rate: {
      p_total: 0,
      develop_owner_count: 0,
      develop_owner_rate: 0,
      test_owner_count: 0,
      test_owner_rate: 0,
    },
    plan_refresh_rate: {
      planned_test_time_count: 0,
      planned_test_time_rate: 0,
      due_date_count: 0,
      due_date_rate: 0,
    },
    delay_summary: {
      development: { count: 0, rate: 0, preview_items: [] },
      acceptance: { count: 0, rate: 0, preview_items: [] },
    },
    delivery_delay_rankings: {
      pl_group: { development: [], acceptance: [] },
      project: { development: [], acceptance: [] },
    },
    development_delivery_trend: [],
    acceptance_delivery_trend: [],
  };
}
