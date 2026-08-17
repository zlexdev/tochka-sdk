"""Typed error hierarchy — every error carries its args, never a pre-formatted string."""

from __future__ import annotations

from typing import Any


class TochkaError(Exception):
    """Base of every SDK error."""


class ConfigurationError(TochkaError):
    """The client was built with an unusable configuration."""


class ModelNotBoundError(TochkaError):
    """A bound method was called on a model that was never attached to a client."""

    def __init__(self, model: str, method: str) -> None:
        super().__init__(model, method)
        self.model = model
        self.method = method


class TransportError(TochkaError):
    """The request never produced an HTTP response (DNS, TLS, timeout, connection reset)."""

    def __init__(self, url: str, cause: str) -> None:
        super().__init__(url, cause)
        self.url = url
        self.cause = cause


class ApiError(TochkaError):
    """The bank answered with a non-success status.

    `code`/`message`/`error_id` come from the bank's own error envelope
    (`{"Errors": [{"errorCode", "message", "id"}]}`), so a caller can branch on the code
    instead of substring-matching a rendered message.
    """

    def __init__(
        self,
        status: int,
        code: str | None,
        message: str | None,
        *,
        url: str,
        error_id: str | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(status, code, message, url)
        self.status = status
        self.code = code
        self.message = message
        self.url = url
        self.error_id = error_id
        self.payload = payload

    def __str__(self) -> str:
        return f"{self.status} {self.code or '-'}: {self.message or ''} ({self.url})"


class AuthenticationError(ApiError):
    """401 — the token is missing, expired or malformed."""


class PermissionDeniedError(ApiError):
    """403 — the token lacks the permission this endpoint requires."""


class NotFoundError(ApiError):
    """404 — no such resource for this customer."""


class RateLimitError(ApiError):
    """429 — too many requests; `retry_after` is the bank's own hint, in seconds."""

    def __init__(
        self,
        status: int,
        code: str | None,
        message: str | None,
        *,
        url: str,
        retry_after: float | None = None,
        error_id: str | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(status, code, message, url=url, error_id=error_id, payload=payload)
        self.retry_after = retry_after


class ServerError(ApiError):
    """5xx — the bank failed; safe to retry an idempotent call."""


class ResponseValidationError(TochkaError):
    """The bank's payload did not match the generated model.

    Raised instead of silently degrading to `dict`: a shape change must surface at the
    call site, not three layers downstream.
    """

    def __init__(self, model: str, url: str, detail: str) -> None:
        super().__init__(model, url, detail)
        self.model = model
        self.url = url
        self.detail = detail


STATUS_ERRORS: dict[int, type[ApiError]] = {
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    429: RateLimitError,
}


def error_for_status(status: int) -> type[ApiError]:
    """Pick the error class for an HTTP status."""

    if status in STATUS_ERRORS:
        return STATUS_ERRORS[status]
    return ServerError if status >= 500 else ApiError
