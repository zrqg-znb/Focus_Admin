import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { UserComplianceStat } from '#/api/compliance';

export function useDetailColumns(
  onActionClick?: OnActionClickFn<UserComplianceStat>,
): VxeTableGridOptions<UserComplianceStat>['columns'] {
  return [
    { 
      field: 'user_name', 
      title: '用户姓名', 
      minWidth: 150,
      slots: { default: 'user_name' }
    },
    { field: 'post_name', title: '岗位', minWidth: 150 },
    {
      title: 'Change记录统计',
      children: [
        { field: 'total_count', title: '总数', minWidth: 80 },
        { 
          field: 'unresolved_count', 
          title: '待处理', 
          minWidth: 80,
          slots: { default: 'unresolved' } 
        },
      ]
    },
    {
      title: '分支风险统计',
      children: [
        { field: 'total_branch_count', title: '总数', minWidth: 80 },
        { 
          field: 'unresolved_branch_count', 
          title: '待处理', 
          minWidth: 80,
          slots: { default: 'unresolved_branch' } 
        },
        { field: 'fixed_branch_count', title: '已修复', minWidth: 80 },
        { field: 'no_risk_branch_count', title: '无风险', minWidth: 80 },
      ]
    },
    {
      field: 'action',
      title: '操作',
      width: 120,
      fixed: 'right',
      slots: { default: 'action' }
    },
  ];
}

export function useDetailSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'user_name',
      label: '用户姓名',
      componentProps: {
        placeholder: '请输入用户姓名',
      },
    },
    {
      component: 'DatePicker',
      fieldName: 'dateRange',
      label: '时间范围',
      componentProps: {
        type: 'daterange',
        rangeSeparator: '至',
        startPlaceholder: '开始日期',
        endPlaceholder: '结束日期',
        valueFormat: 'YYYY-MM-DD HH:mm:ss',
      },
    },
  ];
}
