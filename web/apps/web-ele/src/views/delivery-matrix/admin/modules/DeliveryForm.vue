<script lang="ts" setup>
import type { OrgNode } from '#/api/delivery-matrix';

import { ref, watch } from 'vue';

import { ElButton, ElCard, ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createNode,
  updateNode,
  updateNodePositions,
} from '#/api/delivery-matrix';

import { useNodeFormSchema } from '../../data';
import PositionEdit from './PositionEdit.vue';

const props = defineProps<{
  isEdit?: boolean;
  node?: OrgNode;
  parentNode?: OrgNode;
}>();

const emit = defineEmits<{ success: [] }>();

const positions = ref<{ name: string; sort?: number; user_ids: string[] }[]>([]);
const submitLoading = ref(false);

const [Form, formApi] = useVbenForm({
  commonConfig: { colon: true, componentProps: { class: 'w-full' } },
  schema: useNodeFormSchema(),
  showDefaultActions: false,
});

watch(
  () => [props.node, props.isEdit],
  () => {
    if (props.isEdit && props.node) {
      formApi.setValues({
        ...props.node,
        parent_id: props.node.parent_id || null,
      });
      // Map positions
      positions.value = props.node.positions
        ? props.node.positions.map((p) => ({
            name: p.name,
            sort: p.sort,
            user_ids: p.users_info.map((u) => u.id),
          }))
        : [];
    } else {
      formApi.resetForm();
      formApi.setValues({
        parent_id: props.parentNode?.id || null,
      });
      positions.value = [];
    }
  },
  { immediate: true },
);

async function onSubmit() {
  if (submitLoading.value) return; // 防止重复提交

  const { valid } = await formApi.validate();
  if (!valid) return;

  const data = await formApi.getValues();
  submitLoading.value = true;

  try {
    if (props.isEdit && props.node) {
      // Update Node
      await updateNode(props.node.id, data);
      // Update Positions - 始终调用，无论是否为根节点
      await updateNodePositions(props.node.id, positions.value);
    } else {
      // Create
      const payload = {
        ...data,
        parent_id: data.parent_id || null,
        positions: positions.value,
      } as any;
      await createNode(payload);
    }
    ElMessage.success('保存成功');
    emit('success');
  } catch (error: any) {
    console.error('保存失败:', error);
    const msg = error?.response?.data?.detail || error?.message || '保存失败，请重试';
    ElMessage.error(msg);
  } finally {
    submitLoading.value = false;
  }
}
</script>

<template>
  <ElCard
    class="h-full border-none shadow-none"
    :body-style="{ padding: '20px', height: '100%', overflowY: 'auto' }"
  >
    <template #header>
      <div class="mb-4 border-b pb-2 text-lg font-bold">
        {{ isEdit ? '编辑节点' : '新增节点' }}
      </div>
    </template>

    <Form />

    <div class="mt-4 border-t pt-4">
      <PositionEdit v-model="positions" />
    </div>

    <div class="mt-8 flex justify-end">
      <ElButton type="primary" :loading="submitLoading" @click="onSubmit">
        保存
      </ElButton>
    </div>
  </ElCard>
</template>
