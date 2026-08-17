"""Webhook verification — the security boundary, so the failure paths matter most."""

from __future__ import annotations

import json

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWK, algorithms

from tochka.webhooks import StaticKeyProvider, WebhookReceiver, WebhookType
from tochka.webhooks.events import PaymentEvent, UnknownEvent
from tochka.webhooks.receiver import WebhookVerificationError

PAYLOAD = {
    "webhookType": "incomingPayment",
    "customerCode": "300123456",
    "paymentId": "0000000001",
    "purpose": "Тестовое назначение платежа",
    "SidePayer": {"account": "40817810802000000008", "name": "ИП Тест", "amount": "40.0", "currency": "RUB"},
    "SideRecipient": {"account": "40802810500000000001", "name": "ООО Получатель"},
}


@pytest.fixture(scope="module")
def keypair() -> tuple[str, dict[str, object]]:
    """A throwaway RSA key: the private half signs, the public half verifies."""

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    return _pem(private), jwk


def _pem(private: rsa.RSAPrivateKey) -> str:
    return private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


@pytest.fixture
def receiver(keypair: tuple[str, dict[str, object]]) -> WebhookReceiver:
    _, jwk = keypair
    return WebhookReceiver(keys=StaticKeyProvider(jwk))


def sign(payload: dict[str, object], pem: str) -> str:
    return jwt.encode(payload, pem, algorithm="RS256")


async def test_valid_webhook_parses_into_a_typed_event(receiver: WebhookReceiver, keypair) -> None:
    pem, _ = keypair

    event = await receiver.verify(sign(PAYLOAD, pem))

    assert isinstance(event, PaymentEvent)
    assert event.payment_id == "0000000001"
    assert event.payer is not None
    assert event.payer.name == "ИП Тест"


async def test_body_may_arrive_as_bytes_with_whitespace(receiver: WebhookReceiver, keypair) -> None:
    pem, _ = keypair

    event = await receiver.verify(f"  {sign(PAYLOAD, pem)}\n".encode())

    assert event.webhook_type == WebhookType.INCOMING_PAYMENT


async def test_a_forged_token_is_rejected(receiver: WebhookReceiver) -> None:
    forged = jwt.encode(PAYLOAD, "not-the-bank-key", algorithm="HS256")

    with pytest.raises(WebhookVerificationError):
        await receiver.verify(forged)


async def test_a_token_signed_by_another_rsa_key_is_rejected(receiver: WebhookReceiver) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(WebhookVerificationError):
        await receiver.verify(sign(PAYLOAD, _pem(other)))


async def test_empty_body_is_rejected(receiver: WebhookReceiver) -> None:
    with pytest.raises(WebhookVerificationError):
        await receiver.verify(b"   ")


async def test_unknown_event_type_does_not_crash_the_receiver(receiver: WebhookReceiver, keypair) -> None:
    pem, _ = keypair

    event = await receiver.verify(sign({**PAYLOAD, "webhookType": "somethingNew"}, pem))

    assert isinstance(event, UnknownEvent)
    assert event.raw()["paymentId"] == "0000000001"


async def test_handlers_run_for_their_event_type(receiver: WebhookReceiver, keypair) -> None:
    pem, _ = keypair
    seen: list[str] = []

    @receiver.on(WebhookType.INCOMING_PAYMENT)
    async def credited(event: PaymentEvent) -> None:
        seen.append(event.payment_id or "")

    @receiver.on(WebhookType.OUTGOING_PAYMENT)
    def debited(event: PaymentEvent) -> None:
        seen.append("wrong-handler")

    await receiver.handle(sign(PAYLOAD, pem))

    assert seen == ["0000000001"]


async def test_static_key_provider_is_a_real_pyjwk(keypair) -> None:
    _, jwk = keypair

    provider = StaticKeyProvider(jwk)

    assert isinstance(await provider.get(), PyJWK)
