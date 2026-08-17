"""Types shared by every generated domain model.

Hand-written and stable: the generator imports these by name, so renaming one breaks all
153 generated files at import time (loudly, which is the point).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BeforeValidator, Field

from ._base import TochkaObject


def _ensure_tz(value: Any) -> Any:
    """Attach UTC to a naive datetime the bank sent without an offset.

    A naive datetime compared against an aware one raises at runtime, far from here — and
    Tochka's statement endpoints do return bare `YYYY-MM-DDTHH:MM:SS` for some fields.
    """

    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.endswith("Z"):
        return value[:-1] + "+00:00"
    return value


TZDatetime = Annotated[datetime, BeforeValidator(_ensure_tz)]
"""A timezone-aware datetime; naive input is read as UTC rather than left naive."""


class TochkaErrorBody(TochkaObject):
    """The bank's error element, shared by every endpoint's 4xx/5xx envelope."""

    error_code: str | None = Field(default=None, alias="errorCode")
    message: str | None = Field(default=None)
    url: str | None = Field(default=None)


__all__ = ["TZDatetime", "TochkaErrorBody"]
