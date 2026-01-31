# 核心模块概览

核心模块 (`core/`) 是 Focus Admin 的基础功能模块，提供用户认证、权限管理、组织架构等核心功能。

## 架构概览

### 模块关系图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Core 核心模块                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       认证与授权层                              │  │
│  │  ┌────────────┐      ┌────────────┐      ┌────────────┐       │  │
│  │  │    Auth    │      │ Permission │      │   OAuth    │       │  │
│  │  │  认证登录    │      │  权限管理   │      │  第三方登录  │       │  │
│  │  └────────────┘      └────────────┘      └────────────┘       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                │                                      │
│                                ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       用户与组织层                              │  │
│  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐          │  │
│  │  │ User  │ │ Role  │ │ Dept  │ │ Post  │ │ Menu  │          │  │
│  │  │ 用户   │ │ 角色   │ │ 部门   │ │ 岗位   │ │ 菜单   │          │  │
│  │  └───┬───┘ └───┬───┘ └───┬───┘ └───────┘ └───────┘          │  │
│  │      │         │         │                                    │  │
│  │      └─────────┴─────────┘                                    │  │
│  │              │                                                  │  │
│  │              ▼                                                  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │    User ↔ Role ↔ Permission ↔ Menu (多对多关联)    │  │  │
│  │  │    User ↔ Dept (属于关系)                          │  │  │
│  │  │    Dept (树形结构，自关联)                         │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                │                                      │
│                                ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       系统辅助层                              │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │  │
│  │  │  Dict   │ │LoginLog│ │ OpLog   │ │FileMgr  │  ...   │  │
│  │  │  字典    │ │登录日志 │ │操作日志  │ │文件管理  │        │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                │                                      │
│                                ▼                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                       系统监控层                              │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │  │
│  │  │ServerMonitor│ │ DBMonitor   │ │RedisMonitor│  ...   │  │
│  │  │  服务器监控   │ │  数据库监控  │ │ Redis监控  │        │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### RBAC 权限模型

系统采用基于角色的访问控制（RBAC）模型：

```
     ┌─────────┐
     │  User   │
     │  用户    │
     └────┬────┘
          │ M:N
          ▼
     ┌─────────┐
     │  Role   │
     │  角色    │
     └────┬────┘
          │ M:N
    ┌─────┼─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│Permission│ │  Menu   │
│ API权限   │ │ 菜单权限  │
└─────────┘ └─────────┘
```

**关系说明：**

| 关系 | 说明 |
| --- | --- |
| User ↔ Role | 用户可拥有多个角色，角色可分配给多个用户 |
| Role ↔ Permission | 角色可拥有多个 API 权限 |
| Role ↔ Menu | 角色可拥有多个菜单权限 |
| User → Dept | 用户属于一个部门 |

### 组织架构

```
Dept (部门 - 树形结构)
├── Dept (子部门)
│   ├── User
│   └── User
├── Dept (子部门)
│   ├── Dept (孙部门)
│   │   └── User
│   └── User
└── ...
```

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

## 模块分类

### 认证与授权

| 模块 | 目录 | 说明 |
| --- | --- | --- |
| 认证模块 | `core/auth/` | 用户登录、JWT Token 管理 |
| 权限管理 | `core/permission/` | API 权限、按钮权限 |
| OAuth | `core/oauth/` | 第三方登录集成 |

### 用户与组织

| 模块 | 目录 | 说明 |
| --- | --- | --- |
| 用户管理 | `core/user/` | 用户增删改查、状态管理 |
| 角色管理 | `core/role/` | 角色定义、权限分配 |
| 部门管理 | `core/dept/` | 组织架构管理 |
| 岗位管理 | `core/post/` | 岗位定义 |
| 菜单管理 | `core/menu/` | 动态菜单配置 |

### 系统辅助

| 模块 | 目录 | 说明 |
| --- | --- | --- |
| 字典管理 | `core/dict/` | 数据字典配置 |
| 字典项 | `core/dict_item/` | 字典项管理 |
| 文件管理 | `core/file_manager/` | 文件上传/下载/预览 |
| 登录日志 | `core/login_log/` | 用户登录记录 |
| 操作日志 | `core/operation_log/` | 用户操作审计 |
| WebSocket | `core/websocket/` | 实时通信 |

### 系统监控

| 模块 | 目录 | 说明 |
| --- | --- | --- |
| 服务器监控 | `core/server_monitor/` | CPU/内存/磁盘指标 |
| 数据库管理 | `core/database_manager/` | 数据库连接管理 |
| 数据库监控 | `core/database_monitor/` | 慢查询/连接池 |
| Redis 管理 | `core/redis_manager/` | Redis 连接管理 |
| Redis 监控 | `core/redis_monitor/` | Redis 性能指标 |

## 下一步

- [认证模块详解](/backend/core/auth)
- [用户管理详解](/backend/core/user)
- [角色管理详解](/backend/core/role)
- [权限管理详解](/backend/core/permission)
