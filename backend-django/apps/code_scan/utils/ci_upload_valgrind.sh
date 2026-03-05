#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

CODE_SCAN_API_BASE="${CODE_SCAN_API_BASE:-}"
CODE_SCAN_PROJECT_KEY="${CODE_SCAN_PROJECT_KEY:-}"
VALGRIND_LOG_PATH="${VALGRIND_LOG_PATH:-./artifacts/valgrind.log}"
VALGRIND_SUB_MODULE="${VALGRIND_SUB_MODULE:-}"
VALGRIND_TOOL_NAME="${VALGRIND_TOOL_NAME:-valgrind}"
VALGRIND_UPLOAD_MODE="${VALGRIND_UPLOAD_MODE:-auto}"
VALGRIND_CHUNK_SIZE="${VALGRIND_CHUNK_SIZE:-1048576}"
VALGRIND_TIMEOUT="${VALGRIND_TIMEOUT:-60}"
VALGRIND_RETRIES="${VALGRIND_RETRIES:-2}"
VALGRIND_PRETTY="${VALGRIND_PRETTY:-false}"

if [[ -z "${CODE_SCAN_API_BASE}" ]]; then
  echo "[ci-valgrind] 缺少 CODE_SCAN_API_BASE" >&2
  exit 1
fi

if [[ -z "${CODE_SCAN_PROJECT_KEY}" ]]; then
  echo "[ci-valgrind] 缺少 CODE_SCAN_PROJECT_KEY" >&2
  exit 1
fi

if [[ -z "${VALGRIND_SUB_MODULE}" ]]; then
  echo "[ci-valgrind] 缺少 VALGRIND_SUB_MODULE（必填）" >&2
  exit 1
fi

if [[ ! -f "${VALGRIND_LOG_PATH}" ]]; then
  echo "[ci-valgrind] 日志文件不存在: ${VALGRIND_LOG_PATH}" >&2
  exit 1
fi

cmd=(
  "${PYTHON_BIN}"
  "${SCRIPT_DIR}/pipeline_valgrind_parse_and_upload.py"
  --log "${VALGRIND_LOG_PATH}"
  --project-key "${CODE_SCAN_PROJECT_KEY}"
  --api-base "${CODE_SCAN_API_BASE}"
  --tool-name "${VALGRIND_TOOL_NAME}"
  --sub-module "${VALGRIND_SUB_MODULE}"
  --upload-mode "${VALGRIND_UPLOAD_MODE}"
  --chunk-size "${VALGRIND_CHUNK_SIZE}"
  --timeout "${VALGRIND_TIMEOUT}"
  --retries "${VALGRIND_RETRIES}"
)

if [[ "${VALGRIND_PRETTY}" == "1" || "${VALGRIND_PRETTY,,}" == "true" ]]; then
  cmd+=(--pretty)
fi

"${cmd[@]}"
