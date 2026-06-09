#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

CODE_SCAN_API_BASE="${CODE_SCAN_API_BASE:-}"
CODE_SCAN_PROJECT_KEY="${CODE_SCAN_PROJECT_KEY:-}"
TSAN_LOG_PATH="${TSAN_LOG_PATH:-./artifacts/tsan.log}"
TSAN_SUB_MODULE="${TSAN_SUB_MODULE:-}"
TSAN_TOOL_NAME="${TSAN_TOOL_NAME:-tsan}"
TSAN_UPLOAD_MODE="${TSAN_UPLOAD_MODE:-auto}"
TSAN_CHUNK_SIZE="${TSAN_CHUNK_SIZE:-1048576}"
TSAN_TIMEOUT="${TSAN_TIMEOUT:-60}"
TSAN_RETRIES="${TSAN_RETRIES:-2}"
TSAN_PRETTY="${TSAN_PRETTY:-false}"

if [[ -z "${CODE_SCAN_API_BASE}" ]]; then
  echo "[ci-tsan] 缺少 CODE_SCAN_API_BASE" >&2
  exit 1
fi

if [[ -z "${CODE_SCAN_PROJECT_KEY}" ]]; then
  echo "[ci-tsan] 缺少 CODE_SCAN_PROJECT_KEY" >&2
  exit 1
fi

if [[ -z "${TSAN_SUB_MODULE}" ]]; then
  echo "[ci-tsan] 缺少 TSAN_SUB_MODULE（必填）" >&2
  exit 1
fi

if [[ ! -f "${TSAN_LOG_PATH}" ]]; then
  echo "[ci-tsan] 日志文件不存在: ${TSAN_LOG_PATH}" >&2
  exit 1
fi

cmd=(
  "${PYTHON_BIN}"
  "${SCRIPT_DIR}/pipeline_tsan_parse_and_upload.py"
  --log "${TSAN_LOG_PATH}"
  --project-key "${CODE_SCAN_PROJECT_KEY}"
  --api-base "${CODE_SCAN_API_BASE}"
  --tool-name "${TSAN_TOOL_NAME}"
  --sub-module "${TSAN_SUB_MODULE}"
  --upload-mode "${TSAN_UPLOAD_MODE}"
  --chunk-size "${TSAN_CHUNK_SIZE}"
  --timeout "${TSAN_TIMEOUT}"
  --retries "${TSAN_RETRIES}"
)

if [[ "${TSAN_PRETTY}" == "1" || "${TSAN_PRETTY,,}" == "true" ]]; then
  cmd+=(--pretty)
fi

"${cmd[@]}"
