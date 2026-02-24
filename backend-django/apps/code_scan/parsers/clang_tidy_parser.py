import re
from typing import Any, Dict, List

from .base import BaseParser
from .tabular_utils import (
    as_int,
    as_text,
    build_header_index,
    find_col_index,
    load_rows_by_extension,
    value_by_index,
)


class ClangTidyParser(BaseParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        header, rows = load_rows_by_extension(file_path)
        header_index = build_header_index(header)

        path_idx = find_col_index(header_index, ["path", "file", "file_path"])
        line_idx = find_col_index(header_index, ["line", "line_number"])
        column_idx = find_col_index(header_index, ["column", "col"])
        severity_idx = find_col_index(header_index, ["severity", "level"])
        msg_idx = find_col_index(header_index, ["msg", "message", "description", "reason"])
        code_block_idx = find_col_index(header_index, ["code_block", "codeblock", "code_snippet", "code"])

        results: List[Dict[str, Any]] = []
        for row in rows:
            file_path_value = as_text(value_by_index(row, path_idx)) or "unknown"
            line_number = as_int(value_by_index(row, line_idx), 0)
            column = as_int(value_by_index(row, column_idx), 0)
            severity_value = as_text(value_by_index(row, severity_idx))
            message = as_text(value_by_index(row, msg_idx))
            code_block = as_text(value_by_index(row, code_block_idx))

            defect_type = self._extract_rule_from_message(message) or "clang-tidy"
            help_info = f"Column: {column}" if column > 0 else ""

            results.append(
                {
                    "file_path": file_path_value,
                    "line_number": line_number,
                    "defect_type": defect_type,
                    "severity": self._map_severity(severity_value),
                    "description": message or "clang-tidy finding",
                    "help_info": help_info,
                    "code_snippet": code_block,
                }
            )

        return results

    def _extract_rule_from_message(self, message: str) -> str:
        if not message:
            return ""
        matched = re.search(r"\[([^\[\]]+)\]\s*$", message)
        if matched:
            return matched.group(1).strip()
        return ""

    def _map_severity(self, severity: str) -> str:
        normalized = (severity or "").strip().lower()
        if normalized in {"error", "fatal", "critical", "high"}:
            return "High"
        if normalized in {"warning", "warn", "medium"}:
            return "Medium"
        if normalized in {"note", "info", "informational", "remark", "low"}:
            return "Low"
        return "Medium"
