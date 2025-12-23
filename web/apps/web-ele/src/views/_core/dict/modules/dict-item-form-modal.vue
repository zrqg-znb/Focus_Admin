<script lang="ts" setup>
import type { DictItem } from '#/api/core/dict';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElButton } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { createDictItemApi, updateDictItemApi } from '#/api/core/dict';

import { useDictItemFormSchema } from '../data';

const emit = defineEmits(['success']);
const formData = ref<DictItem>();
const dictId = ref<string>();

const getTitle = computed(() => {
  return formData.value?.id
    ? $t('ui.actionTitle.edit', [$t('dict.itemName')])
    : $t('ui.actionTitle.create', [$t('dict.itemName')]);
});

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: useDictItemFormSchema(),
  showDefaultActions: false,
});

function resetForm() {
  formApi.resetForm();
  formApi.setValues(formData.value || {});
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (valid) {
      modalApi.lock();
      const data = await formApi.getValues();
      try {
        const payload = {
          ...data,
          dict_id: dictId.value,
        };
        await (formData.value?.id
          ? updateDictItemApi(formData.value.id, payload)
          : createDictItemApi(payload));
        modalApi.close();
        emit('success');
      } finally {
        modalApi.lock(false);
      }
    }
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<any>();
      if (data?.id) {
        // 编辑现有字典项
        formData.value = data;
        dictId.value = data.dict_id;
        formApi.setValues(formData.value);
      } else {
        // 创建新字典项
        formData.value = undefined;
        dictId.value = data?.dictId;
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

