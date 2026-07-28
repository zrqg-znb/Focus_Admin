#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
ZQ_ENV="${ZQ_ENV:-dev}"
ENABLE_SCHEDULER="${ENABLE_SCHEDULER:-false}"
UVICORN_HOST="${UVICORN_HOST:-127.0.0.1}"
UVICORN_PORT="${UVICORN_PORT:-8001}"
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"
DEEPAUDIT_QUEUE="${DEEPAUDIT_QUEUE:-deepaudit}"
SKILL_OPTIMIZER_QUEUE="${SKILL_OPTIMIZER_QUEUE:-skill_optimizer}"
CELERY_WORKER_QUEUES="${CELERY_WORKER_QUEUES:-${DEEPAUDIT_QUEUE},${SKILL_OPTIMIZER_QUEUE}}"

HOST_TAG="$(hostname -s 2>/dev/null || hostname || echo local)"
HOST_TAG="${HOST_TAG//[^A-Za-z0-9._-]/-}"

RUN_DIR="$ROOT_DIR/run/ip-http"
LOG_DIR="$ROOT_DIR/logs/ip-http"
mkdir -p "$RUN_DIR" "$LOG_DIR"

BACKEND_PID_FILE="$RUN_DIR/uvicorn.pid"
DEFAULT_WORKER_PID_FILE="$RUN_DIR/celery-default.pid"
DEEPAUDIT_WORKER_PID_FILE="$RUN_DIR/celery-deepaudit.pid"
SCHEDULER_PID_FILE="$RUN_DIR/scheduler.pid"

BACKEND_LOG_FILE="$LOG_DIR/uvicorn.log"
DEFAULT_WORKER_LOG_FILE="$LOG_DIR/celery-default.log"
DEEPAUDIT_WORKER_LOG_FILE="$LOG_DIR/celery-deepaudit.log"
SCHEDULER_LOG_FILE="$LOG_DIR/scheduler.log"

usage() {
  cat <<'EOF'
用法:
  bash scripts/start-ip-http.sh prepare
  bash scripts/start-ip-http.sh start-backend
  bash scripts/start-ip-http.sh start-workers
  bash scripts/start-ip-http.sh start-scheduler
  bash scripts/start-ip-http.sh start-all
  bash scripts/start-ip-http.sh stop
  bash scripts/start-ip-http.sh status

默认环境变量:
  PYTHON_BIN=python3
  ZQ_ENV=dev
  ENABLE_SCHEDULER=false
  UVICORN_HOST=127.0.0.1
  UVICORN_PORT=8001
  UVICORN_WORKERS=1
  DEEPAUDIT_QUEUE=deepaudit
  SKILL_OPTIMIZER_QUEUE=skill_optimizer
  CELERY_WORKER_QUEUES=deepaudit,skill_optimizer
EOF
}

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -d '[:space:]' <"$pid_file"
  fi
}

is_alive() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

run_nohup() {
  local pid_file="$1"
  local log_file="$2"
  shift 2

  local pid
  pid="$(read_pid "$pid_file")"
  if is_alive "$pid"; then
    echo "已在运行: PID=$pid"
    return 0
  fi

  nohup "$@" >"$log_file" 2>&1 &
  echo $! >"$pid_file"
  echo "已启动: PID=$(cat "$pid_file") LOG=$log_file"
}

stop_one() {
  local label="$1"
  local pid_file="$2"
  local pid
  pid="$(read_pid "$pid_file")"

  if ! is_alive "$pid"; then
    rm -f "$pid_file"
    echo "$label: 未运行"
    return 0
  fi

  kill "$pid" >/dev/null 2>&1 || true
  sleep 1
  if is_alive "$pid"; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$pid_file"
  echo "$label: 已停止"
}

status_one() {
  local label="$1"
  local pid_file="$2"
  local pid
  pid="$(read_pid "$pid_file")"
  if is_alive "$pid"; then
    echo "$label: 运行中 PID=$pid"
  else
    echo "$label: 未运行"
  fi
}

prepare_backend() {
  echo "正在执行 collectstatic / init_deepaudit ..."
  env ZQ_ENV="$ZQ_ENV" ENABLE_SCHEDULER="$ENABLE_SCHEDULER" \
    "$PYTHON_BIN" manage.py collectstatic --noinput
  env ZQ_ENV="$ZQ_ENV" ENABLE_SCHEDULER="$ENABLE_SCHEDULER" \
    "$PYTHON_BIN" manage.py init_deepaudit
}

start_backend() {
  run_nohup \
    "$BACKEND_PID_FILE" \
    "$BACKEND_LOG_FILE" \
    env ZQ_ENV="$ZQ_ENV" ENABLE_SCHEDULER="$ENABLE_SCHEDULER" \
    "$PYTHON_BIN" -m uvicorn application.asgi:application \
    --host "$UVICORN_HOST" \
    --port "$UVICORN_PORT" \
    --workers "$UVICORN_WORKERS"
}

start_default_worker() {
  run_nohup \
    "$DEFAULT_WORKER_PID_FILE" \
    "$DEFAULT_WORKER_LOG_FILE" \
    env ZQ_ENV="$ZQ_ENV" ENABLE_SCHEDULER="$ENABLE_SCHEDULER" \
    "$PYTHON_BIN" -m celery -A application worker \
    -Q celery \
    -n "focus-default@${HOST_TAG}" \
    -l info \
    --concurrency=2 \
    --max-tasks-per-child=5
}

start_deepaudit_worker() {
  echo "启动 DeepAudit 与 AI 辅助工具共用 Worker: QUEUES=$CELERY_WORKER_QUEUES"
  run_nohup \
    "$DEEPAUDIT_WORKER_PID_FILE" \
    "$DEEPAUDIT_WORKER_LOG_FILE" \
    env ZQ_ENV="$ZQ_ENV" ENABLE_SCHEDULER="$ENABLE_SCHEDULER" DEEPAUDIT_QUEUE="$DEEPAUDIT_QUEUE" SKILL_OPTIMIZER_QUEUE="$SKILL_OPTIMIZER_QUEUE" \
    "$PYTHON_BIN" -m celery -A application worker \
    -Q "$CELERY_WORKER_QUEUES" \
    -n "focus-deepaudit@${HOST_TAG}" \
    -l info \
    --concurrency=2 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=5
}

start_scheduler() {
  run_nohup \
    "$SCHEDULER_PID_FILE" \
    "$SCHEDULER_LOG_FILE" \
    env ZQ_ENV="$ZQ_ENV" ENABLE_SCHEDULER="$ENABLE_SCHEDULER" \
    "$PYTHON_BIN" start_scheduler.py
}

stop_all() {
  stop_one "backend" "$BACKEND_PID_FILE"
  stop_one "default worker" "$DEFAULT_WORKER_PID_FILE"
  stop_one "deepaudit / agent-tools worker" "$DEEPAUDIT_WORKER_PID_FILE"
  stop_one "scheduler" "$SCHEDULER_PID_FILE"
}

status_all() {
  status_one "backend" "$BACKEND_PID_FILE"
  status_one "default worker" "$DEFAULT_WORKER_PID_FILE"
  status_one "deepaudit / agent-tools worker" "$DEEPAUDIT_WORKER_PID_FILE"
  status_one "scheduler" "$SCHEDULER_PID_FILE"
}

cmd="${1:-}"
case "$cmd" in
  prepare)
    prepare_backend
    ;;
  start-backend)
    start_backend
    ;;
  start-workers)
    start_default_worker
    start_deepaudit_worker
    ;;
  start-scheduler)
    start_scheduler
    ;;
  start-all)
    start_backend
    start_default_worker
    start_deepaudit_worker
    start_scheduler
    ;;
  stop)
    stop_all
    ;;
  status)
    status_all
    ;;
  *)
    usage
    exit 1
    ;;
esac
