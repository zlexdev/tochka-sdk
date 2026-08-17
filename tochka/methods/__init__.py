"""Method classes — one per endpoint, generated from the spec.

`_base` is hand-written; every sibling module is emitted by `dev.codegen` and safe to
delete and regenerate.
"""

from __future__ import annotations

from ._base import BaseMethod, passthrough

__all__ = ["BaseMethod", "passthrough"]
