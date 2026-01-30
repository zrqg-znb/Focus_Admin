# 代码规范

## 后端规范 (Python/Django)

### 命名规范

| 类型 | 规范 | 示例 |
| --- | --- | --- |
| 模块/文件 | snake_case | `user_service.py` |
| 类名 | PascalCase | `UserService` |
| 函数/方法 | snake_case | `get_user_by_id` |
| 变量 | snake_case | `user_name` |
| 常量 | UPPER_CASE | `MAX_PAGE_SIZE` |

### 代码风格

遵循 PEP 8 规范，使用工具检查：

```bash
# 安装工具
pip install flake8 black isort

# 检查代码
flake8 .

# 格式化代码
black .
isort .
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def get_user(user_id: int) -> User:
    """获取用户信息
    
    Args:
        user_id: 用户ID
        
    Returns:
        User: 用户对象
        
    Raises:
        NotFound: 用户不存在时抛出
    """
    pass
```

## 前端规范 (Vue/TypeScript)

### 命名规范

| 类型 | 规范 | 示例 |
| --- | --- | --- |
| 组件文件 | PascalCase | `UserList.vue` |
| 工具文件 | camelCase | `request.ts` |
| 常量 | UPPER_CASE | `API_BASE_URL` |
| 变量/函数 | camelCase | `getUserList` |
| 类型/接口 | PascalCase | `UserInfo` |

### ESLint + Prettier

项目已配置 ESLint 和 Prettier：

```bash
# 检查代码
pnpm lint

# 自动修复
pnpm lint:fix
```

### 组件规范

```vue
<template>
  <!-- 模板内容 -->
</template>

<script setup lang="ts">
// 1. 导入
import { ref, computed } from 'vue'

// 2. 类型定义
interface Props {
  userId: number
}

// 3. Props / Emits
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update', value: string): void
}>()

// 4. 响应式数据
const loading = ref(false)

// 5. 计算属性
const displayName = computed(() => {})

// 6. 方法
const handleClick = () => {}

// 7. 生命周期
onMounted(() => {})
</script>

<style scoped lang="scss">
/* 样式 */
</style>
```
