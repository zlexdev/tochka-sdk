"""Pagination — a cursor that fetches nothing until it is used, and stops at the right page."""

from __future__ import annotations

from collections.abc import Mapping

from conftest import FakeSession, ok

from tochka import Client
from tochka.methods.subscriptions import GetSubscriptionList
from tochka.pagination import MethodPaginator


def page(items: list[Mapping[str, object]]) -> dict[str, object]:
    return {
        "Data": {"Subscription": items},
        "Links": {"self": "https://enter.tochka.com/uapi"},
        "Meta": {"totalPages": 1},
    }


#: Exactly the required fields of `GetSubscriptionListResponseDataSubscription` — the
#: model rejects anything less, which is the behaviour test_client asserts separately.
SUBSCRIPTION = {
    # `Items` карает minItems=1 — пустой список отвергается схемой банка, а не SDK.
    "Items": [{"amount": 100.0, "name": "Заказ № 1024", "quantity": 1.0, "vatType": "none"}],
    "amount": 100.0,
    "createdAt": "2026-08-17T12:00:00+03:00",
    "customerCode": "300123456",
    "operationId": "op-1",
    "paymentLink": "https://enter.tochka.com/pay/op-1",
    "status": "CREATED",
}


async def test_paginated_facade_returns_a_cursor_without_calling(
    client: Client, session: FakeSession
) -> None:
    cursor = client.get_subscription_list(customer_code="300123456")

    assert isinstance(cursor, MethodPaginator)
    assert session.calls == [], "курсор не должен ходить в сеть, пока его не использовали"


async def test_awaiting_the_cursor_fetches_the_first_page(client: Client, session: FakeSession) -> None:
    session.responses.append(ok(page([SUBSCRIPTION])))

    result = await client.get_subscription_list(customer_code="300123456")

    assert len(session.calls) == 1
    assert result.data.subscription[0].operation_id == "op-1"


async def test_iteration_stops_on_the_first_empty_page(client: Client, session: FakeSession) -> None:
    session.responses += [ok(page([SUBSCRIPTION])), ok(page([SUBSCRIPTION])), ok(page([]))]

    pages = [p async for p in client.get_subscription_list(customer_code="300123456")]

    assert len(pages) == 2, "пустая страница завершает обход и сама не отдаётся"
    assert len(session.calls) == 3


async def test_items_flattens_the_pages(client: Client, session: FakeSession) -> None:
    session.responses += [ok(page([SUBSCRIPTION, SUBSCRIPTION])), ok(page([SUBSCRIPTION])), ok(page([]))]

    items = [item async for item in client.get_subscription_list(customer_code="300123456").items()]

    assert len(items) == 3


async def test_page_number_advances_across_requests(client: Client, session: FakeSession) -> None:
    session.responses += [ok(page([SUBSCRIPTION])), ok(page([]))]

    _ = [p async for p in client.get_subscription_list(customer_code="300123456")]

    assert session.calls[0].params["page"] == 1
    assert session.calls[1].params["page"] == 2


async def test_paginated_method_class_declares_its_own_page_fields() -> None:
    method = GetSubscriptionList(customer_code="300123456")

    assert "page" in type(method).model_fields
    assert "per_page" in type(method).model_fields
