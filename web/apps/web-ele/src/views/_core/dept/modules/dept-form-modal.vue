<script lang="ts" setup>
import type { VbenFormSchema } from '#/adapter/form';
import type { Dept } from '#/api/core/dept';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElButton } from 'element-plus';

import { useVbenForm, z } from '#/adapter/form';
import {
  createDeptApi,
  updateDeptApi,
} from '#/api/core/dept';

const emit = defineEmits(['success']);
const formData = ref<Dept>();

/**
 * 获取部门类型选项
 */
function getDeptTypeOptions() {
  return [
    { label: $t('dept.deptTypeOptions.company'), value: 'company' },
    { label: $t('dept.deptTypeOptions.department'), value: 'department' },
    { label: $t('dept.deptTypeOptions.team'), value: 'team' },
    { label: $t('dept.deptTypeOptions.other'), value: 'other' },
  ];
}

function getFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'DeptSelector',
      componentProps: {
        allowClear: true,
        class: 'w-full',
        labelField: 'name',
        valueField: 'id',
      },
      fieldName: 'parent_id',
      label: $t('dept.parentDept'),
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('dept.deptName'),
      rules: z
        .string()
        .min(2, $t('ui.formRules.minLength', [$t('dept.deptName'), 2]))
        .max(
          64,
          $t('ui.formRules.maxLength', [$t('dept.deptName'), 64]),
        ),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: $t('dept.deptCode'),
      help: $t('dept.deptCodeHelp'),
      rules: z
        .string()
        .max(32, $t('ui.formRules.maxLength', [$t('dept.deptCode'), 32]))
        .regex(/^[a-zA-Z0-9_-]*$/, $t('dept.deptCodeFormatError'))
        .optional(),
    },
    {
      component: 'Select',
      componentProps: {
        options: getDeptTypeOptions(),
      },
      defaultValue: 'department',
      fieldName: 'dept_type',
      label: $t('dept.deptType'),
    },

    {
      component: 'Input',
      fieldName: 'phone',
      label: $t('dept.phone'),
      help: $t('dept.phoneHelp'),
      rules: z
        .string()
        .max(20, $t('ui.formRules.maxLength', [$t('dept.phone'), 20]))
        .regex(/^[\d\-\+\(\)\s]*$/, $t('dept.phoneFormatError'))
        .optional(),
    },
    {
      component: 'Input',
      fieldName: 'email',
      label: $t('dept.email'),
      help: $t('dept.emailHelp'),
      rules: z.string().email($t('dept.emailFormatError')).optional(),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        buttonStyle: 'solid',
        options: [
          { label: $t('common.enabled'), value: true },
          { label: $t('common.disabled'), value: false },
        ],
        isButton: true,
      },
      defaultValue: true,
      fieldName: 'status',
      label: $t('dept.status'),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        max: 9999,
        class: 'w-full',
      },
      defaultValue: 1,
      fieldName: 'sort',
      label: $t('dept.sort'),
    },
    {
      component: 'Textarea',
      componentProps: {
        maxLength: 200,
        rows: 3,
        showCount: true,
        placeholder: $t('dept.descriptionPlaceholder'),
      },
      fieldName: 'description',
      label: $t('dept.description'),
      help: $t('dept.descriptionHelp'),
      rules: z
        .string()
        .max(200, $t('ui.formRules.maxLength', [$t('dept.description'), 200]))
        .optional(),
    },
  ];
}

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: getFormSchema(),
  showDefaultActions: false,
});

function resetForm() {
  formApi.resetForm();
  formApi.setValues(formData.value || {});
}

const getTitle = computed(() => {
  return formData.value?.id
    ? $t('common.ui.actionTitle.edit', [$t('dept.name')])
    : $t('common.ui.actionTitle.add', [$t('dept.name')]);
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (valid) {
      modalApi.lock();
      const data = await formApi.getValues();
      try {
        await (formData.value?.id
          ? updateDeptApi(formData.value.id, data as any)
          : createDeptApi(data as any));
        modalApi.close();
        emit('success', data);
      } finally {
        modalApi.lock(false);
      }
    }
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<Dept>();
      if (data) {
        formData.value = data;
        formApi.setValues(formData.value);
      } else {
        formData.value = undefined;
        formApi.resetForm();
      }
    }
  },
});
</script>

<template>
  <Modal :title="getTitle">
    <Form class="mx-4" />
    <template #prepend-footer>
      <div class="flex-auto">
        <ElButton type="primary" @click="resetForm">
          {{ $t('common.reset') }}
        </ElButton>
      </div>
    </template>
  </Modal>
</template>
