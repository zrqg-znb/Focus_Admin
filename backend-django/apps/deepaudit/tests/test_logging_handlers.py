from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from application.logging_handlers import (
    NonWorkerConsoleFilter,
    ProcessAwareRotatingFileHandler,
    resolve_deepaudit_log_file,
)


class DeepAuditLoggingHandlersTestCase(SimpleTestCase):
    def test_settings_use_process_aware_logging_handlers(self) -> None:
        self.assertEqual(
            settings.LOGGING['handlers']['file']['class'],
            'application.logging_handlers.ProcessAwareRotatingFileHandler',
        )
        self.assertIn('non_worker_console', settings.LOGGING['handlers']['console'].get('filters', []))
        self.assertEqual(
            settings.LOGGING['filters']['non_worker_console']['()'],
            'application.logging_handlers.NonWorkerConsoleFilter',
        )

    def test_worker_target_uses_queue_specific_log_file(self) -> None:
        with patch.dict(
            os.environ,
            {
                'DEEPAUDIT_LOG_FILE': '',
                'DEEPAUDIT_LOG_TARGET': 'worker',
                'DEEPAUDIT_QUEUE': 'deepaudit',
            },
            clear=False,
        ):
            expected_path = '/tmp/focusaudit/logs/celery-deepaudit.log'
            self.assertEqual(
                resolve_deepaudit_log_file('/tmp/focusaudit/logs/server.log'),
                expected_path,
            )
            handler = ProcessAwareRotatingFileHandler('/tmp/focusaudit/logs/server.log', delay=True)
            try:
                self.assertEqual(Path(handler.baseFilename), Path(expected_path))
            finally:
                handler.close()

    def test_explicit_log_file_override_wins(self) -> None:
        with patch.dict(
            os.environ,
            {
                'DEEPAUDIT_LOG_FILE': '/tmp/focusaudit/logs/worker.log',
                'DEEPAUDIT_LOG_TARGET': 'worker',
                'DEEPAUDIT_QUEUE': 'deepaudit',
            },
            clear=False,
        ):
            self.assertEqual(
                resolve_deepaudit_log_file('/tmp/focusaudit/logs/server.log'),
                '/tmp/focusaudit/logs/worker.log',
            )

    def test_console_filter_silences_worker_processes(self) -> None:
        record = logging.makeLogRecord({'msg': 'hello', 'levelno': logging.INFO, 'levelname': 'INFO'})

        with patch.dict(os.environ, {'DEEPAUDIT_LOG_FILE': '', 'DEEPAUDIT_LOG_TARGET': 'worker'}, clear=False):
            self.assertFalse(NonWorkerConsoleFilter().filter(record))

        with patch.dict(os.environ, {'DEEPAUDIT_LOG_FILE': '', 'DEEPAUDIT_LOG_TARGET': 'server'}, clear=False):
            self.assertTrue(NonWorkerConsoleFilter().filter(record))
