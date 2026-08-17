"""Map a failed HTTP response onto the typed error hierarchy.

The envelope is the bank's own, taken from the spec, not from memory::

    {"code": "400", "id": "<uuid>", "message": "...",
     "Errors": [{"errorCode": "Validation Error", "message": "...", "url": "..."}]}

`errorCode` (the low-level reason) beats `code` (the HTTP status echoed as text) as the
branchable value, so it wins when both are present.
"""

from __future__ import annotations

from typing import Any

from ..exceptions import ApiError, RateLimitError, error_for_status


def _retry_after(headers: dict[str, str]) -> float | None:
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_error(status: int, url: str, payload: Any, headers: dict[str, str]) -> ApiError:
    """Build the typed error for a non-success response."""

    code: str | None = None
    message: str | None = None
    error_id: str | None = None

    if isinstance(payload, dict):
        code = payload.get("code") if isinstance(payload.get("code"), str) else None
        message = payload.get("message") if isinstance(payload.get("message"), str) else None
        error_id = payload.get("id") if isinstance(payload.get("id"), str) else None
        errors = payload.get("Errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            first = errors[0]
            code = first.get("errorCode") or code
            message = first.get("message") or message

    error_class = error_for_status(status)
    if error_class is RateLimitError:
        return RateLimitError(
            status,
            code,
            message,
            url=url,
            retry_after=_retry_after(headers),
            error_id=error_id,
            payload=payload,
        )
    return error_class(status, code, message, url=url, error_id=error_id, payload=payload)
