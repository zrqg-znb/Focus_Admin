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
  if (typeof row.is_leaf === 'boolean') {
    return row.is_leaf;
  }
  return !row.child_count;
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
    { key: 'child_count', dataKey: 'child_count', title: '子需求数', width: 100 },
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
