# 目录结构

## 应用目录结构

```
web/apps/web-ele/src/
├── adapter/                # 适配器层
│   ├── component/         # 组件适配
│   └── form/              # 表单适配
│
├── api/                    # API 接口定义
│   ├── core/              # 核心模块 API
│   │   ├── auth.ts        # 认证
│   │   ├── user.ts        # 用户
│   │   ├── role.ts        # 角色
│   │   ├── menu.ts        # 菜单
│   │   └── ...
│   └── request.ts         # 请求配置
│
├── components/             # 业务组件
│   ├── common/            # 通用组件
│   └── ...
│
├── layouts/                # 布局组件
│   ├── default/           # 默认布局
│   └── ...
│
├── locales/                # 国际化
│   ├── zh-CN/             # 中文
│   └── en-US/             # 英文
│
├── router/                 # 路由配置
│   ├── routes/            # 路由定义
│   │   ├── modules/       # 模块路由
│   │   └── index.ts       # 路由汇总
│   ├── guard.ts           # 路由守卫
│   └── index.ts           # 路由入口
│
├── store/                  # 状态管理
│   └── modules/           # Store 模块
│
├── utils/                  # 工具函数
│
├── views/                  # 页面视图
│   ├── _core/             # 核心页面（登录等）
│   ├── dashboard/         # 仪表盘
│   ├── system/            # 系统管理
│   │   ├── user/          # 用户管理
│   │   ├── role/          # 角色管理
│   │   ├── menu/          # 菜单管理
│   │   └── ...
│   └── ...
│
├── app.vue                 # 根组件
├── main.ts                 # 应用入口
├── bootstrap.ts            # 启动配置
└── preferences.ts          # 偏好设置
```

## 页面模块结构

每个功能模块的页面通常按以下结构组织：

```
views/system/user/
├── index.vue              # 列表页面
├── detail.vue             # 详情页面（可选）
├── components/            # 局部组件
│   ├── UserForm.vue       # 用户表单
│   └── UserSearch.vue     # 搜索表单
└── composables/           # 组合式函数（可选）
    └── useUser.ts
```

## 命名规范

### 文件命名

- 组件文件：PascalCase，如 `UserList.vue`
- 工具文件：camelCase，如 `request.ts`
- 样式文件：kebab-case，如 `user-list.scss`

### 组件命名

```vue
<script setup lang="ts">
// 组件名通过文件名自动推断
defineOptions({
  name: 'UserList'
})
</script>
```
