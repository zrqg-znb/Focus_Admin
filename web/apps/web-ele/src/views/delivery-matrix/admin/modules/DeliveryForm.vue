<script lang="ts" setup>
import type { DeliveryTreeNode } from '#/api/delivery-matrix';

import { computed, watch } from 'vue';

import { ElButton, ElCard, ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createComponent,
  createGroup,
  updateComponent,
  updateDomain,
  updateGroup,
} from '#/api/delivery-matrix';
import { listProjectsApi } from '#/api/project-manager/project';

const props = defineProps<{
  isEdit?: boolean; // true for edit selected, false for create new
  node?: DeliveryTreeNode;
  parentNode?: DeliveryTreeNode; // for create
  type?: 'component' | 'domain' | 'group'; // for create
}>();

const emit = defineEmits<{ success: [] }>();

// Define Schemas
const domainSchema = [
  {
    component: 'Input',
    fieldName: 'name',
    label: '领域名称',
    componentProps: { disabled: false },
  },
  {
    component: 'Input',
    fieldName: 'code',
    label: '领域编码',
    componentProps: { disabled: false },
  },
  {
    component: 'UserSelector',
    fieldName: 'interface_people_ids',
    label: '领域接口人',
    componentProps: { multiple: true, placeholder: '请选择接口人' },
  },
  { component: 'Textarea', fieldName: 'remark', label: '备注' },
];

const groupSchema = [
  {
    component: 'Input',
    fieldName: 'name',
    label: '项目群名称',
    rules: 'required',
  },
  {
    component: 'UserSelector',
    fieldName: 'manager_ids',
    label: '项目群经理',
    componentProps: { multiple: true, placeholder: '请选择经理' },
  },
  { component: 'Textarea', fieldName: 'remark', label: '备注' },
];

const componentSchema = [
  {
    component: 'Input',
    fieldName: 'name',
    label: '组件名称',
    rules: 'required',
  },
  {
    component: 'UserSelector',
    fieldName: 'manager_ids',
    label: '项目经理',
    componentProps: { multiple: true, placeholder: '请选择经理' },
  },
  {
    component: 'ApiSelect',
    fieldName: 'linked_project_id',
    label: '关联项目',
    componentProps: {
      api: async () => {
        const res = await listProjectsApi({ pageSize: 1000 });
        return res.items;
      },
      labelField: 'name',
      valueField: 'id',
      showSearch: true,
      optionFilterProp: 'label',
    },
  },
  { component: 'Textarea', fieldName: 'remark', label: '备注' },
];

const currentSchema = computed(() => {
  const targetType = props.isEdit ? props.node?.type : props.type;
  if (targetType === 'domain') return domainSchema;
  if (targetType === 'group') return groupSchema;
  if (targetType === 'component') return componentSchema;
  return [];
});

const [Form, formApi] = useVbenForm({
  commonConfig: { colon: true, componentProps: { class: 'w-full' } },
  schema: [],
  showDefaultActions: false,
});

// Watch for changes to update form
watch(
  () => [props.node, props.isEdit, props.type],
  () => {
    if (!props.isEdit && !props.type) return; // Nothing to show

    // Update Schema
    formApi.setState({ schema: currentSchema.value });

    // Update Values
    if (props.isEdit && props.node) {
      const data = { ...props.node };
      // Map fields
      switch (props.node.type) {
        case 'component': {
          data.manager_ids = props.node.managers;

          break;
        }
        case 'domain': {
          data.interface_people_ids = props.node.interface_people;

          break;
        }
        case 'group': {
          data.manager_ids = props.node.managers;

          break;
        }
        // No default
      }
      formApi.setValues(data);
    } else {
      formApi.resetForm();
    }
  },
  { immediate: true },
);

async function onSubmit() {
  const { valid } = await formApi.validate();
  if (!valid) return;

  const data = await formApi.getValues();
  try {
    if (props.isEdit && props.node) {
      switch (props.node.type) {
        case 'component': {
          {
            await updateComponent(props.node.real_id, data);
            // No default
          }
          break;
        }
        case 'domain': {
          await updateDomain(props.node.real_id, data);
          break;
        }
        case 'group': {
          await updateGroup(props.node.real_id, data);
          break;
        }
      }
    } else {
      // Create
      if (props.type === 'group') {
        await createGroup({ ...data, domain_id: props.parentNode?.real_id });
      } else if (props.type === 'component') {
        await createComponent({ ...data, group_id: props.parentNode?.real_id });
      }
    }
    ElMessage.success('保存成功');
    emit('success');
  } catch (error) {
    console.error(error);
  }
}
</script>

<template>
  <ElCard
    class="h-full border-none shadow-none"
    :body-style="{ padding: '20px' }"
  >
    <template #header>
      <div class="mb-4 border-b pb-2 text-lg font-bold">
        {{ isEdit ? '编辑' : '新增' }}
        {{ type === 'domain' ? '领域' : type === 'group' ? '项目群' : '组件' }}
      </div>
    </template>
    <Form />
    <div class="mt-4 flex justify-end">
      <ElButton type="primary" @click="onSubmit">保存</ElButton>
    </div>
  </ElCard>
</template>
