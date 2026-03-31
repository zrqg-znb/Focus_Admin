import type { Column } from 'element-plus';
import type { ZqTableGridOptions } from '#/components/zq-table';
import type { ProductFailureModeItem } from '#/api/failure_mode_workflow';

function withCenter<T extends Record<string, any>>(
  columns: Column<T>[],
): ZqTableGridOptions<T>['columns'] {
  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function useProductFailureModeColumns(): ZqTableGridOptions<ProductFailureModeItem>['columns'] {
  return withCenter<ProductFailureModeItem>([
    {
      key: 'subsystem',
      dataKey: 'subsystem',
      title: '子系统',
      width: 150,
    },
    {
      key: 'failure_mode_brief',
      dataKey: 'failure_mode_brief',
      title: '故障模式简述',
      width: 400,
    },
    {
      key: 'sys_create_datetime',
      dataKey: 'sys_create_datetime',
      title: '基线同步时间',
      width: 200,
    },
  ]);
}
