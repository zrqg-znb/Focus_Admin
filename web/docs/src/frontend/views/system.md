# 系统管理页面

## 页面列表

| 页面 | 路径 | 说明 |
| --- | --- | --- |
| 用户管理 | /system/user | 用户增删改查 |
| 角色管理 | /system/role | 角色和权限配置 |
| 菜单管理 | /system/menu | 菜单配置 |
| 部门管理 | /system/dept | 组织架构 |
| 字典管理 | /system/dict | 数据字典 |
| 操作日志 | /system/log | 操作日志查询 |

## 用户管理页面

### 功能点

- 用户列表展示
- 用户搜索（用户名、姓名、部门）
- 新增/编辑用户
- 删除用户
- 重置密码
- 分配角色

### 页面结构

```
views/system/user/
├── index.vue           # 主页面
├── components/
│   ├── UserForm.vue    # 用户表单弹窗
│   ├── UserSearch.vue  # 搜索表单
│   └── RoleSelect.vue  # 角色选择组件
└── hooks/
    └── useUserTable.ts # 表格逻辑
```

## 菜单管理页面

菜单管理使用树形表格展示：

```vue
<template>
  <Page>
    <vxe-grid
      ref="gridRef"
      :tree-config="{ transform: true, rowField: 'id', parentField: 'parentId' }"
      v-bind="gridOptions"
    >
      <template #icon="{ row }">
        <span :class="row.icon" />
      </template>
    </vxe-grid>
  </Page>
</template>
```
