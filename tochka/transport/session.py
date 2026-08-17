"""HTTP session — the only place in the SDK that touches the network.

Behind an ABC so a test can swap in a fake without patching, and so a future transport
(mTLS with a Минцифры certificate, a proxied egress) is a sibling class rather than an
`if` inside this one.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from ..exceptions import TransportError


@dataclass(frozen=True, slots=True)
class Response:
    """One HTTP answer, already decoded."""

    status: int
    headers: dict[str, str]
    payload: Any
    url: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class BaseSession(ABC):
    """Contract every transport implements."""

    @abstractmethod
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
        """Perform one request; raise `TransportError` when no response was produced."""

    @abstractmethod
    async def close(self) -> None:
        """Release the underlying connections."""


class HttpxSession(BaseSession):
    """Default transport: one pooled `httpx.AsyncClient` per client instance."""

    def __init__(self, *, timeout: float, proxy: str | None = None) -> None:
        self._client = httpx.AsyncClient(timeout=timeout, proxy=proxy, follow_redirects=False)

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
        try:
            response = await self._client.request(
                method,
                url,
                params=params,
                json=json_body if files is None else None,
                data=json_body if files is not None else None,
                headers=headers,
                files=files,
            )
        except httpx.HTTPError as exc:
            raise TransportError(url, str(exc)) from exc

        return Response(
            status=response.status_code,
            headers={key.lower(): value for key, value in response.headers.items()},
            payload=_decode(response),
            url=str(response.url),
        )

    async def close(self) -> None:
        await self._client.aclose()


def _decode(response: httpx.Response) -> Any:
    """JSON when the bank says JSON, raw bytes otherwise (statements ship as PDF)."""

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type:
        return response.content
    try:
        return response.json()
    except json.JSONDecodeError:
        return response.text
