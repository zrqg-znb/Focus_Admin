import type { VbenFormSchema } from '#/adapter/form';
import type { McuPlatformItem, VehicleItem } from '#/api/auto-test-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

export function usePlatformColumns(): ZqTableGridOptions<McuPlatformItem>['columns'] {
  return [
    {
      key: 'name',
      dataKey: 'name',
      title: '平台名称',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'version_code',
      dataKey: 'version_code',
      title: '版本标识',
      width: 140,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'vehicle_count',
      dataKey: 'vehicle_count',
      title: '车型数',
      width: 100,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'remark',
      dataKey: 'remark',
      title: '备注',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 140,
      align: 'center',
      headerAlign: 'center',
      showOverflowTooltip: false,
    },
  ];
}

export function useVehicleColumns(): ZqTableGridOptions<VehicleItem>['columns'] {
  return [
    {
      key: 'name',
      dataKey: 'name',
      title: '车型名称',
      width: 160,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'vehicle_code',
      dataKey: 'vehicle_code',
      title: '车型编号',
      width: 160,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'cdc_platform',
      dataKey: 'cdc_platform',
      title: 'CDC平台',
      width: 160,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'execution_machine',
      dataKey: 'execution_machine',
      title: '执行机器',
      width: 200,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'sys_update_datetime',
      dataKey: 'sys_update_datetime',
      title: '更新时间',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 160,
      align: 'center',
      headerAlign: 'center',
      showOverflowTooltip: false,
    },
  ];
}

export function useVehicleSearchSchema(): VbenFormSchema[] {
  return [{ component: 'Input', fieldName: 'keyword', label: '关键词' }];
}
