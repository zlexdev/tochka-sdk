"""`TochkaObject` — the base every generated DTO extends.

Response models are built by the codegen from the portal's inline schemas; this base adds
the two things the wire needs (alias population, forward-compatible extra fields) and the
client binding that makes `await payment.get()` possible on a returned model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict, PrivateAttr

from ..exceptions import ModelNotBoundError

if TYPE_CHECKING:
    from ..client import Client


class TochkaObject(BaseModel):
    """Base DTO: wire aliases in, snake_case out, unknown fields preserved.

    `extra="allow"` is deliberate — the bank ships new response fields without a version
    bump, and dropping them would make an SDK upgrade the only way to see new data.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    _client: Client | None = PrivateAttr(default=None)

    def as_(self, client: Client) -> Self:
        """Attach `client`, recursively, so bound methods work on nested models too."""

        self._client = client
        for value in self.__dict__.values():
            for item in value if isinstance(value, list | tuple) else (value,):
                if isinstance(item, TochkaObject):
                    item.as_(client)
        return self

    def bound_client(self) -> Client:
        """The bound client, or `ModelNotBoundError` when the model was hand-built.

        Deliberately a method named `bound_client`, not a `client` property: Tochka's
        subscription payloads carry a wire field literally called `client`, and a property
        of that name would shadow it (pydantic warns, then the data is unreachable).
        """

        if self._client is None:
            raise ModelNotBoundError(type(self).__name__, "bound_client")
        return self._client

    def raw(self) -> dict[str, Any]:
        """The payload as the bank sent it (wire aliases, extras included)."""

        return self.model_dump(by_alias=True)
