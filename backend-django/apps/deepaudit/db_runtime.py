import logging
import time
from collections.abc import Callable
from typing import TypeVar

from django.db import close_old_connections, connection
from django.db.utils import DatabaseError, InterfaceError, OperationalError


logger = logging.getLogger(__name__)

T = TypeVar("T")

DB_CONNECTION_ERROR_MARKERS = (
    "mysql server has gone away",
    "lost connection",
    "connection refused",
    "connection reset",
    "broken pipe",
    "server has gone away",
    "(0, '')",
    "2006",
    "2013",
)


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


def is_connection_error(exc: Exception) -> bool:
    if isinstance(exc, (InterfaceError, OperationalError)):
        return True
    if isinstance(exc, DatabaseError):
        message = str(exc).lower()
        return any(marker in message for marker in DB_CONNECTION_ERROR_MARKERS)
    return False


def run_with_fresh_connection(func: Callable[..., T], *args, retries: int = 2, retry_delay: float = 0.2, **kwargs) -> T:
    if connection.in_atomic_block:
        return func(*args, **kwargs)

    attempts = max(int(retries), 0) + 1
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            close_runtime_db_connections()
            ensure_runtime_db_connection()
            result = func(*args, **kwargs)
            close_old_connections()
            return result
        except Exception as exc:
            last_error = exc
            close_runtime_db_connections()
            if not is_connection_error(exc) or attempt >= attempts - 1:
                raise
            logger.warning(
                "Retrying DB operation after connection error (attempt %s/%s): %s",
                attempt + 1,
                attempts,
                exc,
            )
            time.sleep(retry_delay * (attempt + 1))

    if last_error:
        raise last_error
    raise RuntimeError("run_with_fresh_connection exited without result")
