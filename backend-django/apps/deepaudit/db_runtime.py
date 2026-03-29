import logging
from collections.abc import Callable
from typing import TypeVar

from django.db import close_old_connections, connection


logger = logging.getLogger(__name__)

T = TypeVar("T")


def close_runtime_db_connections() -> None:
    if connection.in_atomic_block:
        return
    try:
        connection.close()
    except Exception as exc:
        logger.debug("Ignore database close error during runtime cleanup: %s", exc)
    close_old_connections()


def ensure_runtime_db_connection() -> None:
    if connection.in_atomic_block:
        return
    close_old_connections()
    connection.ensure_connection()


def run_with_fresh_connection(func: Callable[..., T], *args, **kwargs) -> T:
    ensure_runtime_db_connection()
    try:
        return func(*args, **kwargs)
    finally:
        close_old_connections()
