import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn } from '#/adapter/vxe-table';
import type { Role, RoleUser } from '#/api/core/role';

import { $t } from '@vben/locales';

import { z } from '#/adapter/form';

/**
 * 获取搜索表单的字段配置
 */
export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.user.userName'),
    },
    {
      component: 'Input',
      fieldName: 'username',
      label: $t('system.user.account'),
    },
  ];
}

/**
 * 获取角色类型选项
 */
export function getRoleTypeOptions() {
  return [
    { label: $t('role.types.system'), value: 0 },
    { label: $t('role.types.custom'), value: 1 },
  ];
}

/**
 * 获取数据范围选项
 */
export function getDataScopeOptions() {
  return [
    { label: $t('role.dataScopes.self'), value: 0 },
    { label: $t('role.dataScopes.dept'), value: 1 },
    { label: $t('role.dataScopes.deptAndSub'), value: 2 },
    { label: $t('role.dataScopes.all'), value: 3 },
    { label: $t('role.dataScopes.custom'), value: 4 },
  ];
}

/**
 * 获取角色树列配置
 */
export function useRoleTreeColumns(
  onActionClick?: OnActionClickFn<Role>,
): VxeTableGridOptions<Role>['columns'] {
  return [
    {
      field: 'name',
      title: $t('system.role.roleName'),
      minWidth: 150,
    },
  ];
}

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.role.roleName'),
      rules: z
        .string()
        .min(2, $t('ui.formRules.minLength', [$t('system.role.roleName'), 2]))
        .max(
          64,
          $t('ui.formRules.maxLength', [$t('system.role.roleName'), 64]),
        ),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: $t('system.role.roleCode'),
      rules: z
        .string()
        .min(2, $t('ui.formRules.minLength', [$t('system.role.roleCode'), 2]))
        .max(
          64,
          $t('ui.formRules.maxLength', [$t('system.role.roleCode'), 64]),
        )
        .regex(/^[a-zA-Z0-9_]+$/, $t('role.codeFormatError')),
    },
    {
      component: 'Select',
      componentProps: {
        options: getRoleTypeOptions(),
      },
      defaultValue: 1,
      fieldName: 'role_type',
      label: $t('role.roleType'),
    },
    {
      component: 'Select',
      componentProps: {
        options: getDataScopeOptions(),
      },
      defaultValue: 0,
      fieldName: 'data_scope',
      label: $t('role.dataScope'),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        max: 9999,
      },
      defaultValue: 0,
      fieldName: 'priority',
      label: $t('role.priority'),
      help: $t('role.priorityHelp'),
      rules: z.number().min(0).max(9999),
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: $t('role.descriptionPlaceholder'),
        rows: 3,
      },
      fieldName: 'description',
      label: $t('role.description'),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        options: [
          { label: $t('common.enabled'), value: true },
          { label: $t('common.disabled'), value: false },
        ],
      },
      defaultValue: true,
      fieldName: 'status',
      label: $t('system.role.status'),
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: $t('role.remarkPlaceholder'),
        rows: 2,
      },
      fieldName: 'remark',
      label: $t('system.role.remark'),
    },
  ];
}

/**
 * 获取用户表格列配置
 */
export function useUserColumns(
  onActionClick?: OnActionClickFn<RoleUser>,
): VxeTableGridOptions<RoleUser>['columns'] {
  return [
    {
      type: 'checkbox',
      minWidth: 60,
      align: 'center',
      fixed: 'left',
    },
    {
      field: 'username',
      title: $t('system.user.account'),
      minWidth: 120,
    },
    {
      field: 'name',
      title: $t('system.user.userName'),
      minWidth: 120,
    },
    {
      field: 'email',
      title: $t('system.user.email'),
      minWidth: 180,
    },
    {
      align: 'right',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: $t('system.user.userName'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: ['edit', 'delete'],
      },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: $t('system.user.operation'),
      minWidth: 150,
    },
  ];
}
