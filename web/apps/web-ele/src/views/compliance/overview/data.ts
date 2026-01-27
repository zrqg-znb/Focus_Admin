import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PostComplianceStat } from '#/api/compliance';

export function useOverviewColumns(
  onActionClick?: OnActionClickFn<PostComplianceStat>,
): VxeTableGridOptions<PostComplianceStat>['columns'] {
  return [
    { field: 'post_name', title: '岗位名称', minWidth: 150 },
    { field: 'user_count', title: '涉及用户数', minWidth: 100 },
    {
      title: 'Change记录统计',
      children: [
        { field: 'total_risk_count', title: '总数', minWidth: 100 },
        { 
          field: 'unresolved_count', 
          title: '待处理', 
          minWidth: 100,
          slots: { default: 'unresolved' } 
        },
      ]
    },
    {
      title: '分支风险统计',
      children: [
        { field: 'total_branch_count', title: '总数', minWidth: 100 },
        { 
          field: 'unresolved_branch_count', 
          title: '待处理', 
          minWidth: 100,
          slots: { default: 'unresolved_branch' } 
        },
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

export function useOverviewSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'post_name',
      label: '岗位名称',
      componentProps: {
        placeholder: '请输入岗位名称',
      },
    },
  ];
}
