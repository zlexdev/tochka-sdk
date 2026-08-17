"""Inbound webhooks — verify the bank's JWT and dispatch typed events.

    from tochka.webhooks import WebhookReceiver, WebhookType

    receiver = WebhookReceiver()

    @receiver.on(WebhookType.INCOMING_PAYMENT)
    async def credited(event):
        ...

    # FastAPI: the body is text/plain, so read it raw — never `await request.json()`
    @app.post("/tochka")
    async def hook(request: Request):
        await receiver.handle(await request.body())
        return Response(status_code=200)

Answering anything but 200 makes Tochka resend the event 30 times, 10 seconds apart.
"""

from __future__ import annotations

from .events import (
    EVENT_MODELS,
    AcquiringEvent,
    PaymentEvent,
    PaymentSide,
    SbpPaymentEvent,
    UnknownEvent,
    WebhookEvent,
    WebhookType,
    parse_event,
)
from .keys import PUBLIC_KEY_URL, KeyProvider, StaticKeyProvider
from .receiver import WebhookReceiver, WebhookVerificationError

__all__ = [
    "EVENT_MODELS",
    "PUBLIC_KEY_URL",
    "AcquiringEvent",
    "KeyProvider",
    "PaymentEvent",
    "PaymentSide",
    "SbpPaymentEvent",
    "StaticKeyProvider",
    "UnknownEvent",
    "WebhookEvent",
    "WebhookReceiver",
    "WebhookType",
    "WebhookVerificationError",
    "parse_event",
]
