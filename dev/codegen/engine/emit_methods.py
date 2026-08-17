"""Render ``methods/<module>.py`` — one ``BaseMethod``/``PageMethod`` subclass per endpoint."""

from __future__ import annotations

import re

from . import dedup, render
from .build import PAGINATION_STYLES, GeneratedDomain, MethodSpec


def emit(gen: GeneratedDomain) -> str:
    text = _scan_text(gen)
    out = [
        render.GENERATED_HEADER,
        render.module_doc(gen.title, "domain endpoints"),
        "\nfrom __future__ import annotations\n",
        _import_block(gen, text),
        "\n",
    ]
    note = f"See: {gen.docs_url}"
    for method in gen.methods:
        out.append(_render_method(method, note))
        out.append("\n")
    return "".join(out)


def _scan_text(gen: GeneratedDomain) -> str:
    parts: list[str] = []
    for m in gen.methods:
        parts.append(m.generic_arg)
        for f in m.fields:
            parts.append(f.annotation)
            parts.append(f.assignment or "")
    return " ".join(parts)


def _import_block(gen: GeneratedDomain, text: str) -> str:
    lines = ["from typing import ClassVar" + (", Any" if "Any" in text else "")]
    lines.extend(render.datetime_imports(_needs(text), in_methods=True))

    if any(m.fields for m in gen.methods):
        lines.append("from pydantic import Field")

    bases = {m.base for m in gen.methods}
    paging_bases = sorted(bases & {base for base, _ in PAGINATION_STYLES.values()})
    if paging_bases:
        lines.append(f"from ..pagination import {', '.join(paging_bases)}")
    if "BaseMethod" in bases:
        lines.append("from ._base import BaseMethod")

    all_models = list(gen.models) + list(gen.root_models)
    models_used = sorted(m for m in all_models if re.search(rf"\b{m}\b", text))
    if models_used:
        lines.append(f"from ..models.{gen.module} import {', '.join(models_used)}")
    enums_used = sorted(e for e in gen.enums if re.search(rf"\b{e}\b", text))
    if enums_used:
        lines.append(f"from ..enums.{gen.module} import {', '.join(enums_used)}")
    lines.extend(dedup.shared_import_lines(gen, text, in_models_pkg=False))
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


def _render_method(m: MethodSpec, note: str) -> str:
    doc = render.class_docstring(m.doc, "Args", [(f.name, f.description) for f in m.fields], note=note)
    lines = [f"class {m.class_name}({m.base}[{m.generic_arg}]):", doc.rstrip("\n"), ""]

    lines.append(f'    __http_method__: ClassVar[str] = "{m.http_method}"')
    lines.append(f'    __endpoint__: ClassVar[str] = "{m.endpoint}"')
    # The product decides the HOST, not just a path prefix — cyclops lives on
    # api.tochka.com. Emitted on every method so the client never has to guess.
    lines.append(f'    __product__: ClassVar[str] = "{m.product}"')
    if m.idempotent:
        lines.append("    __idempotent_mutation__: ClassVar[bool] = True")
    if m.multipart:
        lines.append("    __multipart__: ClassVar[bool] = True")
    if m.binary:
        lines.append("    __binary_response__: ClassVar[bool] = True")

    if m.fields:
        lines.append("")
        for f in m.fields:
            lines.append(render.field_line(f.name, f.annotation, f.assignment).rstrip("\n"))
    return "\n".join(lines) + "\n"
