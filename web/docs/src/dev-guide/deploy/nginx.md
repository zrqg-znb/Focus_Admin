# Focus 生产部署与 Nginx 配置

本文档面向当前 Focus 仓库的生产部署场景，重点解决：

- 主站 `web-ele` 与 `web-deepaudit` 如何共存
- 域名、Nginx、静态资源、后端 API 如何统一编排
- 为什么本地一切正常，但生产环境 `WebSocket / SSE` 都不工作
- Nginx 应该怎么代理 `/basic-api/`、`/ws/`、DeepAudit `/stream`

如果你当前现象是：

- Focus 基础功能正常
- DeepAudit 页面能打开
- 但 `ws` 能力不支持
- `sse` 能力也不支持

那么几乎可以确定问题不在前端业务代码，而在部署链路。

## 1. 部署结论先说

当前项目要想在生产环境里同时支持普通 API、WebSocket 和 DeepAudit 的 SSE，必须满足以下条件：

1. 后端必须运行 `application.asgi:application`
2. 运行进程必须是 ASGI 进程，而不是纯 WSGI
3. Nginx 必须代理 `/basic-api/` 到同一个 ASGI 服务
4. Nginx 必须代理 `/ws/` 并正确转发 `Upgrade/Connection`
5. DeepAudit 的 SSE 路径必须单独关闭 `proxy_buffering`
6. `CHANNEL_LAYERS` 必须可用，Redis `REDIS_CHANNEL_DB` 不能缺
7. `web-deepaudit` 的前端 API 基址必须保持 `/basic-api/api`

只要其中任意一项缺失，就会出现“基础功能正常，但 WS/SSE 挂掉”的情况。

## 2. 你这个项目的真实访问路径

当前仓库的前端与后端路径约定不是通用模板，而是固定成了下面这套：

### 主站

- 主站页面：`/`
- 主站 API：`/basic-api/`

### DeepAudit

- DeepAudit 页面：`/deepaudit-app/`
- DeepAudit API：`/basic-api/api/deepaudit/*`
- DeepAudit SSE：`/basic-api/api/deepaudit/agent-tasks/{task_id}/stream`
- DeepAudit WebSocket：`/ws/deepaudit/tasks/{task_id}/`

### 为什么不是直接 `/api/`

因为 `web/apps/web-deepaudit/src/shared/api/focusAdapter.ts` 里默认写的是：

```ts
const API_BASE_URL_RAW = import.meta.env.VITE_API_BASE_URL || '/basic-api/api';
```

所以生产环境如果你只代理 `/api/`，DeepAudit 会天然打不到正确路径。

## 3. 后端必须怎么启动

### 正确做法

必须启动：

```bash
gunicorn application.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8001 --workers 4 --timeout 120
```

或者：

```bash
uvicorn application.asgi:application --host 127.0.0.1 --port 8001
```

### 错误做法

如果你启动的是：

```bash
gunicorn application.wsgi:application
```

或者任何纯 WSGI 入口，那么结果通常是：

- 普通 HTTP API 正常
- WebSocket 不可用
- DeepAudit 的流式能力也容易异常

原因很简单：

- WebSocket 依赖 ASGI 与 Channels
- 当前项目 `application/asgi.py` 明确挂了 `ProtocolTypeRouter`
- `core/websocket/routing.py` 已经注册了 `/ws/deepaudit/tasks/{task_id}/`

也就是说，这个项目的实时能力从设计上就要求跑 ASGI。

## 4. Redis 与 Channels 不能缺

在 `application/settings.py` 中已经启用了：

- `ASGI_APPLICATION = 'application.asgi.application'`
- `CHANNEL_LAYERS`

并且 `CHANNEL_LAYERS` 走的是：

- `REDIS_CHANNEL_DB`

因此生产环境至少要保证：

- Redis 正常
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_PASSWORD`
- `REDIS_CHANNEL_DB`

如果 Redis Channels 不通，最常见表现是：

- WebSocket 能连上但收不到事件
- 或者 WebSocket 直接异常断开

## 5. Nginx 单域名生产配置

下面给的是适合生产环境的一套单域名配置示例。假设：

- 域名：`focus.example.com`
- 主站 dist：`/var/www/focus`
- DeepAudit dist：`/var/www/deepaudit`
- 后端 ASGI：`127.0.0.1:8001`

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

upstream focus_backend {
    server 127.0.0.1:8001;
    keepalive 32;
}

server {
    listen 80;
    server_name focus.example.com;

    client_max_body_size 500M;
    root /var/www/focus;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location = /deepaudit-app {
        return 301 /deepaudit-app/;
    }

    location /deepaudit-app/ {
        alias /var/www/deepaudit/;
        index index.html;
        try_files $uri $uri/ /deepaudit-app/index.html;
    }

    location /static/ {
        alias /srv/focus-prod/Focus_Admin/backend-django/static_root/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public";
    }

    location /media/ {
        alias /srv/focus-prod/Focus_Admin/backend-django/media/;
    }

    # DeepAudit SSE 必须单独处理
    location ~ ^/basic-api/api/deepaudit/agent-tasks/[^/]+/stream$ {
        rewrite ^/basic-api/(.*)$ /$1 break;
        proxy_pass http://focus_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering off;
        proxy_cache off;
        proxy_set_header X-Accel-Buffering no;
        chunked_transfer_encoding on;

        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_connect_timeout 30s;
    }

    # Focus + DeepAudit 常规 API
    location /basic-api/ {
        proxy_pass http://focus_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://focus_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

## 6. HTTPS 版本要点

如果你使用 HTTPS，对 WebSocket 不需要额外改业务代码，但要保证浏览器最终走的是：

- 页面：`https://focus.example.com/deepaudit-app/`
- WebSocket：`wss://focus.example.com/ws/...`

一个标准 HTTPS server block 只需要在上面基础上补：

- `listen 443 ssl http2`
- 证书配置
- 80 到 443 的 301 跳转

## 7. 为什么 SSE 在 Nginx 下最容易失效

DeepAudit 的 SSE 使用的是：

- `StreamingHttpResponse`
- `content_type = text/event-stream`

如果 Nginx 没有对这条路径单独配置：

- `proxy_buffering off`
- `proxy_cache off`
- `X-Accel-Buffering no`
- 足够长的 `proxy_read_timeout`

就会出现这些现象：

- Network 面板看请求 200 了
- 但前端日志要么很久不刷新
- 要么直到任务结束才一次性把数据吐出来

这不是后端没返回，而是被 Nginx 缓冲了。

## 8. 为什么 WebSocket 在生产最容易失效

DeepAudit 的 WS 路径是：

- `/ws/deepaudit/tasks/{task_id}/`

这条链同时依赖：

- ASGI 进程
- Channels
- Redis channel layer
- Nginx `Upgrade/Connection` 头

如果你漏了下面任意一个：

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

就会出现：

- 握手失败
- 101 切换协议失败
- 连接秒断

## 9. 前端构建时必须确认的环境变量

### `web-ele`

主站通常保持：

```env
VITE_GLOB_API_URL=/basic-api/
```

### `web-deepaudit`

DeepAudit 需要：

```env
VITE_API_BASE_URL=/basic-api/api
```

同时 Vite `base` 需要保持：

```ts
base: '/deepaudit-app/'
```

如果这里写错，最常见现象就是：

- 主站正常
- DeepAudit 静态资源或 API 全部 404

## 10. 进程建议

生产环境至少建议这几类进程分开：

### 1. Django ASGI

- 负责所有 HTTP、SSE、WebSocket

### 2. Celery 默认 worker

- 负责常规异步任务

### 3. Celery DeepAudit worker

- 负责 DeepAudit 任务执行

### 4. Scheduler

- 负责调度类任务

如果只起了 Django 后端而没起 DeepAudit worker，常见表现是：

- 能创建任务
- 但任务一直停在 `pending`

## 11. 服务器检查清单

上线前建议按下面顺序排：

### 1. 进程检查

```bash
ps -ef | grep gunicorn | grep application.asgi
ps -ef | grep celery
```

### 2. Redis 检查

```bash
redis-cli -h 127.0.0.1 -p 6379 ping
```

### 3. Nginx 检查

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4. 本机回环检查

```bash
curl -I http://127.0.0.1:8001/api/deepaudit/projects
```

### 5. SSE 检查

拿一个真实任务 ID：

```bash
curl -N "http://focus.example.com/basic-api/api/deepaudit/agent-tasks/<task_id>/stream?include_thinking=true&include_tool_calls=true&after_sequence=0" \
  -H "Authorization: Bearer <access_token>"
```

如果这条命令本机直连有输出，但域名访问没输出，优先查 Nginx 缓冲。

### 6. WebSocket 检查

用浏览器 Network 或专门 WebSocket 工具看：

- 是否出现 101 Switching Protocols
- 是否很快收到 `deepaudit_ready`

## 12. 最常见的错误部署方式

下面这些都是高频坑：

### 1. 用 `application.wsgi` 启动

后果：

- WS 直接不可用

### 2. 只代理 `/api/`，没代理 `/basic-api/`

后果：

- `web-ele` 可能部分功能正常
- `web-deepaudit` 接口全挂或流式路径打空

### 3. `/deepaudit-app/` 没做 SPA 回退

后果：

- 刷新子路由 404

### 4. SSE 没单独禁缓冲

后果：

- 请求 200 但日志长期不刷新

### 5. 没配 `/ws/`

后果：

- 所有实时 socket 失效

### 6. Redis 只给 cache/celery，没给 channel layer

后果：

- WebSocket 连接建立但事件推送异常

## 13. 推荐阅读

- [DeepAudit 智能审计主线页](/modules/deepaudit)
- [DeepAudit 后端实现附录](/backend/apps/deepaudit)
- [DeepAudit 前端应用附录](/frontend/views/deepaudit)
