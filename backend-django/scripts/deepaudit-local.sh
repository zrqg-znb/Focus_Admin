#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

resolve_python_bin() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    echo "$PYTHON_BIN"
    return 0
  fi

  if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    echo "${VIRTUAL_ENV}/bin/python"
    return 0
  fi

  if [[ -n "${CONDA_PREFIX:-}" && "${CONDA_DEFAULT_ENV:-}" != "base" && -x "${CONDA_PREFIX}/bin/python" ]]; then
    echo "${CONDA_PREFIX}/bin/python"
    return 0
  fi

  local conda_base=""
  if command -v conda >/dev/null 2>&1; then
    conda_base="$(conda info --base 2>/dev/null || true)"
  fi

  local candidates=()
  if [[ -n "$conda_base" ]]; then
    candidates+=("${conda_base}/envs/focus-platform/bin/python")
  fi
  candidates+=(
    "${HOME}/miniconda3/envs/focus-platform/bin/python"
    "${HOME}/anaconda3/envs/focus-platform/bin/python"
  )

  local candidate=""
  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  command -v python
}

PYTHON_BIN="$(resolve_python_bin)"
RUNSERVER_ADDR="${RUNSERVER_ADDR:-0.0.0.0:8001}"
DEEPAUDIT_QUEUE="${DEEPAUDIT_QUEUE:-deepaudit}"
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
LOG_DIR="$ROOT_DIR/logs"
HOST_TAG="$(hostname -s 2>/dev/null || hostname || echo local)"
HOST_TAG="${HOST_TAG//[^A-Za-z0-9._-]/-}"
WORKER_NAME="${WORKER_NAME:-focus-local-${DEEPAUDIT_QUEUE}@${HOST_TAG}}"
PID_DIR="$ROOT_DIR/run"
WORKER_PID_FILE="$PID_DIR/celery-${DEEPAUDIT_QUEUE}.pid"
WORKER_LOG_FILE="$LOG_DIR/celery-${DEEPAUDIT_QUEUE}.log"
SERVER_LOG_FILE="$LOG_DIR/server.log"
ERROR_LOG_FILE="$LOG_DIR/error.log"
UVICORN_RELOAD_DIRS=(
  "$ROOT_DIR/application"
  "$ROOT_DIR/apps"
  "$ROOT_DIR/common"
  "$ROOT_DIR/core"
  "$ROOT_DIR/scheduler"
  "$ROOT_DIR/system"
)
UVICORN_RELOAD_ARGS=()
for reload_dir in "${UVICORN_RELOAD_DIRS[@]}"; do
  UVICORN_RELOAD_ARGS+=(--reload-dir "$reload_dir")
done

mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

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
  bash scripts/deepaudit-local.sh stop    # 停止 DeepAudit Celery Worker
  bash scripts/deepaudit-local.sh restart # 重启 DeepAudit Celery Worker
  bash scripts/deepaudit-local.sh status  # 查看 DeepAudit Celery Worker 状态
  bash scripts/deepaudit-local.sh server  # 启动 Django ASGI 服务器
  bash scripts/deepaudit-local.sh all     # 自动拉起 Redis + Worker，并在前台启动 Django ASGI 服务器

可选环境变量:
  PYTHON_BIN=/path/to/python
  REDIS_HOST=127.0.0.1
  REDIS_PORT=6379
  REDIS_PASSWORD=
  DEEPAUDIT_QUEUE=deepaudit
  RUNSERVER_ADDR=0.0.0.0:8001
  WORKER_NAME=focus-local-deepaudit@your-host
EOF
}

read_worker_pid() {
  if [[ -f "$WORKER_PID_FILE" ]]; then
    tr -d '[:space:]' <"$WORKER_PID_FILE"
  fi
}

worker_process_alive() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

cleanup_worker_pidfile() {
  local pid
  pid="$(read_worker_pid)"
  if [[ -n "$pid" ]] && ! worker_process_alive "$pid"; then
    rm -f "$WORKER_PID_FILE"
  fi
}

ensure_no_duplicate_worker() {
  cleanup_worker_pidfile
  local pid
  pid="$(read_worker_pid)"
  if [[ -n "$pid" ]] && worker_process_alive "$pid"; then
    echo "DeepAudit Worker 已在运行: PID=$pid NAME=$WORKER_NAME QUEUE=$DEEPAUDIT_QUEUE"
    return 1
  fi
  return 0
}

reset_worker_log_file() {
  rm -f "$WORKER_LOG_FILE"
  : >"$WORKER_LOG_FILE"
}

print_log_destinations() {
  echo "Celery 运行日志: $WORKER_LOG_FILE"
  echo "DeepAudit 业务日志: $SERVER_LOG_FILE"
  echo "错误日志: $ERROR_LOG_FILE"
}

check_python_deps() {
  echo "Using PYTHON_BIN=$PYTHON_BIN"
  "$PYTHON_BIN" - <<'PY'
import importlib.metadata as md
required = ['channels', 'channels-redis', 'celery', 'redis', 'pydantic-settings']
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

start_uvicorn_server() {
  local host="${RUNSERVER_ADDR%:*}"
  local port="${RUNSERVER_ADDR##*:}"
  # 只监听代码目录，避免 DeepAudit 拉代码写入 media/run/logs 时触发重载。
  exec "$PYTHON_BIN" -m uvicorn application.asgi:application --host "$host" --port "$port" "${UVICORN_RELOAD_ARGS[@]}"
}

run_worker() {
  ensure_redis
  check_python_deps
  check_django_settings
  ensure_no_duplicate_worker || exit 0
  reset_worker_log_file
  print_log_destinations
  exec "$PYTHON_BIN" -m celery -A application worker -Q "$DEEPAUDIT_QUEUE" -n "$WORKER_NAME" --pidfile "$WORKER_PID_FILE" -l info --logfile "$WORKER_LOG_FILE"
}

run_stop() {
  cleanup_worker_pidfile
  local pid
  pid="$(read_worker_pid)"
  if [[ -z "$pid" ]]; then
    echo "DeepAudit Worker 未运行。"
    return 0
  fi
  echo "停止 DeepAudit Worker: PID=$pid NAME=$WORKER_NAME"
  kill "$pid" >/dev/null 2>&1 || true
  for _ in {1..10}; do
    if ! worker_process_alive "$pid"; then
      rm -f "$WORKER_PID_FILE"
      echo "DeepAudit Worker 已停止。"
      return 0
    fi
    sleep 1
  done
  echo "Worker 未在预期时间内退出，尝试强制结束 PID=$pid"
  kill -9 "$pid" >/dev/null 2>&1 || true
  rm -f "$WORKER_PID_FILE"
}

run_status() {
  cleanup_worker_pidfile
  local pid
  pid="$(read_worker_pid)"
  if [[ -n "$pid" ]] && worker_process_alive "$pid"; then
    echo "DeepAudit Worker 运行中: PID=$pid NAME=$WORKER_NAME QUEUE=$DEEPAUDIT_QUEUE"
    print_log_destinations
    return 0
  fi
  echo "DeepAudit Worker 未运行。"
}

run_restart() {
  run_stop
  run_background_worker
}

run_background_worker() {
  ensure_redis
  check_python_deps
  check_django_settings
  ensure_no_duplicate_worker || return 0
  reset_worker_log_file
  print_log_destinations
  "$PYTHON_BIN" -m celery -A application worker -Q "$DEEPAUDIT_QUEUE" -n "$WORKER_NAME" --pidfile "$WORKER_PID_FILE" -l info --logfile "$WORKER_LOG_FILE" >/dev/null 2>&1 < /dev/null &
  local celery_pid=$!
  printf 'DeepAudit Celery Worker 已启动，PID=%s，NAME=%s\n' "$celery_pid" "$WORKER_NAME"
}

run_server() {
  ensure_redis
  check_python_deps
  check_django_settings
  start_uvicorn_server
}

run_all() {
  ensure_redis
  check_python_deps
  check_django_settings

  celery_pid=""
  cleanup() {
    if [[ -n "${celery_pid:-}" ]]; then
      kill "$celery_pid" >/dev/null 2>&1 || true
    fi
  }

  ensure_no_duplicate_worker || exit 0
  reset_worker_log_file
  print_log_destinations
  "$PYTHON_BIN" -m celery -A application worker -Q "$DEEPAUDIT_QUEUE" -n "$WORKER_NAME" --pidfile "$WORKER_PID_FILE" -l info --logfile "$WORKER_LOG_FILE" >/dev/null 2>&1 < /dev/null &
  celery_pid=$!
  printf 'DeepAudit Celery Worker 已启动，PID=%s，NAME=%s\n' "$celery_pid" "$WORKER_NAME"
  trap cleanup EXIT INT TERM

  start_uvicorn_server
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
  stop)
    run_stop
    ;;
  restart)
    run_restart
    ;;
  status)
    run_status
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
