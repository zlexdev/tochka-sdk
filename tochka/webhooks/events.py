"""The five webhook events Tochka sends, as typed models.

Field names and event list come from the portal's webhook pages, not from guesswork:
`incomingPayment`, `outgoingPayment`, `incomingSbpPayment`, `incomingSbpB2BPayment`,
`acquiringInternetPayment`. Unknown fields are preserved (the base allows extras), and an
unrecognised `webhookType` degrades to `UnknownEvent` rather than raising — a new event
type must not take down a live receiver.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field

from ..models._base import TochkaObject


class WebhookType(StrEnum):
    """Event types the bank publishes."""

    INCOMING_PAYMENT = "incomingPayment"
    OUTGOING_PAYMENT = "outgoingPayment"
    INCOMING_SBP_PAYMENT = "incomingSbpPayment"
    INCOMING_SBP_B2B_PAYMENT = "incomingSbpB2BPayment"
    ACQUIRING_INTERNET_PAYMENT = "acquiringInternetPayment"


class PaymentSide(TochkaObject):
    """Payer or recipient block of a payment webhook."""

    account: str | None = Field(default=None)
    name: str | None = Field(default=None)
    bank_code: str | None = Field(default=None, alias="bankCode")
    bank_name: str | None = Field(default=None, alias="bankName")
    bank_correspondent_account: str | None = Field(default=None, alias="bankCorrespondentAccount")
    amount: Decimal | None = Field(default=None)
    currency: str | None = Field(default=None)
    inn: str | None = Field(default=None)
    kpp: str | None = Field(default=None)


class WebhookEvent(TochkaObject):
    """Base of every event — what all five carry."""

    webhook_type: str = Field(alias="webhookType")
    customer_code: str | None = Field(default=None, alias="customerCode")


class PaymentEvent(WebhookEvent):
    """`incomingPayment` / `outgoingPayment` — a payment settled on the account."""

    payment_id: str | None = Field(default=None, alias="paymentId")
    document_number: str | None = Field(default=None, alias="documentNumber")
    date: str | None = Field(default=None)
    purpose: str | None = Field(default=None)
    payer: PaymentSide | None = Field(default=None, alias="SidePayer")
    recipient: PaymentSide | None = Field(default=None, alias="SideRecipient")


class SbpPaymentEvent(WebhookEvent):
    """`incomingSbpPayment` / `incomingSbpB2BPayment` — a payment settled over SBP."""

    qrc_id: str | None = Field(default=None, alias="qrcId")
    payment_id: str | None = Field(default=None, alias="paymentId")
    amount: Decimal | None = Field(default=None)
    currency: str | None = Field(default=None)
    purpose: str | None = Field(default=None)


class AcquiringEvent(WebhookEvent):
    """`acquiringInternetPayment` — a payment made through a payment link."""

    operation_id: str | None = Field(default=None, alias="operationId")
    payment_id: str | None = Field(default=None, alias="paymentId")
    amount: Decimal | None = Field(default=None)
    payment_type: str | None = Field(default=None, alias="paymentType")
    purpose: str | None = Field(default=None)
    consumer_id: str | None = Field(default=None, alias="consumerId")


class UnknownEvent(WebhookEvent):
    """An event type this SDK version does not know — payload kept intact."""


EVENT_MODELS: dict[str, type[WebhookEvent]] = {
    WebhookType.INCOMING_PAYMENT: PaymentEvent,
    WebhookType.OUTGOING_PAYMENT: PaymentEvent,
    WebhookType.INCOMING_SBP_PAYMENT: SbpPaymentEvent,
    WebhookType.INCOMING_SBP_B2B_PAYMENT: SbpPaymentEvent,
    WebhookType.ACQUIRING_INTERNET_PAYMENT: AcquiringEvent,
}


def parse_event(payload: dict[str, Any]) -> WebhookEvent:
    """Build the typed event for a decoded JWT payload."""

    model = EVENT_MODELS.get(str(payload.get("webhookType")), UnknownEvent)
    return model.model_validate(payload)
