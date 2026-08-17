"""Pagination — two wire styles, one object the caller iterates.

Tochka pages two different ways: `page`/`perPage` on the Open Banking surface and
`limit`/`offset` on the acquiring one. Both are hidden behind `MethodPaginator`, which a
generated facade method returns *synchronously* — nothing is fetched until it is awaited
or iterated. There is deliberately no `*_paginated` twin of any method.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from pydantic import Field

from .methods._base import BaseMethod

if TYPE_CHECKING:
    from .client import Client

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 100


class PageMethod(BaseMethod[T], Generic[T]):
    """A `page`/`perPage` paginated call."""

    __page_size__: ClassVar[int] = DEFAULT_PAGE_SIZE

    page: int | None = Field(default=None)
    per_page: int | None = Field(default=None, alias="perPage")

    def next_page(self, index: int, size: int) -> PageMethod[T]:
        """This call, aimed at page `index` (1-based)."""

        return self.model_copy(update={"page": index + 1, "per_page": size})


class OffsetMethod(BaseMethod[T], Generic[T]):
    """A `limit`/`offset` paginated call."""

    __page_size__: ClassVar[int] = DEFAULT_PAGE_SIZE

    limit: int | None = Field(default=None)
    offset: int | None = Field(default=None)

    def next_page(self, index: int, size: int) -> OffsetMethod[T]:
        """This call, aimed at the page starting `index * size` items in."""

        return self.model_copy(update={"limit": size, "offset": index * size})


PaginatedMethod = PageMethod[Any] | OffsetMethod[Any]


class MethodPaginator(Generic[T]):
    """Lazy cursor over a paginated endpoint.

    Nothing is requested until the paginator is awaited (first page) or iterated::

        first = await client.get_payments_by_qrc_id(...)          # one request
        async for page in client.get_payments_by_qrc_id(...):     # page after page
            ...
        async for item in client.get_payments_by_qrc_id(...).items():
            ...
    """

    def __init__(self, client: Client, method: PaginatedMethod, *, page_size: int | None = None) -> None:
        self._client = client
        self._method = method
        self._size = page_size or type(method).__page_size__

    def __await__(self) -> Generator[Any, None, T]:
        return self.first().__await__()

    async def first(self) -> T:
        """Fetch just the first page."""

        result: T = await self._client.execute(self._method.next_page(0, self._size))
        return result

    async def __aiter__(self) -> AsyncIterator[T]:
        """Yield page after page until one comes back empty."""

        index = 0
        while True:
            page = await self._client.execute(self._method.next_page(index, self._size))
            if _is_empty(page):
                return
            yield page
            index += 1

    async def items(self) -> AsyncIterator[Any]:
        """Flatten the pages: yield each element of every page's list field."""

        async for page in self:
            for item in _items_of(page):
                yield item


def _payload_lists(page: Any) -> list[list[Any]]:
    """Every list field of the page's `Data` envelope (`{"Data": {"Payments": [...]}}`)."""

    data = getattr(page, "data", page)
    fields = getattr(data, "__dict__", None)
    if not isinstance(fields, dict):
        return []
    return [value for value in fields.values() if isinstance(value, list)]


def _items_of(page: Any) -> list[Any]:
    lists = _payload_lists(page)
    return lists[0] if lists else []


def _is_empty(page: Any) -> bool:
    """A page ends the walk when its payload list is empty.

    A page with no list field at all is treated as non-empty and terminal — guessing
    "empty" there would silently truncate a response shape nobody has seen yet.
    """

    lists = _payload_lists(page)
    return bool(lists) and not lists[0]
