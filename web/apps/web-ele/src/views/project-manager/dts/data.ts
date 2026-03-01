import type { ZqTableGridOptions } from '#/components/zq-table';

function withCenterAlign(columns: Record<string, any>[]) {
  return columns.map((column) => {
    const nextColumn: Record<string, any> = {
      ...column,
      align: column.align ?? 'center',
      headerAlign: column.headerAlign ?? 'center',
    };
    if (Array.isArray(column.children)) {
      nextColumn.children = withCenterAlign(column.children);
    }
    return nextColumn;
  });
}

export function useDashboardColumns(): ZqTableGridOptions['columns'] {
  return withCenterAlign([
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目名称',
      minWidth: 180,
      fixed: true,
    },
    { key: 'project_domain', dataKey: 'project_domain', title: '领域', width: 120 },
    { key: 'project_type', dataKey: 'project_type', title: '类型', width: 120 },
    { key: 'project_managers', dataKey: 'project_managers', title: '项目经理', minWidth: 160 },
    { key: 'ws_id', dataKey: 'ws_id', title: '中台配置ID', width: 150 },
    { key: 'root_teams_count', dataKey: 'root_teams_count', title: '责任团队数', width: 110 },
    {
      key: 'has_data_today',
      dataKey: 'has_data_today',
      title: '今日数据',
      width: 100,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 100,
      fixed: 'right',
    },
  ]);
}

export function useDetailColumns(): ZqTableGridOptions['columns'] {
  return withCenterAlign([
    {
      key: 'team_name',
      dataKey: 'team_name',
      title: '团队名称',
      minWidth: 250,
      fixed: true,
    },
    { key: 'di', dataKey: 'di', title: 'DI值', width: 90 },
    { key: 'target_di', dataKey: 'target_di', title: '目标DI', width: 90 },
    { key: 'today_in_di', dataKey: 'today_in_di', title: '今日流入', width: 100 },
    { key: 'today_out_di', dataKey: 'today_out_di', title: '今日流出', width: 100 },
    { key: 'solve_rate', dataKey: 'solve_rate', title: '解决率', width: 100 },
    { key: 'critical_solve_rate', dataKey: 'critical_solve_rate', title: '严重解决率', width: 120 },
    { key: 'fatal_num', dataKey: 'fatal_num', title: '关键', width: 80 },
    { key: 'major_num', dataKey: 'major_num', title: '严重', width: 80 },
    { key: 'minor_num', dataKey: 'minor_num', title: '提示', width: 80 },
    { key: 'suggestion_num', dataKey: 'suggestion_num', title: '建议', width: 80 },
  ]);
}

export function useDefectListColumns(): ZqTableGridOptions['columns'] {
  return withCenterAlign([
    { key: 'defectNo', dataKey: 'defectNo', title: '问题单号', width: 160 },
    { key: 'brief', dataKey: 'brief', title: '简述', minWidth: 220 },
    { key: 'severity', dataKey: 'severity', title: '严重程度', width: 100 },
    { key: 'currentHandler', dataKey: 'currentHandler', title: '当前处理人', width: 150 },
    { key: 'currentStageStayDay', dataKey: 'currentStageStayDay', title: '停留天数', width: 100 },
    { key: 'progress', dataKey: 'progress', title: '进展', minWidth: 220 },
  ]);
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
