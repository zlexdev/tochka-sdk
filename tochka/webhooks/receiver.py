"""Receive and verify an inbound Tochka webhook.

Framework-agnostic by design: `WebhookReceiver.handle()` takes the raw request body and
returns a typed event, so it drops into FastAPI, aiohttp, Django or a bare ASGI app
without the SDK depending on any of them.

Three traps the bank's own docs name, all handled here:
  * the body is a BARE JWT string sent as `text/plain`, not JSON;
  * an unverified payload must never be trusted — signature check is not optional;
  * a non-200 answer makes the bank retry 30 times, 10 seconds apart, so a handler that
    raises turns one event into thirty.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

import jwt

from ..exceptions import TochkaError
from .events import WebhookEvent, WebhookType, parse_event
from .keys import KeyProvider

Handler = Callable[[WebhookEvent], Awaitable[None] | None]

ALGORITHM = "RS256"


class WebhookVerificationError(TochkaError):
    """The body was not a JWT signed by Tochka's current key."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class WebhookReceiver:
    """Verifies inbound webhooks and dispatches them to registered handlers.

    receiver = WebhookReceiver()

    @receiver.on(WebhookType.INCOMING_PAYMENT)
    async def credited(event: PaymentEvent) -> None:
        ...

    event = await receiver.handle(await request.body())
    """

    def __init__(self, *, keys: KeyProvider | None = None) -> None:
        self._keys = keys or KeyProvider()
        self._handlers: dict[str, list[Handler]] = {}

    def on(self, event_type: WebhookType | str) -> Callable[[Handler], Handler]:
        """Register a handler for one event type."""

        def register(handler: Handler) -> Handler:
            self._handlers.setdefault(str(event_type), []).append(handler)
            return handler

        return register

    async def verify(self, body: bytes | str) -> WebhookEvent:
        """Decode and verify the body, returning the typed event.

        The key is re-fetched once on a signature failure: the bank rotates its key, and a
        cached stale key would otherwise reject every event until the process restarts.
        """

        token = body.decode("utf-8").strip() if isinstance(body, bytes) else body.strip()
        if not token:
            raise WebhookVerificationError("пустое тело вебхука")

        try:
            payload = await self._decode(token, refreshed=False)
        except jwt.InvalidSignatureError:
            payload = await self._decode(token, refreshed=True)
        except jwt.PyJWTError as exc:
            raise WebhookVerificationError(f"не разобрали JWT: {exc}") from exc

        if not isinstance(payload, dict):
            raise WebhookVerificationError("payload вебхука не объект")
        return parse_event(payload)

    async def _decode(self, token: str, *, refreshed: bool) -> Any:
        key = await (self._keys.refresh() if refreshed else self._keys.get())
        try:
            return jwt.decode(token, key.key, algorithms=[ALGORITHM], options={"verify_aud": False})
        except jwt.InvalidSignatureError:
            if refreshed:
                raise WebhookVerificationError("подпись не сходится даже со свежим ключом") from None
            raise

    async def handle(self, body: bytes | str) -> WebhookEvent:
        """Verify, then run every handler registered for the event's type.

        Handlers run in registration order; the first one to raise propagates, because
        answering 200 on a half-processed event loses it — the bank does not resend a
        webhook it considers delivered.
        """

        event = await self.verify(body)
        for handler in self._handlers.get(event.webhook_type, []):
            result = handler(event)
            if inspect.isawaitable(result):
                await result
        return event
