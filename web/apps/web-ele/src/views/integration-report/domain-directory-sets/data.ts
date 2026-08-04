import type { VbenFormSchema } from '#/adapter/form';
import type { DomainDirectorySetRow } from '#/api/integration-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      fieldName: 'keyword',
      label: '关键词',
      component: 'Input',
      componentProps: {
        placeholder: '搜索配置集/领域/目录',
      },
    },
    {
      fieldName: 'enabled',
      label: '状态',
      component: 'Select',
      componentProps: {
        clearable: true,
        options: [
          { label: '启用', value: true },
          { label: '停用', value: false },
        ],
        placeholder: '全部状态',
      },
    },
  ];
}

export function useColumns(): ZqTableGridOptions<DomainDirectorySetRow>['columns'] {
  return [
    { type: 'index', width: 56, label: '#', fixed: true, align: 'center' },
    {
      key: 'name',
      prop: 'name',
      title: '配置集名称',
      width: 240,
      fixed: true,
    },
    {
      key: 'description',
      prop: 'description',
      title: '说明',
      width: 260,
      minWidth: 260,
      slots: { default: 'description_default' },
    },
    {
      key: 'enabled',
      prop: 'enabled',
      title: '状态',
      width: 100,
      slots: { default: 'enabled_default' },
    },
    {
      key: 'domain_count',
      prop: 'domain_count',
      title: '领域数',
      width: 100,
      align: 'right',
    },
    {
      key: 'directory_count',
      prop: 'directory_count',
      title: '目录数',
      width: 100,
      align: 'right',
    },
    {
      key: 'sys_update_datetime',
      prop: 'sys_update_datetime',
      title: '最近更新',
      width: 180,
      slots: { default: 'updated_default' },
    },
    {
      key: 'actions',
      prop: 'actions',
      title: '操作',
      width: 150,
      slots: { default: 'action_default' },
    },
  ];
}
