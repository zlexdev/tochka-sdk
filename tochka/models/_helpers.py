"""Helpers the generated code calls — kept tiny and stable, since it is imported by name."""

from __future__ import annotations

from typing import Any

from ..exceptions import ConfigurationError, ModelNotBoundError


def _resolve_customer_code(source: Any) -> str:
    """Account context for a `{customerCode}` segment the caller did not pass.

    `source` is either the client (facade path) or a bound model's client (bound-method
    path). A missing code is an error, never an empty segment: an empty `{customerCode}`
    silently becomes a 404 against a URL nobody meant to call.
    """

    if source is None:
        raise ModelNotBoundError("<model>", "customer_code")
    code = getattr(source, "customer_code", None)
    if not code:
        raise ConfigurationError(
            "customer_code не задан — передайте его в Client(...) или аргументом вызова",
        )
    return str(code)
