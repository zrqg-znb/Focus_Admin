import type { VbenFormSchema } from '#/adapter/form';

import { $t } from '@vben/locales';

import { z } from '#/adapter/form';

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('pl.groupName'),
      rules: z
        .string()
        .min(2, $t('ui.formRules.minLength', [$t('pl.groupName'), 2]))
        .max(64, $t('ui.formRules.maxLength', [$t('pl.groupName'), 64])),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: $t('pl.groupCode'),
      rules: z
        .string()
        .max(32, $t('ui.formRules.maxLength', [$t('pl.groupCode'), 32]))
        .regex(/^[\w-]*$/, $t('pl.codeFormatError'))
        .optional(),
    },
    {
      component: 'UserSelector',
      componentProps: {
        clearable: false,
        placeholder: $t('pl.selectPl'),
      },
      fieldName: 'pl_user_id',
      label: $t('pl.plUser'),
      rules: z.string().min(1, $t('pl.selectPl')),
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
      label: $t('pl.status'),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        max: 9999,
        class: 'w-full',
      },
      defaultValue: 0,
      fieldName: 'sort',
      label: $t('pl.sort'),
    },
    {
      component: 'Textarea',
      componentProps: {
        maxLength: 200,
        rows: 3,
        showCount: true,
        placeholder: $t('pl.descriptionPlaceholder'),
      },
      fieldName: 'description',
      label: $t('pl.description'),
      rules: z
        .string()
        .max(200, $t('ui.formRules.maxLength', [$t('pl.description'), 200]))
        .optional(),
    },
  ];
}
