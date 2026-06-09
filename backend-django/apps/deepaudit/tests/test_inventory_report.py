from __future__ import annotations

import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from apps.deepaudit.inventory_report import normalize_inventory_report


class InventoryReportTestCase(SimpleTestCase):
    def test_normalize_report_records_invalid_references_in_qa_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src/main.c").write_text("int main(void) {\n  return 0;\n}\n", encoding="utf-8")

            report = normalize_inventory_report(
                {
                    "items": [
                        {
                            "file_path": "src/missing.c",
                            "line_start": 1,
                            "evidence": "missing",
                        },
                        {
                            "file_path": "src/main.c",
                            "line_start": 99,
                            "evidence": "return 0",
                        },
                        {
                            "file_path": "src/main.c",
                            "line_start": 1,
                            "evidence": "not in file",
                        },
                    ]
                },
                scenario_profile={
                    "scenario_key": "api_chain",
                    "scenario_name": "高危 API 调用链梳理",
                    "objective_type": "inventory",
                },
                target_files=["src/main.c"],
                project_root=str(root),
            )

        warnings = report["qa"]["warnings"]
        warning_types = {item["type"] for item in warnings}
        self.assertEqual(report["qa"]["status"], "warnings")
        self.assertIn("missing_file", warning_types)
        self.assertIn("invalid_line", warning_types)
        self.assertIn("evidence_mismatch", warning_types)
