import type { VbenFormProps } from '@vben/common-ui';
import type { VxeGridProps } from '#/adapter/vxe-table';

export function useColumns() {
  const columns: VxeGridProps['columns'] = [
    {
      field: 'name',
      title: '项目名称',
      minWidth: 150,
      fixed: 'left',
    },
    {
      field: 'code',
      title: '项目编码',
      width: 120,
    },
    {
      field: 'domain',
      title: '项目领域',
      width: 120,
    },
    {
      field: 'type',
      title: '项目类型',
      width: 120,
    },
    {
      field: 'managers',
      title: '项目经理',
      minWidth: 150,
      slots: { default: 'managers' },
    },
    {
      field: 'enable_milestone',
      title: '里程碑',
      width: 100,
      slots: { default: 'enable_milestone' },
    },
    {
      field: 'enable_iteration',
      title: '迭代',
      width: 100,
      slots: { default: 'enable_iteration' },
    },
    {
      field: 'enable_quality',
      title: '代码质量',
      width: 100,
      slots: { default: 'enable_quality' },
    },
    {
      field: 'is_closed',
      title: '状态',
      width: 100,
      slots: { default: 'status' },
    },
    {
      field: 'action',
      title: '操作',
      width: 140,
      fixed: 'right',
      slots: { default: 'action' },
    },
  ];
  return columns;
}

export function useSearchFormSchema(): VbenFormProps {
  return {
    schema: [
      {
        fieldName: 'keyword',
        label: '关键字',
        component: 'Input',
        componentProps: {
          placeholder: '项目名称/编码',
          clearable: true,
        },
      },
      {
        fieldName: 'domain',
        label: '领域',
        component: 'Input',
        componentProps: {
          clearable: true,
        },
      },
      {
        fieldName: 'type',
        label: '类型',
        component: 'Input',
        componentProps: {
          clearable: true,
        },
      },
      {
        fieldName: 'is_closed',
        label: '状态',
        component: 'Select',
        componentProps: {
          clearable: true,
          options: [
            { label: '进行中', value: false },
            { label: '已结项', value: true },
          ],
        },
      },
    ],
  };
}

export function useFormSchema(): VbenFormProps {
  return {
    schema: [
      {
        fieldName: 'name',
        label: '项目名称',
        component: 'Input',
        rules: 'required',
      },
      {
        fieldName: 'code',
        label: '项目编码',
        component: 'Input',
        rules: 'required',
      },
      {
        fieldName: 'domain',
        label: '项目领域',
        component: 'Input',
        rules: 'required',
      },
      {
        fieldName: 'type',
        label: '项目类型',
        component: 'Input',
        rules: 'required',
      },
      {
        fieldName: 'manager_ids',
        label: '项目经理',
        component: 'Select',
        componentProps: {
          multiple: true,
          filterable: true,
          options: [], // 这里需要在组件中动态加载用户列表
          placeholder: '请选择项目经理',
        },
        rules: 'required',
      },
      {
        fieldName: 'repo_url',
        label: '制品仓地址',
        component: 'Input',
      },
      {
        fieldName: 'remark',
        label: '备注',
        component: 'Textarea',
      },
      {
        fieldName: 'enable_milestone',
        label: '里程碑统计',
        component: 'Switch',
        defaultValue: true,
        help: '开启后将自动创建里程碑看板',
      },
      {
        fieldName: 'enable_iteration',
        label: '迭代统计',
        component: 'Switch',
        defaultValue: true,
      },
      {
        fieldName: 'enable_quality',
        label: '代码质量',
        component: 'Switch',
        defaultValue: true,
      },
    ],
  };
}
