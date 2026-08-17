"""Retry policy and the token bucket that paces outbound calls.

Separate from the session on purpose: what counts as retryable is a decision about the
bank's semantics, while sending bytes is not.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass

from ..exceptions import ApiError, RateLimitError, ServerError, TransportError

#: A retry must never replay a non-idempotent write blindly; POST is retried only when the
#: request carried an Idempotency-Key (the caller declares that via `idempotent`).
RETRYABLE_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """How many times to retry, and how long to wait between attempts."""

    max_retries: int = 3
    base: float = 0.5
    maximum: float = 8.0

    def should_retry(self, attempt: int, error: Exception, *, idempotent: bool) -> bool:
        if attempt >= self.max_retries:
            return False
        if isinstance(error, TransportError):
            return idempotent
        if isinstance(error, RateLimitError):
            return True
        if isinstance(error, ServerError | ApiError):
            return idempotent and error.status in RETRYABLE_STATUSES
        return False

    def delay(self, attempt: int, error: Exception) -> float:
        """Exponential backoff with jitter; the bank's own `Retry-After` wins when given."""

        if isinstance(error, RateLimitError) and error.retry_after is not None:
            hinted: float = error.retry_after
            return min(hinted, self.maximum)
        # `2**attempt` with an int exponent is `Any` to mypy (int.__pow__ may return float
        # for a negative exponent) — a float base keeps the whole expression typed.
        window = min(self.base * 2.0**attempt, self.maximum)
        return window * (0.5 + random.random() / 2)


class RateLimiter:
    """Token bucket, shared by every request of one client."""

    def __init__(self, rate_per_second: float, *, burst: float | None = None) -> None:
        self._rate = rate_per_second
        self._capacity = burst if burst is not None else max(rate_per_second, 1.0)
        self._tokens = self._capacity
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until one token is available."""

        async with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(self._capacity, self._tokens + (now - self._updated) * self._rate)
                self._updated = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                await asyncio.sleep((1 - self._tokens) / self._rate)
