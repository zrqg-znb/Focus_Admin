#!/usr/bin/env python3
"""
ThreadSanitizer 日志解析脚本（供流水线调用）。

示例：
  python apps/code_scan/utils/parse_tsan_log.py \
    --input ./artifacts/tsan.log \
    --output ./artifacts/tsan_findings.json

  python apps/code_scan/utils/parse_tsan_log.py \
    --input ./artifacts/tsan.log \
    --format csv \
    --output ./artifacts/tsan_findings.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from apps.code_scan.parsers.tsan_parser import TSanParser


DEFAULT_COLUMNS = [
    "file_path",
    "line_number",
    "defect_type",
    "severity",
    "description",
    "help_info",
    "code_snippet",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="解析 tsan 日志为标准扫描结果")
    parser.add_argument("--input", required=True, help="tsan 原始日志路径（.log/.txt/.out/.json）")
    parser.add_argument(
        "--output",
        help="输出文件路径；不传则默认生成到输入文件同目录",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="输出格式，默认 json",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON 输出时是否格式化缩进",
    )
    return parser.parse_args()


def _default_output_path(input_path: Path, output_format: str) -> Path:
    suffix = f".parsed.{output_format}"
    return input_path.with_suffix(input_path.suffix + suffix)


def _write_json(output_path: Path, rows: List[Dict[str, Any]], pretty: bool) -> None:
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    output_path.write_text(json.dumps(rows, **kwargs), encoding="utf-8")


def _write_csv(output_path: Path, rows: List[Dict[str, Any]]) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DEFAULT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in DEFAULT_COLUMNS})


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"[tsan-parser] 输入文件不存在: {input_path}", file=sys.stderr)
        return 1

    parser = TSanParser()
    findings = parser.parse(str(input_path))

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else _default_output_path(input_path, args.format)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "csv":
        _write_csv(output_path, findings)
    else:
        _write_json(output_path, findings, args.pretty)

    print(f"[tsan-parser] 输入: {input_path}")
    print(f"[tsan-parser] 输出: {output_path}")
    print(f"[tsan-parser] 解析结果: {len(findings)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
