# 认证模块

认证模块（`core/oauth`）提供基于 OAuth 2.0 的第三方登录能力，支持多种主流平台集成。

## 支持的 OAuth 提供商

| 提供商 | 代码 | 说明 | 获取字段 |
|--------|------|------|----------|
| Gitee | `gitee` | 码云登录 | username, email, avatar |
| GitHub | `github` | GitHub 登录 | username, email, avatar |
| Google | `google` | Google 登录 | email, name, avatar |
| 微软 | `microsoft` | Microsoft 登录 | email, name |
| QQ | `qq` | QQ 互联 | nickname, avatar (无 email) |
| 微信 | `wechat` | 微信开放平台 | nickname, avatar (无 email) |
| 钉钉 | `dingtalk` | 钉钉扫码登录 | nick, email, mobile, avatar |
| 飞书 | `feishu` | 飞书登录 | name, email, mobile, avatar |

## OAuth 2.0 授权流程

### 标准流程图

```
前端                         后端                      OAuth 平台
  │                           │                           │
  │  1. 请求授权 URL           │                           │
  ├──────────────────────────►│                           │
  │                           │  2. 构造授权 URL           │
  │                           ├──────────────────────────►│
  │◄──────────────────────────┤                           │
  │   返回 authorize_url       │                           │
  │                           │                           │
  │  3. 重定向到授权页面        │                           │
  ├───────────────────────────────────────────────────────►│
  │                           │                     4. 用户授权
  │                           │                           │
  │  5. 回调并返回 code        │                           │
  │◄──────────────────────────────────────────────────────┤
  │                           │                           │
  │  6. 发送 code 到后端       │                           │
  ├──────────────────────────►│                           │
  │                           │  7. 用 code 换 access_token
  │                           ├──────────────────────────►│
  │                           │◄──────────────────────────┤
  │                           │  8. 用 token 获取用户信息   │
  │                           ├──────────────────────────►│
  │                           │◄──────────────────────────┤
  │                           │  9. 创建/更新用户          │
  │                           │  10. 生成 JWT Token       │
  │◄──────────────────────────┤                           │
  │   返回 JWT + 用户信息      │                           │
```

### 流程说明

| 步骤 | 说明 | API |
|------|------|-----|
| **1-2** | 前端请求授权 URL，后端构造跳转链接 | `GET /api/oauth/{provider}/authorize` |
| **3-5** | 用户在 OAuth 平台授权，平台回调返回 `code` | 前端处理重定向 |
| **6-10** | 前端将 `code` 发送后端，后端完成换 token、获取用户信息、创建用户、生成 JWT | `POST /api/oauth/{provider}/callback` |

## 架构设计

### 类层次结构

```
BaseOAuthService (抽象基类)
    ├── 定义标准 OAuth 流程
    ├── get_authorize_url()
    ├── get_access_token()
    ├── get_user_info() [抽象]
    └── normalize_user_info() [抽象]
    
    ↓ 子类实现
    
├── GiteeOAuthService
├── GitHubOAuthService
├── QQOAuthService (特殊 token 格式)
├── GoogleOAuthService
├── WeChatOAuthService (需要 openid)
├── MicrosoftOAuthService
├── DingTalkOAuthService (POST JSON body)
└── FeishuOAuthService (需要 app_access_token)
```

### 工厂模式

```python
# oauth_api.py
OAUTH_PROVIDERS = {
    'gitee': GiteeOAuthService,
    'github': GitHubOAuthService,
    'qq': QQOAuthService,
    'google': GoogleOAuthService,
    'wechat': WeChatOAuthService,
    'microsoft': MicrosoftOAuthService,
    'dingtalk': DingTalkOAuthService,
    'feishu': FeishuOAuthService,
}
```

## API 接口

### 获取授权 URL

```http
GET /api/oauth/{provider}/authorize?state=xxx
```

**路径参数：**
- `provider`: OAuth 提供商（gitee/github/qq 等）

**查询参数：**
- `state` (可选): 防 CSRF 攻击的随机字符串

**响应：**
```json
{
  "authorize_url": "https://gitee.com/oauth/authorize?client_id=xxx&redirect_uri=xxx&response_type=code"
}
```

### OAuth 回调处理

```http
POST /api/oauth/{provider}/callback
```

**请求体：**
```json
{
  "code": "授权码",
  "state": "可选的状态参数"
}
```

**响应：**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "expire": 7200,
  "user_info": {
    "id": "123",
    "username": "user123",
    "name": "张三",
    "email": "user@example.com",
    "avatar": "https://...",
    "user_type": "oauth",
    "is_superuser": false
  }
}
```

## 核心实现

### BaseOAuthService

```python
class BaseOAuthService(ABC):
    """OAuth 服务基类"""
    
    PROVIDER_NAME: str = None
    AUTHORIZE_URL: str = None
    TOKEN_URL: str = None
    USER_INFO_URL: str = None
    
    @classmethod
    def get_authorize_url(cls, state: str = None) -> str:
        """构造授权 URL"""
        config = cls.get_client_config()
        params = {
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'response_type': 'code',
        }
        if state:
            params['state'] = state
        params.update(cls.get_extra_authorize_params())
        return f"{cls.AUTHORIZE_URL}?{urlencode(params)}"
    
    @classmethod
    def handle_oauth_login(cls, code: str, ip_address: str, 
                           user_agent: str, login_type: str):
        """处理 OAuth 登录流程"""
        # 1. 用 code 换 access_token
        access_token = cls.get_access_token(code)
        
        # 2. 用 access_token 获取用户信息
        raw_user_info = cls.get_user_info(access_token)
        
        # 3. 标准化用户信息
        user_info = cls.normalize_user_info(raw_user_info)
        
        # 4. 创建或更新用户
        user = cls.create_or_update_user(user_info)
        
        # 5. 生成 JWT token
        return AuthService.generate_tokens(user, ip_address, 
                                          user_agent, login_type)
```

### Gitee 实现示例

```python
class GiteeOAuthService(BaseOAuthService):
    PROVIDER_NAME = 'gitee'
    AUTHORIZE_URL = "https://gitee.com/oauth/authorize"
    TOKEN_URL = "https://gitee.com/oauth/token"
    USER_INFO_URL = "https://gitee.com/api/v5/user"
    
    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        return {
            'client_id': settings.GITEE_CLIENT_ID,
            'client_secret': settings.GITEE_CLIENT_SECRET,
            'redirect_uri': settings.GITEE_REDIRECT_URI,
        }
    
    @classmethod
    def get_user_info(cls, access_token: str) -> Optional[Dict]:
        response = requests.get(
            cls.USER_INFO_URL,
            params={'access_token': access_token}
        )
        return response.json()
    
    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        return {
            'provider_id': str(raw_user_info.get('id')),
            'username': raw_user_info.get('login'),
            'name': raw_user_info.get('name'),
            'email': raw_user_info.get('email'),
            'avatar': raw_user_info.get('avatar_url'),
        }
```

## 特殊平台适配

### QQ 互联

**特殊点**：
- Token 响应是 URL 参数格式：`access_token=xxx&expires_in=xxx`
- 需要先用 token 获取 openid，再用 openid 获取用户信息

```python
# 解析 token
match = re.search(r'access_token=([^&]+)', response_text)
access_token = match.group(1)

# 获取 openid
openid_response = requests.get(OPENID_URL, params={'access_token': access_token})
openid = parse_jsonp(openid_response.text)

# 获取用户信息
user_info = requests.get(USER_INFO_URL, params={
    'access_token': access_token,
    'oauth_consumer_key': client_id,
    'openid': openid
})
```

### 微信开放平台

**特殊点**：
- 使用 `appid` 而非 `client_id`
- 需要同时传递 `access_token` 和 `openid`
- 使用 `unionid` 作为唯一标识

```python
@classmethod
def get_authorize_url(cls, state: str = None) -> str:
    params = {
        'appid': config['client_id'],
        'redirect_uri': config['redirect_uri'],
        'scope': 'snsapi_login',
    }
    return f"{cls.AUTHORIZE_URL}?{urlencode(params)}#wechat_redirect"
```

### 钉钉

**特殊点**：
- 使用 POST JSON body 传递参数
- Token 响应格式：`{"accessToken": "xxx"}`

```python
data = {
    'clientId': config['client_id'],
    'clientSecret': config['client_secret'],
    'code': code,
    'grantType': 'authorization_code',
}
response = requests.post(TOKEN_URL, json=data)
```

### 飞书

**特殊点**：
- 需要先获取 `app_access_token`
- Token 响应格式：`{"code": 0, "data": {"access_token": "xxx"}}`

```python
@classmethod
def get_access_token(cls, code: str) -> Optional[str]:
    app_token = cls._get_app_access_token()
    headers = {'Authorization': f'Bearer {app_token}'}
    response = requests.post(TOKEN_URL, json={'code': code}, headers=headers)
    return response.json()['data']['access_token']
```

## 用户创建与关联

### 唯一标识字段

| 平台 | 字段名 | 说明 |
|------|--------|------|
| Gitee/GitHub | `gitee_id` / `github_id` | provider_id |
| QQ | `qq_openid` | openid |
| 微信 | `wechat_unionid` | unionid (跨应用唯一) |
| 钉钉 | `dingtalk_unionid` | unionId |
| 飞书 | `feishu_union_id` | union_id |

### 用户创建逻辑

```python
@classmethod
def create_or_update_user(cls, user_info: Dict) -> User:
    """创建或更新 OAuth 用户"""
    user_id_field = cls.get_user_id_field()
    provider_id = user_info['provider_id']
    
    # 1. 查找已绑定用户
    user = User.objects.filter(**{user_id_field: provider_id}).first()
    
    if not user:
        # 2. 尝试通过 email 匹配
        if user_info.get('email'):
            user = User.objects.filter(email=user_info['email']).first()
        
        if not user:
            # 3. 创建新用户
            user = User.objects.create(
                username=user_info['username'],
                name=user_info['name'],
                email=user_info['email'],
                avatar=user_info['avatar'],
                user_type='oauth',
                **{user_id_field: provider_id}
            )
            # 分配默认角色
            default_role = Role.objects.filter(code='user').first()
            if default_role:
                user.role.add(default_role)
        else:
            # 4. 绑定现有用户
            setattr(user, user_id_field, provider_id)
            user.save()
    
    return user
```

## 配置说明

在 `env/dev_env.py` 中配置各平台的 OAuth 凭证：

```python
# Gitee OAuth
GITEE_CLIENT_ID = 'your_client_id'
GITEE_CLIENT_SECRET = 'your_client_secret'
GITEE_REDIRECT_URI = 'http://localhost:5173/oauth/gitee/callback'

# GitHub OAuth
GITHUB_CLIENT_ID = 'your_client_id'
GITHUB_CLIENT_SECRET = 'your_client_secret'
GITHUB_REDIRECT_URI = 'http://localhost:5173/oauth/github/callback'

# QQ 互联
QQ_APP_ID = 'your_app_id'
QQ_APP_KEY = 'your_app_key'
QQ_REDIRECT_URI = 'http://localhost:5173/oauth/qq/callback'

# 微信开放平台
WECHAT_APP_ID = 'your_app_id'
WECHAT_APP_SECRET = 'your_app_secret'
WECHAT_REDIRECT_URI = 'http://localhost:5173/oauth/wechat/callback'

# 钉钉
DINGTALK_APP_ID = 'your_app_id'
DINGTALK_APP_SECRET = 'your_app_secret'
DINGTALK_REDIRECT_URI = 'http://localhost:5173/oauth/dingtalk/callback'

# 飞书
FEISHU_APP_ID = 'your_app_id'
FEISHU_APP_SECRET = 'your_app_secret'
FEISHU_REDIRECT_URI = 'http://localhost:5173/oauth/feishu/callback'
```

## 前端集成示例

```typescript
// 1. 获取授权 URL
const { authorize_url } = await fetch('/api/oauth/gitee/authorize').then(r => r.json())

// 2. 重定向到授权页面
window.location.href = authorize_url

// 3. 授权回调页面，提取 code
const code = new URLSearchParams(window.location.search).get('code')

// 4. 将 code 发送到后端
const { access_token, user_info } = await fetch('/api/oauth/gitee/callback', {
  method: 'POST',
  body: JSON.stringify({ code })
}).then(r => r.json())

// 5. 保存 JWT 并跳转
localStorage.setItem('token', access_token)
router.push('/dashboard')
```

## 扩展新平台

### 添加新的 OAuth 提供商

1. 创建 Service 类继承 `BaseOAuthService`
2. 实现必需方法：`get_client_config()`、`get_user_info()`、`normalize_user_info()`
3. 在 `OAUTH_PROVIDERS` 中注册

```python
class GitLabOAuthService(BaseOAuthService):
    PROVIDER_NAME = 'gitlab'
    AUTHORIZE_URL = "https://gitlab.com/oauth/authorize"
    TOKEN_URL = "https://gitlab.com/oauth/token"
    USER_INFO_URL = "https://gitlab.com/api/v4/user"
    
    # 实现必需方法...

# 注册到工厂
OAUTH_PROVIDERS['gitlab'] = GitLabOAuthService
```
