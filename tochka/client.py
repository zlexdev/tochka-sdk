"""`Client` — the one object a user builds, and the only caller of the transport.

The endpoint surface is not written here: every domain contributes a generated facade
mixin (`tochka/facade/<domain>.py`), and `Client` inherits all of them, so the public API
stays flat (`await client.get_balance_info(...)`) while the file count stays sane.
"""

from __future__ import annotations

import asyncio
import uuid
from types import TracebackType
from typing import Any, Self, TypeVar, cast

from pydantic import ValidationError

from .config import Config
from .exceptions import ApiError, ResponseValidationError, TransportError
from .facade import GeneratedFacades
from .methods._base import BaseMethod
from .models._base import TochkaObject
from .pagination import MethodPaginator, PaginatedMethod
from .transport.errors import parse_error
from .transport.retry import RateLimiter, RetryPolicy
from .transport.session import BaseSession, HttpxSession, Response
from .types import Environment, Product

T = TypeVar("T")


class Client(GeneratedFacades):
    """Async Tochka Bank client.

    Usage::

        async with Client(token="...", customer_code="300123456") as client:
            balances = await client.get_balances_list()
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        config: Config | None = None,
        customer_code: str | None = None,
        environment: Environment = Environment.PRODUCTION,
        session: BaseSession | None = None,
        **options: Any,
    ) -> None:
        if config is None:
            if token is None:
                raise ValueError("нужен либо token, либо готовый config")
            config = Config(
                token=token,
                environment=environment,
                customer_code=customer_code,
                **options,
            )
        self.config = config
        self._session = session or HttpxSession(timeout=config.timeout)
        self._owns_session = session is None
        self._retry = RetryPolicy(
            max_retries=config.max_retries,
            base=config.backoff_base,
            maximum=config.backoff_max,
        )
        self._limiter = RateLimiter(config.requests_per_second)

    @property
    def customer_code(self) -> str | None:
        """Account context filled into `{customerCode}` path segments."""

        return self.config.customer_code

    async def execute(self, method: BaseMethod[T]) -> T:
        """Run one method class and return its parsed model."""

        # `_url_path` / `_request_payload` are the method's own API, underscored only so a
        # spec field named `payload` or `url` cannot shadow them.
        product = Product(method.__product__)
        url = self.config.base_url_for(product).rstrip("/") + method._url_path()
        verb = method.__http_method__
        payload = method._request_payload()
        params = payload if verb in ("GET", "DELETE") else None
        body = None if verb in ("GET", "DELETE") else payload

        response = await self._send(verb, url, params=params, body=body, method=method)
        return self._parse(method, response)

    def paginate(self, method: PaginatedMethod, *, page_size: int | None = None) -> MethodPaginator[Any]:
        """Lazy cursor over a paginated endpoint — nothing is fetched until awaited."""

        return MethodPaginator(self, method, page_size=page_size)

    async def _send(
        self,
        verb: str,
        url: str,
        *,
        params: dict[str, Any] | None,
        body: Any,
        method: BaseMethod[Any],
    ) -> Response:
        idempotent = verb in ("GET", "HEAD") or method.__idempotent_mutation__
        headers = self._headers(idempotent=idempotent, product=Product(method.__product__))

        attempt = 0
        while True:
            await self._limiter.acquire()
            try:
                response = await self._session.request(
                    verb,
                    url,
                    params=params,
                    json_body=body,
                    headers=headers,
                )
                if response.ok:
                    return response
                raise parse_error(response.status, response.url, response.payload, response.headers)
            except (ApiError, TransportError) as error:
                if not self._retry.should_retry(attempt, error, idempotent=idempotent):
                    raise
                await asyncio.sleep(self._retry.delay(attempt, error))
                attempt += 1

    def _headers(self, *, idempotent: bool, product: Product) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.token_for(product)}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.config.user_agent,
            **self.config.extra_headers,
        }
        if not idempotent:
            headers["Idempotency-Key"] = str(uuid.uuid4())
        return headers

    def _parse(self, method: BaseMethod[T], response: Response) -> T:
        model = method._returning()
        if model is None or not isinstance(response.payload, dict):
            # Binary bodies (statements ship as PDF) and unmodelled successes pass through.
            return cast("T", response.payload)
        try:
            parsed = model.model_validate(response.payload)
        except ValidationError as exc:
            raise ResponseValidationError(model.__name__, response.url, str(exc)) from exc
        if isinstance(parsed, TochkaObject):
            parsed.as_(self)
        return cast("T", parsed)

    async def close(self) -> None:
        """Close the session when this client owns it."""

        if self._owns_session:
            await self._session.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
