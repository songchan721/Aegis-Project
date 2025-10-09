import asyncio
import functools
from typing import Any, Callable

from sqlalchemy.exc import OperationalError

from .exceptions import DatabaseConnectionError

# Retryable database exceptions
RETRYABLE_EXCEPTIONS = (
    OperationalError,
    DatabaseConnectionError,
    ConnectionError,
)


def with_db_retry(max_retries: int = 3, delay: float = 1.0):
    """데이터베이스 재시도 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except RETRYABLE_EXCEPTIONS:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(delay * (2**attempt))
                except Exception:
                    # Non-retryable exceptions are raised immediately
                    raise
            return None

        return wrapper

    return decorator


def db_retry(func):
    """A decorator to retry database operations."""
    return with_db_retry()(func)
