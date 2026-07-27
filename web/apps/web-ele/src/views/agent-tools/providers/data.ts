import type { Provider } from '#/api/agent-tools/providers';
import type { ZqTableGridOptions } from '#/components/zq-table';

export function useProviderColumns(): ZqTableGridOptions<Provider>['columns'] {
  return [
    { key: 'name', dataKey: 'name', title: '档案名称', minWidth: 160 },
    { key: 'base_url', dataKey: 'base_url', title: 'Base URL', minWidth: 280 },
    { key: 'model', dataKey: 'model', title: '模型', minWidth: 160 },
    { key: 'has_api_key', dataKey: 'has_api_key', title: '凭证', width: 90 },
    { key: 'is_active', dataKey: 'is_active', title: '状态', width: 90 },
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
      width: 160,
      fixed: 'right',
      showOverflowTooltip: false,
    },
  ].map((item) => ({ align: 'center', headerAlign: 'center', ...item }));
}
