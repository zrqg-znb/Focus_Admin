# 认证模块

认证模块负责用户登录、登出、Token 管理等功能。

## 功能概述

- 用户名密码登录
- JWT Token 生成和验证
- Token 刷新
- 用户登出

## API 接口

### 登录

```
POST /api/auth/login
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 7200
  }
}
```

### 获取用户信息

```
GET /api/auth/userinfo
```

**请求头：**

```
Authorization: Bearer <access_token>
```

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "id": 1,
    "username": "admin",
    "name": "管理员",
    "avatar": "https://...",
    "roles": ["admin"],
    "permissions": ["user:list", "user:add", "user:edit"]
  }
}
```

### 刷新 Token

```
POST /api/auth/refresh
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| refresh_token | string | 是 | 刷新 Token |

### 登出

```
POST /api/auth/logout
```

## Token 机制

### JWT 结构

```
Header.Payload.Signature
```

**Payload 内容：**

```json
{
  "user_id": 1,
  "username": "admin",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Token 有效期

| Token 类型 | 有效期 | 说明 |
| --- | --- | --- |
| Access Token | 2 小时 | 用于 API 认证 |
| Refresh Token | 7 天 | 用于刷新 Access Token |

## 代码示例

### 登录实现

```python
# core/auth/api.py
from ninja import Router
from core.auth.schemas import LoginSchema, TokenSchema
from common.fu_auth import create_token

router = Router()

@router.post('/login', response=TokenSchema)
def login(request, data: LoginSchema):
    # 验证用户
    user = authenticate(username=data.username, password=data.password)
    if not user:
        raise AuthenticationFailed('用户名或密码错误')
    
    # 生成 Token
    access_token = create_token(user, token_type='access')
    refresh_token = create_token(user, token_type='refresh')
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 7200
    }
```

### Schema 定义

```python
# core/auth/schemas.py
from pydantic import BaseModel

class LoginSchema(BaseModel):
    username: str
    password: str

class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
```

## 配置说明

在 `env/dev_env.py` 中配置 JWT 相关参数：

```python
# JWT 配置
JWT_SECRET_KEY = 'your-secret-key'
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE = 7200  # 2小时
JWT_REFRESH_TOKEN_EXPIRE = 604800  # 7天
```
