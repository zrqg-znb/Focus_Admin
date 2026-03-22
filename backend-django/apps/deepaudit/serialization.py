from __future__ import annotations

from datetime import datetime
from typing import Any

from django.utils import timezone


DATETIME_TEXT_FORMAT = '%Y-%m-%d %H:%M:%S'


def format_datetime_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime(DATETIME_TEXT_FORMAT)


def normalize_json_payload(value: Any) -> Any:
    if isinstance(value, datetime):
        return format_datetime_text(value)
    if isinstance(value, dict):
        return {key: normalize_json_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_json_payload(item) for item in value]
    return value
