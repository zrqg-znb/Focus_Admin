<script setup lang="ts">
import { ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { ElButton, ElCard, ElMessage } from 'element-plus';
import { storeToRefs } from 'pinia';

import FormDesign from '#/components/form-design/index.vue';
import { useFormDesignStore } from '#/components/form-design/store/formDesignStore';

defineOptions({
  name: 'FormDesignDemo',
});

const store = useFormDesignStore();
const { formConf } = storeToRefs(store);
const schemaJson = ref('');

// 监听配置变化，实时更新 JSON 展示
watch(
  () => formConf.value,
  (newVal) => {
    schemaJson.value = JSON.stringify(newVal, null, 2);
  },
  { deep: true, immediate: true },
);

// 获取当前配置
const handleGetSchema = () => {
  const schema = JSON.stringify(formConf.value);
  navigator.clipboard.writeText(schema);
  ElMessage.success('配置已复制到剪贴板');
  console.log('表单配置:', formConf.value);
};

// 加载示例配置
const handleLoadDemo = () => {
  formConf.value.items = [
    {
      id: 'demo1',
      type: 'input',
      field: 'username',
      label: '用户名',
      props: {
        placeholder: '请输入用户名',
        clearable: true,
        width: '100%',
        required: true,
      },
    },
    {
      id: 'demo2',
      type: 'input',
      field: 'email',
      label: '邮箱',
      props: {
        placeholder: '请输入邮箱',
        clearable: true,
        width: '100%',
        required: true,
      },
    },
    {
      id: 'demo3',
      type: 'select',
      field: 'role',
      label: '角色',
      props: {
        placeholder: '请选择角色',
        clearable: true,
        width: '100%',
        required: true,
      },
      options: [
        { label: '管理员', value: 'admin' },
        { label: '普通用户', value: 'user' },
        { label: '访客', value: 'guest' },
      ],
    },
    {
      id: 'demo4',
      type: 'radio',
      field: 'gender',
      label: '性别',
      props: {
        disabled: false,
        required: false,
      },
      options: [
        { label: '男', value: 1 },
        { label: '女', value: 2 },
      ],
    },
    {
      id: 'demo5',
      type: 'date',
      field: 'birthday',
      label: '生日',
      props: {
        placeholder: '选择日期',
        format: 'YYYY-MM-DD',
        valueFormat: 'YYYY-MM-DD',
        width: '100%',
        required: false,
      },
    },
  ];

  ElMessage.success('示例配置已加载');
};
</script>

<template>
  <Page auto-content-height>
    <div>
      <ElCard>
        <template #header>
          <div class="flex items-center justify-between">
            <span class="font-bold">表单设计器</span>
            <div class="space-x-2">
              <ElButton type="primary" size="small" @click="handleGetSchema">
                获取配置
              </ElButton>
              <ElButton type="success" size="small" @click="handleLoadDemo">
                加载示例
              </ElButton>
            </div>
          </div>
        </template>

        <!-- 表单设计器组件 -->
        <div class="h-[600px]">
          <FormDesign />
        </div>
      </ElCard>

      <ElCard>
        <template #header>
          <span class="font-bold">配置数据 (JSON Schema)</span>
        </template>
        <pre
          class="max-h-[300px] overflow-auto rounded bg-gray-50 p-4 text-xs"
          >{{ schemaJson }}</pre>
      </ElCard>
    </div>
  </Page>
</template>
