import type { AutoTestReportDomain } from '../shared/domain';

import type { VbenFormSchema } from '#/adapter/form';
import type { McuPlatformItem, VehicleItem } from '#/api/auto-test-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { getAutoTestReportDomainMeta } from '../shared/domain';

export function usePlatformColumns(
  domain: AutoTestReportDomain,
): ZqTableGridOptions<McuPlatformItem>['columns'] {
  const domainMeta = getAutoTestReportDomainMeta(domain);
  return [
    {
      key: 'name',
      dataKey: 'name',
      title: domainMeta.platformLabel,
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

export function useVehicleColumns(
  domain: AutoTestReportDomain,
): ZqTableGridOptions<VehicleItem>['columns'] {
  const columns: ZqTableGridOptions<VehicleItem>['columns'] = [
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
      key: 'responsible_users',
      dataKey: 'responsible_users',
      title: '责任人',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
  ];

  if (domain !== 'vehicle') {
    columns.push({
      key: 'cdc_platform',
      dataKey: 'cdc_platform',
      title: 'CDC平台',
      width: 160,
      align: 'center',
      headerAlign: 'center',
    });
  }

  columns.push({
    key: 'execution_machine',
    dataKey: 'execution_machine',
    title: '执行机器',
    width: 200,
    align: 'center',
    headerAlign: 'center',
  });

  if (domain === 'vehicle') {
    columns.push({
      key: 'viu_codes',
      dataKey: 'viu_codes',
      title: '可用 VIU 编号',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    });
  }

  columns.push(
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
  );

  return columns;
}

export function useVehicleSearchSchema(): VbenFormSchema[] {
  return [{ component: 'Input', fieldName: 'keyword', label: '关键词' }];
}
