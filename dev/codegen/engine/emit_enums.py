"""Render ``enums/<module>.py`` — one ``StrEnum`` per generated enum for the domain.

Enums live in their own package (mirroring ``methods/`` and ``models/``) so both the model
DTOs and the method-classes import the same enum symbols from a single source of truth.
"""

from __future__ import annotations

from . import render
from .build import GeneratedDomain
from .types import EnumSpec


def emit(gen: GeneratedDomain) -> str:
    out = [
        render.GENERATED_HEADER,
        render.module_doc(gen.title, "domain enums"),
        "\nfrom enum import StrEnum\n\n",
    ]
    for enum in gen.enums.values():
        out.append(_render_enum(enum))
        out.append("\n")
    return "".join(out)


def _render_enum(enum: EnumSpec) -> str:
    lines = [f"class {enum.name}(StrEnum):", f'    """{enum.name} values."""', ""]
    for member, value in enum.members:
        lines.append(f'    {member} = "{value}"')
    return "\n".join(lines) + "\n"
