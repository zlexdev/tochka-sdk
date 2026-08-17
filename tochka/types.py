"""Domain primitives shared across the SDK surface."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import NewType, TypeAlias

AccountId = NewType("AccountId", str)
CustomerCode = NewType("CustomerCode", str)
PaymentId = NewType("PaymentId", str)
QrcId = NewType("QrcId", str)
LegalId = NewType("LegalId", str)
MerchantId = NewType("MerchantId", str)
WebhookId = NewType("WebhookId", str)

Money: TypeAlias = Decimal
JsonValue: TypeAlias = "str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None"
JsonObject: TypeAlias = dict[str, JsonValue]


class Environment(StrEnum):
    """Which Tochka installation the client talks to."""

    PRODUCTION = "production"
    SANDBOX = "sandbox"


class Product(StrEnum):
    """Tochka ships several independent APIs behind one host."""

    TOCHKA_API = "tochka-api"
    CYCLOPS = "cyclops"
    PAY_GATEWAY = "pay-gateway"
    MEDUSA = "medusa"
    EXPRESS_CREDIT = "express-credit"
    INFO = "info"


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class Currency(StrEnum):
    """ISO 4217 codes the bank actually returns."""

    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    CNY = "CNY"
