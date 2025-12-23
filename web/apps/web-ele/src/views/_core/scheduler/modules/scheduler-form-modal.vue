<script lang="ts" setup>
import type { SchedulerJob } from '#/api/core/scheduler';

import { computed, ref, watch } from 'vue';

import { useVbenForm, useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { ElButton } from 'element-plus';

import { createSchedulerJobApi, updateSchedulerJobApi } from '#/api/core/scheduler';
import { useJobFormSchema } from '../data';

const emit = defineEmits(['success']);
const formData = ref<SchedulerJob>();
const triggerType = ref<'cron' | 'interval' | 'date'>('cron');

const getTitle = computed(() => {
  return formData.value?.id
    ? `编辑定时任务`
    : `创建定时任务`;
});

// 根据当前的 trigger_type 动态生成表单配置
const formSchema = computed(() => useJobFormSchema(triggerType.value) as any);

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: formSchema as any,
  showDefaultActions: false,
});

function resetForm() {
  formApi.resetForm();
  if (formData.value) {
    setFormValuesWithConversion(formData.value);
  }
}

/**
 * 处理触发器类型变更
 */
function handleTriggerTypeChange(value: string) {
  triggerType.value = value as 'cron' | 'interval' | 'date';
}

/**
 * 设置表单值，并进行单位转换
 */
function setFormValuesWithConversion(data: SchedulerJob) {
  const formValues = { ...data };
  
  // 处理间隔时间的单位转换
  if (data.trigger_type === 'interval' && data.interval_seconds) {
    const seconds = data.interval_seconds;
    if (seconds % 86400 === 0) {
      formValues.interval_unit = 'days';
      formValues.interval_seconds = seconds / 86400;
    } else if (seconds % 3600 === 0) {
      formValues.interval_unit = 'hours';
      formValues.interval_seconds = seconds / 3600;
    } else if (seconds % 60 === 0) {
      formValues.interval_unit = 'minutes';
      formValues.interval_seconds = seconds / 60;
    } else {
      formValues.interval_unit = 'seconds';
      formValues.interval_seconds = seconds;
    }
  } else {
    // 默认单位
    formValues.interval_unit = 'seconds';
  }
  
  formApi.setValues(formValues);
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (valid) {
      modalApi.lock();
      const data = await formApi.getValues();
      
      // 处理间隔时间的单位转换（转换为秒）
      if (data.trigger_type === 'interval' && data.interval_seconds) {
        const unit = data.interval_unit || 'seconds';
        const value = data.interval_seconds;
        
        let seconds = value;
        if (unit === 'minutes') {
          seconds = value * 60;
        } else if (unit === 'hours') {
          seconds = value * 3600;
        } else if (unit === 'days') {
          seconds = value * 86400;
        }
        
        data.interval_seconds = seconds;
      }
      
      // 移除临时字段
      delete data.interval_unit;
      
      try {
        await (formData.value?.id
          ? updateSchedulerJobApi(formData.value.id, data as any)
          : createSchedulerJobApi(data as any));
        modalApi.close();
        emit('success');
      } finally {
        modalApi.lock(false);
      }
    }
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<SchedulerJob>();
      if (data) {
        formData.value = data;
        triggerType.value = data.trigger_type;
        setFormValuesWithConversion(data);
      } else {
        formData.value = undefined;
        triggerType.value = 'cron';
        formApi.resetForm();
        formApi.setValues({ interval_unit: 'seconds' });
      }
    }
  },
});

// 监听trigger_type变更时重新渲染表单
watch(
  () => triggerType.value,
  () => {
    // 触发表单重新渲染
  },
);
</script>

<template>
  <Modal :title="getTitle" class="w-[800px]">
    <Form class="mx-4" @trigger-type-change="handleTriggerTypeChange" />
    <template #prepend-footer>
      <div class="flex-auto">
        <ElButton @click="resetForm">
          {{ $t('common.reset') || '重置' }}
        </ElButton>
      </div>
    </template>
  </Modal>
</template>

