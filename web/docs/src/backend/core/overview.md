# 核心模块概览

核心模块 (`core/`) 是 Focus Admin 的基础功能模块，提供用户认证、权限管理、组织架构等核心功能。

## 模块列表

| 模块 | 目录 | 说明 |
| --- | --- | --- |
| [认证模块](/backend/core/auth) | `core/auth/` | 用户登录、JWT Token 管理 |
| [用户管理](/backend/core/user) | `core/user/` | 用户增删改查、状态管理 |
| [角色管理](/backend/core/role) | `core/role/` | 角色定义、权限分配 |
| [权限管理](/backend/core/permission) | `core/permission/` | API 权限、按钮权限 |
| [菜单管理](/backend/core/menu) | `core/menu/` | 动态菜单配置 |
| [部门管理](/backend/core/dept) | `core/dept/` | 组织架构管理 |

## 目录结构

```
core/
├── __init__.py
├── apps.py                  # Django App 配置
├── router.py                # 路由汇总
├── models/                  # 共享模型
│
├── auth/                    # 认证模块
│   ├── api.py              # 登录/登出 API
│   └── schemas.py          # 认证 Schema
│
├── user/                    # 用户管理
│   ├── api.py              # 用户 CRUD API
│   ├── models.py           # 用户模型
│   ├── schemas.py          # 用户 Schema
│   └── services.py         # 用户服务
│
├── role/                    # 角色管理
│   ├── api.py
│   ├── models.py
│   ├── schemas.py
│   └── services.py
│
├── permission/              # 权限管理
│   ├── api.py
│   ├── models.py
│   ├── schemas.py
│   └── services.py
│
├── menu/                    # 菜单管理
│   ├── api.py
│   ├── models.py
│   ├── schemas.py
│   └── services.py
│
├── dept/                    # 部门管理
│   ├── api.py
│   ├── models.py
│   ├── schemas.py
│   └── services.py
│
├── dict/                    # 字典管理
├── dict_item/               # 字典项管理
├── post/                    # 岗位管理
├── file_manager/            # 文件管理
├── operation_log/           # 操作日志
├── login_log/               # 登录日志
├── server_monitor/          # 服务器监控
├── database_manager/        # 数据库管理
├── database_monitor/        # 数据库监控
├── redis_manager/           # Redis 管理
├── redis_monitor/           # Redis 监控
├── oauth/                   # OAuth 登录
└── websocket/               # WebSocket
```

## API 路由

核心模块的 API 路由在 `core/router.py` 中汇总：

```python
from ninja import Router
from core.auth.api import router as auth_router
from core.user.api import router as user_router
from core.role.api import router as role_router
# ...

router = Router()
router.add_router('/auth', auth_router, tags=['认证'])
router.add_router('/user', user_router, tags=['用户管理'])
router.add_router('/role', role_router, tags=['角色管理'])
# ...
```

## 公共基类

### Model 基类

`common/fu_model.py` 提供统一的模型基类：

```python
class CoreModel(models.Model):
    """核心模型基类"""
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name="描述")
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    modifier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    create_datetime = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_datetime = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        abstract = True
```

### CRUD 基类

`common/fu_crud.py` 提供统一的 CRUD 操作基类：

```python
class CRUDBase:
    """CRUD 操作基类"""
    
    def get(self, id: int):
        """获取单条记录"""
        pass
    
    def get_list(self, filters=None, page=1, page_size=10):
        """获取列表"""
        pass
    
    def create(self, data: dict):
        """创建记录"""
        pass
    
    def update(self, id: int, data: dict):
        """更新记录"""
        pass
    
    def delete(self, id: int):
        """删除记录"""
        pass
```

## 权限控制

### 认证装饰器

`common/fu_auth.py` 提供认证装饰器：

```python
from functools import wraps
from ninja.security import HttpBearer

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        # 验证 JWT Token
        pass

# 使用示例
@router.get('/users', auth=AuthBearer())
def list_users(request):
    pass
```

### 权限装饰器

```python
def permission_required(permission_code: str):
    """权限验证装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # 检查用户是否具有指定权限
            if not has_permission(request.user, permission_code):
                raise PermissionDenied()
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
```

## 下一步

- [认证模块详解](/backend/core/auth)
- [用户管理详解](/backend/core/user)
- [角色管理详解](/backend/core/role)
- [权限管理详解](/backend/core/permission)
