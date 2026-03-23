# Focus + DeepAudit 生产部署手册

本文档用于把 Focus 平台与 DeepAudit 子应用一起部署到同一台 Linux 服务器，并满足以下目标：

- Focus 主平台通过 `/` 提供服务
- DeepAudit React 子应用通过 `/deepaudit-app/` 提供服务
- Django ASGI 后端统一承载 HTTP API、WebSocket、SSE
- Celery + Redis 承载异步任务，DeepAudit 重任务与平台默认任务分离消费

本文档默认采用以下生产方案：

- 单机同域部署
- `systemd` 管理后端与队列进程
- `nginx` 托管两个前端 `dist` 并反向代理 Django
- 不使用 Docker 作为主流程

## 1. 部署架构总览

生产环境建议采用如下拓扑：

```text
Browser
  ├─ /                    -> Focus Vue dist
  ├─ /deepaudit-app/      -> DeepAudit React dist
  ├─ /basic-api/          -> Nginx -> Django ASGI (:8001) -> /api/
  └─ /ws/                 -> Nginx -> Django ASGI (:8001)

Django ASGI
  ├─ HTTP API: /api/**
  ├─ WebSocket: /ws/deepaudit/tasks/{task_id}/
  └─ SSE: /api/deepaudit/agent-tasks/{task_id}/stream

Celery
  ├─ 默认队列 celery
  └─ DeepAudit 专用队列 deepaudit

Redis
  ├─ Django cache
  ├─ Celery broker
  └─ Channels layer
```

关键说明：

- DeepAudit 没有独立登录入口，登录态复用 Focus。
- WebSocket 与 SSE 都复用同一个 Django ASGI 服务，不需要再单独启动 websocket 服务。
- 前端对外统一走同域：
  - Focus: `/`
  - DeepAudit: `/deepaudit-app/`
  - API 代理入口: `/basic-api/`
  - WebSocket: `/ws/deepaudit/tasks/{task_id}/`

## 2. 服务器准备

建议目录约定如下：

```bash
/srv/focus/Focus_Admin                 # 项目代码
/srv/focus/venv                        # Python 虚拟环境
/srv/www/focus-web                     # Focus 前端 dist
/srv/www/deepaudit-app                 # DeepAudit 前端 dist
```

建议基础环境：

- Linux x86_64
- Python 3.12
- Node.js 20+
- pnpm 10+
- nginx
- Redis
- MySQL 或 PostgreSQL

示例安装准备：

```bash
sudo mkdir -p /srv/focus /srv/www/focus-web /srv/www/deepaudit-app
sudo chown -R $USER:$USER /srv/focus /srv/www/focus-web /srv/www/deepaudit-app

cd /srv/focus
git clone <your-repo-url> Focus_Admin

python3.12 -m venv /srv/focus/venv
source /srv/focus/venv/bin/activate

corepack enable
corepack prepare pnpm@10.14.0 --activate
```

## 3. 后端部署

### 3.1 安装依赖

```bash
cd /srv/focus/Focus_Admin/backend-django
source /srv/focus/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2 创建生产环境变量

项目会自动读取 `backend-django/.env`。推荐创建如下文件：

```bash
cd /srv/focus/Focus_Admin/backend-django
cp .env.example .env 2>/dev/null || touch .env
```

示例 `backend-django/.env`：

```env
ZQ_ENV=prd

# Django / JWT
DJANGO_SECRET_KEY=replace-with-a-strong-secret
JWT_ACCESS_SECRET_KEY=replace-with-a-strong-access-secret
JWT_REFRESH_SECRET_KEY=replace-with-a-strong-refresh-secret

# Database
# 如果你实际生产库不是 prd_env.py 中默认的 PostgreSQL，请先同步 env/prd_env.py 的数据库类型配置
PRD_DB_USER=focus_prod
PRD_DB_PASSWORD=replace-with-db-password

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=2
REDIS_CELERY_DB=3
REDIS_CHANNEL_DB=4

# DeepAudit
DEEPAUDIT_QUEUE=deepaudit
```

如需把缓存、Celery、Channels 隔离，推荐使用不同 Redis DB：

- `REDIS_DB=2`
- `REDIS_CELERY_DB=3`
- `REDIS_CHANNEL_DB=4`

### 3.3 后端生产风险检查

当前代码中有几项上线前必须核对：

- `application/settings.py` 里当前写死了 `DEBUG = True`，上线前必须改为生产安全值。
- `ALLOWED_HOSTS = ['*']` 目前过宽，生产建议改成明确域名或 IP 白名单。
- `env/prd_env.py` 当前默认数据库类型是 `POSTGRESQL`，如果你的生产环境实际使用 MySQL，需要先同步配置。
- `web/apps/web-ele/.env.production` 当前仍指向旧线上域名，生产构建前必须改为同域 `/basic-api/`。

### 3.4 静态资源与目录准备

```bash
cd /srv/focus/Focus_Admin/backend-django
mkdir -p logs static_root media/file_manager media/chunk_uploads
python manage.py collectstatic --noinput
```

这些目录必须确保运行用户可写：

- `backend-django/logs`
- `backend-django/static_root`
- `backend-django/media/file_manager`
- 分片上传临时目录

否则可能影响：

- ZIP 上传
- 报告导出
- 文件管理
- Django 日志轮转

## 4. 数据库初始化

### 4.1 迁移

```bash
cd /srv/focus/Focus_Admin/backend-django
source /srv/focus/venv/bin/activate
python manage.py migrate
```

### 4.2 是否加载基础种子数据

仅在“全新空库且需要 Focus 基础平台菜单、角色、权限”的情况下执行：

```bash
python manage.py loaddata db_init.json
```

如果当前生产库已经是现有 Focus 主库，不要重复执行 `loaddata db_init.json`，避免覆盖或引入重复基础数据。

### 4.3 确保存在超管

`init_deepaudit` 会使用首个超管用户作为初始化操作人。执行前请确认数据库里已有超管用户。

如果没有，可以先创建：

```bash
python manage.py createsuperuser
```

### 4.4 初始化 DeepAudit

```bash
python manage.py init_deepaudit
```

该命令会增量初始化以下内容：

- DeepAudit 平台菜单
- DeepAudit 菜单权限与接口权限
- 默认提示词模板
- 默认规则集

这是生产环境启用 DeepAudit 的关键命令，而且支持重复执行，用于补齐或修正菜单权限数据。

### 4.5 初始化后的验收点

- Focus 左侧菜单出现 `DeepAudit 平台`
- 该菜单是一个新窗口入口，指向 `/deepaudit-app/`
- DeepAudit 相关权限码已写入数据库

如果菜单没出现，优先检查：

- 是否执行了 `python manage.py init_deepaudit`
- 当前登录角色是否已分配对应菜单权限
- 菜单缓存/权限缓存是否已刷新

## 5. 前端构建与发布

### 5.1 安装依赖

```bash
cd /srv/focus/Focus_Admin/web
pnpm install --frozen-lockfile
```

### 5.2 构建前确认生产 API 地址

#### Focus

`web-ele` 当前仓库内的 `web/apps/web-ele/.env.production` 仍然指向旧线上地址：

```env
VITE_GLOB_API_URL=https://django-ninja.zq-platform.cn/basic-api/
```

生产部署前建议改为同域相对地址：

```env
VITE_GLOB_API_URL=/basic-api/
```

推荐做法有两种，二选一：

1. 直接修改 `web/apps/web-ele/.env.production`
2. 新建 `web/apps/web-ele/.env.production.local` 覆盖该变量

#### DeepAudit

DeepAudit 当前生产 API 基址已经是同域相对路径：

```env
VITE_API_BASE_URL=/basic-api/api
```

同时其 Vite `base` 已固定为：

```env
/deepaudit-app/
```

这部分保持不变即可。

### 5.3 构建两个前端

```bash
cd /srv/focus/Focus_Admin/web
pnpm build:ele
pnpm build:deepaudit
```

构建产物目录：

- Focus: `web/apps/web-ele/dist`
- DeepAudit: `web/apps/web-deepaudit/dist`

### 5.4 发布 dist 到 nginx 目录

```bash
rsync -av --delete /srv/focus/Focus_Admin/web/apps/web-ele/dist/ /srv/www/focus-web/
rsync -av --delete /srv/focus/Focus_Admin/web/apps/web-deepaudit/dist/ /srv/www/deepaudit-app/
```

## 6. 常驻进程与 systemd

推荐拆成 3 个常驻服务：

- `focus-backend.service`
- `focus-celery-default.service`
- `focus-celery-deepaudit.service`

这样可以把 DeepAudit 重任务和 Focus 其他异步任务拆开，互不影响。

### 6.1 focus-backend.service

文件路径：

```bash
/etc/systemd/system/focus-backend.service
```

示例内容：

```ini
[Unit]
Description=Focus Django ASGI Backend
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus/Focus_Admin/backend-django
EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=/srv/focus/venv/bin/gunicorn application.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8001 --workers 4 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

说明：

- 该服务同时承载 HTTP API、WebSocket、SSE。
- 不需要额外再启动一个独立 websocket 服务。

### 6.2 focus-celery-default.service

文件路径：

```bash
/etc/systemd/system/focus-celery-default.service
```

示例内容：

```ini
[Unit]
Description=Focus Celery Worker (default queue)
After=network.target redis.service focus-backend.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus/Focus_Admin/backend-django
EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=/srv/focus/venv/bin/python -m celery -A application worker -Q celery -l info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

该服务负责消费 Focus 平台默认异步任务，例如未显式指定 DeepAudit 队列的 Celery 任务。

### 6.3 focus-celery-deepaudit.service

文件路径：

```bash
/etc/systemd/system/focus-celery-deepaudit.service
```

示例内容：

```ini
[Unit]
Description=Focus Celery Worker (DeepAudit queue)
After=network.target redis.service focus-backend.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus/Focus_Admin/backend-django
EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=/srv/focus/venv/bin/python -m celery -A application worker -Q deepaudit -l info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

该服务专门消费：

- `deepaudit.run_scan_task`
- `deepaudit.run_agent_task`

### 6.4 可选调度器

如果生产环境还需要启用 Focus 自身的调度中心，可再单独运行一个可选服务：

```bash
python start_scheduler.py
```

注意：

- 这不是 DeepAudit 必需链路
- 只有你确实在生产环境使用平台调度中心时，才需要额外常驻该进程

### 6.5 启动与开机自启

```bash
sudo systemctl daemon-reload
sudo systemctl enable focus-backend focus-celery-default focus-celery-deepaudit
sudo systemctl start focus-backend focus-celery-default focus-celery-deepaudit
```

查看状态：

```bash
systemctl status focus-backend
systemctl status focus-celery-default
systemctl status focus-celery-deepaudit
```

## 7. nginx 部署

### 7.1 推荐站点配置

文件路径：

```bash
/etc/nginx/conf.d/focus.conf
```

示例配置：

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;
    server_name your.domain.com;

    client_max_body_size 500M;

    root /srv/www/focus-web;
    index index.html;

    # Focus 主应用
    location / {
        try_files $uri $uri/ /index.html;
    }

    # DeepAudit React 子应用
    location /deepaudit-app/ {
        alias /srv/www/deepaudit-app/;
        index index.html;
        try_files $uri $uri/ /deepaudit-app/index.html;
    }

    # Django static
    location /static/ {
        alias /srv/focus/Focus_Admin/backend-django/static_root/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public";
    }

    # DeepAudit SSE 流接口
    location ~ ^/basic-api/api/deepaudit/agent-tasks/[^/]+/stream$ {
        rewrite ^/basic-api/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:8001;
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

    # Django API
    location /basic-api/ {
        proxy_pass http://127.0.0.1:8001/;
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
        proxy_pass http://127.0.0.1:8001;
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

    # 前端静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # HTTPS 证书配置占位
    # listen 443 ssl http2;
    # ssl_certificate     /path/to/fullchain.pem;
    # ssl_certificate_key /path/to/privkey.pem;
}
```

### 7.2 为什么这样配置

- `/` 使用 Focus `dist`
- `/deepaudit-app/` 使用独立 `alias`，避免和 Focus 主站资源混淆
- `/basic-api/` 代理到 Django `127.0.0.1:8001`，并自动把 `/basic-api/` 前缀去掉，落到后端真实 `/api/`
- `/ws/` 保留原始路径，直接转发给 ASGI
- DeepAudit 的 `/stream` 接口单独关闭缓冲，避免 SSE 事件被 nginx 攒包导致前端长时间无输出

### 7.3 检查并重载 nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 8. 运维、验证与排障

### 8.1 建议启动顺序

1. 数据库
2. Redis
3. `focus-backend`
4. `focus-celery-default`
5. `focus-celery-deepaudit`
6. nginx

### 8.2 常用运维命令

```bash
sudo systemctl restart focus-backend
sudo systemctl restart focus-celery-default
sudo systemctl restart focus-celery-deepaudit

sudo systemctl status focus-backend
sudo systemctl status focus-celery-default
sudo systemctl status focus-celery-deepaudit

journalctl -u focus-backend -f
journalctl -u focus-celery-default -f
journalctl -u focus-celery-deepaudit -f
```

### 8.3 业务日志路径

应用内部日志默认会写入：

- `backend-django/logs/server.log`
- `backend-django/logs/error.log`

nginx 默认日志：

- `/var/log/nginx/access.log`
- `/var/log/nginx/error.log`

### 8.4 Redis / Celery 验证

```bash
redis-cli -h 127.0.0.1 -p 6379 ping
```

预期：

```text
PONG
```

验证 Celery：

```bash
cd /srv/focus/Focus_Admin/backend-django
source /srv/focus/venv/bin/activate
python -m celery -A application inspect ping
```

### 8.5 WebSocket / SSE 验证

#### WebSocket

真实路径：

```text
/ws/deepaudit/tasks/{task_id}/
```

如果需要手工测试，可使用浏览器开发者工具或 `wscat` / `websocat`。

#### SSE

真实访问路径：

```text
/basic-api/api/deepaudit/agent-tasks/{task_id}/stream
```

可用 `curl` 简单验证是否持续输出：

```bash
curl -N \
  -H "Authorization: Bearer <access-token>" \
  "http://your.domain.com/basic-api/api/deepaudit/agent-tasks/<task-id>/stream?include_thinking=true&include_tool_calls=true&after_sequence=0"
```

### 8.6 构建与接入验收清单

#### 构建验证

- `pnpm build:ele` 成功
- `pnpm build:deepaudit` 成功
- `web/apps/web-ele/dist` 已发布到 `/srv/www/focus-web`
- `web/apps/web-deepaudit/dist` 已发布到 `/srv/www/deepaudit-app`

#### 后端验证

- `python manage.py migrate` 成功
- `python manage.py init_deepaudit` 成功
- `systemctl status focus-backend focus-celery-default focus-celery-deepaudit` 全部正常

#### 接入验证

- 访问 `/` 能正常进入 Focus
- Focus 菜单点击 `DeepAudit 平台` 会新标签页打开 `/deepaudit-app/`
- 直接刷新 `/deepaudit-app/` 任意子路由不返回 404

#### 实时链路验证

- `/ws/deepaudit/tasks/{task_id}/` 能建立连接
- `/basic-api/api/deepaudit/agent-tasks/{task_id}/stream` 能持续收到事件
- DeepAudit Worker 能实际消费 `deepaudit` 队列任务

#### 初始化验证

- 全新库：`migrate` + `loaddata db_init.json` + `init_deepaudit` 后能看到 DeepAudit 菜单
- 现有 Focus 主库：只执行 `migrate` + `init_deepaudit`，不重复执行 `loaddata db_init.json`

### 8.7 常见问题

#### 1. Focus 菜单里没有 DeepAudit 入口

优先检查：

- 是否执行了 `python manage.py init_deepaudit`
- 当前账号角色是否有对应菜单权限
- 是否刷新了菜单缓存、权限缓存

#### 2. DeepAudit 页面能打开，但任务一启动就失败

优先检查：

- Redis 是否在线
- `focus-celery-deepaudit` 是否已启动
- `DEEPAUDIT_QUEUE` 是否与 worker 消费队列一致

#### 3. DeepAudit 的流式输出长时间没有内容

优先检查：

- nginx 是否对 `/stream` 关闭了 `proxy_buffering`
- SSE location 是否命中了更具体的 `/stream` 配置
- `focus-backend` 是否正常承载长连接

#### 4. WebSocket 连接失败

优先检查：

- nginx 是否配置了 `Upgrade` / `Connection`
- `/ws/` 是否正确代理到 ASGI 服务
- JWT 是否有效

## 附录：本项目与生产部署直接相关的现状

以下是当前仓库中已经存在、可直接用于部署判断的事实：

- Django ASGI 入口：`application.asgi:application`
- 后端 API 实际前缀：`/api/`
- WebSocket 路由：`/ws/deepaudit/tasks/{task_id}/`
- DeepAudit 前端 Vite `base`：`/deepaudit-app/`
- DeepAudit 生产 API 地址：`/basic-api/api`
- DeepAudit 初始化命令：`python manage.py init_deepaudit`

上线前请特别核对以下风险项：

- `DEBUG = True`
- `ALLOWED_HOSTS = ['*']`
- `env/prd_env.py` 的数据库类型是否与你的生产库一致
- `web-ele` 的生产 API 地址是否已改成同域 `/basic-api/`
