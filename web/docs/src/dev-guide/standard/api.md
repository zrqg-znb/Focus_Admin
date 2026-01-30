# API 规范

## 接口设计

### RESTful 风格

```
GET    /api/users          # 获取列表
GET    /api/users/{id}     # 获取详情
POST   /api/users          # 创建
PUT    /api/users/{id}     # 更新
DELETE /api/users/{id}     # 删除
```

### 命名规范

- 使用小写字母
- 多个单词使用连字符 `-` 连接
- 使用名词复数形式

```
✓ /api/users
✓ /api/user-roles
✗ /api/getUsers
✗ /api/user_list
```

## 响应格式

### 统一响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

### 状态码

| 状态码 | 说明 |
| --- | --- |
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

### 分页响应

```json
{
  "code": 200,
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "page_size": 10
  }
}
```

## 请求规范

### 请求头

```
Authorization: Bearer <token>
Content-Type: application/json
```

### 分页参数

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| page | int | 页码，从 1 开始 |
| page_size | int | 每页数量 |

### 排序参数

```
GET /api/users?sort=create_time&order=desc
```

## 错误处理

### 错误响应

```json
{
  "code": 400,
  "message": "参数错误",
  "errors": [
    {
      "field": "username",
      "message": "用户名不能为空"
    }
  ]
}
```

## 版本管理

API 版本通过 URL 前缀区分：

```
/api/v1/users
/api/v2/users
```
