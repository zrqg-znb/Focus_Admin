# Focus + DeepAudit 同机双环境部署手册

本文档面向“同一台 Linux 服务器同时运行测试环境与正式环境”的场景，统一整理 Focus 主平台与 DeepAudit 子应用的部署、发布与运维流程。

本文固定采用以下约束，不建议实施时再临时改名或改路径：

| 项目 | 正式环境 | 测试环境 |
|---|---|---|
| 域名 | `focus.example.com` | `focus-test.example.com` |
| Django ASGI | `127.0.0.1:8001` | `127.0.0.1:8002` |
| Focus 前端 dist | `/var/www/focus` | `/var/www/focus_test` |
| DeepAudit 前端 dist | `/var/www/deepaudit` | `/var/www/deepaudit_test` |
| 代码目录 | `/srv/focus-prod/Focus_Admin` | `/srv/focus-test/Focus_Admin` |
| Python venv | `/srv/focus-prod/venv` | `/srv/focus-test/venv` |
| 日志目录 | `/srv/focus-prod/Focus_Admin/backend-django/logs` | `/srv/focus-test/Focus_Admin/backend-django/logs` |
| PID 目录 | `/srv/focus-prod/Focus_Admin/backend-django/run` | `/srv/focus-test/Focus_Admin/backend-django/run` |
| Redis cache DB | `2` | `5` |
| Redis celery DB | `3` | `6` |
| Redis channels DB | `4` | `7` |

本文同时提供两套进程管理方案：

- `nohup`：适合你当前现状，先落地可用。
- `systemd`：适合长期运维，推荐后续迁移。

如果你还需要处理内网 LLM 网关、用户级 API Key、`tiktoken` 离线缓存，请同时参考：

- `docs/deepaudit-private-llm-checklist.md`

## 1. 部署总览

### 1.1 双环境拓扑

```text
Browser
  ├─ https://focus.example.com/                  -> /var/www/focus
  ├─ https://focus.example.com/deepaudit-app/    -> /var/www/deepaudit
  ├─ https://focus-test.example.com/             -> /var/www/focus_test
  ├─ https://focus-test.example.com/deepaudit-app/ -> /var/www/deepaudit_test
  ├─ /basic-api/                                 -> nginx -> Django ASGI
  └─ /ws/                                        -> nginx -> Django ASGI

正式环境
  ├─ 代码目录: /srv/focus-prod/Focus_Admin
  ├─ Python venv: /srv/focus-prod/venv
  ├─ Django ASGI: 127.0.0.1:8001
  ├─ Celery default worker
  ├─ Celery DeepAudit worker
  └─ scheduler 独立进程

测试环境
  ├─ 代码目录: /srv/focus-test/Focus_Admin
  ├─ Python venv: /srv/focus-test/venv
  ├─ Django ASGI: 127.0.0.1:8002
  ├─ Celery default worker
  ├─ Celery DeepAudit worker
  └─ scheduler 独立进程
```

### 1.2 运行入口与路径规则

本次部署不改接口协议，两个环境统一使用同一套访问路径规则，只允许以下差异：

- 差异项：`server_name`、后端端口、前端静态目录、后端 `static_root` / `media` / 日志路径。
- 保持一致：`/`、`/deepaudit-app/`、`/basic-api/`、`/ws/`、DeepAudit `/stream`。
- DeepAudit 入口务必使用带尾部斜杠的 `/deepaudit-app/`；建议把 `/deepaudit-app` 301 到 `/deepaudit-app/`，否则请求会落到主站 SPA 并显示 404。
- 正式 API 入口：`https://focus.example.com/basic-api/`
- 测试 API 入口：`https://focus-test.example.com/basic-api/`
- 正式 DeepAudit：`https://focus.example.com/deepaudit-app/`
- 测试 DeepAudit：`https://focus-test.example.com/deepaudit-app/`

### 1.3 推荐目录布局

```bash
/srv/focus-prod/Focus_Admin
/srv/focus-prod/venv
/srv/focus-prod/tiktoken-cache
/srv/focus-prod/Focus_Admin/backend-django/logs
/srv/focus-prod/Focus_Admin/backend-django/run
/srv/focus-prod/Focus_Admin/backend-django/static_root
/srv/focus-prod/Focus_Admin/backend-django/media

/srv/focus-test/Focus_Admin
/srv/focus-test/venv
/srv/focus-test/tiktoken-cache
/srv/focus-test/Focus_Admin/backend-django/logs
/srv/focus-test/Focus_Admin/backend-django/run
/srv/focus-test/Focus_Admin/backend-django/static_root
/srv/focus-test/Focus_Admin/backend-django/media

/var/www/focus
/var/www/focus_test
/var/www/deepaudit
/var/www/deepaudit_test
```

约束说明：

- 推荐两套独立代码目录，不采用“一套代码双配置”。
- `logs`、`run`、`static_root`、`media`、`tiktoken-cache` 均应按环境隔离。
- DeepAudit 默认运行目录在 `backend-django/media/deepaudit` 下；由于正式和测试本来就是两套代码目录，因此天然隔离。
- nginx 只读取 `/var/www/*` 和各自环境的 `static_root` / `media`，不要把测试与正式放到同一个静态 root 下。

### 1.4 为什么 Redis 必须分 DB

当前项目里 scheduler 心跳 key 固定，Celery、缓存、Channels 也会共用 Redis 实例；如果测试和正式共用同一个 Redis DB，很容易出现以下问题：

- scheduler 心跳互相覆盖
- Celery 队列串环境
- Channels / SSE / WebSocket 状态互相污染
- DeepAudit 运行缓存互相干扰

因此本文固定采用：

- 正式：`REDIS_DB=2`、`REDIS_CELERY_DB=3`、`REDIS_CHANNEL_DB=4`
- 测试：`REDIS_DB=5`、`REDIS_CELERY_DB=6`、`REDIS_CHANNEL_DB=7`

## 2. 服务器准备与代码目录初始化

### 2.1 基础软件

建议目标机器至少具备：

- Linux x86_64
- Python 3.12
- Node.js 20+
- pnpm 10+
- nginx
- Redis
- PostgreSQL 或 MySQL

示例：

```bash
sudo mkdir -p /srv/focus-prod /srv/focus-test
sudo mkdir -p /var/www/focus /var/www/focus_test /var/www/deepaudit /var/www/deepaudit_test
sudo chown -R $USER:$USER /srv/focus-prod /srv/focus-test /var/www/focus /var/www/focus_test /var/www/deepaudit /var/www/deepaudit_test
```

如果后续由 `focus` 用户运行 `systemd` 服务，建议额外准备运行账号：

```bash
sudo useradd --system --create-home --shell /bin/bash focus
sudo chown -R focus:focus /srv/focus-prod /srv/focus-test
```

如果你计划使用别的系统用户，把后续文档中的 `focus:focus` 统一替换成你的运行用户即可。

### 2.2 初始化两套代码目录

```bash
cd /srv/focus-prod
git clone <your-repo-url> Focus_Admin
python3.12 -m venv /srv/focus-prod/venv

cd /srv/focus-test
git clone <your-repo-url> Focus_Admin
python3.12 -m venv /srv/focus-test/venv
```

推荐分支策略：

- 正式目录 checkout 稳定分支或 release tag。
- 测试目录 checkout `develop` / `uat` 分支。
- 两套目录独立拉代码、独立回滚、独立发布。

### 2.3 安装 Python 与前端依赖

正式环境：

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cd /srv/focus-prod/Focus_Admin/web
corepack enable
corepack prepare pnpm@10.14.0 --activate
pnpm install --frozen-lockfile
```

测试环境：

```bash
cd /srv/focus-test/Focus_Admin/backend-django
source /srv/focus-test/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cd /srv/focus-test/Focus_Admin/web
corepack enable
corepack prepare pnpm@10.14.0 --activate
pnpm install --frozen-lockfile
```

### 2.4 日志、PID、静态目录预创建

```bash
mkdir -p /srv/focus-prod/tiktoken-cache
mkdir -p /srv/focus-prod/Focus_Admin/backend-django/logs
mkdir -p /srv/focus-prod/Focus_Admin/backend-django/run
mkdir -p /srv/focus-prod/Focus_Admin/backend-django/static_root
mkdir -p /srv/focus-prod/Focus_Admin/backend-django/media/file_manager
mkdir -p /srv/focus-prod/Focus_Admin/backend-django/media/chunk_uploads

mkdir -p /srv/focus-test/tiktoken-cache
mkdir -p /srv/focus-test/Focus_Admin/backend-django/logs
mkdir -p /srv/focus-test/Focus_Admin/backend-django/run
mkdir -p /srv/focus-test/Focus_Admin/backend-django/static_root
mkdir -p /srv/focus-test/Focus_Admin/backend-django/media/file_manager
mkdir -p /srv/focus-test/Focus_Admin/backend-django/media/chunk_uploads
```

如使用 `focus` 运行账号：

```bash
sudo chown -R focus:focus /srv/focus-prod /srv/focus-test
```

## 3. 两套 `.env` 与后端公共准备

项目会自动读取各自 `backend-django/.env`。由于正式和测试是两套独立代码目录，所以每个目录各自维护自己的 `.env`。

### 3.1 正式环境 `.env` 示例

文件：`/srv/focus-prod/Focus_Admin/backend-django/.env`

```env
ZQ_ENV=prd

# Django / JWT
DJANGO_SECRET_KEY=replace-with-prod-secret
JWT_ACCESS_SECRET_KEY=replace-with-prod-access-secret
JWT_REFRESH_SECRET_KEY=replace-with-prod-refresh-secret

# 调度器护栏：Web / Celery 进程一律关闭自动启动
ENABLE_SCHEDULER=false

# 正式数据库账号
PRD_DB_USER=focus_prod
PRD_DB_PASSWORD=replace-with-prod-db-password

# Redis 隔离
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=2
REDIS_CELERY_DB=3
REDIS_CHANNEL_DB=4
DEEPAUDIT_QUEUE=deepaudit
SKILL_OPTIMIZER_QUEUE=skill_optimizer

# DeepAudit 默认 LLM / Embedding
LLM_PROVIDER=openai
LLM_BASE_URL=http://your-internal-llm-gateway/v1
LLM_API_KEY=replace-with-prod-llm-key
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=http://your-internal-embedding-gateway/v1
EMBEDDING_API_KEY=replace-with-prod-embedding-key

# 首 Token / 流式超时
LLM_FIRST_TOKEN_TIMEOUT=120
LLM_STREAM_TIMEOUT=180
TOOL_TIMEOUT_SECONDS=120
SUB_AGENT_TIMEOUT_SECONDS=900
AGENT_TIMEOUT_SECONDS=2400

# tiktoken 离线缓存
DEEPAUDIT_TIKTOKEN_MODE=local
TIKTOKEN_CACHE_DIR=/srv/focus-prod/tiktoken-cache
DATA_GYM_CACHE_DIR=/srv/focus-prod/tiktoken-cache
```

### 3.2 测试环境 `.env` 示例

文件：`/srv/focus-test/Focus_Admin/backend-django/.env`

```env
ZQ_ENV=uat

# Django / JWT
DJANGO_SECRET_KEY=replace-with-test-secret
JWT_ACCESS_SECRET_KEY=replace-with-test-access-secret
JWT_REFRESH_SECRET_KEY=replace-with-test-refresh-secret

# 调度器护栏：Web / Celery 进程一律关闭自动启动
ENABLE_SCHEDULER=false

# 测试数据库账号
UAT_DB_USER=focus_test
UAT_DB_PASSWORD=replace-with-test-db-password

# Redis 隔离
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=5
REDIS_CELERY_DB=6
REDIS_CHANNEL_DB=7
DEEPAUDIT_QUEUE=deepaudit
SKILL_OPTIMIZER_QUEUE=skill_optimizer

# DeepAudit 默认 LLM / Embedding
LLM_PROVIDER=openai
LLM_BASE_URL=http://your-internal-llm-gateway/v1
LLM_API_KEY=replace-with-test-llm-key
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=http://your-internal-embedding-gateway/v1
EMBEDDING_API_KEY=replace-with-test-embedding-key

# 首 Token / 流式超时
LLM_FIRST_TOKEN_TIMEOUT=120
LLM_STREAM_TIMEOUT=180
TOOL_TIMEOUT_SECONDS=120
SUB_AGENT_TIMEOUT_SECONDS=900
AGENT_TIMEOUT_SECONDS=2400

# tiktoken 离线缓存
DEEPAUDIT_TIKTOKEN_MODE=local
TIKTOKEN_CACHE_DIR=/srv/focus-test/tiktoken-cache
DATA_GYM_CACHE_DIR=/srv/focus-test/tiktoken-cache
```

### 3.3 两套环境都要执行的后端初始化

正式环境：

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py init_deepaudit
```

测试环境：

```bash
cd /srv/focus-test/Focus_Admin/backend-django
source /srv/focus-test/venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py init_deepaudit
```

如果是全新空库，并且需要初始化 Focus 平台菜单、角色、权限，才执行：

```bash
python manage.py loaddata db_init.json
```

注意：

- 正式库和测试库分别执行，不要混用。
- 已经有正式业务数据的库，不要重复执行 `loaddata db_init.json`。
- 两个环境都要各自完成 `init_deepaudit`，这样 DeepAudit 菜单与配置才会落库。

### 3.4 两套代码目录的更新流程

正式环境更新：

```bash
cd /srv/focus-prod/Focus_Admin
git fetch --all
git checkout <prod-branch-or-tag>
git pull --ff-only

cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

测试环境更新：

```bash
cd /srv/focus-test/Focus_Admin
git fetch --all
git checkout <test-branch>
git pull --ff-only

cd /srv/focus-test/Focus_Admin/backend-django
source /srv/focus-test/venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

### 3.5 上线前必须额外确认的现状

当前仓库里仍有几项配置不是标准生产形态，部署前需要你自行确认或修正：

- `backend-django/application/settings.py` 当前仍是 `DEBUG = True`。
- `backend-django/application/settings.py` 当前仍是 `ALLOWED_HOSTS = ['*']`。
- `web/apps/web-ele/.env.production` 当前仍指向旧的外部域名，不能直接拿去上线。
- `backend-django/env/prd_env.py` 与 `backend-django/env/uat_env.py` 里，数据库 `HOST` / `PORT` / `NAME` 以及部分 OAuth 回调地址仍是代码内固定值，不是全部走 `.env`；正式上线前要按你的真实环境核对。
- scheduler 存在 `AppConfig.ready()` 自动启动逻辑，因此本文档统一要求 Web 与 Celery 进程都显式携带 `ENABLE_SCHEDULER=false`，scheduler 只通过 `python start_scheduler.py` 独立运行。

## 4. 前端双环境静态发布流程

### 4.1 固定的前端 API 路径

两套环境都统一用相对路径，避免同一份 dist 写死环境域名：

- `web-ele` 生产 API 地址：`/basic-api/`
- `web-deepaudit` 生产 API 地址：`/basic-api/api`
- DeepAudit Vite `base` 固定：`/deepaudit-app/`

### 4.2 检查 `web-ele/.env.production`

当前仓库中：`web/apps/web-ele/.env.production`

```env
VITE_GLOB_API_URL=https://django-ninja.zq-platform.cn/basic-api/
```

发布前必须改成相对路径，推荐在各自代码目录下新增 `web/apps/web-ele/.env.production.local`：

```env
VITE_BASE=/
VITE_GLOB_API_URL=/basic-api/
```

这样做的好处：

- 不必直接改仓库里的 `.env.production`
- 正式和测试可以共用同一套路径规则
- 两个域名下都能使用同一类构建产物

### 4.3 检查 `web-deepaudit` 生产配置

`web/apps/web-deepaudit/.env.production` 当前为：

```env
VITE_API_BASE_URL=/basic-api/api
```

`web/apps/web-deepaudit/vite.config.ts` 当前为：

```text
base: /deepaudit-app/
```

这两项保持现状即可，不要改成根路径。

### 4.4 标准构建流程

主推荐流程是测试、正式分别在自己的代码目录中构建。这样最安全，不会把测试代码误发到正式目录。

正式环境：

```bash
cd /srv/focus-prod/Focus_Admin/web
pnpm install --frozen-lockfile
pnpm build:ele
pnpm build:deepaudit
```

测试环境：

```bash
cd /srv/focus-test/Focus_Admin/web
pnpm install --frozen-lockfile
pnpm build:ele
pnpm build:deepaudit
```

如果正式和测试恰好完全是同一个 commit，也可以共用一次构建产物；但发布时仍必须分别同步到四个静态目录，不能混放。

### 4.5 发布到四个静态目录

正式环境：

```bash
rsync -av --delete /srv/focus-prod/Focus_Admin/web/apps/web-ele/dist/ /var/www/focus/
rsync -av --delete /srv/focus-prod/Focus_Admin/web/apps/web-deepaudit/dist/ /var/www/deepaudit/
```

测试环境：

```bash
rsync -av --delete /srv/focus-test/Focus_Admin/web/apps/web-ele/dist/ /var/www/focus_test/
rsync -av --delete /srv/focus-test/Focus_Admin/web/apps/web-deepaudit/dist/ /var/www/deepaudit_test/
```

说明：

- 这四个目录必须事先存在且 nginx 可读。
- 发布后目标文件应直接落在 `/var/www/deepaudit/index.html` 与 `/var/www/deepaudit_test/index.html`，不要变成多一层的 `dist/index.html`。
- DeepAudit 继续通过 `/deepaudit-app/` 访问，不修改 `base`。
- 测试和正式的路径规则保持完全一致，只是各自指向不同域名和不同静态目录。

## 5. `nohup` 方案

`nohup` 方案适合你当前现状。每个环境各 4 个进程，共 8 个：

- backend
- celery-default
- celery-deepaudit
- scheduler

### 5.1 正式环境 4 个进程

#### 正式 backend

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
nohup env ENABLE_SCHEDULER=false \
  /srv/focus-prod/venv/bin/gunicorn application.asgi:application \
  -k uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8001 \
  --workers 4 \
  --timeout 120 \
  > logs/backend-prod.log 2>&1 &
echo $! > run/backend-prod.pid
```

#### 正式 celery-default

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
nohup env ENABLE_SCHEDULER=false \
  /srv/focus-prod/venv/bin/python -m celery -A application worker \
  -Q celery \
  -n focus-prod-default@%h \
  -l info \
  --concurrency=2 \
  --max-tasks-per-child=5 \
  > logs/celery-default-prod.log 2>&1 &
echo $! > run/celery-default-prod.pid
```

#### 正式 celery-deepaudit（同时消费 AI 辅助工具队列）

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
nohup env ENABLE_SCHEDULER=false \
  /srv/focus-prod/venv/bin/python -m celery -A application worker \
  -Q deepaudit,skill_optimizer \
  -n focus-prod-deepaudit@%h \
  -l info \
  --concurrency=2 \
  --prefetch-multiplier=1 \
  --max-tasks-per-child=5 \
  > logs/celery-deepaudit-prod.log 2>&1 &
echo $! > run/celery-deepaudit-prod.pid
```

#### 正式 scheduler

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
nohup env ENABLE_SCHEDULER=false \
  /srv/focus-prod/venv/bin/python start_scheduler.py \
  > logs/scheduler-prod.log 2>&1 &
echo $! > run/scheduler-prod.pid
```

### 5.2 测试环境 4 个进程

#### 测试 backend

```bash
cd /srv/focus-test/Focus_Admin/backend-django
source /srv/focus-test/venv/bin/activate
nohup env ENABLE_SCHEDULER=false \
  /srv/focus-test/venv/bin/gunicorn application.asgi:application \
  -k uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8002 \
  --workers 4 \
  --timeout 120 \
  > logs/backend-test.log 2>&1 &
echo $! > run/backend-test.pid
```

#### 测试 celery-default

```bash
cd /srv/focus-test/Focus_Admin/backend-django
source /srv/focus-test/venv/bin/activate
nohup env ENABLE_SCHEDULER=false \
  /srv/focus-test/venv/bin/python -m celery -A application worker \
  -Q celery \
  -n focus-test-default@%h \
  -l info \
  --concurrency=2 \
  --max-tasks-per-child=5 \
  > logs/celery-default-test.log 2>&1 &
echo $! > run/celery-default-test.pid
```

#### 测试 celery-deepaudit

```bash
cd /srv/focus-test/Focus_Admin/backend-django
source /srv/focus-test/venv/bin/activate
nohup env ENABLE_SCHEDULER=false \
  /srv/focus-test/venv/bin/python -m celery -A application worker \
  -Q deepaudit,skill_optimizer \
  -n focus-test-deepaudit@%h \
  -l info \
  --concurrency=2 \
  --prefetch-multiplier=1 \
  --max-tasks-per-child=5 \
  > logs/celery-deepaudit-test.log 2>&1 &
echo $! > run/celery-deepaudit-test.pid
```

#### 测试 scheduler

```bash
cd /srv/focus-test/Focus_Admin/backend-django
source /srv/focus-test/venv/bin/activate
nohup env ENABLE_SCHEDULER=false \
  /srv/focus-test/venv/bin/python start_scheduler.py \
  > logs/scheduler-test.log 2>&1 &
echo $! > run/scheduler-test.pid
```

### 5.3 `nohup` 停止命令

```bash
[ -f /srv/focus-prod/Focus_Admin/backend-django/run/backend-prod.pid ] && kill $(cat /srv/focus-prod/Focus_Admin/backend-django/run/backend-prod.pid)
[ -f /srv/focus-prod/Focus_Admin/backend-django/run/celery-default-prod.pid ] && kill $(cat /srv/focus-prod/Focus_Admin/backend-django/run/celery-default-prod.pid)
[ -f /srv/focus-prod/Focus_Admin/backend-django/run/celery-deepaudit-prod.pid ] && kill $(cat /srv/focus-prod/Focus_Admin/backend-django/run/celery-deepaudit-prod.pid)
[ -f /srv/focus-prod/Focus_Admin/backend-django/run/scheduler-prod.pid ] && kill $(cat /srv/focus-prod/Focus_Admin/backend-django/run/scheduler-prod.pid)

[ -f /srv/focus-test/Focus_Admin/backend-django/run/backend-test.pid ] && kill $(cat /srv/focus-test/Focus_Admin/backend-django/run/backend-test.pid)
[ -f /srv/focus-test/Focus_Admin/backend-django/run/celery-default-test.pid ] && kill $(cat /srv/focus-test/Focus_Admin/backend-django/run/celery-default-test.pid)
[ -f /srv/focus-test/Focus_Admin/backend-django/run/celery-deepaudit-test.pid ] && kill $(cat /srv/focus-test/Focus_Admin/backend-django/run/celery-deepaudit-test.pid)
[ -f /srv/focus-test/Focus_Admin/backend-django/run/scheduler-test.pid ] && kill $(cat /srv/focus-test/Focus_Admin/backend-django/run/scheduler-test.pid)
```

### 5.4 `nohup` 重启流程

标准流程：

1. 先执行上一节的停止命令。
2. 用 `lsof` 确认 `8001` 与 `8002` 已释放。
3. 确认没有残留 `celery` / `start_scheduler.py` 进程。
4. 删除旧 PID 文件。
5. 重新执行 5.1 与 5.2 的 8 条启动命令。

删除旧 PID 示例：

```bash
rm -f /srv/focus-prod/Focus_Admin/backend-django/run/*.pid
rm -f /srv/focus-test/Focus_Admin/backend-django/run/*.pid
```

### 5.5 `nohup` 存活检查

检查端口：

```bash
lsof -iTCP:8001 -sTCP:LISTEN -P -n
lsof -iTCP:8002 -sTCP:LISTEN -P -n
```

检查进程：

```bash
ps -ef | grep gunicorn | grep application.asgi
ps -ef | grep "celery -A application worker"
ps -ef | grep start_scheduler.py
```

检查日志：

```bash
tail -f /srv/focus-prod/Focus_Admin/backend-django/logs/backend-prod.log
tail -f /srv/focus-prod/Focus_Admin/backend-django/logs/celery-default-prod.log
tail -f /srv/focus-prod/Focus_Admin/backend-django/logs/celery-deepaudit-prod.log
tail -f /srv/focus-prod/Focus_Admin/backend-django/logs/scheduler-prod.log

tail -f /srv/focus-test/Focus_Admin/backend-django/logs/backend-test.log
tail -f /srv/focus-test/Focus_Admin/backend-django/logs/celery-default-test.log
tail -f /srv/focus-test/Focus_Admin/backend-django/logs/celery-deepaudit-test.log
tail -f /srv/focus-test/Focus_Admin/backend-django/logs/scheduler-test.log
```

## 6. `systemd` 方案

`systemd` 方案与 `nohup` 的进程集合完全一致，只是改由 `systemd` 托管。长期建议迁移到本方案。

### 6.1 服务命名规范

正式环境：

- `focus-prod-backend.service`
- `focus-prod-celery-default.service`
- `focus-prod-celery-deepaudit.service`
- `focus-prod-scheduler.service`

测试环境：

- `focus-test-backend.service`
- `focus-test-celery-default.service`
- `focus-test-celery-deepaudit.service`
- `focus-test-scheduler.service`

### 6.2 正式环境 4 个 service 文件

#### `/etc/systemd/system/focus-prod-backend.service`

```ini
[Unit]
Description=Focus Prod Django ASGI Backend
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus-prod/Focus_Admin/backend-django
EnvironmentFile=/srv/focus-prod/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus-prod/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus-prod/venv/bin/gunicorn application.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8001 --workers 4 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/focus-prod-celery-default.service`

```ini
[Unit]
Description=Focus Prod Celery Worker (default queue)
After=network.target redis.service focus-prod-backend.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus-prod/Focus_Admin/backend-django
EnvironmentFile=/srv/focus-prod/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus-prod/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus-prod/venv/bin/python -m celery -A application worker -Q celery -n focus-prod-default@%%h -l info --concurrency=2 --max-tasks-per-child=5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/focus-prod-celery-deepaudit.service`

```ini
[Unit]
Description=Focus Prod Celery Worker (DeepAudit and Agent Tools queues)
After=network.target redis.service focus-prod-backend.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus-prod/Focus_Admin/backend-django
EnvironmentFile=/srv/focus-prod/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus-prod/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus-prod/venv/bin/python -m celery -A application worker -Q deepaudit,skill_optimizer -n focus-prod-deepaudit@%%h -l info --concurrency=2 --prefetch-multiplier=1 --max-tasks-per-child=5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/focus-prod-scheduler.service`

```ini
[Unit]
Description=Focus Prod Scheduler
After=network.target redis.service focus-prod-backend.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus-prod/Focus_Admin/backend-django
EnvironmentFile=/srv/focus-prod/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus-prod/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus-prod/venv/bin/python start_scheduler.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.3 测试环境 4 个 service 文件

#### `/etc/systemd/system/focus-test-backend.service`

```ini
[Unit]
Description=Focus Test Django ASGI Backend
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus-test/Focus_Admin/backend-django
EnvironmentFile=/srv/focus-test/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus-test/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus-test/venv/bin/gunicorn application.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8002 --workers 4 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/focus-test-celery-default.service`

```ini
[Unit]
Description=Focus Test Celery Worker (default queue)
After=network.target redis.service focus-test-backend.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus-test/Focus_Admin/backend-django
EnvironmentFile=/srv/focus-test/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus-test/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus-test/venv/bin/python -m celery -A application worker -Q celery -n focus-test-default@%%h -l info --concurrency=2 --max-tasks-per-child=5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/focus-test-celery-deepaudit.service`

```ini
[Unit]
Description=Focus Test Celery Worker (DeepAudit and Agent Tools queues)
After=network.target redis.service focus-test-backend.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus-test/Focus_Admin/backend-django
EnvironmentFile=/srv/focus-test/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus-test/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus-test/venv/bin/python -m celery -A application worker -Q deepaudit,skill_optimizer -n focus-test-deepaudit@%%h -l info --concurrency=2 --prefetch-multiplier=1 --max-tasks-per-child=5
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/focus-test-scheduler.service`

```ini
[Unit]
Description=Focus Test Scheduler
After=network.target redis.service focus-test-backend.service
Requires=redis.service

[Service]
Type=simple
User=focus
Group=focus
WorkingDirectory=/srv/focus-test/Focus_Admin/backend-django
EnvironmentFile=/srv/focus-test/Focus_Admin/backend-django/.env
Environment=PATH=/srv/focus-test/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
Environment=ENABLE_SCHEDULER=false
ExecStart=/srv/focus-test/venv/bin/python start_scheduler.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.4 `systemd` 安装、启动、重启、状态查看

安装或修改 service 文件后：

```bash
sudo systemctl daemon-reload

sudo systemctl enable focus-prod-backend focus-prod-celery-default focus-prod-celery-deepaudit focus-prod-scheduler
sudo systemctl enable focus-test-backend focus-test-celery-default focus-test-celery-deepaudit focus-test-scheduler

sudo systemctl start focus-prod-backend focus-prod-celery-default focus-prod-celery-deepaudit focus-prod-scheduler
sudo systemctl start focus-test-backend focus-test-celery-default focus-test-celery-deepaudit focus-test-scheduler
```

常用运维命令：

```bash
sudo systemctl restart focus-prod-backend
sudo systemctl restart focus-prod-celery-default
sudo systemctl restart focus-prod-celery-deepaudit
sudo systemctl restart focus-prod-scheduler

sudo systemctl restart focus-test-backend
sudo systemctl restart focus-test-celery-default
sudo systemctl restart focus-test-celery-deepaudit
sudo systemctl restart focus-test-scheduler

sudo systemctl status focus-prod-backend focus-prod-celery-default focus-prod-celery-deepaudit focus-prod-scheduler
sudo systemctl status focus-test-backend focus-test-celery-default focus-test-celery-deepaudit focus-test-scheduler

# 输出中必须同时包含 deepaudit 与 skill_optimizer
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
celery -A application inspect active_queues
```

日志查看：

```bash
journalctl -u focus-prod-backend -f
journalctl -u focus-prod-celery-default -f
journalctl -u focus-prod-celery-deepaudit -f
journalctl -u focus-prod-scheduler -f

journalctl -u focus-test-backend -f
journalctl -u focus-test-celery-default -f
journalctl -u focus-test-celery-deepaudit -f
journalctl -u focus-test-scheduler -f
```

### 6.5 scheduler 的推荐方式

主推荐方案是：

- Web 进程不依赖 `AppConfig.ready()` 自动拉起 scheduler。
- Celery 进程也不承担 scheduler 职责。
- scheduler 固定作为独立进程运行，即 `python start_scheduler.py`。

这样做的原因：

- 双环境同机时最容易避免误起多个 scheduler 实例。
- 更容易排查到底是谁在持有调度器心跳。
- 更方便从 `nohup` 迁移到 `systemd`。

## 7. nginx 双域名配置

建议文件：`/etc/nginx/conf.d/focus-dual-env.conf`

### 7.1 HTTP 可直接运行版本

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

upstream focus_prod_backend {
    server 127.0.0.1:8001;
    keepalive 32;
}

upstream focus_test_backend {
    server 127.0.0.1:8002;
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

    location ~ ^/basic-api/api/deepaudit/agent-tasks/[^/]+/stream$ {
        rewrite ^/basic-api/(.*)$ /$1 break;
        proxy_pass http://focus_prod_backend;
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
        proxy_pass http://focus_prod_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    location /ws/ {
        proxy_pass http://focus_prod_backend;
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

server {
    listen 80;
    server_name focus-test.example.com;

    client_max_body_size 500M;
    root /var/www/focus_test;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location = /deepaudit-app {
        return 301 /deepaudit-app/;
    }

    location /deepaudit-app/ {
        alias /var/www/deepaudit_test/;
        index index.html;
        try_files $uri $uri/ /deepaudit-app/index.html;
    }

    location /static/ {
        alias /srv/focus-test/Focus_Admin/backend-django/static_root/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public";
    }

    location /media/ {
        alias /srv/focus-test/Focus_Admin/backend-django/media/;
    }

    location ~ ^/basic-api/api/deepaudit/agent-tasks/[^/]+/stream$ {
        rewrite ^/basic-api/(.*)$ /$1 break;
        proxy_pass http://focus_test_backend;
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
        proxy_pass http://focus_test_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    location /ws/ {
        proxy_pass http://focus_test_backend;
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

说明：

- 两个 `server` 的路径规则必须完全一致，只允许 `server_name`、`upstream`、`root`、`alias`、`static/media` 目录不同。
- DeepAudit `/stream` 单独关闭 `proxy_buffering`，否则前端会表现为请求成功但日志很久不刷新。
- `/basic-api/` 与 `/ws/` 都继续走同一个 ASGI 服务，避免测试和正式路径不一致。

### 7.2 HTTPS 增强位

如果要上 HTTPS，可以在上面的每个 `server` 块基础上增加：

```nginx
listen 443 ssl http2;
ssl_certificate     /path/to/fullchain.pem;
ssl_certificate_key /path/to/privkey.pem;
```

同时保留一个 80 端口 server 做 301 跳转即可。不要因为文档只写了 HTTPS 片段，就把可运行的 HTTP 基线配置删掉。

### 7.3 nginx 检查与重载

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 8. 验收清单

### 8.1 页面与路由

- `https://focus.example.com/` 能进入正式 `web-ele`。
- `https://focus-test.example.com/` 能进入测试 `web-ele`。
- 两个域名的 `/deepaudit-app/` 都能正常打开。
- 刷新 `/deepaudit-app/` 的任意子路由都不会 404。

### 8.2 API、WebSocket、SSE

- 正式 `/basic-api/` 请求命中 `127.0.0.1:8001`。
- 测试 `/basic-api/` 请求命中 `127.0.0.1:8002`。
- 正式 `/ws/` 能连到 `8001`。
- 测试 `/ws/` 能连到 `8002`。
- 正式与测试的 DeepAudit `/stream` 都能实时返回，不会长时间无日志刷新。

### 8.3 异步任务与调度器

- 正式创建 DeepAudit 任务后，由正式 `celery-deepaudit` 消费。
- 测试创建 DeepAudit 任务后，由测试 `celery-deepaudit` 消费。
- 两个环境的 scheduler 都独立运行，互不影响。
- 正式停止某个进程，不应影响测试环境对应进程。
- 两个环境的数据库、Redis 队列、日志、静态目录都不会串用。

### 8.4 `nohup` / `systemd` 验收

`nohup` 场景：

- 8 个进程都能通过 `ps`、端口、日志验证。
- 8 个进程都拥有各自 PID 文件。

`systemd` 场景：

- 8 个服务都能 `enable/start/status`。
- `journalctl` 能看到每个服务的独立日志。
- 任意单个服务异常退出后可自动拉起。

## 9. 从 `nohup` 迁移到 `systemd`

建议按以下顺序迁移：

1. 停止当前 `nohup` 管理的 8 个进程。
2. 用 `lsof` 确认 `8001`、`8002` 已释放。
3. 用 `ps -ef` 确认没有残留 `celery` 与 `start_scheduler.py` 进程。
4. 安装 8 个 `systemd` service 文件。
5. 执行 `sudo systemctl daemon-reload`。
6. 执行 `enable` 与 `start`。
7. 用 `status`、`journalctl`、浏览器访问、API 调用逐项验收。
8. 清理旧的 `run/*.pid`。

明确要求：

- 禁止 `nohup` 和 `systemd` 同时管理同一组 backend / Celery / scheduler 进程。
- 迁移时一定先停旧再起新，避免端口冲突与重复消费。

## 10. `nohup` 与 `systemd` 方案对比

| 对比项 | `nohup` | `systemd` |
|---|---|---|
| 启动简单性 | 高，复制命令即可 | 中，需要维护 service 文件 |
| 自动拉起 | 无 | 有 |
| 崩溃恢复 | 需要人工介入 | 自动重启 |
| 日志管理 | 文件日志为主 | `journalctl` + 标准输出 |
| PID 管理 | 需要自己维护 | `systemd` 托管 |
| 运维可观测性 | 一般 | 更强 |
| 当前适用阶段 | 先快速落地 | 长期稳定运行 |

建议：

- 当前先按 `nohup` 方案跑通完全没有问题。
- 一旦双环境稳定运行，优先切换到 `systemd`。

## 11. 常见问题

### 11.1 为什么文档要求 Web / Celery 都带 `ENABLE_SCHEDULER=false`

因为项目里 scheduler 仍有自动启动逻辑。如果 Web 进程或 Celery 进程在错误条件下带着 `ENABLE_SCHEDULER=true` 启动，同一环境内就可能出现多个 scheduler；双环境同机时问题会更难排查。

因此本手册固定要求：

- Web 进程：`ENABLE_SCHEDULER=false`
- Celery 进程：`ENABLE_SCHEDULER=false`
- scheduler：独立运行 `python start_scheduler.py`

### 11.2 测试和正式能共用一套代码目录吗

不推荐。因为这样会让以下内容互相污染：

- `.env`
- `logs`
- `run`
- `static_root`
- `media`
- git 分支与回滚节奏

### 11.3 测试和正式能共用一个 Redis DB 吗

不推荐。scheduler 心跳、Celery 队列、Channels 状态、缓存都可能互相影响。

### 11.4 现在应该先用哪种方案

- 你当前已经在用 `nohup`，可以直接按第 5 节落地。
- 等上线稳定后，再按第 9 节迁移到 `systemd`。
