import type { VbenFormSchema } from '#/adapter/form';
import type {
  SubscriptionManagementProjectRow,
  SubscriptionSubscriberRow,
} from '#/api/integration-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      fieldName: 'keyword',
      label: '配置/项目',
      component: 'Input',
      componentProps: {
        placeholder: '搜索配置名或项目名',
      },
    },
    {
      fieldName: 'project_type',
      label: '项目类型',
      component: 'Select',
      componentProps: {
        clearable: true,
        options: [
          { label: '自研项目', value: 'self_developed' },
          { label: '外包项目', value: 'outsourced' },
          { label: '生态项目', value: 'ecological' },
        ],
        placeholder: '全部类型',
      },
    },
    {
      fieldName: 'enabled',
      label: '配置状态',
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
    {
      fieldName: 'has_subscribers',
      label: '订阅情况',
      component: 'Select',
      componentProps: {
        clearable: true,
        options: [
          { label: '已有订阅人', value: true },
          { label: '暂无订阅人', value: false },
        ],
        placeholder: '全部',
      },
    },
    {
      fieldName: 'has_missing_email',
      label: '邮箱风险',
      component: 'Select',
      componentProps: {
        clearable: true,
        options: [
          { label: '存在无邮箱订阅人', value: true },
          { label: '无邮箱缺失', value: false },
        ],
        placeholder: '全部',
      },
    },
    {
      fieldName: 'create_time',
      label: '创建时间',
      component: 'RangePicker',
      componentProps: {
        valueFormat: 'YYYY-MM-DD',
        clearable: true,
      },
    },
  ];
}

export function useProjectColumns(): ZqTableGridOptions<SubscriptionManagementProjectRow>['columns'] {
  return [
    { type: 'selection', width: 48, fixed: true, align: 'center' },
    { type: 'index', width: 56, label: '#', fixed: true, align: 'center' },
    {
      key: 'name',
      prop: 'name',
      title: '配置名称',
      width: 220,
      fixed: true,
    },
    {
      key: 'project_name',
      prop: 'project_name',
      title: '所属项目',
      width: 190,
    },
    {
      key: 'managers',
      prop: 'managers',
      title: '负责人',
      width: 170,
      slots: { default: 'managers_default' },
    },
    {
      key: 'enabled',
      prop: 'enabled',
      title: '配置状态',
      width: 110,
      slots: { default: 'enabled_default' },
    },
    {
      key: 'subscriber_count',
      prop: 'subscriber_count',
      title: '订阅人数',
      width: 110,
      slots: { default: 'subscriber_count_default' },
    },
    {
      key: 'missing_email_count',
      prop: 'missing_email_count',
      title: '无邮箱',
      width: 100,
      slots: { default: 'missing_email_count_default' },
    },
    {
      key: 'sys_update_datetime',
      prop: 'sys_update_datetime',
      title: '最近更新',
      width: 170,
      slots: { default: 'updated_default' },
    },
    {
      key: 'actions',
      prop: 'actions',
      title: '操作',
      width: 140,
      slots: { default: 'action_default' },
    },
  ];
}

export function useSubscriberColumns(): ZqTableGridOptions<SubscriptionSubscriberRow>['columns'] {
  return [
    { type: 'selection', width: 48, fixed: true, align: 'center' },
    { type: 'index', width: 56, label: '#', fixed: true, align: 'center' },
    {
      key: 'name',
      prop: 'name',
      title: '姓名',
      width: 130,
      slots: { default: 'subscriber_name_default' },
    },
    {
      key: 'username',
      prop: 'username',
      title: '用户名',
      width: 150,
    },
    {
      key: 'email',
      prop: 'email',
      title: '邮箱',
      width: 220,
      slots: { default: 'subscriber_email_default' },
    },
    {
      key: 'enabled',
      prop: 'enabled',
      title: '订阅状态',
      width: 110,
      slots: { default: 'subscriber_enabled_default' },
    },
    {
      key: 'sys_update_datetime',
      prop: 'sys_update_datetime',
      title: '更新时间',
      width: 170,
      slots: { default: 'subscriber_updated_default' },
    },
    {
      key: 'actions',
      prop: 'actions',
      title: '操作',
      width: 100,
      slots: { default: 'subscriber_action_default' },
    },
  ];
}

export function useSubscriberSearchSchema(): VbenFormSchema[] {
  return [
    {
      fieldName: 'keyword',
      label: '订阅人',
      component: 'Input',
      componentProps: {
        placeholder: '搜索姓名/用户名/邮箱',
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
