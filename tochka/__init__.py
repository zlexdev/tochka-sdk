"""Async SDK for the Tochka Bank Open API.

    from tochka import Client

    async with Client(token="...", customer_code="300123456") as client:
        balances = await client.get_balances_list()

The endpoint surface (`methods/`, `models/`, `enums/`, `facade/`) is generated from the
bank's own specs — see `dev/codegen`. Everything else here is hand-written.
"""

from __future__ import annotations

from .client import Client
from .config import Config
from .exceptions import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    ModelNotBoundError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ResponseValidationError,
    ServerError,
    TochkaError,
    TransportError,
)
from .types import Currency, Environment, Product

__version__ = "0.1.0"

__all__ = [
    "ApiError",
    "AuthenticationError",
    "Client",
    "Config",
    "ConfigurationError",
    "Currency",
    "Environment",
    "ModelNotBoundError",
    "NotFoundError",
    "PermissionDeniedError",
    "Product",
    "RateLimitError",
    "ResponseValidationError",
    "ServerError",
    "TochkaError",
    "TransportError",
    "__version__",
]
