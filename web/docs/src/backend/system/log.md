# 日志管理

日志管理模块负责记录系统的操作日志和登录日志。

## 功能概述

- 操作日志记录
- 登录日志记录
- 日志查询
- 日志导出

## 操作日志

### 数据模型

```python
class OperationLog(CoreModel):
    """操作日志"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    module = models.CharField(max_length=64, verbose_name="模块")
    action = models.CharField(max_length=64, verbose_name="操作")
    method = models.CharField(max_length=16, verbose_name="请求方法")
    url = models.CharField(max_length=255, verbose_name="请求URL")
    ip = models.CharField(max_length=64, verbose_name="IP地址")
    request_data = models.TextField(blank=True, verbose_name="请求参数")
    response_data = models.TextField(blank=True, verbose_name="响应数据")
    status = models.IntegerField(default=1, verbose_name="状态")
    cost_time = models.IntegerField(default=0, verbose_name="耗时(ms)")
    
    class Meta:
        db_table = 'sys_operation_log'
```

### API 接口

```
GET /api/operation-log/list
```

## 登录日志

### 数据模型

```python
class LoginLog(CoreModel):
    """登录日志"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    username = models.CharField(max_length=64)
    ip = models.CharField(max_length=64, verbose_name="登录IP")
    location = models.CharField(max_length=128, blank=True, verbose_name="登录地点")
    browser = models.CharField(max_length=64, blank=True, verbose_name="浏览器")
    os = models.CharField(max_length=64, blank=True, verbose_name="操作系统")
    status = models.IntegerField(default=1, verbose_name="状态")
    msg = models.CharField(max_length=255, blank=True, verbose_name="消息")
    
    class Meta:
        db_table = 'sys_login_log'
```

### API 接口

```
GET /api/login-log/list
```

## 日志记录

### 使用装饰器

```python
from common.decorators import operation_log

@router.post('/user/add')
@operation_log(module='用户管理', action='新增用户')
def add_user(request, data: UserSchema):
    pass
```

### 自动记录

系统会自动记录以下操作：

- 用户登录/登出
- 数据增删改操作
- 重要业务操作
