from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _is_worker_log_target() -> bool:
    return str(os.environ.get('DEEPAUDIT_LOG_TARGET') or '').strip().lower() == 'worker'


def resolve_deepaudit_log_file(default_filename: str) -> str:
    explicit = str(os.environ.get('DEEPAUDIT_LOG_FILE') or '').strip()
    if explicit:
        return explicit

    if _is_worker_log_target():
        default_path = Path(default_filename)
        queue_name = str(os.environ.get('DEEPAUDIT_QUEUE') or 'deepaudit').strip() or 'deepaudit'
        return str(default_path.with_name(f'celery-{queue_name}.log'))

    return default_filename


class ProcessAwareRotatingFileHandler(RotatingFileHandler):
    """Rotate logs to the process-specific DeepAudit target file."""

    def __init__(self, filename, *args, **kwargs):
        super().__init__(resolve_deepaudit_log_file(str(filename)), *args, **kwargs)


class NonWorkerConsoleFilter(logging.Filter):
    """Keep console output on the server side and silence it in worker processes."""

    def filter(self, record):  # noqa: D401 - logging filter API
        return not _is_worker_log_target()
