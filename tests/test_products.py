"""Routing per product — a method must reach ITS host, not the default one.

Tochka is not one API behind one URL: cyclops is served from api.tochka.com and
pay-gateway from `uapi/pay/`. A regression here is silent — the request succeeds against
the wrong host or 404s, and nothing in the type system notices.
"""

from __future__ import annotations

import pytest
from conftest import FakeSession, ok

from tochka import Client, Config
from tochka.config import PRODUCT_BASE_URLS
from tochka.exceptions import ConfigurationError
from tochka.methods.balances import GetBalanceInfo
from tochka.methods.deals import CreateDealV2
from tochka.models.deals import CreateDealV2Params
from tochka.types import Environment, Product


def _deal() -> CreateDealV2:
    """Cyclops говорит по JSON-RPC: полезные поля лежат в `params`, а не в корне."""

    return CreateDealV2(
        id=1,
        jsonrpc="2.0",
        method="create_deal",
        params=CreateDealV2Params(amount=1.0, payers=[], recipients=[]),
    )


def test_every_product_has_a_production_base_url() -> None:
    for product in Product:
        production, _ = PRODUCT_BASE_URLS[product]
        assert production.startswith("https://"), product


def test_products_do_not_share_one_host() -> None:
    hosts = {PRODUCT_BASE_URLS[product][0] for product in Product}

    assert len(hosts) >= 3, "cyclops и pay-gateway обязаны отличаться от основного хоста"
    assert PRODUCT_BASE_URLS[Product.CYCLOPS][0].startswith("https://api.tochka.com")
    assert PRODUCT_BASE_URLS[Product.PAY_GATEWAY][0].endswith("/pay/")


def test_generated_methods_declare_their_product() -> None:
    assert GetBalanceInfo.__product__ == Product.TOCHKA_API
    assert CreateDealV2.__product__ == Product.CYCLOPS


async def test_cyclops_call_goes_to_the_cyclops_host(session: FakeSession) -> None:
    client = Client(config=Config(token="t", requests_per_second=1000.0), session=session)
    session.responses.append(ok({"id": 1, "jsonrpc": "2.0", "result": {}}))

    await client.execute(_deal())

    assert session.calls[0].url.startswith("https://api.tochka.com/api/v1/cyclops")


async def test_each_product_may_carry_its_own_token(session: FakeSession) -> None:
    config = Config(
        token="open-banking-token",
        product_tokens={Product.CYCLOPS: "cyclops-token"},
        requests_per_second=1000.0,
    )
    client = Client(config=config, session=session)
    session.responses += [ok({"id": 1, "jsonrpc": "2.0", "result": {}}), ok(BALANCE)]

    await client.execute(_deal())
    await client.execute(GetBalanceInfo(account_id="acc"))

    assert session.calls[0].headers["Authorization"] == "Bearer cyclops-token"
    assert session.calls[1].headers["Authorization"] == "Bearer open-banking-token"


def test_sandbox_without_a_test_server_fails_loudly() -> None:
    config = Config(token="t", environment=Environment.SANDBOX)

    # У pay-gateway тестового сервера нет. Молчаливый откат на прод из песочницы двигал бы
    # настоящие деньги, поэтому это ошибка конфигурации, а не фолбэк.
    with pytest.raises(ConfigurationError):
        config.base_url_for(Product.PAY_GATEWAY)

    assert config.base_url_for(Product.CYCLOPS).startswith("https://pre.tochka.com")


def test_explicit_override_wins() -> None:
    config = Config(token="t", product_base_urls={Product.CYCLOPS: "https://stand.local/cyclops"})

    assert config.base_url_for(Product.CYCLOPS) == "https://stand.local/cyclops"


BALANCE = {
    "Data": {
        "Balance": [
            {
                "accountId": "acc",
                "amount": {"amount": 1.0, "currency": "RUB"},
                "creditDebitIndicator": "Credit",
                "dateTime": "2026-08-17T12:00:00+03:00",
                "type": "OpeningAvailable",
            },
        ],
    },
    "Links": {"self": "https://enter.tochka.com/uapi"},
    "Meta": {"totalPages": 1},
}
