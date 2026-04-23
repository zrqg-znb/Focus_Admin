# Focus + DeepAudit 原生部署落地文档（单环境 / HTTP）

本文用于 `zrqznb.work` 在单台服务器（`8.146.236.192`）的原生部署（非 Docker），同时运行 Focus 主站与 DeepAudit 子应用。

## 1. 部署目标

- 域名访问（不启用 HTTPS）：
  - `http://zrqznb.work/` -> Focus
  - `http://zrqznb.work/deepaudit-app/` -> DeepAudit
  - `http://zrqznb.work/basic-api/` -> Django API
- 单环境部署，一套代码目录、一套虚拟环境、一套 nginx 配置
- 进程由 `systemd` 托管（backend/celery-default/celery-deepaudit/scheduler）

## 2. 服务器固定目录

- 代码：`/srv/focus/Focus_Admin`
- Python venv：`/srv/focus/venv`
- Focus 前端静态：`/var/www/focus`
- DeepAudit 前端静态：`/var/www/deepaudit`
- 后端静态：`/srv/focus/Focus_Admin/backend-django/static_root`
- 媒体目录：`/srv/focus/Focus_Admin/backend-django/media`

## 3. 已确认前置条件

- 已安装：`python3.12`、`nodejs 20`、`pnpm 10.14.0`、`nginx`、`redis-server`
- 代码已拉取到：`/srv/focus/Focus_Admin`
- `.env` 已存在：`/srv/focus/Focus_Admin/backend-django/.env`
- `web-ele/.env.production.local` 已设置：
  - `VITE_BASE=/`
  - `VITE_GLOB_API_URL=/basic-api/`

## 4. 注意事项（数据库迁移）

当前仓库执行 `python manage.py migrate` 会报错：

- `NodeNotFoundError: ('core', '0006_alter_user_manager')`

这是因为当前代码树中缺失 `core` app 的迁移文件，不影响“接入已有库”的上线场景。  
本次采用“使用现有数据库 + 不执行 migrate”的方式落地；只执行：

- `collectstatic`
- `init_deepaudit`

## 5. 控制台一键收尾命令（可直接执行）

> 在服务器控制台（ECS 管理终端）执行。

```bash
set -e

# 0) 基础目录
mkdir -p /srv/focus/Focus_Admin/backend-django/{logs,run,static_root,media/file_manager,media/chunk_uploads}
mkdir -p /var/www/focus /var/www/deepaudit

# 1) 后端初始化（不跑 migrate）
cd /srv/focus/Focus_Admin/backend-django
/srv/focus/venv/bin/python manage.py collectstatic --noinput
/srv/focus/venv/bin/python manage.py init_deepaudit

# 2) 前端构建发布
cd /srv/focus/Focus_Admin/web
pnpm install --frozen-lockfile
pnpm build:ele
pnpm build:deepaudit
rsync -av --delete /srv/focus/Focus_Admin/web/apps/web-ele/dist/ /var/www/focus/
rsync -av --delete /srv/focus/Focus_Admin/web/apps/web-deepaudit/dist/ /var/www/deepaudit/

# 3) nginx 配置（HTTP）
cat >/etc/nginx/conf.d/focus.conf <<'EOF'
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
    server_name zrqznb.work 8.146.236.192;

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
        alias /srv/focus/Focus_Admin/backend-django/static_root/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public";
    }

    location /media/ {
        alias /srv/focus/Focus_Admin/backend-django/media/;
    }

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
EOF

nginx -t
systemctl reload nginx

# 4) systemd 服务
cat >/etc/systemd/system/focus-backend.service <<'EOF'
[Unit]
Description=Focus Django ASGI Backend
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/srv/focus/Focus_Admin/backend-django
EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus/venv/bin/gunicorn application.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8001 --workers 4 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/focus-celery-default.service <<'EOF'
[Unit]
Description=Focus Celery Worker (default)
After=network.target redis-server.service focus-backend.service
Requires=redis-server.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/srv/focus/Focus_Admin/backend-django
EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus/venv/bin/python -m celery -A application worker -Q celery -n focus-default@%%h -l info --concurrency=2 --max-tasks-per-child=5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/focus-celery-deepaudit.service <<'EOF'
[Unit]
Description=Focus Celery Worker (deepaudit)
After=network.target redis-server.service focus-backend.service
Requires=redis-server.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/srv/focus/Focus_Admin/backend-django
EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus/venv/bin/python -m celery -A application worker -Q deepaudit -n focus-deepaudit@%%h -l info --concurrency=2 --prefetch-multiplier=1 --max-tasks-per-child=5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/focus-scheduler.service <<'EOF'
[Unit]
Description=Focus Scheduler
After=network.target redis-server.service focus-backend.service
Requires=redis-server.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/srv/focus/Focus_Admin/backend-django
EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus/venv/bin/python start_scheduler.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler
```

## 6. 验收命令（必须全部通过）

```bash
# 服务状态
systemctl is-active focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler

# 端口监听
lsof -iTCP:8001 -sTCP:LISTEN -P -n

# 域名访问（HTTP）
curl -I http://zrqznb.work/
curl -I http://zrqznb.work/deepaudit-app/
curl -I http://zrqznb.work/basic-api/

# 本机回环访问（确认 nginx + upstream）
curl -I http://127.0.0.1/
curl -I http://127.0.0.1/deepaudit-app/
curl -I http://127.0.0.1/basic-api/
```

预期：

- `systemctl is-active` 均为 `active`
- `lsof` 显示 `127.0.0.1:8001` 监听
- 上述 `curl -I` 返回 `200` 或 API 返回 `401/404`（说明后端路由已接通）

## 7. 运行状态检查方法

- 服务状态：
  - `systemctl status focus-backend`
  - `systemctl status focus-celery-default`
  - `systemctl status focus-celery-deepaudit`
  - `systemctl status focus-scheduler`
- 实时日志：
  - `journalctl -u focus-backend -f`
  - `journalctl -u focus-celery-default -f`
  - `journalctl -u focus-celery-deepaudit -f`
  - `journalctl -u focus-scheduler -f`
- nginx：
  - `nginx -t`
  - `tail -f /var/log/nginx/error.log`

## 8. 稳定性与安全建议

- 建议尽快改为非 root 运行服务（新建 `focus` 用户）
- 轮换敏感信息：
  - 服务器 root 密码
  - 数据库密码
  - LLM API Key
- 若后续要 `DEBUG=false` 且继续 HTTP，需要在代码中将 `SECURE_SSL_REDIRECT` 改为可配置，否则会强制跳转 HTTPS
- 建议把 SSH `MaxStartups` 调整为更稳健值，避免频繁连接时出现 banner timeout

