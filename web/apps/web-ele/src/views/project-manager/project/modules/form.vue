<script lang="ts" setup>
import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';
import { useVbenForm } from '#/adapter/form';
import { ElButton, ElInput, ElMessage, ElTable, ElTableColumn, ElDatePicker, ElForm, ElFormItem } from 'element-plus';

import { createProjectApi, updateProjectApi } from '#/api/project-manager/project';
import { updateMilestoneApi } from '#/api/project-manager/milestone';
import { createIterationApi } from '#/api/project-manager/iteration';
import { configModuleApi } from '#/api/project-manager/code_quality';
import { getProjectFormSchema } from '../data';

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<any>();
const milestoneForm = ref({
  qg1_date: '',
  qg2_date: '',
  qg3_date: '',
  qg4_date: '',
  qg5_date: '',
  qg6_date: '',
  qg7_date: '',
  qg8_date: '',
});
const iterationForm = ref({
  name: '',
  code: '',
  start_date: '',
  end_date: '',
  is_current: true,
  is_healthy: true,
});
type ModuleRow = { name: string; owner_id?: string };
const moduleRows = ref<ModuleRow[]>([]);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: {
      class: 'w-full',
    },
  },
  schema: getProjectFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

const [Drawer, drawerApi] = useVbenDrawer({
  onConfirm: onSubmit,
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = drawerApi.getData<any>();
      if (data) {
        formData.value = data;
        const normalized = {
          ...formData.value,
          manager_ids: Array.isArray(formData.value.managers_info)
            ? formData.value.managers_info.map((m: any) => m.id)
            : [],
        };
        formApi.setValues(normalized);
      } else {
        formApi.resetForm();
      }
    }
  },
});

const getDrawerTitle = computed(() =>
  formData.value?.id ? '编辑项目' : '新增项目',
);

async function onSubmit() {
  const { valid } = await formApi.validate();
  if (valid) {
    drawerApi.lock();
    const data = await formApi.getValues<any>();
    try {
      if (formData.value?.id) {
        const projectId = formData.value.id;
        await updateProjectApi(projectId, data);
        if (data.enable_milestone) {
          await updateMilestoneApi(projectId, milestoneForm.value);
        }
        if (data.enable_iteration && iterationForm.value.name && iterationForm.value.code && iterationForm.value.start_date && iterationForm.value.end_date) {
          await createIterationApi({
            project_id: projectId,
            name: iterationForm.value.name,
            code: iterationForm.value.code,
            start_date: iterationForm.value.start_date,
            end_date: iterationForm.value.end_date,
            is_current: iterationForm.value.is_current,
            is_healthy: iterationForm.value.is_healthy,
          });
        }
        if (data.enable_quality && moduleRows.value.length) {
          for (const row of moduleRows.value) {
            await configModuleApi({
              project_id: projectId,
              name: row.name,
              owner_id: row.owner_id,
            });
          }
        }
        ElMessage.success('更新成功');
      } else {
        const project = await createProjectApi(data);
        const projectId = project.id;
        if (data.enable_milestone) {
          await updateMilestoneApi(projectId, milestoneForm.value);
        }
        if (data.enable_iteration && iterationForm.value.name && iterationForm.value.code && iterationForm.value.start_date && iterationForm.value.end_date) {
          await createIterationApi({
            project_id: projectId,
            name: iterationForm.value.name,
            code: iterationForm.value.code,
            start_date: iterationForm.value.start_date,
            end_date: iterationForm.value.end_date,
            is_current: iterationForm.value.is_current,
            is_healthy: iterationForm.value.is_healthy,
          });
        }
        if (data.enable_quality && moduleRows.value.length) {
          for (const row of moduleRows.value) {
            await configModuleApi({
              project_id: projectId,
              name: row.name,
              owner_id: row.owner_id,
            });
          }
        }
        ElMessage.success('创建成功');
      }
      drawerApi.close();
      emit('success');
    } finally {
      drawerApi.unlock();
    }
  }
}
</script>

<template>
  <Drawer class="w-full max-w-[700px]" :title="getDrawerTitle">
    <Form class="mx-4" />
    <div class="mx-4 mt-4">
      <div class="text-sm font-medium mb-2">里程碑配置</div>
      <ElForm label-width="120px">
        <ElFormItem label="QG1"><ElDatePicker v-model="milestoneForm.qg1_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
        <ElFormItem label="QG2"><ElDatePicker v-model="milestoneForm.qg2_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
        <ElFormItem label="QG3"><ElDatePicker v-model="milestoneForm.qg3_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
        <ElFormItem label="QG4"><ElDatePicker v-model="milestoneForm.qg4_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
        <ElFormItem label="QG5"><ElDatePicker v-model="milestoneForm.qg5_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
        <ElFormItem label="QG6"><ElDatePicker v-model="milestoneForm.qg6_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
        <ElFormItem label="QG7"><ElDatePicker v-model="milestoneForm.qg7_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
        <ElFormItem label="QG8"><ElDatePicker v-model="milestoneForm.qg8_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
      </ElForm>
    </div>
    <div class="mx-4 mt-6">
      <div class="text-sm font-medium mb-2">健康迭代配置</div>
      <ElForm label-width="120px">
        <ElFormItem label="迭代名称"><ElInput v-model="iterationForm.name" /></ElFormItem>
        <ElFormItem label="迭代编号"><ElInput v-model="iterationForm.code" /></ElFormItem>
        <ElFormItem label="开始时间"><ElDatePicker v-model="iterationForm.start_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
        <ElFormItem label="结束时间"><ElDatePicker v-model="iterationForm.end_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
      </ElForm>
    </div>
    <div class="mx-4 mt-6">
      <div class="text-sm font-medium mb-2">代码质量模块配置</div>
      <div class="mb-2">
        <ElButton type="primary" @click="moduleRows.push({ name: '', owner_id: '' })">新增模块</ElButton>
      </div>
      <ElTable :data="moduleRows">
        <ElTableColumn label="模块名">
          <template #default="{ row }">
            <ElInput v-model="row.name" placeholder="模块名" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="责任人ID">
          <template #default="{ row }">
            <ElInput v-model="row.owner_id" placeholder="责任人ID" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="120">
          <template #default="{ $index }">
            <ElButton type="danger" link @click="moduleRows.splice($index, 1)">删除</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>
  </Drawer>
  </template>
