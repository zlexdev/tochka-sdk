"""Transport layer — sessions, retry policy, rate limiting, error mapping."""

from __future__ import annotations

from .errors import parse_error
from .retry import RateLimiter, RetryPolicy
from .session import BaseSession, HttpxSession, Response

__all__ = [
    "BaseSession",
    "HttpxSession",
    "RateLimiter",
    "Response",
    "RetryPolicy",
    "parse_error",
]
