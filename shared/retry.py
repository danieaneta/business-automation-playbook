"""Retry with exponential backoff.

Real integrations fail transiently — rate limits, timeouts, brief 5xx blips. This decorator
retries those, backs off exponentially, and gives up cleanly with the original error attached.
"""

from __future__ import annotations

import functools
import time
from typing import Callable, Iterable, Type, TypeVar

T = TypeVar("T")


class RetryError(RuntimeError):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_exc: BaseException):
        super().__init__(f"Failed after {attempts} attempt(s): {last_exc!r}")
        self.attempts = attempts
        self.last_exc = last_exc


def retry(
    attempts: int = 3,
    base_delay: float = 0.5,
    backoff: float = 2.0,
    max_delay: float = 30.0,
    exceptions: Iterable[Type[BaseException]] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry the wrapped callable on the given exceptions.

    Delay for attempt *n* (1-indexed) is ``min(base_delay * backoff**(n-1), max_delay)``.

    Args:
        attempts: Total tries before giving up (must be >= 1).
        base_delay: Delay before the first retry, in seconds.
        backoff: Multiplier applied to the delay after each failed attempt.
        max_delay: Ceiling on any single delay.
        exceptions: Exception types that trigger a retry. Anything else propagates immediately.
        sleep: Injectable sleep function (tests pass a no-op to stay fast).
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    exc_tuple = tuple(exceptions)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exc_tuple as exc:  # noqa: PERF203 - retry loop is intentional
                    last_exc = exc
                    if attempt == attempts:
                        break
                    delay = min(base_delay * (backoff ** (attempt - 1)), max_delay)
                    sleep(delay)
            assert last_exc is not None  # loop ran at least once
            raise RetryError(attempts, last_exc) from last_exc

        return wrapper

    return decorator
