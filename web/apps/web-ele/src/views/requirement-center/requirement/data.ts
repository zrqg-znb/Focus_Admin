import type { Column } from 'element-plus';

import type { VbenFormSchema } from '#/adapter/form';
import type {
  RequirementItem,
  RequirementStatus,
} from '#/api/requirement-center/requirement';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { z } from '#/adapter/form';

export interface OptionItem {
  label: string;
  value: string;
}

export type RequirementTreeRow = RequirementItem & {
  children: RequirementTreeRow[];
  leaf_closed: number;
  leaf_done: number;
  leaf_total: number;
  progress_percent: number;
};

export type RequirementBoardItem = RequirementTreeRow & {
  ancestor_titles: string[];
};

export const REQUIREMENT_VIEW_MODE_OPTIONS = [
  { label: '树表', value: 'tree' },
  { label: '平铺', value: 'flat' },
] as const;

export const REQUIREMENT_STATUS_OPTIONS: Array<{
  label: string;
  value: RequirementStatus;
}> = [
  { label: '草稿', value: 'draft' },
  { label: '待评审', value: 'submitted' },
  { label: '待补充', value: 'need_info' },
  { label: '已接纳', value: 'accepted' },
  { label: '已排期', value: 'planned' },
  { label: '开发中', value: 'in_dev' },
  { label: '待验收', value: 'in_acceptance' },
  { label: '已完成', value: 'done' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已归档', value: 'archived' },
];

export function getStatusLabel(status: RequirementStatus) {
  return (
    REQUIREMENT_STATUS_OPTIONS.find((item) => item.value === status)?.label ||
    status
  );
}

export function isRequirementLeaf(row: RequirementItem) {
  // Prefer runtime tree structure when available (frontend decorated tree keeps `children` always defined).
  const children = (row as any)?.children;
  if (Array.isArray(children) && children.length > 0) {
    return false;
  }
  if (typeof row.is_leaf === 'boolean') {
    return row.is_leaf;
  }
  if (typeof row.child_count === 'number') {
    return row.child_count === 0;
  }
  return !row.child_count;
}

export function formatDateText(value?: null | string) {
  if (!value) return '-';
  return String(value).replace('T', ' ').slice(0, 16);
}

export function dueCountdownText(value?: null | string) {
  if (!value) return '未设置截止时间';
  const target = new Date(value).getTime();
  if (Number.isNaN(target)) return '截止时间格式异常';
  const diff = target - Date.now();
  const day = Math.ceil(diff / (24 * 60 * 60 * 1000));
  if (day > 0) return `剩余 ${day} 天`;
  if (day === 0) return '今天到期';
  return `逾期 ${Math.abs(day)} 天`;
}

export function getLeafProgressPercent(status: RequirementStatus): number {
  const mapper: Record<RequirementStatus, number> = {
    draft: 10,
    need_info: 15,
    submitted: 25,
    accepted: 35,
    planned: 45,
    in_dev: 65,
    in_acceptance: 85,
    done: 100,
    archived: 100,
    rejected: 100,
  };
  return mapper[status] ?? 0;
}

export function getRequirementProgressPercent(row: {
  progress_percent?: number;
  status: RequirementStatus;
}): number {
  const value = Number(row.progress_percent);
  if (Number.isFinite(value) && value >= 0) {
    return Math.max(0, Math.min(100, Math.round(value)));
  }
  return getLeafProgressPercent(row.status);
}

function clampPercent(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

/**
 * Decorate backend tree rows with progress aggregation fields.
 * - Leaf node: progress is derived from status mapping.
 * - Parent node: progress is weighted average of descendant leaf nodes (within current dataset).
 * Note: when a node is non-leaf on backend but has no children in filtered dataset,
 * we fall back to status mapping to avoid 0/0 progress.
 */
export function decorateRequirementTree(
  nodes: RequirementItem[] = [],
): RequirementTreeRow[] {
  const walk = (node: RequirementItem): RequirementTreeRow => {
    const rawChildren = Array.isArray(node.children) ? node.children : [];
    const children = rawChildren.map((item) => walk(item));
    const hasChildren = children.length > 0;

    // Leaf in current dataset OR backend leaf.
    if (!hasChildren) {
      const progress = getLeafProgressPercent(node.status);
      const isDone = node.status === 'done' || node.status === 'archived';
      const isClosed = isDone || node.status === 'rejected';
      return {
        ...(node as RequirementItem),
        children: [],
        leaf_total: 1,
        leaf_done: isDone ? 1 : 0,
        leaf_closed: isClosed ? 1 : 0,
        progress_percent: progress,
      };
    }

    const leafTotal = children.reduce(
      (sum, child) => sum + (child.leaf_total || 0),
      0,
    );
    const safeTotal = Math.max(1, leafTotal);
    const leafDone = children.reduce(
      (sum, child) => sum + (child.leaf_done || 0),
      0,
    );
    const leafClosed = children.reduce(
      (sum, child) => sum + (child.leaf_closed || 0),
      0,
    );
    const weightedProgress =
      children.reduce(
        (sum, child) =>
          sum + clampPercent(child.progress_percent) * (child.leaf_total || 0),
        0,
      ) / safeTotal;

    return {
      ...(node as RequirementItem),
      children,
      leaf_total: leafTotal,
      leaf_done: leafDone,
      leaf_closed: leafClosed,
      progress_percent: clampPercent(weightedProgress),
    };
  };

  return (nodes || []).map((item) => walk(item));
}

export function flattenRequirementTree(
  nodes: RequirementTreeRow[] = [],
  ancestors: string[] = [],
): RequirementBoardItem[] {
  const results: RequirementBoardItem[] = [];
  for (const node of nodes) {
    results.push({
      ...(node as RequirementTreeRow),
      ancestor_titles: ancestors,
    });
    const childNodes = Array.isArray(node.children) ? node.children : [];
    if (childNodes.length > 0) {
      results.push(
        ...flattenRequirementTree(childNodes, [...ancestors, node.title]),
      );
    }
  }
  return results;
}

export function collectExpandableIds(
  nodes: RequirementTreeRow[] = [],
): string[] {
  const ids: string[] = [];
  const walk = (items: RequirementTreeRow[]) => {
    for (const item of items) {
      const children = Array.isArray(item.children) ? item.children : [];
      if (children.length > 0) {
        ids.push(String(item.id));
        walk(children);
      }
    }
  };
  walk(nodes || []);
  return ids;
}

export function useSearchFormSchema(
  typeOptions: OptionItem[],
  sourceOptions: OptionItem[],
  priorityOptions: OptionItem[],
): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'keyword',
      label: '关键词',
      componentProps: { placeholder: '标题/描述/业务价值' },
    },
    {
      component: 'Select',
      fieldName: 'status',
      label: '状态',
      componentProps: {
        clearable: true,
        options: REQUIREMENT_STATUS_OPTIONS,
      },
    },
    {
      component: 'Select',
      fieldName: 'priority',
      label: '优先级',
      componentProps: {
        clearable: true,
        options: priorityOptions,
      },
    },
    {
      component: 'Select',
      fieldName: 'type',
      label: '类型',
      componentProps: {
        clearable: true,
        options: typeOptions,
      },
    },
    {
      component: 'Select',
      fieldName: 'source',
      label: '来源',
      componentProps: {
        clearable: true,
        options: sourceOptions,
      },
    },
    {
      component: 'UserSelector',
      fieldName: 'reviewer_id',
      label: '评审人',
      componentProps: { multiple: false },
    },
    {
      component: 'UserSelector',
      fieldName: 'owner_id',
      label: '责任人',
      componentProps: { multiple: false },
    },
    {
      component: 'Select',
      fieldName: 'overdue',
      label: '逾期',
      componentProps: {
        clearable: true,
        options: [
          { label: '全部', value: undefined },
          { label: '仅逾期', value: true },
          { label: '仅未逾期', value: false },
        ],
      },
    },
  ];
}

export function useZqColumns(): ZqTableGridOptions<RequirementItem>['columns'] {
  const columns: Column<RequirementItem>[] = [
    {
      key: 'title',
      dataKey: 'title',
      title: '需求标题',
      width: 280,
      fixed: true,
    },
    {
      key: 'child_count',
      dataKey: 'child_count',
      title: '子需求数',
      width: 100,
    },
    { key: 'type', dataKey: 'type', title: '类型', width: 120 },
    { key: 'source', dataKey: 'source', title: '来源', width: 120 },
    { key: 'priority', dataKey: 'priority', title: '优先级', width: 100 },
    { key: 'status', dataKey: 'status', title: '状态', width: 120 },
    {
      key: 'submitter_info',
      dataKey: 'submitter_info',
      title: '提单人',
      width: 140,
    },
    {
      key: 'reviewer_info',
      dataKey: 'reviewer_info',
      title: '评审人',
      width: 140,
    },
    { key: 'owner_info', dataKey: 'owner_info', title: '责任人', width: 140 },
    {
      key: 'review_due_at',
      dataKey: 'review_due_at',
      title: '评审截止',
      width: 170,
    },
    { key: 'dev_due_at', dataKey: 'dev_due_at', title: '开发截止', width: 170 },
    {
      key: 'sys_create_datetime',
      dataKey: 'sys_create_datetime',
      title: '创建时间',
      width: 180,
    },
    { key: 'actions', dataKey: 'actions', title: '操作', width: 380 },
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function useTreeColumns(): ZqTableGridOptions<RequirementTreeRow>['columns'] {
  const columns: Column<RequirementTreeRow>[] = [
    {
      key: 'title',
      dataKey: 'title',
      title: '需求标题',
      width: 360,
      fixed: true,
      showOverflowTooltip: false,
    },
    // Keep the tree column as the first "normal" column so ElTable can render
    // the indent/expand icon correctly. Selection column must not be prepended.
    {
      key: '__selection__',
      type: 'selection',
      width: 50,
      fixed: true,
      align: 'center',
      headerAlign: 'center',
    } as any,
    { key: 'status', dataKey: 'status', title: '状态', width: 120 },
    {
      key: 'progress',
      dataKey: 'progress',
      title: '进度',
      width: 200,
      showOverflowTooltip: false,
    },
    { key: 'priority', dataKey: 'priority', title: '优先级', width: 110 },
    { key: 'type', dataKey: 'type', title: '类型', width: 120 },
    { key: 'source', dataKey: 'source', title: '来源', width: 120 },
    {
      key: 'reviewer_info',
      dataKey: 'reviewer_info',
      title: '评审人',
      width: 180,
      showOverflowTooltip: false,
    },
    {
      key: 'owner_info',
      dataKey: 'owner_info',
      title: '责任人',
      width: 180,
      showOverflowTooltip: false,
    },
    {
      key: 'review_due_at',
      dataKey: 'review_due_at',
      title: '评审截止',
      width: 180,
      showOverflowTooltip: false,
    },
    {
      key: 'dev_due_at',
      dataKey: 'dev_due_at',
      title: '开发截止',
      width: 180,
      showOverflowTooltip: false,
    },
    {
      key: 'sys_create_datetime',
      dataKey: 'sys_create_datetime',
      title: '创建时间',
      width: 180,
      showOverflowTooltip: false,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 460,
      showOverflowTooltip: false,
    },
  ];

  return columns.map((column: any) => {
    const key = String(column?.key || column?.dataKey || '');
    const isTreeTitle = key === 'title';
    const isActions = key === 'actions';
    const align = isTreeTitle || isActions ? 'left' : 'center';
    return {
      ...column,
      align,
      headerAlign: align,
    };
  });
}

export function useRequirementFormSchema(
  typeOptions: OptionItem[],
  sourceOptions: OptionItem[],
  priorityOptions: OptionItem[],
): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'title',
      label: '需求标题',
      rules: z.string().min(1, '请输入需求标题'),
    },
    {
      component: 'Select',
      fieldName: 'type',
      label: '需求类型',
      componentProps: { options: typeOptions, clearable: true },
      rules: z.string().min(1, '请选择需求类型'),
    },
    {
      component: 'Select',
      fieldName: 'source',
      label: '需求来源',
      componentProps: { options: sourceOptions, clearable: true },
      rules: z.string().min(1, '请选择需求来源'),
    },
    {
      component: 'Select',
      fieldName: 'priority',
      label: '优先级',
      componentProps: { options: priorityOptions, clearable: true },
      rules: z.string().min(1, '请选择优先级'),
    },
    {
      component: 'UserSelector',
      fieldName: 'reviewer_id',
      label: '评审人',
      componentProps: { multiple: false, placeholder: '选择评审人' },
    },
    {
      component: 'UserSelector',
      fieldName: 'owner_id',
      label: '责任人',
      componentProps: { multiple: false, placeholder: '选择责任人' },
    },
    {
      component: 'Input',
      fieldName: 'description',
      label: '需求描述',
      componentProps: { rows: 4, type: 'textarea' },
    },
    {
      component: 'Input',
      fieldName: 'business_value',
      label: '业务价值',
      componentProps: { rows: 3, type: 'textarea' },
    },
    {
      component: 'Input',
      fieldName: 'acceptance_criteria',
      label: '验收标准',
      componentProps: { rows: 3, type: 'textarea' },
    },
    {
      component: 'Input',
      fieldName: 'attachments_text',
      label: '附件ID',
      componentProps: {
        placeholder: '多个文件ID用逗号分隔',
      },
    },
  ];
}
