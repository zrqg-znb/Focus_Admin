import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from .base import BaseParser


class ValgrindParser(BaseParser):
    _PID_PREFIX = re.compile(r"^\s*==\d+==\s?(?P<content>.*)$")
    _FRAME = re.compile(
        r"^(?:at|by)\s+0x[0-9a-fA-F]+:\s*(?P<function>.+?)\s+\((?P<location>.+)\)$",
    )
    _FILE_LINE = re.compile(r"^(?P<file>.+?):(?P<line>\d+)(?::\d+)?$")

    _START_PATTERNS = [
        re.compile(r"^Invalid (read|write|free|jump|alignment)", re.IGNORECASE),
        re.compile(r"^Mismatched free", re.IGNORECASE),
        re.compile(r"^Conditional jump or move depends on uninitialised value", re.IGNORECASE),
        re.compile(r"^Use of uninitialised value", re.IGNORECASE),
        re.compile(r"^Syscall param .* uninitialised", re.IGNORECASE),
        re.compile(
            r"^\d+\s+bytes in\s+\d+\s+blocks are\s+(definitely|indirectly|possibly)\s+lost in loss record",
            re.IGNORECASE,
        ),
        re.compile(r"^Possible data race during", re.IGNORECASE),
        re.compile(r"^Lock order .* violated", re.IGNORECASE),
    ]

    _IGNORE_PREFIXES = (
        "Memcheck,",
        "Copyright",
        "Using Valgrind-",
        "Command:",
        "Parent PID:",
        "HEAP SUMMARY:",
        "LEAK SUMMARY:",
        "ERROR SUMMARY:",
        "FILE DESCRIPTORS:",
        "For counts of detected and suppressed errors, rerun with:",
        "Search for errors in the above file descriptors with:",
    )

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        lower = file_path.lower()
        if lower.endswith(".xml"):
            return self._parse_xml(file_path)
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
            results.append(
                {
                    "file_path": self._as_text(item.get("file_path")) or "unknown",
                    "line_number": self._as_int(item.get("line_number"), 0),
                    "defect_type": self._as_text(item.get("defect_type")) or "valgrind",
                    "severity": self._normalize_severity(item.get("severity")),
                    "description": self._as_text(item.get("description")) or "Valgrind finding",
                    "help_info": self._as_text(item.get("help_info")) or "",
                    "code_snippet": self._as_text(item.get("code_snippet")) or "",
                }
            )
        return results

    def _parse_xml(self, file_path: str) -> List[Dict[str, Any]]:
        tree = ET.parse(file_path)
        root = tree.getroot()

        results: List[Dict[str, Any]] = []
        for error in root.findall(".//error"):
            kind = (error.findtext("kind") or "").strip()
            xwhat = error.find("xwhat")
            description = ""
            if xwhat is not None:
                description = (
                    (xwhat.findtext("text") or "").strip()
                    or (xwhat.findtext("what") or "").strip()
                )
            if not description:
                description = (error.findtext("what") or "").strip() or "Valgrind finding"

            stack_lines: List[str] = []
            file_path_value = "unknown"
            line_number = 0
            frames = error.findall(".//stack/frame")
            for frame in frames:
                frame_line = self._frame_to_text(frame)
                if frame_line:
                    stack_lines.append(frame_line)
                candidate_file, candidate_line = self._frame_to_location(frame)
                if candidate_file and candidate_file != "unknown":
                    file_path_value = candidate_file
                    line_number = candidate_line
                    break

            results.append(
                {
                    "file_path": file_path_value,
                    "line_number": line_number,
                    "defect_type": self._infer_defect_type(kind or description),
                    "severity": self._map_severity(kind or description),
                    "description": description,
                    "help_info": " | ".join(stack_lines[:3]),
                    "code_snippet": "",
                }
            )
        return results

    def _parse_text(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [self._normalize_line(raw) for raw in f]

        findings: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None

        for normalized in lines:
            line = normalized.strip()
            if self._should_skip(line):
                continue

            if self._is_start_line(line):
                if current:
                    findings.append(current)
                current = {
                    "header": line,
                    "frames": [],
                    "details": [],
                }
                continue

            if current is None:
                continue

            frame = self._parse_frame(line)
            if frame:
                current["frames"].append(frame)
                continue

            if not self._is_noise_line(line):
                current["details"].append(line)

        if current:
            findings.append(current)

        results: List[Dict[str, Any]] = []
        for finding in findings:
            header = finding["header"]
            frames = finding["frames"]
            details = finding["details"]
            file_path_value, line_number = self._pick_primary_location(frames)

            stack_preview = [frame["text"] for frame in frames[:3]]
            if details:
                stack_preview = details[:1] + stack_preview

            results.append(
                {
                    "file_path": file_path_value,
                    "line_number": line_number,
                    "defect_type": self._infer_defect_type(header),
                    "severity": self._map_severity(header),
                    "description": header,
                    "help_info": " | ".join(stack_preview),
                    "code_snippet": "",
                }
            )
        return results

    def _normalize_line(self, raw_line: str) -> str:
        stripped = raw_line.rstrip("\n")
        matched = self._PID_PREFIX.match(stripped)
        if matched:
            return matched.group("content").strip()
        return stripped.strip()

    def _should_skip(self, line: str) -> bool:
        if not line:
            return True
        return any(line.startswith(prefix) for prefix in self._IGNORE_PREFIXES)

    def _is_start_line(self, line: str) -> bool:
        return any(pattern.search(line) for pattern in self._START_PATTERNS)

    def _is_noise_line(self, line: str) -> bool:
        prefixes = (
            "Address ",
            "Block was alloc'd",
            "Uninitialised value was created",
            "Thread ",
            "Process terminating",
            "at 0x",
            "by 0x",
        )
        return any(line.startswith(prefix) for prefix in prefixes)

    def _parse_frame(self, line: str) -> Optional[Dict[str, Any]]:
        matched = self._FRAME.match(line)
        if not matched:
            return None

        function_name = matched.group("function").strip()
        location = matched.group("location").strip()

        file_path_value = "unknown"
        line_number = 0
        location_match = self._FILE_LINE.match(location)
        if location_match:
            file_path_value = location_match.group("file")
            line_number = self._as_int(location_match.group("line"), 0)

        return {
            "function": function_name,
            "file_path": file_path_value,
            "line_number": line_number,
            "text": f"{function_name} ({location})",
        }

    def _pick_primary_location(self, frames: List[Dict[str, Any]]) -> tuple[str, int]:
        for frame in frames:
            file_path_value = frame.get("file_path") or "unknown"
            line_number = self._as_int(frame.get("line_number"), 0)
            if (
                file_path_value != "unknown"
                and "vg_replace" not in file_path_value
                and "valgrind" not in file_path_value.lower()
            ):
                return file_path_value, line_number

        if frames:
            first = frames[0]
            return (
                self._as_text(first.get("file_path")) or "unknown",
                self._as_int(first.get("line_number"), 0),
            )

        return "unknown", 0

    def _infer_defect_type(self, text: str) -> str:
        normalized = (text or "").strip().lower()
        if "invalid read" in normalized:
            return "invalid_read"
        if "invalid write" in normalized:
            return "invalid_write"
        if "mismatched free" in normalized:
            return "mismatched_free"
        if "invalid free" in normalized:
            return "invalid_free"
        if "uninitialised value" in normalized:
            return "uninitialised_value"
        if "definitely lost" in normalized:
            return "definitely_lost"
        if "indirectly lost" in normalized:
            return "indirectly_lost"
        if "possibly lost" in normalized:
            return "possibly_lost"
        if "data race" in normalized:
            return "data_race"
        return "valgrind"

    def _map_severity(self, text: str) -> str:
        normalized = (text or "").strip().lower()
        if any(flag in normalized for flag in ("invalid read", "invalid write", "invalid free", "mismatched free")):
            return "High"
        if any(flag in normalized for flag in ("definitely lost", "data race", "lock order")):
            return "High"
        if any(flag in normalized for flag in ("possibly lost", "indirectly lost", "uninitialised", "syscall param")):
            return "Medium"
        return "Low"

    def _normalize_severity(self, value: Any) -> str:
        normalized = self._as_text(value) or ""
        lowered = normalized.lower()
        if lowered in {"high", "medium", "low"}:
            return normalized.capitalize()
        return self._map_severity(normalized)

    def _frame_to_text(self, frame: ET.Element) -> str:
        function_name = (frame.findtext("fn") or "").strip()
        file_name = (frame.findtext("file") or "").strip()
        line_number = self._as_int(frame.findtext("line"), 0)
        obj = (frame.findtext("obj") or "").strip()
        if function_name and file_name and line_number:
            return f"{function_name} ({file_name}:{line_number})"
        if function_name and obj:
            return f"{function_name} ({obj})"
        if file_name and line_number:
            return f"{file_name}:{line_number}"
        return function_name or file_name or obj

    def _frame_to_location(self, frame: ET.Element) -> tuple[str, int]:
        file_name = (frame.findtext("file") or "").strip()
        line_number = self._as_int(frame.findtext("line"), 0)
        if file_name:
            return file_name, line_number
        return "unknown", 0

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
