import json
import re
from typing import Any, Dict, List, Optional
from .base import BaseParser
 
 
class WeggliParser(BaseParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        lower = file_path.lower()
        if lower.endswith(".json"):
            return self._parse_json(file_path)
        if lower.endswith(".jsonl"):
            return self._parse_jsonl(file_path)
        return self._parse_text(file_path)
 
    def _parse_json(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = self._extract_items(data)
        return [self._normalize_item(x) for x in items if isinstance(x, dict)]
 
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
        return [self._normalize_item(x) for x in items]
 
    def _parse_text(self, file_path: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        pattern = re.compile(r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<col>\d+))?:\s*(?P<msg>.*)$")
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n")
                m = pattern.match(line)
                if not m:
                    continue
                file_p = (m.group("file") or "").strip()
                line_no = self._to_int(m.group("line"), 0)
                msg = (m.group("msg") or "").strip()
                results.append(
                    {
                        "file_path": file_p or "unknown",
                        "line_number": line_no,
                        "defect_type": "weggli",
                        "severity": "Medium",
                        "description": msg or "Weggli finding",
                        "help_info": "",
                        "code_snippet": "",
                    }
                )
        return results
 
    def _extract_items(self, data: Any) -> List[Any]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in ("results", "findings", "matches", "defects", "items"):
                v = data.get(k)
                if isinstance(v, list):
                    return v
        return []
 
    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self._first_str(item, ["file_path", "file", "path", "filename"]) or "unknown"
        line_number = self._extract_line(item)
        defect_type = (
            self._first_str(item, ["defect_type", "rule_id", "rule", "pattern", "query", "id", "check"])
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
                return self._to_int(item.get(key), 0)
        loc = item.get("location") or item.get("loc") or item.get("range")
        if isinstance(loc, dict):
            for key in ("line", "line_number", "start_line", "startLine"):
                if key in loc:
                    return self._to_int(loc.get(key), 0)
            start = loc.get("start")
            if isinstance(start, dict) and "line" in start:
                return self._to_int(start.get("line"), 0)
        return 0
 
    def _to_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default
 
    def _first_str(self, item: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for k in keys:
            v = item.get(k)
            if v is None:
                continue
            if isinstance(v, str):
                s = v.strip()
                if s:
                    return s
            else:
                s = str(v).strip()
                if s and s.lower() != "none":
                    return s
        return None
 
    def _map_severity(self, severity_str: Optional[str]) -> str:
        if not severity_str:
            return "Medium"
        s = severity_str.strip().lower()
        if s in {"high", "critical", "error", "danger", "p0", "p1", "1"}:
            return "High"
        if s in {"medium", "warning", "warn", "p2", "2"}:
            return "Medium"
        if s in {"low", "info", "informational", "style", "p3", "p4", "3", "4"}:
            return "Low"
        return "Medium"

