# 通用组件

本文档介绍项目中封装的通用组件。

## SearchForm 搜索表单

用于列表页面的搜索条件：

```vue
<template>
  <SearchForm
    :schema="searchSchema"
    @search="handleSearch"
    @reset="handleReset"
  />
</template>

<script setup lang="ts">
const searchSchema = [
  { field: 'name', label: '名称', component: 'Input' },
  { field: 'status', label: '状态', component: 'Select' }
]

const handleSearch = (values) => {
  // 执行搜索
}
</script>
```

## Pagination 分页

统一的分页组件：

```vue
<template>
  <Pagination
    v-model:page="page"
    v-model:pageSize="pageSize"
    :total="total"
    @change="handlePageChange"
  />
</template>
```

## Permission 权限组件

用于按钮级权限控制：

```vue
<template>
  <!-- 方式一：指令 -->
  <el-button v-permission="'user:add'">新增</el-button>
  
  <!-- 方式二：组件 -->
  <Permission :value="'user:add'">
    <el-button>新增</el-button>
  </Permission>
</template>
```

## IconPicker 图标选择器

用于菜单配置等场景：

```vue
<template>
  <IconPicker v-model="icon" />
</template>
```
