from __future__ import annotations

import asyncio
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.deepaudit.scan_task.scan_task_services import _scan_files_with_concurrency


class ScanTaskServicesConcurrencyTestCase(SimpleTestCase):
    def test_scan_files_with_concurrency_respects_llm_concurrency(self) -> None:
        files = [
            {'path': f'app_{index}.py', 'content': 'print("ok")\n', 'lines': 1}
            for index in range(4)
        ]
        in_flight = 0
        max_in_flight = 0
        progress_updates: list[dict] = []

        async def fake_analyze(*_args, **_kwargs):
            nonlocal in_flight, max_in_flight
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.05)
            in_flight -= 1
            return {
                'issues': [],
                'quality_score': 92,
                'total_lines': 1,
            }

        def fake_progress(*_args, **kwargs):
            progress_updates.append(kwargs)

        with (
            patch('apps.deepaudit.scan_task.scan_task_services._analyze_code_payload_async', side_effect=fake_analyze),
            patch('apps.deepaudit.scan_task.scan_task_services._persist_scan_issues', return_value=0),
            patch('apps.deepaudit.scan_task.scan_task_services._update_scan_progress', side_effect=fake_progress),
            patch('apps.deepaudit.scan_task.scan_task_services._is_cancelled', return_value=False),
        ):
            summary = asyncio.run(
                _scan_files_with_concurrency(
                    task_id='scan-task-id',
                    created_by_id='user-id',
                    files=files,
                    user_payload={},
                    profile={},
                    llm_concurrency=2,
                    llm_gap_ms=0,
                )
            )

        self.assertFalse(summary['cancelled'])
        self.assertEqual(summary['scanned_files'], 4)
        self.assertEqual(max_in_flight, 2)
        self.assertEqual(len(progress_updates), 4)
