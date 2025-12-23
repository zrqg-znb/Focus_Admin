// 导入必要的类型和工具
import type { VbenFormSchema } from '#/adapter/form';

import { $t } from '@vben/locales';

import { z } from '#/adapter/form';

/**
 * 权限类型选项
 */
export function getPermissionTypeOptions() {
  return [
    {
      value: 1,
      label: $t('permission.permissionTypes.api'),
      description: $t('permission.permissionTypes.apiDesc'),
      color: 'green',
    },
    {
      value: 0,
      label: $t('permission.permissionTypes.button'),
      description: $t('permission.permissionTypes.buttonDesc'),
      color: 'blue',
    },
    {
      value: 2,
      label: $t('permission.permissionTypes.data'),
      description: $t('permission.permissionTypes.dataDesc'),
      color: 'orange',
    },
    {
      value: 3,
      label: $t('permission.permissionTypes.other'),
      description: $t('permission.permissionTypes.otherDesc'),
      color: 'gray',
    },
  ];
}

export const PERMISSION_TYPE_OPTIONS = getPermissionTypeOptions();

/**
 * HTTP 方法选项
 */
export const HTTP_METHOD_OPTIONS = [
  { value: 0, label: 'GET', method: 'GET' },
  { value: 1, label: 'POST', method: 'POST' },
  { value: 2, label: 'PUT', method: 'PUT' },
  { value: 3, label: 'DELETE', method: 'DELETE' },
  { value: 4, label: 'PATCH', method: 'PATCH' },
  { value: 5, label: 'ALL', method: 'ALL' },
];

/**
 * 获取权限表单 Schema
 */
export function getFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'RadioGroup',
      fieldName: 'permission_type',
      label: $t('permission.permissionType'),
      defaultValue: 1,
      componentProps: {
        buttonStyle: 'solid',
        options: getPermissionTypeOptions(),
        isButton: true,
      },
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('permission.permissionName'),
      rules: z
        .string()
        .min(1, $t('permission.validationErrors.nameRequired'))
        .max(64, $t('permission.validationErrors.nameMaxLength')),
      componentProps: {
        placeholder: $t('permission.placeholder.name'),
      },
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: $t('permission.permissionCode'),
      rules: z
        .string()
        .min(1, $t('permission.validationErrors.codeRequired'))
        .max(64, $t('permission.validationErrors.codeMaxLength'))
        .regex(/^[\w:]+$/, $t('permission.validationErrors.codeFormat')),
      componentProps: {
        placeholder: $t('permission.placeholder.code'),
      },
    },
    {
      component: 'Input',
      fieldName: 'api_path',
      label: $t('permission.apiPath'),
      rules: z.string().optional(),
      componentProps: {
        placeholder: $t('permission.placeholder.apiPath'),
      },
      dependencies: {
        show: (values) => {
          return values.permission_type === 1;
        },
        triggerFields: ['permission_type'],
      },
    },
    {
      component: 'RadioGroup',
      fieldName: 'http_method',
      label: $t('permission.httpMethod'),
      defaultValue: 0,
      componentProps: {
        buttonStyle: 'solid',
        options: HTTP_METHOD_OPTIONS,
        isButton: true,
      },
      dependencies: {
        show: (values) => {
          return values.permission_type === 1;
        },
        triggerFields: ['permission_type'],
      },
    },
    {
      component: 'RadioGroup',
      fieldName: 'is_active',
      label: $t('common.status'),
      defaultValue: true,
      componentProps: {
        buttonStyle: 'solid',
        options: [
          { label: $t('common.enabled'), value: true },
          { label: $t('common.disabled'), value: false },
        ],
        isButton: true,
      },
    },
  ];
}

/**
 * 获取权限列表搜索 Schema
 */
export function getSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('permission.permissionName'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: $t('permission.permissionCode'),
    },
  ];
}
