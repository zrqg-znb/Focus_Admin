import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { UserComplianceStat } from '#/api/compliance';

export function useDetailColumns(
  onActionClick?: OnActionClickFn<UserComplianceStat>,
): VxeTableGridOptions<UserComplianceStat>['columns'] {
  return [
    { field: 'user_name', title: '用户姓名', minWidth: 120 },
    { field: 'dept_name', title: '部门', minWidth: 150 },
    { field: 'total_count', title: '总风险数', minWidth: 120 },
    { 
      field: 'unresolved_count', 
      title: '待处理', 
      minWidth: 120,
      slots: { default: 'unresolved' } 
    },
    { field: 'fixed_count', title: '已修复', minWidth: 120 },
    { field: 'no_risk_count', title: '无风险', minWidth: 120 },
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
  ];
}
