"""Tochka's webhook signing key — fetched, cached, and refreshable.

The bank publishes one RSA public key as a bare JWK. Hard-coding it (as the portal's own
example does) means a key rotation silently rejects every webhook, so the default is to
fetch it and cache it in memory.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from jwt import PyJWK

from ..exceptions import TransportError

PUBLIC_KEY_URL = "https://enter.tochka.com/doc/openapi/static/keys/public"


class KeyProvider:
    """Supplies the verification key, caching it until `refresh()` is called."""

    def __init__(self, *, url: str = PUBLIC_KEY_URL, timeout: float = 10.0) -> None:
        self._url = url
        self._timeout = timeout
        self._key: PyJWK | None = None

    async def get(self) -> PyJWK:
        """The cached key, fetching it on first use."""

        if self._key is None:
            self._key = await self._fetch()
        return self._key

    async def refresh(self) -> PyJWK:
        """Drop the cache and fetch again — call this on a signature failure, once."""

        self._key = await self._fetch()
        return self._key

    async def _fetch(self) -> PyJWK:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._url)
                response.raise_for_status()
                payload: Any = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise TransportError(self._url, str(exc)) from exc
        return PyJWK.from_dict(payload)


class StaticKeyProvider(KeyProvider):
    """A key supplied by the caller — for tests, air-gapped deploys, or a pinned key."""

    def __init__(self, jwk: dict[str, Any] | PyJWK) -> None:
        super().__init__()
        self._key = jwk if isinstance(jwk, PyJWK) else PyJWK.from_dict(jwk)

    async def refresh(self) -> PyJWK:
        if self._key is None:  # pragma: no cover — constructor guarantees a key
            raise ValueError("статический ключ не задан")
        return self._key
