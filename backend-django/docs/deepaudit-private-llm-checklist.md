# DeepAudit 内网 LLM / Celery 双环境检查清单

适用场景：

- 生产与测试部署在同一台公司内网服务器
- 大模型请求走内网网关或中转站
- DeepAudit 任务由 Celery Worker 异步执行
- 需要避免 `tiktoken` 访问公网 `openaipublic.blob.core.windows.net`

本文默认沿用双环境部署手册中的目录与服务命名：

| 项目 | 正式环境 | 测试环境 |
|---|---|---|
| 代码目录 | `/srv/focus-prod/Focus_Admin` | `/srv/focus-test/Focus_Admin` |
| Python venv | `/srv/focus-prod/venv` | `/srv/focus-test/venv` |
| `.env` | `/srv/focus-prod/Focus_Admin/backend-django/.env` | `/srv/focus-test/Focus_Admin/backend-django/.env` |
| tiktoken cache | `/srv/focus-prod/tiktoken-cache` | `/srv/focus-test/tiktoken-cache` |
| DeepAudit worker service | `focus-prod-celery-deepaudit` | `focus-test-celery-deepaudit` |

## 1. `.env` 必检项

正式环境建议至少包含：

```env
ZQ_ENV=prd

# Django / JWT
DJANGO_SECRET_KEY=replace-with-a-strong-secret
JWT_ACCESS_SECRET_KEY=replace-with-a-strong-access-secret
JWT_REFRESH_SECRET_KEY=replace-with-a-strong-refresh-secret

# Redis / Celery
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=2
REDIS_CELERY_DB=3
REDIS_CHANNEL_DB=4
DEEPAUDIT_QUEUE=deepaudit
SKILL_OPTIMIZER_QUEUE=skill_optimizer

# DeepAudit 全局默认 LLM（给未单独配置用户做回退）
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=replace-with-your-private-gateway-key
LLM_BASE_URL=http://your-internal-llm-gateway/v1
LLM_TIMEOUT=180
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096

# 首 Token / 流式超时
LLM_FIRST_TOKEN_TIMEOUT=120
LLM_STREAM_TIMEOUT=180
TOOL_TIMEOUT_SECONDS=120
SUB_AGENT_TIMEOUT_SECONDS=900
AGENT_TIMEOUT_SECONDS=2400

# Embedding
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=replace-with-your-private-embedding-key
EMBEDDING_BASE_URL=http://your-internal-embedding-gateway/v1
EMBEDDING_DIMENSIONS=1536

# tiktoken 离线缓存
DEEPAUDIT_TIKTOKEN_MODE=local
TIKTOKEN_CACHE_DIR=/srv/focus-prod/tiktoken-cache
DATA_GYM_CACHE_DIR=/srv/focus-prod/tiktoken-cache

# 可选：如你的网关兼容 OpenAI 专属字段
OPENAI_API_KEY=replace-with-your-private-gateway-key
OPENAI_BASE_URL=http://your-internal-llm-gateway/v1
```

测试环境只需把 `ZQ_ENV`、Redis DB、cache 目录与密钥替换成测试值，例如：

```env
ZQ_ENV=uat
REDIS_DB=5
REDIS_CELERY_DB=6
REDIS_CHANNEL_DB=7
TIKTOKEN_CACHE_DIR=/srv/focus-test/tiktoken-cache
DATA_GYM_CACHE_DIR=/srv/focus-test/tiktoken-cache
```

重点检查：

- `LLM_BASE_URL` 与 `EMBEDDING_BASE_URL` 是否都指向内网地址。
- 如果 embedding 也走内网，不能只配聊天模型的 `LLM_BASE_URL`。
- `DEEPAUDIT_TIKTOKEN_MODE` 生产建议固定为 `local`。
- `TIKTOKEN_CACHE_DIR` 必须对 Django 与 Celery 运行用户都可读。
- `LLM_FIRST_TOKEN_TIMEOUT` 建议先提高到 `120` 或 `180`。
- `DJANGO_SECRET_KEY` 必须长期稳定；用户保存在数据库里的 API Key 依赖它解密。

## 2. Celery Worker 启动参数检查

DeepAudit 与 AI 辅助工具共用同一 Worker，并同时消费两个专用队列。双环境 service 名称分别是：

- 正式：`focus-prod-celery-deepaudit.service`
- 测试：`focus-test-celery-deepaudit.service`

正式环境参考 service：

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

测试环境只需要把路径、端口依赖与节点名切换到 `focus-test-*` 即可。

推荐检查项：

- `-Q deepaudit,skill_optimizer` 必须同时覆盖 `.env` 里的 `DEEPAUDIT_QUEUE=deepaudit` 和 `SKILL_OPTIMIZER_QUEUE=skill_optimizer`。
- `EnvironmentFile` 必须和 Django Web 进程使用同一份 `.env`。
- `--prefetch-multiplier=1` 可减少单 Worker 抢太多重任务。
- `--max-tasks-per-child=5` 可缓解长时间运行后的内存与连接残留。
- 如果首 Token 很慢，先不要把 `--concurrency` 调太高，建议从 `2` 开始。

重启 Worker 后，在同一虚拟环境内执行以下命令，输出中应同时出现 `deepaudit` 和 `skill_optimizer`：

```bash
celery -A application inspect active_queues
```

## 3. tiktoken 缓存预热

### 3.1 直接在目标机器预热

正式环境：

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
python scripts/warm_tiktoken_cache.py \
  --cache-dir /srv/focus-prod/tiktoken-cache \
  --encodings cl100k_base o200k_base \
  --models gpt-4 gpt-4o gpt-5 text-embedding-3-small
```

测试环境：

```bash
cd /srv/focus-test/Focus_Admin/backend-django
source /srv/focus-test/venv/bin/activate
python scripts/warm_tiktoken_cache.py \
  --cache-dir /srv/focus-test/tiktoken-cache \
  --encodings cl100k_base o200k_base \
  --models gpt-4 gpt-4o gpt-5 text-embedding-3-small
```

### 3.2 打包后分发到无公网机器

在一台可访问公网 blob 的机器执行：

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
python scripts/warm_tiktoken_cache.py \
  --cache-dir /tmp/tiktoken-cache \
  --archive /tmp/tiktoken-cache.tar.gz
```

再把 `/tmp/tiktoken-cache.tar.gz` 拷到目标机器并按环境解压：

```bash
sudo mkdir -p /srv/focus-prod/tiktoken-cache
sudo tar -xzf /path/to/tiktoken-cache.tar.gz -C /srv/focus-prod
sudo chown -R focus:focus /srv/focus-prod/tiktoken-cache

sudo mkdir -p /srv/focus-test/tiktoken-cache
sudo tar -xzf /path/to/tiktoken-cache.tar.gz -C /srv/focus-test
sudo chown -R focus:focus /srv/focus-test/tiktoken-cache
```

### 3.3 只做校验

```bash
python scripts/warm_tiktoken_cache.py \
  --cache-dir /srv/focus-prod/tiktoken-cache \
  --verify-only

python scripts/warm_tiktoken_cache.py \
  --cache-dir /srv/focus-test/tiktoken-cache \
  --verify-only
```

## 4. 发布后自检命令

确认 Django 进程实际读取到了 `.env`：

正式环境：

```bash
cd /srv/focus-prod/Focus_Admin/backend-django
source /srv/focus-prod/venv/bin/activate
python - <<'PY'
from django.conf import settings
print("LLM_BASE_URL =", settings.LLM_BASE_URL)
print("EMBEDDING_BASE_URL =", settings.EMBEDDING_BASE_URL)
print("DEEPAUDIT_TIKTOKEN_MODE =", settings.DEEPAUDIT_TIKTOKEN_MODE)
print("TIKTOKEN_CACHE_DIR =", settings.TIKTOKEN_CACHE_DIR)
print("LLM_FIRST_TOKEN_TIMEOUT =", settings.LLM_FIRST_TOKEN_TIMEOUT)
PY
```

测试环境把路径替换成 `/srv/focus-test/...` 再执行一次。

确认 `systemd` 里的 DeepAudit Worker 也吃到了同一份变量：

```bash
systemctl cat focus-prod-celery-deepaudit
systemctl show focus-prod-celery-deepaudit --property=Environment --no-pager
journalctl -u focus-prod-celery-deepaudit -n 100 --no-pager

systemctl cat focus-test-celery-deepaudit
systemctl show focus-test-celery-deepaudit --property=Environment --no-pager
journalctl -u focus-test-celery-deepaudit -n 100 --no-pager
```

重点看：

- 是否仍然出现 `openaipublic.blob.core.windows.net`
- 是否仍然出现 `Address family not supported by protocol`
- 是否仍然出现 `async_streaming was never awaited`

## 5. 首 Token 超时排查顺序

如果内网环境里首 Token 仍然经常超时，按这个顺序排查：

1. 先确认 `LLM_BASE_URL` 是内网地址，不是默认公网 OpenAI 地址。
2. 再确认 Celery Worker 和 Web 进程都加载了相同 `.env`。
3. 确认 embedding 请求是否也走了内网 `EMBEDDING_BASE_URL`。
4. 预热 `tiktoken` cache，避免第一次请求时额外触发编码文件下载。
5. 提高 `LLM_FIRST_TOKEN_TIMEOUT`。
6. 降低 Worker 并发和 DeepAudit 扫描并发。

用户级并发可在 DeepAudit 设置中降低：

- `other_config.scan_config.llm_concurrency`
- `other_config.scan_config.llm_gap_ms`

## 6. 不同用户如何配置自己的 API Key

DeepAudit 当前支持“用户级配置覆盖系统默认”：

- 每个用户的配置保存在 `deepaudit_user_config` 表。
- `llm_config.api_key` 与 `other_config.embedding_config.api_key` 入库前会加密。
- Agent / Scan 任务执行时，会按任务创建人 `created_by` 加载该用户配置。

对应接口：

- `GET /api/deepaudit/settings/me`
- `PUT /api/deepaudit/settings/me`
- `GET /api/deepaudit/embedding/config`
- `PUT /api/deepaudit/embedding/config`

运行时优先级：

1. 当前任务创建人的用户配置
2. 系统 `.env` / Django settings 默认值
3. 代码内 provider 默认值

因此生产建议是：

- 平台层在 `.env` 提供一套兜底的内网网关配置。
- 高权限或特殊账号在 DeepAudit 设置页里保存自己的专属 key / base URL。
- Celery 任务会跟随任务创建人的用户配置，不会串用其他用户的 key。
- 不要在不做迁移的情况下随意更换 `DJANGO_SECRET_KEY`，否则历史保存的用户 key 可能无法解密。
