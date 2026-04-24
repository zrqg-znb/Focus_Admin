#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_MODULE="${APP_MODULE:-application.asgi:application}"

RUN_DIR="$ROOT_DIR/run"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$RUN_DIR/focus.pid"
LOG_FILE="$LOG_DIR/app.log"

mkdir -p "$RUN_DIR" "$LOG_DIR"

usage() {
  cat <<'EOF'
用法:
  bash scripts/start-focus-simple.sh dev
  bash scripts/start-focus-simple.sh prod
  bash scripts/start-focus-simple.sh stop
  bash scripts/start-focus-simple.sh status

说明:
  - dev: 前台启动（自动重载）
  - prod: 后台启动（不建议开启自动重载）
  - DeepAudit 与 Focus 同属一个 Django ASGI 进程，启动本服务即一并加载
EOF
}

read_pid() {
  if [[ -f "$PID_FILE" ]]; then
    tr -d '[:space:]' <"$PID_FILE"
  fi
}

is_alive() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

start_dev() {
  echo "[dev] ${PYTHON_BIN} -m uvicorn ${APP_MODULE} --reload --host ${HOST} --port ${PORT}"
  exec "$PYTHON_BIN" -m uvicorn "$APP_MODULE" --reload --host "$HOST" --port "$PORT"
}

start_prod() {
  local pid
  pid="$(read_pid)"
  if is_alive "$pid"; then
    echo "Focus 已在运行, PID=$pid"
    exit 0
  fi

  # 生产建议去掉 --reload，避免额外资源开销和不稳定
  nohup "$PYTHON_BIN" -m uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  echo "Focus 已启动, PID=$(cat "$PID_FILE"), LOG=$LOG_FILE"
}

stop_prod() {
  local pid
  pid="$(read_pid)"
  if ! is_alive "$pid"; then
    rm -f "$PID_FILE"
    echo "Focus 未运行"
    exit 0
  fi

  kill "$pid" >/dev/null 2>&1 || true
  sleep 1
  if is_alive "$pid"; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$PID_FILE"
  echo "Focus 已停止"
}

status_prod() {
  local pid
  pid="$(read_pid)"
  if is_alive "$pid"; then
    echo "Focus 运行中, PID=$pid"
  else
    echo "Focus 未运行"
  fi
}

cmd="${1:-}"
case "$cmd" in
  dev)
    start_dev
    ;;
  prod)
    start_prod
    ;;
  stop)
    stop_prod
    ;;
  status)
    status_prod
    ;;
  *)
    usage
    exit 1
    ;;
esac
