"""Reusable engineering layer shared by every blueprint.

Exposes the three things every production automation needs and most no-code-only
portfolios are missing: retry-with-backoff, structured logging, and an idempotent store.
"""

from .retry import retry, RetryError
from .logging_config import get_logger
from .store import JsonStore

__all__ = ["retry", "RetryError", "get_logger", "JsonStore"]
