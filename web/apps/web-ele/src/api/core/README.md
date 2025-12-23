# Core API 模块

本目录包含了与 `backend-v5/core` 模块对应的前端 API 接口定义。

## 📁 文件结构

```
src/api/core/
├── index.ts          # 统一导出所有 API
├── auth.ts           # 认证相关 API
├── user.ts           # 用户管理 API
├── role.ts           # 角色管理 API
├── permission.ts     # 权限管理 API
├── dept.ts           # 部门管理 API
├── post.ts           # 岗位管理 API
├── menu.ts           # 菜单管理 API
└── README.md         # 本文档
```

## 📚 模块说明

### 1. User API (`user.ts`)

用户管理相关接口，包括：

- CRUD 操作（创建、查询、更新、删除）
- 批量操作（批量删除、批量更新状态）
- 密码管理（重置密码）
- 个人信息管理
- 权限检查
- 下属查询
- 简单列表（用于选择器）

**主要接口：**
```typescript
createUserApi(data: UserCreateInput): Promise<User>
getUserListApi(params?: UserListParams): Promise<PaginatedResponse<User>>
getUserDetailApi(userId: string): Promise<User>
updateUserApi(userId: string, data: UserUpdateInput): Promise<User>
deleteUserApi(userId: string): Promise<User>
batchDeleteUserApi(data: UserBatchDeleteInput): Promise<{count: number}>
batchUpdateUserStatusApi(data: UserBatchUpdateStatusInput): Promise<{count: number}>
resetUserPasswordApi(userId: string, data: UserPasswordResetInput): Promise<User>
updateUserProfileApi(data: UserProfileUpdateInput): Promise<User>
checkUserPermissionApi(data: UserPermissionCheckInput): Promise<{has_permission: boolean}>
getUserSubordinatesApi(userId: string): Promise<User[]>
getSimpleUserListApi(): Promise<User[]>
```

### 2. Role API (`role.ts`)

角色管理相关接口，包括：

- CRUD 操作
- 批量操作
- 角色用户管理
- 菜单权限树
- 简单列表

**主要接口：**
```typescript
createRoleApi(data: RoleCreateInput): Promise<Role>
getRoleListApi(params?: RoleListParams): Promise<PaginatedResponse<Role>>
getRoleDetailApi(roleId: string): Promise<Role>
updateRoleApi(roleId: string, data: RoleUpdateInput): Promise<Role>
deleteRoleApi(roleId: string): Promise<Role>
batchDeleteRoleApi(data: RoleBatchDeleteInput): Promise<{count: number}>
batchUpdateRoleStatusApi(data: RoleBatchUpdateStatusInput): Promise<{count: number}>
getRoleUsersApi(roleId: string, params?): Promise<PaginatedResponse<RoleUser>>
addRoleUsersApi(roleId: string, data: RoleUserInput): Promise<{count: number}>
removeRoleUsersApi(roleId: string, data: RoleUserInput): Promise<{count: number}>
getRoleMenuPermissionTreeApi(roleId: string): Promise<MenuPermissionTree>
getSimpleRoleListApi(): Promise<Role[]>
```

### 3. Permission API (`permission.ts`)

权限管理相关接口，包括：

- CRUD 操作
- 批量操作
- 按菜单查询
- 统计信息
- 编码检查

**主要接口：**
```typescript
createPermissionApi(data: PermissionCreateInput): Promise<Permission>
getPermissionListApi(params?: PermissionListParams): Promise<PaginatedResponse<Permission>>
getPermissionDetailApi(permissionId: string): Promise<Permission>
updatePermissionApi(permissionId: string, data: PermissionUpdateInput): Promise<Permission>
deletePermissionApi(permissionId: string): Promise<Permission>
batchDeletePermissionApi(data: PermissionBatchDeleteInput): Promise<{count: number}>
batchUpdatePermissionStatusApi(data: PermissionBatchUpdateStatusInput): Promise<{count: number}>
getPermissionsByMenuApi(menuId: string): Promise<Permission[]>
getPermissionStatsApi(): Promise<PermissionStats>
checkPermissionCodeApi(code: string, menuId: string): Promise<{available: boolean}>
```

### 4. Dept API (`dept.ts`)

部门管理相关接口，包括：

- CRUD 操作
- 树形结构
- 批量操作
- 部门移动
- 部门用户管理
- 统计信息
- 简单列表

**主要接口：**
```typescript
createDeptApi(data: DeptCreateInput): Promise<Dept>
getDeptListApi(params?: DeptListParams): Promise<Dept[]>
getDeptTreeApi(): Promise<DeptTreeNode[]>
getDeptDetailApi(deptId: string): Promise<Dept>
updateDeptApi(deptId: string, data: DeptUpdateInput): Promise<Dept>
deleteDeptApi(deptId: string): Promise<Dept>
batchDeleteDeptApi(data: DeptBatchDeleteInput): Promise<{count: number}>
getDeptByParentApi(parentId?: string): Promise<Dept[]>
searchDeptApi(keyword: string): Promise<Dept[]>
moveDeptApi(deptId: string, data: DeptMoveInput): Promise<Dept>
getDeptPathApi(deptId: string): Promise<Dept[]>
getDeptUsersApi(deptId: string, params?): Promise<PaginatedResponse<DeptUser>>
addDeptUsersApi(deptId: string, data): Promise<{count: number}>
removeDeptUsersApi(deptId: string, data): Promise<{count: number}>
getDeptStatsApi(): Promise<DeptStats>
getSimpleDeptListApi(): Promise<Dept[]>
```

### 5. Post API (`post.ts`)

岗位管理相关接口，包括：

- CRUD 操作
- 批量操作
- 按部门查询
- 岗位用户管理
- 导入导出
- 统计信息
- 简单列表

**主要接口：**
```typescript
createPostApi(data: PostCreateInput): Promise<Post>
getPostListApi(params?: PostListParams): Promise<PaginatedResponse<Post>>
getPostDetailApi(postId: string): Promise<Post>
updatePostApi(postId: string, data: PostUpdateInput): Promise<Post>
deletePostApi(postId: string): Promise<Post>
batchDeletePostApi(data: PostBatchDeleteInput): Promise<{count: number}>
batchUpdatePostStatusApi(data: PostBatchUpdateStatusInput): Promise<{count: number}>
getPostsByDeptApi(deptId: string): Promise<Post[]>
getPostUsersApi(postId: string, params?): Promise<PaginatedResponse<PostUser>>
addPostUsersApi(postId: string, data): Promise<{count: number}>
removePostUsersApi(postId: string, data): Promise<{count: number}>
getPostStatsApi(): Promise<PostStats>
exportPostApi(params?: PostListParams): Promise<Blob>
importPostApi(file: File): Promise<{success_count: number; error_count: number}>
getSimplePostListApi(): Promise<Post[]>
```

### 6. Menu API (`menu.ts`)

菜单管理相关接口，包括：

- CRUD 操作
- 树形结构
- 用户路由树
- 菜单移动
- 搜索功能
- 统计信息

**主要接口：**
```typescript
getAllMenusApi(): Promise<RouteRecordStringComponent[]>  // 兼容旧版
getUserRouteTreeApi(): Promise<MenuTreeNode[]>
createMenuApi(data: MenuCreateInput): Promise<Menu>
getMenuListApi(params?: MenuListParams): Promise<Menu[]>
getAllMenuTreeApi(): Promise<MenuTreeNode[]>
getMenuDetailApi(menuId: string): Promise<Menu>
updateMenuApi(menuId: string, data: MenuUpdateInput): Promise<Menu>
deleteMenuApi(menuId: string): Promise<Menu>
getMenuByParentApi(parentId?: string): Promise<Menu[]>
searchMenuApi(keyword: string): Promise<Menu[]>
moveMenuApi(menuId: string, data: MenuMoveInput): Promise<Menu>
getMenuPathApi(menuId: string): Promise<Menu[]>
getMenuStatsApi(): Promise<MenuStats>
```

## 🔧 使用示例

### 用户管理

```typescript
import { createUserApi, getUserListApi, updateUserApi } from '#/api/core';

// 创建用户
const newUser = await createUserApi({
  username: 'zhangsan',
  name: '张三',
  email: 'zhangsan@example.com',
  mobile: '13800138000',
  dept_id: 'dept-uuid',
  core_roles: ['role-uuid-1', 'role-uuid-2'],
});

// 获取用户列表
const users = await getUserListApi({
  page: 1,
  pageSize: 20,
  name: '张',
  user_status: 1,
});

// 更新用户
await updateUserApi('user-uuid', {
  name: '张三（已更新）',
  user_status: 1,
});
```

### 角色管理

```typescript
import { createRoleApi, getRoleMenuPermissionTreeApi } from '#/api/core';

// 创建角色
const newRole = await createRoleApi({
  name: '产品经理',
  code: 'product_manager',
  role_type: 1,
  data_scope: 1,
  menu: ['menu-uuid-1', 'menu-uuid-2'],
  permission: ['perm-uuid-1', 'perm-uuid-2'],
});

// 获取角色的菜单权限树
const tree = await getRoleMenuPermissionTreeApi('role-uuid');
console.log(tree.menu_tree);
console.log(tree.selected_menu_ids);
```

### 部门管理

```typescript
import { getDeptTreeApi, createDeptApi, moveDeptApi } from '#/api/core';

// 获取部门树
const deptTree = await getDeptTreeApi();

// 创建部门
const newDept = await createDeptApi({
  name: '技术部',
  parent_id: 'parent-dept-uuid',
  dept_type: 1,
  code: 'TECH',
  lead_id: 'user-uuid',
});

// 移动部门
await moveDeptApi('dept-uuid', {
  target_parent_id: 'new-parent-uuid',
  position: 0,
});
```

### 菜单管理

```typescript
import { getUserRouteTreeApi, createMenuApi, getMenuStatsApi } from '#/api/core';

// 获取用户路由树
const routes = await getUserRouteTreeApi();

// 创建菜单
const newMenu = await createMenuApi({
  name: 'dashboard',
  title: '工作台',
  path: '/dashboard',
  type: 'catalog',
  icon: 'carbon:dashboard',
  order: 1,
});

// 获取菜单统计
const stats = await getMenuStatsApi();
console.log(`总菜单数: ${stats.total_count}`);
console.log(`最大层级: ${stats.max_level}`);
```

## 📝 类型定义

所有 API 模块都包含完整的 TypeScript 类型定义，包括：

- 实体类型（User, Role, Permission, Dept, Post, Menu）
- 输入类型（CreateInput, UpdateInput）
- 查询参数类型（ListParams）
- 响应类型（PaginatedResponse, Stats 等）

## 🔗 API 路径映射

| 前端模块 | 后端模块 | API 前缀 |
|---------|---------|---------|
| user.ts | core/user/user_api.py | /api/core/user |
| role.ts | core/role/role_api.py | /api/core/role |
| permission.ts | core/permission/permission_api.py | /api/core/permission |
| dept.ts | core/dept/dept_api.py | /api/core/dept |
| post.ts | core/post/post_api.py | /api/core/post |
| menu.ts | core/menu/menu_api.py | /api/core/menu |

## 特性

- 完整的 TypeScript 类型定义
- 与后端 API 1:1 对应
- 支持分页查询
- 支持批量操作
- 支持树形结构
- 统一的错误处理
- 统一的响应格式

## 📌 注意事项

1. **UUID 主键**
   - 所有 ID 字段均为 UUID 字符串格式
   - 示例：`'a0000000-0000-0000-0000-000000000001'`

2. **分页参数**
   - `page`: 页码（从 1 开始）
   - `pageSize`: 每页数量

3. **日期时间格式**
   - 所有日期时间字段使用 ISO 8601 格式
   - 示例：`'2025-11-08T12:00:00Z'`

4. **批量操作**
   - 批量操作返回影响的记录数：`{ count: number }`

5. **树形结构**
   - 树形数据包含 `children` 字段
   - 支持无限层级

## 🔄 更新日志

### 2025-11-08
- 创建所有 Core 模块的 TypeScript API 文件
- 更新 user.ts 和 menu.ts，保留原有接口
- 新增 role.ts, permission.ts, dept.ts, post.ts
- 统一导出到 index.ts
- 添加完整的类型定义和文档

## 📚 相关文档

- [Backend Core API 文档](../../../../../backend-v5/core/README.md)
- [RootModel 迁移指南](../../../../../backend-v5/core/ROOTMODEL_MIGRATION.md)
- [UUID 迁移总结](../../../../../backend-v5/core/UUID_MIGRATION_SUMMARY.md)

