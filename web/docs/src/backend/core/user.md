# 用户管理

用户管理模块负责用户的增删改查、状态管理等功能。

## 功能概述

- 用户列表查询
- 用户新增/编辑/删除
- 用户状态管理
- 密码重置
- 用户角色分配

## 数据模型

```python
class User(CoreModel):
    """用户模型"""
    username = models.CharField(max_length=150, unique=True, verbose_name="用户名")
    password = models.CharField(max_length=128, verbose_name="密码")
    name = models.CharField(max_length=40, blank=True, null=True, verbose_name="姓名")
    email = models.EmailField(blank=True, null=True, verbose_name="邮箱")
    mobile = models.CharField(max_length=20, blank=True, null=True, verbose_name="手机号")
    avatar = models.CharField(max_length=255, blank=True, null=True, verbose_name="头像")
    gender = models.IntegerField(choices=((0, '未知'), (1, '男'), (2, '女')), default=0)
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    
    # 关联
    dept = models.ForeignKey('Dept', on_delete=models.SET_NULL, null=True, verbose_name="部门")
    roles = models.ManyToManyField('Role', blank=True, verbose_name="角色")
    
    class Meta:
        db_table = 'sys_user'
        verbose_name = '用户'
```

## API 接口

### 用户列表

```
GET /api/user/list
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 10 |
| username | string | 否 | 用户名模糊查询 |
| name | string | 否 | 姓名模糊查询 |
| dept_id | int | 否 | 部门 ID |
| is_active | bool | 否 | 状态筛选 |

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "username": "admin",
        "name": "管理员",
        "email": "admin@example.com",
        "mobile": "13800138000",
        "dept_id": 1,
        "dept_name": "总部",
        "is_active": true,
        "roles": [{"id": 1, "name": "管理员"}]
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 10
  }
}
```

### 新增用户

```
POST /api/user/add
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |
| name | string | 否 | 姓名 |
| email | string | 否 | 邮箱 |
| mobile | string | 否 | 手机号 |
| dept_id | int | 否 | 部门 ID |
| role_ids | array | 否 | 角色 ID 列表 |

### 编辑用户

```
PUT /api/user/edit/{id}
```

### 删除用户

```
DELETE /api/user/delete/{id}
```

### 重置密码

```
POST /api/user/reset-password/{id}
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| new_password | string | 是 | 新密码 |

## 使用示例

### 服务层调用

```python
from core.user.services import UserService

# 创建用户
user_service = UserService()
user = user_service.create({
    'username': 'newuser',
    'password': 'password123',
    'name': '新用户',
    'dept_id': 1
})

# 更新用户
user_service.update(user.id, {'name': '更新后的名称'})

# 删除用户
user_service.delete(user.id)
```

## 权限说明

| 权限标识 | 说明 |
| --- | --- |
| user:list | 用户列表 |
| user:add | 新增用户 |
| user:edit | 编辑用户 |
| user:delete | 删除用户 |
| user:reset-password | 重置密码 |
