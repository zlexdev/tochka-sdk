"""What a generated facade mixin may rely on — nothing more than `execute`.

Keeping this an ABC (rather than letting mixins call into `Client` internals) is what
makes the generated files safe to delete and re-emit: they depend on one method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

from ..methods._base import BaseMethod

if TYPE_CHECKING:
    from ..pagination import MethodPaginator, PaginatedMethod

T = TypeVar("T")


class FacadeBase(ABC):
    """Base of every generated `<Domain>Facade` mixin."""

    @abstractmethod
    async def execute(self, method: BaseMethod[T]) -> T:
        """Run a method class and return its parsed response."""

    @abstractmethod
    def paginate(self, method: PaginatedMethod) -> MethodPaginator[Any]:
        """Wrap a paginated method in a lazy cursor — synchronous, fetches nothing yet."""

    @property
    @abstractmethod
    def customer_code(self) -> str | None:
        """Account context used to fill `{customerCode}` path segments."""
