import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { EmailDeliveryRow } from '#/api/integration-report';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      fieldName: 'status',
      label: '状态',
      component: 'Select',
      componentProps: {
        placeholder: '选择状态',
        options: [
          { label: '全部', value: undefined },
          { label: '待发送', value: 'pending' },
          { label: '已发送', value: 'sent' },
          { label: '发送失败', value: 'failed' },
        ],
        clearable: true,
      },
    },
    {
      fieldName: 'to_email',
      label: '收件邮箱',
      component: 'Input',
      componentProps: {
        placeholder: '输入收件邮箱',
      },
    },
    {
      fieldName: 'user_id',
      label: '用户ID',
      component: 'Input',
      componentProps: {
        placeholder: '输入用户ID',
      },
    },
    {
      fieldName: 'start_date',
      label: '开始日期',
      component: 'DatePicker',
      componentProps: {
        placeholder: '选择开始日期',
        type: 'date',
        valueFormat: 'YYYY-MM-DD',
      },
    },
    {
      fieldName: 'end_date',
      label: '结束日期',
      component: 'DatePicker',
      componentProps: {
        placeholder: '选择结束日期',
        type: 'date',
        valueFormat: 'YYYY-MM-DD',
      },
    },
  ];
}

export function useColumns(
  onActionClick?: OnActionClickFn<EmailDeliveryRow>,
): VxeTableGridOptions<EmailDeliveryRow>['columns'] {
  return [
    { type: 'seq', width: 50, fixed: 'left' },
    { field: 'record_date', title: '记录日期', width: 120 },
    { field: 'user_name', title: '用户', minWidth: 120 },
    { field: 'to_email', title: '收件邮箱', minWidth: 180 },
    { field: 'subject', title: '邮件主题', minWidth: 200 },
    {
      field: 'status',
      title: '状态',
      width: 100,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '待发送', value: 'pending', type: 'warning' },
          { label: '已发送', value: 'sent', type: 'success' },
          { label: '发送失败', value: 'failed', type: 'danger' },
        ],
      },
    },
    {
      field: 'error_message',
      title: '错误信息',
      minWidth: 200,
      showOverflow: 'tooltip',
    },
    { field: 'sys_create_datetime', title: '创建时间', width: 160 },
  ];
}