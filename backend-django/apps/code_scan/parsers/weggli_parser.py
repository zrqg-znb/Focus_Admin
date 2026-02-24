import json
import re
from typing import Any, Dict, List, Optional

from .base import BaseParser
from .tabular_utils import (
    as_int,
    as_text,
    build_header_index,
    find_col_index,
    load_rows_by_extension,
    value_by_index,
)


class WeggliParser(BaseParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        lower = file_path.lower()
        if lower.endswith(".xlsx"):
            return self._parse_xlsx(file_path)
        if lower.endswith(".json"):
            return self._parse_json(file_path)
        if lower.endswith(".jsonl"):
            return self._parse_jsonl(file_path)
        return self._parse_text(file_path)

    def _parse_xlsx(self, file_path: str) -> List[Dict[str, Any]]:
        header, rows = load_rows_by_extension(file_path)
        header_index = build_header_index(header)

        defect_type_idx = find_col_index(header_index, ["defect_type", "defect type", "type"])
        description_idx = find_col_index(header_index, ["description", "desc", "message", "msg", "reason"])
        path_idx = find_col_index(header_index, ["path", "file_path", "file", "filename"])
        line_idx = find_col_index(header_index, ["line_number", "line", "line no", "lineno"])
        code_snippet_idx = find_col_index(
            header_index,
            ["code_snippet", "code snippet", "snippet", "code", "source"],
        )

        results: List[Dict[str, Any]] = []
        for row in rows:
            file_path_value = as_text(value_by_index(row, path_idx)) or "unknown"
            line_number = as_int(value_by_index(row, line_idx), 0)
            defect_type = as_text(value_by_index(row, defect_type_idx)) or "weggli"
            description = (
                as_text(value_by_index(row, description_idx))
                or defect_type
                or "Weggli finding"
            )
            code_snippet = as_text(value_by_index(row, code_snippet_idx))
            results.append(
                {
                    "file_path": file_path_value,
                    "line_number": line_number,
                    "defect_type": defect_type,
                    "severity": "Medium",
                    "description": description,
                    "help_info": "",
                    "code_snippet": code_snippet,
                }
            )
        return results

    def _parse_json(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = self._extract_items(data)
        return [self._normalize_item(item) for item in items if isinstance(item, dict)]

    def _parse_jsonl(self, file_path: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if line in {"[", "]"}:
                    continue
                if line.endswith(","):
                    line = line[:-1].strip()
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    items.append(obj)
        return [self._normalize_item(item) for item in items]

    def _parse_text(self, file_path: str) -> List[Dict[str, Any]]:
        pattern = re.compile(
            r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<col>\d+))?:\s*(?P<msg>.*)$"
        )
        results: List[Dict[str, Any]] = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n")
                matched = pattern.match(line)
                if not matched:
                    continue
                results.append(
                    {
                        "file_path": as_text(matched.group("file")) or "unknown",
                        "line_number": as_int(matched.group("line"), 0),
                        "defect_type": "weggli",
                        "severity": "Medium",
                        "description": as_text(matched.group("msg")) or "Weggli finding",
                        "help_info": "",
                        "code_snippet": "",
                    }
                )
        return results

    def _extract_items(self, data: Any) -> List[Any]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("results", "findings", "matches", "defects", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self._first_str(item, ["file_path", "file", "path", "filename"]) or "unknown"
        line_number = self._extract_line(item)
        defect_type = (
            self._first_str(
                item,
                ["defect_type", "rule_id", "rule", "pattern", "query", "id", "check"],
            )
            or "weggli"
        )
        description = (
            self._first_str(item, ["description", "message", "msg", "title"])
            or self._first_str(item, ["match", "matched", "snippet"])
            or "Weggli finding"
        )
        code_snippet = self._first_str(item, ["code_snippet", "snippet", "code", "match", "matched"]) or ""
        help_info = self._first_str(item, ["help_info", "help", "note"]) or ""
        severity = self._map_severity(self._first_str(item, ["severity", "level", "priority"]))
        return {
            "file_path": file_path,
            "line_number": line_number,
            "defect_type": defect_type,
            "severity": severity,
            "description": description,
            "help_info": help_info,
            "code_snippet": code_snippet,
        }

    def _extract_line(self, item: Dict[str, Any]) -> int:
        for key in ("line_number", "line", "lineNumber", "start_line", "startLine"):
            if key in item:
                return as_int(item.get(key), 0)

        location = item.get("location") or item.get("loc") or item.get("range")
        if isinstance(location, dict):
            for key in ("line", "line_number", "start_line", "startLine"):
                if key in location:
                    return as_int(location.get(key), 0)
            start = location.get("start")
            if isinstance(start, dict) and "line" in start:
                return as_int(start.get("line"), 0)
        return 0

    def _first_str(self, item: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for key in keys:
            value = item.get(key)
            text = as_text(value)
            if text and text.lower() != "none":
                return text
        return None

    def _map_severity(self, severity: Optional[str]) -> str:
        if not severity:
            return "Medium"
        normalized = severity.strip().lower()
        if normalized in {"high", "critical", "error", "danger", "p0", "p1", "1"}:
            return "High"
        if normalized in {"medium", "warning", "warn", "p2", "2"}:
            return "Medium"
        if normalized in {"low", "info", "informational", "style", "p3", "p4", "3", "4"}:
            return "Low"
        return "Medium"
