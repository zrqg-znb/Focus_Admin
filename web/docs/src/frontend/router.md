# 路由管理

## 路由配置

路由配置位于 `src/router/` 目录下。

### 静态路由

不需要权限的路由，如登录页：

```typescript
// router/routes/index.ts
export const staticRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/_core/login/index.vue'),
    meta: {
      title: '登录'
    }
  }
]
```

### 动态路由

根据用户权限动态生成的路由，从后端菜单接口获取。

## 路由守卫

```typescript
// router/guard.ts
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  // 白名单路由
  if (whiteList.includes(to.path)) {
    next()
    return
  }
  
  // 检查登录状态
  if (!userStore.token) {
    next('/login')
    return
  }
  
  // 加载用户信息和动态路由
  if (!userStore.userInfo) {
    await userStore.getUserInfo()
    await userStore.getMenus()
    next({ ...to, replace: true })
    return
  }
  
  next()
})
```

## 路由元信息

```typescript
interface RouteMeta {
  title: string           // 页面标题
  icon?: string           // 菜单图标
  hidden?: boolean        // 是否隐藏
  keepAlive?: boolean     // 是否缓存
  permission?: string[]   // 权限标识
}
```

## 页面缓存

使用 `keep-alive` 实现页面缓存：

```vue
<template>
  <router-view v-slot="{ Component }">
    <keep-alive :include="cachedViews">
      <component :is="Component" />
    </keep-alive>
  </router-view>
</template>
```
