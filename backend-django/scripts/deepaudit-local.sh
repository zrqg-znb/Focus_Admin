#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python}"
RUNSERVER_ADDR="${RUNSERVER_ADDR:-0.0.0.0:8000}"
DEEPAUDIT_QUEUE="${DEEPAUDIT_QUEUE:-deepaudit}"
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
LOG_DIR="$ROOT_DIR/logs"

mkdir -p "$LOG_DIR"

redis_auth_args=()
if [[ -n "$REDIS_PASSWORD" ]]; then
  redis_auth_args=(-a "$REDIS_PASSWORD" --no-auth-warning)
fi

print_usage() {
  cat <<'EOF'
用法:
  bash scripts/deepaudit-local.sh check   # 检查 DeepAudit 本地依赖与配置
  bash scripts/deepaudit-local.sh redis   # 确保本地 Redis 可用
  bash scripts/deepaudit-local.sh worker  # 启动 DeepAudit Celery Worker
  bash scripts/deepaudit-local.sh server  # 启动 Django 开发服务器
  bash scripts/deepaudit-local.sh all     # 自动拉起 Redis + Worker，并在前台启动 Django

可选环境变量:
  PYTHON_BIN=/path/to/python
  REDIS_HOST=127.0.0.1
  REDIS_PORT=6379
  REDIS_PASSWORD=
  DEEPAUDIT_QUEUE=deepaudit
  RUNSERVER_ADDR=0.0.0.0:8000
EOF
}

check_python_deps() {
  "$PYTHON_BIN" - <<'PY'
import importlib.metadata as md
required = ['channels', 'channels-redis', 'celery', 'redis']
for name in required:
    try:
        print(f'{name}: {md.version(name)}')
    except md.PackageNotFoundError as exc:
        raise SystemExit(f'缺少依赖 {name}: {exc}')
PY
}

check_django_settings() {
  DJANGO_SETTINGS_MODULE=application.settings "$PYTHON_BIN" - <<'PY'
import django
django.setup()
from django.conf import settings

print(f'CELERY_BROKER_URL={settings.CELERY_BROKER_URL}')
print(f'CHANNEL_LAYER_BACKEND={settings.CHANNEL_LAYERS["default"]["BACKEND"]}')
print(f'CHANNEL_LAYER_HOSTS={settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"]}')
print(f'DEEPAUDIT_QUEUE={getattr(settings, "DEEPAUDIT_QUEUE", "deepaudit")}')
PY
}

redis_ping() {
  if [[ ${#redis_auth_args[@]} -gt 0 ]]; then
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" "${redis_auth_args[@]}" ping >/dev/null 2>&1
  else
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1
  fi
}

ensure_redis() {
  if redis_ping; then
    echo "Redis 已可用: ${REDIS_HOST}:${REDIS_PORT}"
    return 0
  fi

  if [[ "$REDIS_HOST" != "127.0.0.1" && "$REDIS_HOST" != "localhost" ]]; then
    echo "Redis 不可用，且当前 REDIS_HOST=$REDIS_HOST 不是本机地址，请先手动启动远端 Redis。" >&2
    return 1
  fi

  if ! command -v redis-server >/dev/null 2>&1; then
    echo "未找到 redis-server，请先安装 Redis。" >&2
    return 1
  fi

  echo "检测到本地 Redis 未启动，尝试自动启动..."
  if [[ -n "$REDIS_PASSWORD" ]]; then
    redis-server \
      --port "$REDIS_PORT" \
      --daemonize yes \
      --requirepass "$REDIS_PASSWORD" \
      --logfile "$LOG_DIR/redis-${REDIS_PORT}.log"
  else
    redis-server \
      --port "$REDIS_PORT" \
      --daemonize yes \
      --logfile "$LOG_DIR/redis-${REDIS_PORT}.log"
  fi

  for _ in {1..10}; do
    if redis_ping; then
      echo "Redis 启动成功: ${REDIS_HOST}:${REDIS_PORT}"
      return 0
    fi
    sleep 1
  done

  echo "Redis 启动失败，请检查日志: $LOG_DIR/redis-${REDIS_PORT}.log" >&2
  return 1
}

run_check() {
  check_python_deps
  ensure_redis
  check_django_settings
  echo "DeepAudit 本地链路检查通过。"
}

run_worker() {
  ensure_redis
  exec "$PYTHON_BIN" -m celery -A application worker -Q "$DEEPAUDIT_QUEUE" -l info
}

run_server() {
  ensure_redis
  exec "$PYTHON_BIN" manage.py runserver "$RUNSERVER_ADDR"
}

run_all() {
  ensure_redis
  check_python_deps

  "$PYTHON_BIN" -m celery -A application worker -Q "$DEEPAUDIT_QUEUE" -l info >"$LOG_DIR/celery-deepaudit.log" 2>&1 &
  local celery_pid=$!
  echo "DeepAudit Celery Worker 已启动，PID=$celery_pid，日志: $LOG_DIR/celery-deepaudit.log"

  cleanup() {
    kill "$celery_pid" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT INT TERM

  exec "$PYTHON_BIN" manage.py runserver "$RUNSERVER_ADDR"
}

cmd="${1:-check}"
case "$cmd" in
  check)
    run_check
    ;;
  redis)
    ensure_redis
    ;;
  worker)
    run_worker
    ;;
  server)
    run_server
    ;;
  all)
    run_all
    ;;
  *)
    print_usage
    exit 1
    ;;
esac
