import type { VbenFormSchema } from '#/adapter/form';
import type {
  HardwarePoint,
  PlatformConfig,
  ViuHardwarePlatform,
} from '#/api/project-manager/hardware';
import type { ZqTableGridOptions } from '#/components/zq-table';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [{ component: 'Input', fieldName: 'keyword', label: '关键词' }];
}

export function usePointColumns(): ZqTableGridOptions<HardwarePoint>['columns'] {
  const columns: NonNullable<ZqTableGridOptions<HardwarePoint>['columns']> = [
    { key: 'code', dataKey: 'code', title: '硬件点位', width: 160 },
    { key: 'boards', dataKey: 'boards', title: '单板列表', width: 260 },
    { key: 'remark', dataKey: 'remark', title: '备注', width: 220 },
    {
      key: 'sys_create_datetime',
      dataKey: 'sys_create_datetime',
      title: '创建时间',
      width: 180,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 120,
      showOverflowTooltip: false,
    },
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function usePlatformColumns(
  title: string,
): ZqTableGridOptions<PlatformConfig>['columns'] {
  const columns: NonNullable<ZqTableGridOptions<PlatformConfig>['columns']> = [
    { key: 'name', dataKey: 'name', title, width: 240 },
    { key: 'remark', dataKey: 'remark', title: '备注', width: 240 },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 120,
      showOverflowTooltip: false,
    },
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function useViuPlatformColumns(): ZqTableGridOptions<ViuHardwarePlatform>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<ViuHardwarePlatform>['columns']
  > = [
    { key: 'name', dataKey: 'name', title: 'VIU 硬件单板型号', width: 240 },
    { key: 'configs', dataKey: 'configs', title: '典配列表', width: 260 },
    { key: 'remark', dataKey: 'remark', title: '备注', width: 220 },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 120,
      showOverflowTooltip: false,
    },
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}
