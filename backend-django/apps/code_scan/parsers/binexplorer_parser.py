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


class BinExplorerParser(BaseParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        header, rows = load_rows_by_extension(file_path)
        header_index = build_header_index(header)

        file_idx = find_col_index(header_index, ["file", "path", "file_path"])
        function_idx = find_col_index(header_index, ["function"])
        language_idx = find_col_index(header_index, ["language", "lang"])
        line_idx = find_col_index(header_index, ["line", "line_number"])
        reason_idx = find_col_index(header_index, ["reason", "description", "message", "msg"])

        results: List[Dict[str, Any]] = []
        for row in rows:
            file_path_value = as_text(value_by_index(row, file_idx)) or "unknown"
            line_number = as_int(value_by_index(row, line_idx), 0)
            function = as_text(value_by_index(row, function_idx))
            language = as_text(value_by_index(row, language_idx))
            reason = as_text(value_by_index(row, reason_idx))

            help_parts = []
            if function:
                help_parts.append(f"Function: {function}")
            if language:
                help_parts.append(f"Language: {language}")

            results.append(
                {
                    "file_path": file_path_value,
                    "line_number": line_number,
                    "defect_type": language or "binexplorer",
                    "severity": "Medium",
                    "description": reason or "BinExplorer finding",
                    "help_info": " | ".join(help_parts),
                    "code_snippet": "",
                }
            )

        return results
