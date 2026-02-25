import re
from typing import Any, Dict, List, Tuple

from .base import BaseParser
from .tabular_utils import (
    as_int,
    as_text,
    build_header_index,
    find_col_index,
    join_path,
    load_rows_by_extension,
    value_by_index,
)


class CooddyParser(BaseParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        header, rows = load_rows_by_extension(file_path)
        header_index = build_header_index(header)

        path_idx = find_col_index(header_index, ["path"])
        file_idx = find_col_index(header_index, ["file", "filename"])
        function_idx = find_col_index(header_index, ["function"])
        line_idx = find_col_index(header_index, ["line", "line_number"])
        column_idx = find_col_index(header_index, ["column", "col"])
        checker_idx = find_col_index(header_index, ["checker", "check", "rule"])
        profile_idx = find_col_index(header_index, ["profile"])
        problem_type_idx = find_col_index(header_index, ["problemtype", "problem_type", "type"])
        source_idx = find_col_index(header_index, ["source", "code", "code_snippet"])
        reason_idx = find_col_index(header_index, ["reason", "description", "message", "msg"])

        results: List[Dict[str, Any]] = []
        for row in rows:
            file_path_value = join_path(
                value_by_index(row, path_idx),
                value_by_index(row, file_idx),
            ) or "unknown"
            line_number, column = self._parse_location(
                as_text(value_by_index(row, line_idx)),
                as_text(value_by_index(row, column_idx)),
            )

            checker = as_text(value_by_index(row, checker_idx))
            profile = as_text(value_by_index(row, profile_idx))
            function = as_text(value_by_index(row, function_idx))
            problem_type = as_text(value_by_index(row, problem_type_idx))
            source = as_text(value_by_index(row, source_idx))
            reason = as_text(value_by_index(row, reason_idx))

            detail_parts = []
            if function:
                detail_parts.append(f"Function: {function}")
            if checker:
                detail_parts.append(f"Checker: {checker}")
            if profile:
                detail_parts.append(f"Profile: {profile}")
            if column:
                detail_parts.append(f"Column: {column}")

            results.append(
                {
                    "file_path": file_path_value,
                    "line_number": line_number,
                    "defect_type": problem_type or checker or "cooddy",
                    "severity": self._map_severity(problem_type or checker),
                    "description": reason or source or "Cooddy finding",
                    "help_info": " | ".join(detail_parts),
                    "code_snippet": source,
                }
            )
        return results

    def _parse_location(self, line_value: str, column_value: str) -> Tuple[int, str]:
        line_number = as_int(line_value, 0)
        column_text = column_value

        if line_value:
            matched = re.search(r"(\d+)\s*[:：]\s*(\d+)", line_value)
            if matched:
                line_number = as_int(matched.group(1), line_number)
                if not column_text:
                    column_text = matched.group(2)
            elif not line_number:
                first_number = re.search(r"\d+", line_value)
                if first_number:
                    line_number = as_int(first_number.group(0), 0)

        return line_number, column_text

    def _map_severity(self, value: str) -> str:
        normalized = (value or "").strip().lower()
        if not normalized:
            return "Medium"
        if any(flag in normalized for flag in ("critical", "fatal", "error", "high", "p0", "p1")):
            return "High"
        if any(flag in normalized for flag in ("warning", "warn", "medium", "p2")):
            return "Medium"
        if any(flag in normalized for flag in ("info", "low", "style", "p3", "p4")):
            return "Low"
        return "Medium"
