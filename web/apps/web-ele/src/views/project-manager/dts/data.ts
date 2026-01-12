import type { VxeGridProps } from '#/adapter/vxe-table';

export function useDashboardColumns(onNameClick: (row: any) => void): VxeGridProps['columns'] {
  return [
    { type: 'seq', width: 50 },
    { 
      field: 'project_name', 
      title: '项目名称',
      slots: { default: 'name_slot' }
    },
    { field: 'project_domain', title: '领域', width: 120 },
    { field: 'project_type', title: '类型', width: 120 },
    { field: 'project_managers', title: '项目经理' },
    { field: 'ws_id', title: '中台配置ID', width: 150 },
    { field: 'root_teams_count', title: '责任团队数', width: 100 },
    { 
      field: 'has_data_today', 
      title: '今日数据', 
      width: 100,
      slots: { default: 'status_slot' }
    },
    { title: '操作', width: 100, slots: { default: 'action_slot' } },
  ];
}

export function useDetailColumns(): VxeGridProps['columns'] {
  return [
    { field: 'team_name', title: '团队名称', treeNode: true, width: 250, fixed: 'left' },
    { field: 'latest_data.di', title: 'DI值', width: 80 },
    { field: 'latest_data.target_di', title: '目标DI', width: 80 },
    { field: 'latest_data.today_in_di', title: '今日流入', width: 100 },
    { field: 'latest_data.today_out_di', title: '今日流出', width: 100 },
    { field: 'latest_data.solve_rate', title: '解决率', width: 100 },
    { field: 'latest_data.critical_solve_rate', title: '严重解决率', width: 120 },
    { field: 'latest_data.fatal_num', title: '关键', width: 80 },
    { field: 'latest_data.major_num', title: '严重', width: 80 },
    { field: 'latest_data.minor_num', title: '提示', width: 80 },
    { field: 'latest_data.suggestion_num', title: '建议', width: 80 },
  ];
}

export function useSearchFormSchema() {
  return [
    {
      fieldName: 'keyword',
      label: '项目名称',
      component: 'Input',
      componentProps: {
        placeholder: '请输入项目名称',
      },
    },
  ];
}
