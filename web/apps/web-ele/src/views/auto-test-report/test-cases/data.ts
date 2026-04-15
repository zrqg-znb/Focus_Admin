import type { TestCaseItem } from '#/api/auto-test-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

export function useCaseColumns(): ZqTableGridOptions<TestCaseItem>['columns'] {
  return [
    {
      type: 'selection',
      width: 60,
      fixed: 'left',
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'platform_name',
      dataKey: 'platform_name',
      title: 'MCU平台',
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
      key: 'case_no',
      dataKey: 'case_no',
      title: '用例编号',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'case_name',
      dataKey: 'case_name',
      title: '用例名称',
      width: 260,
      align: 'center',
      headerAlign: 'center',
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
  ];
}
