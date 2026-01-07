import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ProjectOut } from '#/api/project-manager/project';
import { z } from '#/adapter/form';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '关键词' },
    { component: 'Input', fieldName: 'domain', label: '领域' },
    { component: 'Input', fieldName: 'type', label: '类型' },
    { component: 'Input', fieldName: 'manager_id', label: '项目经理ID' },
    {
      component: 'Select',
      fieldName: 'is_closed',
      label: '是否结项',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'enable_milestone',
      label: '统计里程碑',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'enable_iteration',
      label: '统计迭代',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'enable_quality',
      label: '统计代码质量',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
  ];
}

export function useColumns(
  onActionClick?: OnActionClickFn<ProjectOut>,
): VxeTableGridOptions<ProjectOut>['columns'] {
  return [
    { field: 'name', title: '项目名', minWidth: 160 },
    { field: 'domain', title: '项目领域', minWidth: 120 },
    { field: 'type', title: '项目类型', minWidth: 120 },
    { field: 'code', title: '项目编码', minWidth: 140 },
    {
      field: 'managers_info',
      title: '项目经理',
      minWidth: 160,
      formatter: ({ cellValue }) => (cellValue || []).map((i: any) => i.name).join('、'),
    },
    {
      field: 'is_closed',
      title: '是否结项',
      minWidth: 100,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '关闭', value: true, type: 'info' },
          { label: '开启', value: false, type: 'success' },
        ],
      },
    },
    { field: 'repo_url', title: '制品仓号', minWidth: 200 },
    {
      field: 'enable_milestone',
      title: '统计里程碑',
      minWidth: 120,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '开启', value: true, type: 'success' },
          { label: '关闭', value: false, type: 'danger' },
        ],
      },
    },
    {
      field: 'enable_iteration',
      title: '统计迭代',
      minWidth: 120,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '开启', value: true, type: 'success' },
          { label: '关闭', value: false, type: 'danger' },
        ],
      },
    },
    {
      field: 'enable_quality',
      title: '统计代码质量',
      minWidth: 130,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '开启', value: true, type: 'success' },
          { label: '关闭', value: false, type: 'danger' },
        ],
      },
    },
    { field: 'sys_create_datetime', title: '创建时间', minWidth: 160 },
    {
      align: 'right',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: '项目名',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: ['edit', 'delete'],
      },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: '操作',
      minWidth: 120,
    },
  ];
}

export function getProjectFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '项目名',
      rules: z.string().min(1, '请输入项目名'),
    },
    {
      component: 'Input',
      fieldName: 'domain',
      label: '项目领域',
      rules: z.string().min(1, '请输入项目领域'),
    },
    {
      component: 'Input',
      fieldName: 'type',
      label: '项目类型',
      rules: z.string().min(1, '请输入项目类型'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '项目编码',
      rules: z.string().min(1, '请输入项目编码'),
    },
    {
      component: 'UserSelector',
      fieldName: 'manager_ids',
      label: '项目经理',
      componentProps: { multiple: true, placeholder: '选择项目经理' },
      rules: z.array(z.string()).min(1, '至少选择一位项目经理'),
    },
    {
      component: 'RadioGroup',
      fieldName: 'is_closed',
      label: '是否结项',
      defaultValue: false,
      componentProps: {
        isButton: true,
        options: [
          { label: '否', value: false, type: 'success' },
          { label: '是', value: true, type: 'danger' },
        ],
      },
    },
    {
      component: 'Input',
      fieldName: 'repo_url',
      label: '制品仓',
      rules: z.string().min(1, '请输入制品仓号/地址'),
    },
    {
      component: 'Input',
      fieldName: 'remark',
      label: '备注',
      componentProps: {
        placeholder: '请输入备注',
        rows: 3,
      },
      rules: z.string().min(1, '请输入备注'),
    },
  ];
}
