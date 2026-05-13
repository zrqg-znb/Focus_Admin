# 8.146.236.192 原生部署方案（HTTP / 无域名）

这份文档只针对当前这台云服务器：

- 服务器 IP：`8.146.236.192`
- 访问方式：`HTTP + IP + 路径`
- 部署方式：`nginx + nohup uvicorn + nohup celery + nohup python start_scheduler.py`
- 不使用 Docker
- 数据库继续沿用当前 `backend-django/.env` 的配置，不切库

DeepAudit 的主入口以当前代码为准，统一使用：

- `http://8.146.236.192/focusaudit-app/`

`/deepaudit-app/` 只做兼容跳转，不作为新的主入口。

## 1. 目录约定

下面以仓库默认路径为例，如果你服务器上的代码目录不同，把路径整体替换掉即可。

- 代码目录：`/srv/focus/Focus_Admin`
- Python 运行环境：`/srv/focus/venv`
- Focus 前端静态目录：`/var/www/focus`
- DeepAudit 前端静态目录：`/var/www/deepaudit`
- 后端静态目录：`/srv/focus/Focus_Admin/backend-django/static_root`
- 后端媒体目录：`/srv/focus/Focus_Admin/backend-django/media`
- 后端日志目录：`/srv/focus/Focus_Admin/backend-django/logs`
- 后端运行目录：`/srv/focus/Focus_Admin/backend-django/run`

## 2. 前端：只在本地构建，再复制到服务器

服务器配置较低，不建议在服务器上跑前端打包。  
推荐在你本地机器先构建，再把 dist 同步到服务器。

### 2.1 Focus 前端构建

在 `web/apps/web-ele` 里创建本地生产覆盖文件，不要提交到仓库：

```bash
cat > web/apps/web-ele/.env.production.local <<'EOF'
VITE_BASE=/
VITE_GLOB_API_URL=/basic-api/
EOF
```

构建：

```bash
cd /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web
pnpm install --frozen-lockfile
pnpm build:ele
```

### 2.2 DeepAudit 前端构建

DeepAudit 保持当前前缀：

```bash
cat > web/apps/web-deepaudit/.env.production.local <<'EOF'
VITE_APP_ID=deepaudit
VITE_API_BASE_URL=/basic-api/api
EOF
```

构建：

```bash
cd /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web
pnpm build:deepaudit
```

### 2.3 同步到服务器

```bash
rsync -av --delete /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web/apps/web-ele/dist/ \
  root@8.146.236.192:/var/www/focus/

rsync -av --delete /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web/apps/web-deepaudit/dist/ \
  root@8.146.236.192:/var/www/deepaudit/
```

> 如果你不想手工跑这些命令，也可以把本仓库里的 `backend-django/scripts/start-ip-http.sh` 当成后端启动辅助脚本使用；前端仍建议本地构建后再同步。

## 3. 后端：nohup uvicorn + nohup celery + nohup python start_scheduler.py

### 3.1 后端启动原则

- 继续使用当前 `backend-django/.env` 里的数据库配置
- 不修改数据库地址，不切数据库
- 使用 `ZQ_ENV=dev` 方式启动，避免 `DEBUG=false` 时触发 HTTPS 强跳
- 所有后端进程都显式带 `ENABLE_SCHEDULER=false`
- scheduler 独立启动，按你的要求使用 `nohup python start_scheduler.py`

### 3.2 推荐：用脚本启动

仓库里新增了一个辅助脚本：

```bash
cd /srv/focus/Focus_Admin/backend-django
PYTHON_BIN=/srv/focus/venv/bin/python ./scripts/start-ip-http.sh prepare
PYTHON_BIN=/srv/focus/venv/bin/python ./scripts/start-ip-http.sh start-all
```

它会依次启动：

- ASGI 后端
- 默认 Celery worker
- DeepAudit Celery worker
- scheduler

### 3.3 等价的手工 nohup 命令

如果你想手工执行，等价命令如下：

```bash
cd /srv/focus/Focus_Admin/backend-django

# 1) 后端静态资源和 DeepAudit 初始数据
env ZQ_ENV=dev ENABLE_SCHEDULER=false \
  /srv/focus/venv/bin/python manage.py collectstatic --noinput

env ZQ_ENV=dev ENABLE_SCHEDULER=false \
  /srv/focus/venv/bin/python manage.py init_deepaudit

# 2) ASGI 后端
nohup env ZQ_ENV=dev ENABLE_SCHEDULER=false \
  /srv/focus/venv/bin/python -m uvicorn application.asgi:application \
  --host 127.0.0.1 --port 8001 --workers 1 \
  > /srv/focus/Focus_Admin/backend-django/logs/uvicorn-ip-http.log 2>&1 &

# 3) 默认 worker
nohup env ZQ_ENV=dev ENABLE_SCHEDULER=false \
  /srv/focus/venv/bin/python -m celery -A application worker \
  -Q celery -n focus-default@$(hostname -s) -l info \
  --concurrency=2 --max-tasks-per-child=5 \
  > /srv/focus/Focus_Admin/backend-django/logs/celery-default-ip-http.log 2>&1 &

# 4) DeepAudit worker
nohup env ZQ_ENV=dev ENABLE_SCHEDULER=false \
  /srv/focus/venv/bin/python -m celery -A application worker \
  -Q deepaudit -n focus-deepaudit@$(hostname -s) -l info \
  --concurrency=2 --prefetch-multiplier=1 --max-tasks-per-child=5 \
  > /srv/focus/Focus_Admin/backend-django/logs/celery-deepaudit-ip-http.log 2>&1 &

# 5) scheduler
nohup env ZQ_ENV=dev ENABLE_SCHEDULER=false \
  /srv/focus/venv/bin/python start_scheduler.py \
  > /srv/focus/Focus_Admin/backend-django/logs/scheduler-ip-http.log 2>&1 &
```

## 4. nginx：IP 访问 + 路径分流

下面是一个适合这台服务器的单 server block 示例：

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
    listen 80 default_server;
    server_name 8.146.236.192 _;

    client_max_body_size 500M;
    root /var/www/focus;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # DeepAudit canonical path
    location = /focusaudit-app {
        return 301 /focusaudit-app/;
    }

    location /focusaudit-app/ {
        alias /var/www/deepaudit/;
        index index.html;
        try_files $uri $uri/ /focusaudit-app/index.html;
    }

    # Legacy compatibility path
    location = /deepaudit-app {
        return 301 /focusaudit-app/;
    }

    location /deepaudit-app/ {
        return 301 /focusaudit-app/;
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

    # DeepAudit SSE 必须单独关闭 buffering
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

    # 普通 API
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

## 5. 验收命令

### 5.1 路由验收

```bash
curl -I http://8.146.236.192/
curl -I http://8.146.236.192/focusaudit-app/
curl -I http://8.146.236.192/deepaudit-app/
curl -I http://8.146.236.192/basic-api/
```

### 5.2 后端验收

```bash
curl -I http://127.0.0.1:8001/api/core/permCode
curl -I http://127.0.0.1:8001/api/deepaudit/projects
```

### 5.3 进程验收

```bash
ps -ef | grep uvicorn | grep application.asgi
ps -ef | grep celery
ps -ef | grep start_scheduler.py
```

### 5.4 DeepAudit 实际体验验收

- Focus 首页能正常打开
- DeepAudit 首页能正常打开
- 项目列表、场景管理、提示词、规则页都能正常请求
- 发起一次 Agent 审计任务，SSE 日志持续刷新，结束后最后几条日志不需要手动刷新也能看到

## 6. 备注

- 如果 `80` 端口已被占用，可以把 nginx 改成 `8080`，然后访问 `http://8.146.236.192:8080/`
- 这套方案不依赖域名解析
- 如果后续你要切回 `prd` 模式，再单独处理 HTTPS 和 `SECURE_SSL_REDIRECT`
