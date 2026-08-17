"""`BaseMethod[T]` — one endpoint call, expressed as a class.

A method instance is a validated request: its Pydantic fields are the endpoint's path,
query and body parameters, and the three ClassVars say where they go. The client stays
transport-only — it never knows what an endpoint is.
"""

from __future__ import annotations

import re
from collections.abc import Generator
from typing import Any, ClassVar, Generic, Self, TypeVar, get_args, get_origin

from pydantic import BaseModel, ConfigDict, PrivateAttr

from ..exceptions import ModelNotBoundError
from ..models._base import TochkaObject

T = TypeVar("T")

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class BaseMethod(BaseModel, Generic[T]):
    """Base of every generated method class.

    Subclasses set `__http_method__` and `__endpoint__`; the response type comes from the
    generic argument (`BaseMethod[GetBalanceInfoResponse]`), so it cannot drift from the
    declared return type of the facade wrapper.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid", frozen=True)

    __http_method__: ClassVar[str] = "GET"
    __endpoint__: ClassVar[str] = "/"
    #: Which Tochka product this endpoint belongs to — it selects the HOST, not merely a
    #: prefix: cyclops is served from api.tochka.com, pay-gateway from `uapi/pay/`.
    __product__: ClassVar[str] = "tochka-api"
    #: A write that is safe to replay — the client then sends an `Idempotency-Key` and lets
    #: the retry policy repeat it. Names match what the generator emits.
    __idempotent_mutation__: ClassVar[bool] = False
    #: Body fields are sent as JSON unless the endpoint is multipart.
    __multipart__: ClassVar[bool] = False
    #: The success body is not JSON (statement PDFs, QR images) — returned as raw bytes.
    __binary_response__: ClassVar[bool] = False

    _bound_client: Any = PrivateAttr(default=None)

    def as_(self, client: Any) -> Self:
        """Attach a client so the method can be awaited directly.

        This is what makes a bound model method work: `payment.get_payment_status()`
        returns THIS object (synchronously, no request yet), and awaiting it runs the call.
        """

        self._bound_client = client
        return self

    def __await__(self) -> Generator[Any, None, Any]:
        if self._bound_client is None:
            raise ModelNotBoundError(type(self).__name__, "await")
        awaitable: Generator[Any, None, Any] = self._bound_client.execute(self).__await__()
        return awaitable

    @classmethod
    def _returning(cls) -> type[Any] | None:
        """The response model this method parses into, read off the generic argument.

        Pydantic rewrites a generic model's `__orig_bases__` (they end up as
        `BaseModel, Generic[T]`), so the parametrisation is NOT there — it lives in
        `__pydantic_generic_metadata__` on the parametrised class inside the MRO.
        Reading `__orig_bases__` here returns None for every generated method, and every
        response silently degrades to a raw dict.
        """

        for klass in cls.__mro__:
            metadata = getattr(klass, "__pydantic_generic_metadata__", None)
            if metadata:
                args = metadata.get("args") or ()
                if args and isinstance(args[0], type):
                    return args[0]
        for base in getattr(cls, "__orig_bases__", ()):
            origin = get_origin(base)
            if origin is not None and isinstance(origin, type) and issubclass(origin, BaseMethod):
                args = get_args(base)
                if args and isinstance(args[0], type):
                    return args[0]
        return None

    # Every helper below is underscore-prefixed on purpose: field names come from the
    # bank's spec, which ships fields called `payload`, `client` and `url`. A public
    # helper of that name would be shadowed by the field and silently unreachable.
    def _path_fields(self) -> set[str]:
        """Field names consumed by the URL template."""

        return {match.group(1) for match in _PLACEHOLDER.finditer(self.__endpoint__)}

    def _url_path(self) -> str:
        """`__endpoint__` with its placeholders filled from this instance's fields."""

        values = self.model_dump(by_alias=False, exclude_none=True)
        return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), self.__endpoint__)

    def _request_payload(self) -> dict[str, Any]:
        """Everything not consumed by the path, keyed by wire alias."""

        consumed = self._path_fields()
        dumped = self.model_dump(by_alias=True, exclude_none=True)
        aliases = {name: (field.alias or name) for name, field in type(self).model_fields.items()}
        return {
            wire: value
            for name, wire in aliases.items()
            if name not in consumed and (value := dumped.get(wire)) is not None
        }


def passthrough(value: Any) -> Any:
    """Response parser for endpoints whose success body is not a modelled object."""

    return value


__all__ = ["BaseMethod", "TochkaObject", "passthrough"]
