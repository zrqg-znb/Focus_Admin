import json
import re
from typing import Any, Dict, List, Optional

from .base import BaseParser


class TSanParser(BaseParser):
    _ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    _WARNING = re.compile(r"WARNING:\s+ThreadSanitizer:\s*(?P<kind>.+)$")
    _SUMMARY = re.compile(r"SUMMARY:\s+ThreadSanitizer:\s*(?P<kind>.+)$")
    _FRAME_LINE = re.compile(r"^\s*#\d+\s+(?P<frame>.+)$")
    _PATH_LINE = re.compile(
        r"(?P<file>(?:[A-Za-z]:)?[^\s:()]+(?:/[^\s:()]+|\\[^\s:()]+)*)"
        r":(?P<line>\d+)(?::\d+)?",
    )
    _ACCESS_LINE = re.compile(
        r"^\s*(?:Previous\s+)?(?:Atomic\s+)?(?:Write|Read)\b",
        re.IGNORECASE,
    )
    _INTERNAL_PATH_MARKERS = (
        "tsan_interceptors",
        "sanitizer_common",
        "libclang_rt",
        "compiler-rt",
        "__tsan",
    )

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        lower = file_path.lower()
        if lower.endswith(".json"):
            return self._parse_json(file_path)
        return self._parse_text(file_path)

    def _parse_json(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if isinstance(payload, dict):
            for key in ("items", "results", "defects", "findings"):
                value = payload.get(key)
                if isinstance(value, list):
                    payload = value
                    break

        if not isinstance(payload, list):
            return []

        results: List[Dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue

            file_path_value = (
                self._as_text(item.get("file_path"))
                or self._as_text(item.get("file"))
                or self._as_text(item.get("path"))
                or "unknown"
            )
            line_number = self._as_int(
                item.get("line_number", item.get("line")),
                0,
            )

            kind = (
                self._as_text(item.get("defect_type"))
                or self._as_text(item.get("type"))
                or self._as_text(item.get("kind"))
                or "tsan",
            )
            description = (
                self._as_text(item.get("description"))
                or self._as_text(item.get("message"))
                or self._as_text(item.get("msg"))
                or f"WARNING: ThreadSanitizer: {kind}"
            )

            results.append(
                {
                    "file_path": file_path_value,
                    "line_number": line_number,
                    "defect_type": self._normalize_defect_type(kind),
                    "severity": "High",
                    "description": description,
                    "help_info": (
                        self._as_text(item.get("help_info"))
                        or self._as_text(item.get("help"))
                        or self._as_text(item.get("details"))
                        or ""
                    ),
                    "code_snippet": (
                        self._as_text(item.get("code_snippet"))
                        or self._as_text(item.get("code"))
                        or ""
                    ),
                }
            )
        return results

    def _parse_text(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [self._clean_line(raw) for raw in f]

        blocks: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None

        for line in lines:
            warning = self._parse_warning(line)
            if warning:
                if current:
                    blocks.append(current)
                current = {
                    "description": warning["description"],
                    "kind": warning["kind"],
                    "lines": [line],
                }
                continue

            if current is not None:
                current["lines"].append(line)

        if current:
            blocks.append(current)

        results: List[Dict[str, Any]] = []
        for block in blocks:
            lines_in_block: List[str] = block["lines"]
            frames = self._collect_frames(lines_in_block)
            file_path_value, line_number = self._pick_primary_location(frames)

            if file_path_value == "unknown":
                summary_file, summary_line = self._pick_summary_location(lines_in_block)
                if summary_file != "unknown":
                    file_path_value, line_number = summary_file, summary_line

            defect_kind = block.get("kind") or self._pick_summary_kind(lines_in_block) or "tsan"
            help_info = self._build_help_info(lines_in_block, frames)

            results.append(
                {
                    "file_path": file_path_value,
                    "line_number": line_number,
                    "defect_type": self._normalize_defect_type(defect_kind),
                    "severity": "High",
                    "description": block.get("description") or "WARNING: ThreadSanitizer",
                    "help_info": help_info,
                    "code_snippet": "",
                }
            )

        return results

    def _clean_line(self, raw_line: str) -> str:
        without_ansi = self._ANSI_ESCAPE.sub("", raw_line.rstrip("\n"))
        return without_ansi.strip()

    def _parse_warning(self, line: str) -> Optional[Dict[str, str]]:
        matched = self._WARNING.search(line)
        if not matched:
            return None

        kind = matched.group("kind").strip()
        kind = re.sub(r"\(pid=\d+\)\s*$", "", kind).strip()
        return {
            "description": line.strip(),
            "kind": kind,
        }

    def _collect_frames(self, lines: List[str]) -> List[Dict[str, Any]]:
        frames: List[Dict[str, Any]] = []
        for line in lines:
            matched = self._FRAME_LINE.match(line)
            if not matched:
                continue
            text = matched.group("frame").strip()
            file_path_value, line_number = self._extract_location(text)
            frames.append(
                {
                    "text": text,
                    "file_path": file_path_value,
                    "line_number": line_number,
                }
            )
        return frames

    def _extract_location(self, text: str) -> tuple[str, int]:
        for matched in self._PATH_LINE.finditer(text):
            file_path_value = matched.group("file").strip()
            line_number = self._as_int(matched.group("line"), 0)
            if file_path_value:
                return file_path_value, line_number
        return "unknown", 0

    def _pick_primary_location(self, frames: List[Dict[str, Any]]) -> tuple[str, int]:
        for frame in frames:
            file_path_value = self._as_text(frame.get("file_path")) or "unknown"
            line_number = self._as_int(frame.get("line_number"), 0)
            if file_path_value != "unknown" and not self._is_internal_path(file_path_value):
                return file_path_value, line_number
        return "unknown", 0

    def _pick_summary_location(self, lines: List[str]) -> tuple[str, int]:
        fallback: Optional[tuple[str, int]] = None
        for line in lines:
            if "SUMMARY: ThreadSanitizer:" not in line:
                continue
            file_path_value, line_number = self._extract_location(line)
            if file_path_value != "unknown":
                if not self._is_internal_path(file_path_value):
                    return file_path_value, line_number
                if fallback is None:
                    fallback = (file_path_value, line_number)
        if fallback is not None:
            return fallback
        return "unknown", 0

    def _pick_summary_kind(self, lines: List[str]) -> str:
        for line in lines:
            matched = self._SUMMARY.search(line)
            if not matched:
                continue
            kind = matched.group("kind").strip()
            kind = re.sub(r"\s+in\s+.+$", "", kind).strip()
            kind = re.sub(r"\s+at\s+.+$", "", kind).strip()
            return kind
        return ""

    def _build_help_info(self, lines: List[str], frames: List[Dict[str, Any]]) -> str:
        access_lines: List[str] = []
        for line in lines:
            if self._ACCESS_LINE.match(line):
                access_lines.append(line.strip())
            if len(access_lines) >= 3:
                break

        stack_lines = [
            frame["text"]
            for frame in frames
            if frame.get("text")
            and frame.get("file_path")
            and frame.get("file_path") != "unknown"
            and not self._is_internal_path(self._as_text(frame.get("file_path")))
        ]
        if not stack_lines:
            stack_lines = [frame["text"] for frame in frames if frame.get("text")]

        merged = access_lines + stack_lines[:3]
        return " | ".join(merged)

    def _normalize_defect_type(self, raw_kind: str) -> str:
        kind = self._as_text(raw_kind)
        if not kind:
            return "tsan"

        kind = kind.replace("WARNING: ThreadSanitizer:", "").strip()
        kind = re.sub(r"\(pid=\d+\)\s*$", "", kind).strip()
        kind = re.sub(r"\(.*?\)", "", kind).strip()
        kind = kind.lower()
        kind = re.sub(r"[^a-z0-9]+", "_", kind).strip("_")
        return kind or "tsan"

    def _is_internal_path(self, file_path: str) -> bool:
        lowered = (file_path or "").lower()
        return any(marker in lowered for marker in self._INTERNAL_PATH_MARKERS)

    def _as_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _as_int(self, value: Any, default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return default
