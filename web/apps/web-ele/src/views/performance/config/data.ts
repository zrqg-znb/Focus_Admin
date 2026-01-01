import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PerformanceIndicator } from '#/api/core/performance';
import { z } from '#/adapter/form';
import { useUserStore } from '@vben/stores';

/**
 * Get search form schema
 */
export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'search',
      label: '指标名称',
      componentProps: {
        placeholder: '请输入指标名称',
      },
    },
    {
      component: 'Input',
      fieldName: 'module',
      label: '所属模块',
      componentProps: {
        placeholder: '请输入所属模块',
      },
    },
    {
      component: 'Input',
      fieldName: 'project',
      label: '所属项目',
      componentProps: {
        placeholder: '请输入所属项目',
      },
    },
    {
      component: 'Input',
      fieldName: 'chip_type',
      label: '芯片类型',
      componentProps: {
        placeholder: '请输入芯片类型',
      },
    },
  ];
}

/**
 * Get form schema for Create/Edit
 */
export function getFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'code',
      label: 'Code',
      componentProps: {
        placeholder: '请输入业务唯一标识',
      },
      rules: z.string().min(1, '请输入Code'),
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: '指标名称',
      rules: z.string().min(1, '请输入指标名称'),
    },
    {
      component: 'Input',
      fieldName: 'project',
      label: '所属项目',
      rules: z.string().min(1, '请输入所属项目'),
    },
    {
      component: 'Input',
      fieldName: 'module',
      label: '所属模块',
      rules: z.string().min(1, '请输入所属模块'),
    },
    {
      component: 'Input',
      fieldName: 'chip_type',
      label: '芯片类型',
      rules: z.string().min(1, '请输入芯片类型'),
    },
    {
      component: 'Select',
      fieldName: 'value_type',
      label: '值类型',
      defaultValue: 'avg',
      componentProps: {
        options: [
            { label: '平均值', value: 'avg' },
            { label: '最大值', value: 'max' },
            { label: '最小值', value: 'min' },
        ]
      },
    },
    {
      component: 'InputNumber',
      fieldName: 'baseline_value',
      label: '基线值',
      componentProps: {
        class: 'w-full',
      },
      rules: z.number().min(0, '请输入有效的基线值'),
    },
    {
      component: 'Input',
      fieldName: 'baseline_unit',
      label: '单位',
    },
    {
      component: 'InputNumber',
      fieldName: 'fluctuation_range',
      label: '允许浮动',
      componentProps: {
        class: 'w-full',
      },
      defaultValue: 0,
    },
    {
      component: 'Select',
      fieldName: 'fluctuation_direction',
      label: '浮动方向',
      defaultValue: 'none',
      componentProps: {
        options: [
            { label: '越大越好', value: 'up' },
            { label: '越小越好', value: 'down' },
            { label: '无方向', value: 'none' },
        ]
      },
    },
    {
      component: 'UserSelector', // Reusing the component from User module
      fieldName: 'owner_id',
      label: '责任人',
      componentProps: {
        placeholder: '请选择责任人',
        multiple: false,
      },
      rules: z.string().min(1, '请选择责任人'),
    },
  ];
}

/**
 * Get table columns configuration
 */
export function useColumns(
  onActionClick?: OnActionClickFn<PerformanceIndicator>,
): VxeTableGridOptions<PerformanceIndicator>['columns'] {
  const userStore = useUserStore();

  return [
    {
      type: 'checkbox',
      width: 60,
      align: 'center',
      fixed: 'left',
    },
    {
      field: 'code',
      title: 'Code',
      minWidth: 150,
    },
    {
      field: 'name',
      title: '名称',
      minWidth: 150,
    },
    {
      field: 'project',
      title: '项目',
      minWidth: 100,
    },
    {
      field: 'module',
      title: '模块',
      minWidth: 100,
    },
    {
      field: 'chip_type',
      title: '芯片',
      minWidth: 100,
    },
    {
      field: 'baseline_value',
      title: '基线值',
      minWidth: 120,
      formatter: ({ row }) => `${row.baseline_value} ${row.baseline_unit || ''}`,
    },
    {
      field: 'fluctuation_range',
      title: '允许浮动',
      minWidth: 100,
    },
    {
      field: 'fluctuation_direction',
      title: '方向',
      minWidth: 100,
      formatter: ({ row }) => {
        if (row.fluctuation_direction === 'up') return '越大越好';
        if (row.fluctuation_direction === 'down') return '越小越好';
        return '-';
      }
    },
    {
      field: 'owner_name',
      title: '责任人',
      minWidth: 100,
      formatter: ({ row }) => {
          return row.owner_name || '-';
      },
    },
    {
      field: 'action',
      title: '操作',
      fixed: 'right',
      align: 'center',
      width: 150,
      cellRender: {
        name: 'CellOperation',
        attrs: {
            onClick: onActionClick
        },
        options: [
            {
                code: 'edit',
                text: '编辑',
                disabled: (row: PerformanceIndicator) => {
                    const currentUserId = userStore.userInfo?.id;
                    const isSuperuser = userStore.userInfo?.is_superuser || userStore.userInfo?.username === 'admin';
                    const rowOwnerId = row.owner_id;
                    // 如果是超级管理员，或者当前用户是责任人，则不禁用
                    return !(isSuperuser || String(rowOwnerId) === String(currentUserId));
                }
            },
            {
                code: 'delete',
                text: '删除',
                status: 'danger',
                disabled: (row: PerformanceIndicator) => {
                    const currentUserId = userStore.userInfo?.id;
                    const isSuperuser = userStore.userInfo?.is_superuser || userStore.userInfo?.username === 'admin';
                    const rowOwnerId = row.owner_id;
                    return !(isSuperuser || String(rowOwnerId) === String(currentUserId));
                }
            }
        ],
      }
    },
  ];
}
