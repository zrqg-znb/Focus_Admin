# 组件概览

## 组件分类

### 基础组件

来自 Element Plus 的基础组件，如 Button、Input、Table 等。

### 业务组件

针对业务场景封装的组件：

- 搜索表单组件
- 高级表格组件
- 弹窗表单组件

## 常用组件

### 表格组件

基于 Element Plus Table 或 VxeTable 封装：

```vue
<template>
  <vxe-grid
    ref="gridRef"
    v-bind="gridOptions"
    @page-change="handlePageChange"
  />
</template>

<script setup lang="ts">
const gridOptions = reactive({
  columns: [
    { field: 'name', title: '名称' },
    { field: 'status', title: '状态' }
  ],
  pagerConfig: {
    pageSize: 10,
    pageSizes: [10, 20, 50]
  }
})
</script>
```

### 表单组件

基于 Vben Form 组件：

```vue
<template>
  <vben-form
    :schema="formSchema"
    @submit="handleSubmit"
  />
</template>

<script setup lang="ts">
const formSchema = [
  {
    field: 'name',
    label: '名称',
    component: 'Input',
    required: true
  },
  {
    field: 'status',
    label: '状态',
    component: 'Select',
    componentProps: {
      options: [
        { label: '启用', value: 1 },
        { label: '禁用', value: 0 }
      ]
    }
  }
]
</script>
```

### 弹窗组件

```vue
<template>
  <vben-modal
    v-model:open="visible"
    title="编辑用户"
    @confirm="handleConfirm"
  >
    <vben-form ref="formRef" :schema="formSchema" />
  </vben-modal>
</template>
```
