# DeepAudit 本地运行链路

本文档用于把 DeepAudit 的 Redis / Celery / Channels 本地链路一次性打通，确保以下能力可用：

- Agent 审计任务创建后能正常入队
- DeepAudit 扫描任务能被 Celery Worker 消费
- Channels WebSocket 可以连接 `/ws/deepaudit/tasks/{task_id}/`

## 1. 环境依赖

先激活你的后端 Python 环境，例如：

```bash
conda activate focus-platform
```

然后安装依赖：

```bash
cd /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/backend-django
python -m pip install -r requirements.txt
```

本次已经把 `channels-redis==4.3.0` 写入 `requirements.txt`，后续重新装环境不会再漏掉。

## 2. 推荐环境变量

`.env` 中至少保证这些变量可用：

```env
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=2
REDIS_CELERY_DB=2
REDIS_CHANNEL_DB=2
DEEPAUDIT_QUEUE=deepaudit
```

说明：

- `REDIS_DB`：默认缓存 DB
- `REDIS_CELERY_DB`：Celery broker 使用的 DB，默认回退到 `REDIS_DB`
- `REDIS_CHANNEL_DB`：Channels layer 使用的 DB，默认回退到 `REDIS_DB`

如果你希望把缓存、队列、WebSocket 彻底分开，推荐改成：

```env
REDIS_DB=2
REDIS_CELERY_DB=3
REDIS_CHANNEL_DB=4
```

## 3. 一键检查

仓库内新增了本地链路脚本：

```bash
cd /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/backend-django
bash scripts/deepaudit-local.sh check
```

它会做这些事情：

- 检查 `channels` / `channels-redis` / `celery` / `redis` Python 依赖
- 检查 Redis 是否可用；如果是本机地址且 Redis 没启动，会尝试自动拉起
- 输出 Django 当前使用的 Celery broker、Channels backend 和 DeepAudit 队列配置

## 4. 本地启动方式

### 方式 A：分终端启动

终端 1：

```bash
cd /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/backend-django
bash scripts/deepaudit-local.sh worker
```

终端 2：

```bash
cd /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/backend-django
bash scripts/deepaudit-local.sh server
```

### 方式 B：单命令启动

```bash
cd /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/backend-django
bash scripts/deepaudit-local.sh all
```

这个命令会：

- 自动确保本地 Redis 可用
- 后台拉起 DeepAudit Celery Worker
- 前台启动 Django ASGI 服务器

Worker 日志默认输出到：

```bash
backend-django/logs/celery-deepaudit.log
```

## 5. 验证链路

### Redis

```bash
redis-cli -h 127.0.0.1 -p 6379 ping
```

预期输出：

```bash
PONG
```

### Celery

```bash
cd /Users/zrq/CodeSpace/PythonProjects/Focus_Admin/backend-django
python -m celery -A application inspect ping
```

### Channels

启动 Django 后，访问或连接：

```text
ws://127.0.0.1:8001/ws/deepaudit/tasks/{task_id}/?token=<jwt>
```

如果 JWT 正常、任务存在且用户有权限，连接后会收到 DeepAudit ready / subscribed 事件。

## 6. 常见问题

### `kombu.exceptions.OperationalError: [Errno 61] Connection refused`

说明 Celery broker 连不上 Redis。优先检查：

- Redis 是否启动
- `REDIS_HOST` / `REDIS_PORT` 是否正确
- `CELERY_BROKER_URL` 是否指向了正确的 Redis DB

### `InvalidChannelLayerError` 或 `No module named 'channels_redis'`

说明 Channels Redis backend 未安装或环境错了。重新执行：

```bash
python -m pip install -r requirements.txt
```

并确认你启动 Django 的解释器和安装依赖的解释器是同一个。

### 创建任务不再 500，但状态变成 failed

这是 DeepAudit 的安全降级逻辑生效了：接口创建成功，但队列不可用，所以任务会被回写为失败，并在 `error_message` 中写明原因。先把 Redis / Celery Worker 启起来，再重新创建任务即可。
