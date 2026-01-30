# 权限管理

权限管理模块负责系统权限的定义和管理。

## 功能概述

- 权限列表查询
- 权限新增/编辑/删除
- 按钮级权限控制
- API 权限控制

## 数据模型

```python
class Permission(CoreModel):
    """权限模型"""
    name = models.CharField(max_length=64, verbose_name="权限名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="权限标识")
    type = models.IntegerField(choices=((1, '菜单'), (2, '按钮'), (3, 'API')), default=2)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    sort = models.IntegerField(default=0, verbose_name="排序")
    
    class Meta:
        db_table = 'sys_permission'
        verbose_name = '权限'
```

## 权限标识命名规范

权限标识采用 `模块:操作` 的格式：

| 示例 | 说明 |
| --- | --- |
| `user:list` | 用户列表 |
| `user:add` | 新增用户 |
| `user:edit` | 编辑用户 |
| `user:delete` | 删除用户 |

## API 接口

### 权限列表

```
GET /api/permission/list
```

### 权限树

```
GET /api/permission/tree
```

**响应示例：**

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "用户管理",
      "code": "user",
      "children": [
        {"id": 2, "name": "用户列表", "code": "user:list"},
        {"id": 3, "name": "新增用户", "code": "user:add"}
      ]
    }
  ]
}
```

## 权限验证

### 后端权限验证

```python
from common.fu_auth import permission_required

@router.get('/users')
@permission_required('user:list')
def list_users(request):
    pass
```

### 前端权限验证

```vue
<template>
  <!-- 按钮权限 -->
  <el-button v-if="hasPermission('user:add')">新增</el-button>
</template>

<script setup>
import { usePermission } from '@/hooks/usePermission'
const { hasPermission } = usePermission()
</script>
```
