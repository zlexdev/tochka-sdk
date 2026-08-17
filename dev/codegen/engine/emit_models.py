"""Render ``models/<module>.py`` — DTOs (extend ``TochkaObject``) + generated bound methods.

Enums are emitted separately into ``enums/<module>.py`` and imported here by name.
"""

from __future__ import annotations

import re

from . import dedup, render
from .build import GeneratedDomain
from .entities import BoundMethod
from .types import ModelSpec


def emit(gen: GeneratedDomain) -> str:
    text = _scan_text(gen)
    out = [
        render.GENERATED_HEADER,
        render.module_doc(gen.title, "domain models", see=gen.docs_url),
        "\nfrom __future__ import annotations\n",
        _import_block(gen, text),
        "\n",
    ]
    for model in gen.models.values():
        out.append(_render_model(gen, model))
        out.append("\n")
    for name, inner in gen.root_models.items():
        out.append(f"class {name}(RootModel[{inner}]):\n")
        out.append(f'    """Root wrapper for a top-level ``{inner}`` response."""\n\n')
    return "".join(out)


def _scan_text(gen: GeneratedDomain) -> str:
    parts: list[str] = []
    for m in gen.models.values():
        for f in m.fields:
            parts.append(f.annotation)
            parts.append(f.assignment or "")
    for bms in gen.bound.values():
        for bm in bms:
            parts.extend(a.annotation for a in bm.args)
    parts.extend(gen.root_models.values())
    return " ".join(parts)


def _import_block(gen: GeneratedDomain, text: str) -> str:
    lines: list[str] = []
    typing_syms = (["Any"] if "Any" in text else []) + (["TYPE_CHECKING"] if gen.bound else [])
    if typing_syms:
        lines.append(f"from typing import {', '.join(sorted(typing_syms))}")
    lines.extend(render.datetime_imports(_needs(text), in_methods=False))
    pydantic_syms = (["Field"] if any(m.fields for m in gen.models.values()) else []) + (
        ["RootModel"] if gen.root_models else []
    )
    lines.append(
        f"from pydantic import {', '.join(pydantic_syms)}" if pydantic_syms else "from pydantic import Field"
    )
    lines.append("from ._base import TochkaObject")

    used_enums = sorted(e for e in gen.enums if re.search(rf"\b{e}\b", text))
    if used_enums:
        lines.append(f"from ..enums.{gen.module} import {', '.join(used_enums)}")
    lines.extend(dedup.shared_import_lines(gen, text, in_models_pkg=True))
    if gen.bound:
        uses_resolver = any(
            "_resolve_customer_code" in expr
            for bms in gen.bound.values()
            for bm in bms
            for _, expr in bm.fills
        )
        if uses_resolver:
            lines.append("from ._helpers import _resolve_customer_code")
        method_classes = sorted({bm.method_class for bms in gen.bound.values() for bm in bms})
        lines.append("\nif TYPE_CHECKING:")
        lines.append(f"    from ..methods.{gen.module} import {', '.join(method_classes)}")
    return "\n".join(lines) + "\n"


def _needs(text: str) -> set[str]:
    out: set[str] = set()
    if "TZDatetime" in text:
        out.add("TZDatetime")
    if re.search(r"\bdatetime\b", text):
        out.add("datetime")
    if re.search(r"\bdate\b", text):
        out.add("date")
    return out


def _render_model(gen: GeneratedDomain, model: ModelSpec) -> str:
    bound = gen.bound.get(model.name, [])
    doc = render.class_docstring(
        model.doc or f"{model.name} response model.",
        "Attributes",
        [(f.name, f.description) for f in model.fields],
    )
    lines = [f"class {model.name}(TochkaObject):", doc.rstrip("\n")]
    for f in model.fields:
        lines.append(render.field_line(f.name, f.annotation, f.assignment).rstrip("\n"))
    for bm in bound:
        lines.append("")
        lines.append(_render_bound(gen, bm))
    if not model.fields and not bound:
        lines.append("    pass")
    return "\n".join(lines) + "\n"


def _render_bound(gen: GeneratedDomain, bm: BoundMethod) -> str:
    required = [a for a in bm.args if a.required]
    optional = [a for a in bm.args if not a.required]
    params = [f"{a.name}: {a.annotation}" for a in required]
    params += [f"{a.name}: {a.annotation} = {a.default_expr or 'None'}" for a in optional]
    signature = ", ".join(["self", *params])

    call_args = [f"{fld}={expr}" for fld, expr in bm.fills] + [f"{a.name}={a.name}" for a in bm.args]
    call = f"{bm.method_class}({', '.join(call_args)})"

    return "\n".join(
        [
            f"    def {bm.method_name}({signature}) -> {bm.method_class}:",
            f'        """Build an awaitable :class:`{bm.method_class}` bound to this object'
            ' (await to execute)."""',
            f"        from ..methods.{gen.module} import {bm.method_class}",
            "",
            f"        return {call}.as_(self._client)",
        ],
    )
