import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { DeptComplianceStat } from '#/api/compliance';

export function useOverviewColumns(
  onActionClick?: OnActionClickFn<DeptComplianceStat>,
): VxeTableGridOptions<DeptComplianceStat>['columns'] {
  return [
    { field: 'dept_name', title: '部门名称', minWidth: 150 },
    { field: 'user_count', title: '涉及用户数', minWidth: 120 },
    { field: 'total_risk_count', title: '总风险数', minWidth: 120 },
    { 
      field: 'unresolved_count', 
      title: '待处理数', 
      minWidth: 120,
      slots: { default: 'unresolved' } 
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

export function useOverviewSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'dept_name',
      label: '部门名称',
      componentProps: {
        placeholder: '请输入部门名称',
      },
    },
  ];
}
