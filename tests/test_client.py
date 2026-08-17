"""What the client does with a request and a response — the contract every method relies on."""

from __future__ import annotations

import pytest
from conftest import FakeSession, fail, ok

from tochka import Client, Config, NotFoundError, PermissionDeniedError
from tochka.exceptions import ResponseValidationError
from tochka.methods.balances import GetBalanceInfo

BALANCE_PAYLOAD = {
    "Data": {
        "Balance": [
            {
                "accountId": "40817810802000000008/044525104",
                "amount": {"amount": 1234.56, "currency": "RUB"},
                "creditDebitIndicator": "Credit",
                "dateTime": "2026-08-17T12:00:00+03:00",
                "type": "OpeningAvailable",
            },
        ],
    },
    "Links": {"self": "https://enter.tochka.com/uapi"},
    "Meta": {"totalPages": 1},
}


async def test_path_params_land_in_the_url_not_the_query(client: Client, session: FakeSession) -> None:
    session.responses.append(ok(BALANCE_PAYLOAD))

    await client.get_balance_info(account_id="40817810802000000008/044525104")

    call = session.calls[0]
    assert call.method == "GET"
    assert call.url.endswith("/open-banking/v1.0/accounts/40817810802000000008/044525104/balances")
    assert not call.params, "path-параметр не должен уезжать ещё и в query"


async def test_response_parses_into_the_generated_model(client: Client, session: FakeSession) -> None:
    session.responses.append(ok(BALANCE_PAYLOAD))

    result = await client.get_balance_info(account_id="acc")

    balance = result.data.balance[0]
    assert balance.amount.amount == 1234.56
    assert balance.account_id == "40817810802000000008/044525104"


async def test_returned_model_is_bound_to_the_client(client: Client, session: FakeSession) -> None:
    session.responses.append(ok(BALANCE_PAYLOAD))

    result = await client.get_balance_info(account_id="acc")

    assert result.bound_client() is client
    assert result.data.balance[0].bound_client() is client, "привязка должна доходить до вложенных моделей"


async def test_auth_header_is_sent(client: Client, session: FakeSession) -> None:
    session.responses.append(ok(BALANCE_PAYLOAD))

    await client.get_balance_info(account_id="acc")

    assert session.calls[0].headers["Authorization"] == "Bearer test-token"


async def test_error_envelope_becomes_a_typed_error(client: Client, session: FakeSession) -> None:
    session.responses.append(fail(403, "AccessDenied", "нет разрешения ReadBalances"))

    with pytest.raises(PermissionDeniedError) as info:
        await client.get_balance_info(account_id="acc")

    assert info.value.status == 403
    assert info.value.code == "AccessDenied", "код берётся из Errors[0].errorCode, не из HTTP-статуса"
    assert info.value.error_id == "test-id"


async def test_404_is_its_own_error(client: Client, session: FakeSession) -> None:
    session.responses.append(fail(404, "NotFound", "счёт не найден"))

    with pytest.raises(NotFoundError):
        await client.get_balance_info(account_id="acc")


async def test_get_is_retried_on_server_error(client: Client, session: FakeSession) -> None:
    session.responses += [fail(500, "Internal", "упало"), ok(BALANCE_PAYLOAD)]

    result = await client.get_balance_info(account_id="acc")

    assert len(session.calls) == 2, "GET идемпотентен — повтор обязан произойти"
    assert result.meta.total_pages == 1


async def test_retries_stop_at_the_limit(session: FakeSession) -> None:
    config = Config(token="t", max_retries=2, backoff_base=0.0, requests_per_second=1000.0)
    client = Client(config=config, session=session)
    session.responses += [fail(500, "Internal", "упало")] * 3

    with pytest.raises(Exception, match="Internal"):
        await client.get_balance_info(account_id="acc")

    assert len(session.calls) == 3, "первая попытка плюс max_retries=2"


async def test_rate_limit_error_carries_retry_after(client: Client, session: FakeSession) -> None:
    session.responses += [
        fail(429, "TooManyRequests", "притормози", **{"retry-after": "0"}),
        ok(BALANCE_PAYLOAD),
    ]

    await client.get_balance_info(account_id="acc")

    assert len(session.calls) == 2


async def test_malformed_payload_raises_instead_of_degrading(client: Client, session: FakeSession) -> None:
    session.responses.append(ok({"Data": {"Balance": "не список"}}))

    with pytest.raises(ResponseValidationError) as info:
        await client.get_balance_info(account_id="acc")

    assert info.value.model == "GetBalanceInfoResponse"


async def test_unknown_response_fields_survive(client: Client, session: FakeSession) -> None:
    payload = {**BALANCE_PAYLOAD, "Data": {**BALANCE_PAYLOAD["Data"], "NewFieldFromTheBank": 42}}
    session.responses.append(ok(payload))

    result = await client.get_balance_info(account_id="acc")

    assert result.data.raw()["NewFieldFromTheBank"] == 42


async def test_method_class_can_be_executed_directly(client: Client, session: FakeSession) -> None:
    session.responses.append(ok(BALANCE_PAYLOAD))

    result = await client.execute(GetBalanceInfo(account_id="acc"))

    assert result.meta.total_pages == 1


async def test_client_closes_only_sessions_it_owns(session: FakeSession) -> None:
    async with Client(config=Config(token="t"), session=session):
        pass

    assert not session.closed, "чужую сессию клиент закрывать не вправе"
