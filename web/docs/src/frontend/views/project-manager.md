# 项目管理页面

## 页面列表

| 页面 | 路径 | 说明 |
| --- | --- | --- |
| 项目列表 | /project-manager/project | 项目管理主页 |
| 迭代管理 | /project-manager/iteration | 迭代列表 |
| 里程碑 | /project-manager/milestone | 里程碑管理 |
| 代码质量 | /project-manager/code-quality | 代码质量分析 |

## 页面结构

```
views/project-manager/
├── project/
│   ├── index.vue           # 项目列表
│   └── components/
│       ├── ProjectForm.vue # 项目表单
│       └── ProjectCard.vue # 项目卡片
├── iteration/
│   └── index.vue           # 迭代列表
├── milestone/
│   └── index.vue           # 里程碑管理
└── code-quality/
    └── index.vue           # 代码质量
```

## 项目列表页面示例

```vue
<template>
  <Page>
    <!-- 搜索区域 -->
    <SearchForm :schema="searchSchema" @search="handleSearch" />
    
    <!-- 操作按钮 -->
    <div class="mb-4">
      <el-button type="primary" @click="handleAdd">新增项目</el-button>
    </div>
    
    <!-- 数据表格 -->
    <vxe-grid
      ref="gridRef"
      v-bind="gridOptions"
      @page-change="handlePageChange"
    >
      <template #action="{ row }">
        <el-button link @click="handleEdit(row)">编辑</el-button>
        <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
      </template>
    </vxe-grid>
    
    <!-- 编辑弹窗 -->
    <ProjectForm ref="formRef" @success="loadData" />
  </Page>
</template>
```
