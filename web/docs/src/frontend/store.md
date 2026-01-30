# 状态管理

使用 Pinia 进行状态管理。

## Store 结构

```
store/
└── modules/
    ├── user.ts          # 用户状态
    ├── permission.ts    # 权限状态
    └── app.ts           # 应用配置
```

## 用户 Store

```typescript
// store/modules/user.ts
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: null as UserInfo | null,
    roles: [] as string[],
    permissions: [] as string[]
  }),
  
  getters: {
    isLogin: (state) => !!state.token,
    userName: (state) => state.userInfo?.name || ''
  },
  
  actions: {
    async login(data: LoginParams) {
      const res = await loginApi(data)
      this.token = res.data.access_token
      localStorage.setItem('token', this.token)
    },
    
    async getUserInfo() {
      const res = await getUserInfoApi()
      this.userInfo = res.data
      this.roles = res.data.roles
      this.permissions = res.data.permissions
    },
    
    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
    }
  }
})
```

## 使用示例

```vue
<script setup lang="ts">
import { useUserStore } from '@/store/modules/user'

const userStore = useUserStore()

// 获取状态
const userName = computed(() => userStore.userName)

// 调用 action
const handleLogout = () => {
  userStore.logout()
}
</script>
```

## 权限判断

```typescript
// hooks/usePermission.ts
export function usePermission() {
  const userStore = useUserStore()
  
  const hasPermission = (permission: string) => {
    return userStore.permissions.includes(permission)
  }
  
  const hasRole = (role: string) => {
    return userStore.roles.includes(role)
  }
  
  return { hasPermission, hasRole }
}
```
