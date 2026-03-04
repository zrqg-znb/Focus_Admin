#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from apps.code_scan.parsers.tsan_parser import TSanParser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="流水线: 解析 tsan 日志并上传解析结果")
    parser.add_argument("--log", required=True, help="tsan 原始日志路径")
    parser.add_argument("--project-key", required=True, help="代码扫描项目 project_key")
    parser.add_argument("--api-base", required=True, help="服务地址，如 http://host:8001")
    parser.add_argument("--tool-name", default="tsan", help="上传工具名，默认 tsan")
    parser.add_argument("--output", help="解析后 JSON 输出路径，不传则自动生成")
    parser.add_argument(
        "--upload-mode",
        choices=["auto", "direct", "chunk"],
        default="auto",
        help="上传模式：auto/direct/chunk",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024 * 1024,
        help="分片大小（字符数），默认 1048576",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP 超时时间（秒）",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="失败重试次数（不含首次）",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON 输出是否美化",
    )
    return parser.parse_args()


def build_output_path(log_path: Path, output: str | None) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    return log_path.with_suffix(log_path.suffix + ".parsed.json")


def normalize_api_base(api_base: str) -> str:
    base = api_base.strip().rstrip("/")
    if base.endswith("/api/code-scan"):
        return base
    if "/api/code-scan/" in base:
        return base.split("/api/code-scan/")[0] + "/api/code-scan"
    return base + "/api/code-scan"


def unwrap_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload and "code" in payload:
        return payload.get("data")
    return payload


def request_json(
    request_obj: Request,
    timeout: int,
    retries: int,
) -> Tuple[int, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request_obj, timeout=timeout) as response:
                status_code = response.getcode()
                raw = response.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    payload = {"raw": raw}
                return status_code, payload
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(
                f"HTTPError {error.code}: {body or error.reason}",
            )
        except URLError as error:
            last_error = RuntimeError(f"URLError: {error.reason}")
        except Exception as error:
            last_error = error

        if attempt < retries:
            time.sleep(min(1 + attempt, 3))
    raise RuntimeError(str(last_error) if last_error else "unknown request error")


def parse_tsan(log_path: Path, output_path: Path, pretty: bool) -> int:
    parser = TSanParser()
    findings = parser.parse(str(log_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    output_path.write_text(json.dumps(findings, **kwargs), encoding="utf-8")
    return len(findings)


def upload_direct(
    file_path: Path,
    project_key: str,
    tool_name: str,
    api_base: str,
    timeout: int,
    retries: int,
) -> Any:
    upload_url = f"{api_base}/upload"
    boundary = f"----codex-{uuid.uuid4().hex}"
    line = b"\r\n"

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()

    chunks = []
    for key, value in (("project_key", project_key), ("tool_name", tool_name)):
        chunks.append(f"--{boundary}".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{key}"'.encode("utf-8"),
        )
        chunks.append(b"")
        chunks.append(str(value).encode("utf-8"))

    chunks.append(f"--{boundary}".encode("utf-8"))
    chunks.append(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"'.encode("utf-8"),
    )
    chunks.append(f"Content-Type: {content_type}".encode("utf-8"))
    chunks.append(b"")
    chunks.append(file_bytes)
    chunks.append(f"--{boundary}--".encode("utf-8"))
    chunks.append(b"")

    body = line.join(chunks)
    request_obj = Request(
        upload_url,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    _, payload = request_json(request_obj, timeout=timeout, retries=retries)
    return unwrap_payload(payload)


def upload_chunk(
    file_path: Path,
    project_key: str,
    tool_name: str,
    api_base: str,
    chunk_size: int,
    timeout: int,
    retries: int,
) -> Any:
    upload_url = f"{api_base}/upload/chunk"
    content = file_path.read_text(encoding="utf-8")
    total_chunks = max(math.ceil(len(content) / chunk_size), 1)
    file_id = uuid.uuid4().hex
    file_ext = file_path.suffix.lstrip(".") or "json"

    last_payload: Any = {}
    for index in range(total_chunks):
        start = index * chunk_size
        end = start + chunk_size
        payload = {
            "project_key": project_key,
            "tool_name": tool_name,
            "chunk_index": index,
            "total_chunks": total_chunks,
            "chunk_content": content[start:end],
            "file_id": file_id,
            "file_ext": file_ext,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_obj = Request(
            upload_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        _, response_payload = request_json(request_obj, timeout=timeout, retries=retries)
        last_payload = unwrap_payload(response_payload)

    return last_payload


def main() -> int:
    args = parse_args()
    log_path = Path(args.log).expanduser().resolve()
    if not log_path.exists():
        print(f"[pipeline-tsan] 日志文件不存在: {log_path}", file=sys.stderr)
        return 1

    output_path = build_output_path(log_path, args.output)
    findings_count = parse_tsan(log_path, output_path, args.pretty)

    api_base = normalize_api_base(args.api_base)
    file_size = output_path.stat().st_size
    mode = args.upload_mode
    if mode == "auto":
        mode = "chunk" if file_size > args.chunk_size else "direct"

    if mode == "direct":
        upload_result = upload_direct(
            output_path,
            args.project_key,
            args.tool_name,
            api_base,
            args.timeout,
            args.retries,
        )
    else:
        upload_result = upload_chunk(
            output_path,
            args.project_key,
            args.tool_name,
            api_base,
            args.chunk_size,
            args.timeout,
            args.retries,
        )

    print(f"[pipeline-tsan] log: {log_path}")
    print(f"[pipeline-tsan] parsed_json: {output_path}")
    print(f"[pipeline-tsan] findings: {findings_count}")
    print(f"[pipeline-tsan] upload_mode: {mode}")
    print(
        "[pipeline-tsan] upload_result: "
        f"{json.dumps(upload_result, ensure_ascii=False)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
