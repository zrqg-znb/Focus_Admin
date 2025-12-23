import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { OperationLog } from '#/api/core/operation-log';

import { $t } from '@vben/locales';

export function getStatusOptions() {
  return [
    { type: 'success', label: $t('operationLog.statusSuccess'), value: true },
    { type: 'danger', label: $t('operationLog.statusFailed'), value: false },
  ];
}

export function getMethodOptions() {
  return [
    { label: 'GET', value: 'GET', type: 'info' },
    { label: 'POST', value: 'POST', type: 'success' },
    { label: 'PUT', value: 'PUT', type: 'warning' },
    { label: 'DELETE', value: 'DELETE', type: 'danger' },
    { label: 'PATCH', value: 'PATCH', type: 'primary' },
  ];
}

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'request_username',
      label: $t('operationLog.username'),
      componentProps: {
        placeholder: $t('operationLog.searchPlaceholder', [
          $t('operationLog.username'),
        ]),
      },
    },
    {
      component: 'Select',
      fieldName: 'request_method',
      label: $t('operationLog.method'),
      componentProps: {
        placeholder: $t('operationLog.selectMethod'),
        options: getMethodOptions(),
        clearable: true,
      },
    },
    {
      component: 'Input',
      fieldName: 'request_path',
      label: $t('operationLog.path'),
      componentProps: {
        placeholder: $t('operationLog.searchPlaceholder', [
          $t('operationLog.path'),
        ]),
      },
    },
    {
      component: 'Select',
      fieldName: 'status',
      label: $t('operationLog.status'),
      componentProps: {
        placeholder: $t('operationLog.selectStatus'),
        options: getStatusOptions(),
        clearable: true,
      },
    },
  ];
}

export function useColumns(
  onActionClick?: OnActionClickFn<OperationLog>,
): VxeTableGridOptions<OperationLog>['columns'] {
  return [
    { type: 'checkbox', minWidth: 60, align: 'center', fixed: 'left' },
    { field: 'request_username', title: $t('operationLog.username'), minWidth: 140, fixed: 'left' },
    {
      field: 'status',
      title: $t('operationLog.status'),
      minWidth: 100,
      cellRender: { name: 'CellTag', options: getStatusOptions() },
    },
    {
      field: 'request_method',
      title: $t('operationLog.method'),
      minWidth: 100,
      cellRender: { name: 'CellTag', options: getMethodOptions() },
    },
    { field: 'request_path', title: $t('operationLog.path'), minWidth: 220, showOverflow: 'tooltip' },
    { field: 'request_modular', title: $t('operationLog.modular'), minWidth: 140 },
    { field: 'request_ip', title: $t('operationLog.ip'), minWidth: 140 },
    { field: 'response_code', title: $t('operationLog.responseCode'), minWidth: 120 },
    { field: 'request_os', title: $t('operationLog.os'), minWidth: 120 },
    { field: 'request_browser', title: $t('operationLog.browser'), minWidth: 120 },
    { field: 'sys_create_datetime', title: $t('operationLog.time'), minWidth: 180, sortable: true },
    {
      align: 'right',
      cellRender: {
        attrs: { nameField: 'request_username', nameTitle: $t('operationLog.username'), onClick: onActionClick },
        name: 'CellOperation',
        options: [
          { code: 'detail', text: $t('operationLog.detail'), icon: 'ep:document' },
          { code: 'delete', text: $t('common.delete'), icon: 'ep:delete' },
        ],
      },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: $t('operationLog.operation'),
      minWidth: 150,
    },
  ];
}

