import type { AutoTestReportDomain } from '../shared/domain';

import type { TestCaseItem } from '#/api/auto-test-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { getAutoTestReportDomainMeta } from '../shared/domain';

export function useCaseColumns(
  domain: AutoTestReportDomain,
): NonNullable<ZqTableGridOptions<TestCaseItem>['columns']> {
  const domainMeta = getAutoTestReportDomainMeta(domain);
  const columns: NonNullable<ZqTableGridOptions<TestCaseItem>['columns']> = [
    {
      type: 'selection',
      width: 60,
      fixed: true,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'platform_name',
      dataKey: 'platform_name',
      title: domainMeta.platformLabel,
      width: 140,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'vehicle_name',
      dataKey: 'vehicle_name',
      title: '车型',
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

  if (domain === 'vehicle') {
    columns.push({
      key: 'viu_code',
      dataKey: 'viu_code',
      title: 'VIU编号',
      width: 120,
      align: 'center',
      headerAlign: 'center',
    });
  }

  if (domain === 'cockpit_soc') {
    columns.push({
      key: 'module',
      dataKey: 'module',
      title: '模块',
      width: 160,
      align: 'center',
      headerAlign: 'center',
    });
  }

  columns.push(
    {
      key: 'case_no',
      dataKey: 'case_no',
      title: '用例编号',
      width: 180,
      align: 'center',
      headerAlign: 'center',
      slots: { header: 'header-case_no' },
    },
    {
      key: 'case_name',
      dataKey: 'case_name',
      title: '用例名称',
      width: 260,
      align: 'center',
      headerAlign: 'center',
      slots: { header: 'header-case_name' },
    },
    {
      key: 'remark',
      dataKey: 'remark',
      title: '备注',
      width: 240,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'latest_execute_time',
      dataKey: 'latest_execute_time',
      title: '最近执行时间',
      width: 180,
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
      width: 220,
      align: 'center',
      headerAlign: 'center',
      showOverflowTooltip: false,
    },
  );

  return columns;
}
