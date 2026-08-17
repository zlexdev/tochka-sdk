"""Test doubles — a fake session so no test ever needs the network or a token."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from tochka import Client, Config
from tochka.transport.session import BaseSession, Response


@dataclass
class RecordedCall:
    method: str
    url: str
    params: dict[str, Any] | None
    json_body: Any
    headers: dict[str, str]


@dataclass
class FakeSession(BaseSession):
    """Replays a queued list of responses and records what was sent."""

    responses: list[Response] = field(default_factory=list)
    calls: list[RecordedCall] = field(default_factory=list)
    closed: bool = False

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        files: dict[str, Any] | None = None,
    ) -> Response:
        self.calls.append(RecordedCall(method, url, params, json_body, headers or {}))
        if not self.responses:
            raise AssertionError(f"неожиданный запрос {method} {url}: очередь ответов пуста")
        return self.responses.pop(0)

    async def close(self) -> None:
        self.closed = True


def ok(payload: Any, *, status: int = 200, url: str = "https://enter.tochka.com/uapi/x") -> Response:
    return Response(status=status, headers={}, payload=payload, url=url)


def fail(status: int, code: str, message: str, **headers: str) -> Response:
    return Response(
        status=status,
        headers=headers,
        payload={
            "code": str(status),
            "id": "test-id",
            "message": message,
            "Errors": [{"errorCode": code, "message": message}],
        },
        url="https://enter.tochka.com/uapi/x",
    )


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def client(session: FakeSession) -> Client:
    config = Config(
        token="test-token", customer_code="300123456", requests_per_second=1000.0, backoff_base=0.0
    )
    return Client(config=config, session=session)
