"""Render ``facade/<module>.py`` — a mixin class of endpoint methods inherited by ``Client``.

``Client`` subclasses every ``*Facade`` mixin, so ``await client.item_info(item_id=…)``
constructs the generated method-class and awaits it through ``Client.__call__`` (``self`` *is*
the client). ``user_id`` path segments default to the client's account. Paginated endpoints
stay sync and return a ``MethodPaginator``.
"""

from __future__ import annotations

import re
from dataclasses import replace

from . import dedup, naming, render
from .build import GeneratedDomain, MethodSpec
from .types import FieldSpec, ModelSpec


def _base_type(annotation: str) -> str:
    """Drop ``| None`` unions and whitespace to get the leading type name."""

    return annotation.split("|")[0].strip()


def facade_class(module: str) -> str:
    return f"{naming.pascal(module)}Facade"


def emit(gen: GeneratedDomain) -> str:
    sig_text = _signature_text(gen)
    out = [
        render.GENERATED_HEADER,
        render.module_doc(gen.title, "client facade mixin"),
        "\nfrom __future__ import annotations\n",
        _import_block(gen, sig_text),
        "\n\n",
        f"class {facade_class(gen.module)}(FacadeBase):\n",
        f'    """``Client`` mixin — {gen.title} endpoints."""\n\n',
    ]
    for method in gen.methods:
        out.append(_render_call(method, gen.models))
        out.append("\n\n")
    return "".join(out)


def _signature_text(gen: GeneratedDomain) -> str:
    parts: list[str] = []
    for m in gen.methods:
        parts.append(m.generic_arg)
        parts.append(m.return_symbol or "")
        for f in m.fields:
            parts.append(f.annotation)
            # A body-model field is flattened into its sub-fields at render time — the
            # model class still appears here (needed for the reconstruction call import),
            # plus its sub-field annotations so their enums/models get imported too.
            model = gen.models.get(_base_type(f.annotation))
            if model is not None:
                parts.extend(sub.annotation for sub in model.fields)
    return " ".join(parts)


def _import_block(gen: GeneratedDomain, text: str) -> str:
    lines: list[str] = []
    if re.search(r"\bAny\b", text):
        lines.append("from typing import Any")
    needs: set[str] = set()
    if "TZDatetime" in text:
        needs.add("TZDatetime")
    if re.search(r"\bdatetime\b", text):
        needs.add("datetime")
    if re.search(r"\bdate\b", text):
        needs.add("date")
    lines.extend(render.datetime_imports(needs, in_methods=True))
    method_classes = sorted(m.class_name for m in gen.methods)
    if method_classes:
        lines.append(f"from ..methods.{gen.module} import {', '.join(method_classes)}")

    known_models = set(gen.models) | set(gen.root_models)
    candidates = {m.return_symbol for m in gen.methods if m.return_symbol} | {
        s for s in known_models if re.search(rf"\b{s}\b", text)
    }
    models_used = sorted(
        candidates - set(gen.shared_imports)
    )  # shared names import from _shared/common, not the domain module
    if models_used:
        lines.append(f"from ..models.{gen.module} import {', '.join(models_used)}")
    enums_used = sorted(e for e in gen.enums if re.search(rf"\b{e}\b", text))
    if enums_used:
        lines.append(f"from ..enums.{gen.module} import {', '.join(enums_used)}")
    lines.extend(dedup.shared_import_lines(gen, text, in_models_pkg=False))

    lines.append("from ..models._helpers import _resolve_customer_code")
    if any(m.paginated for m in gen.methods):
        lines.append("from ..pagination import MethodPaginator")
    lines.append("from ._base import FacadeBase")
    return "\n".join(lines) + "\n"


def _return_annotation(m: MethodSpec) -> str:
    if m.paginated:
        return f"MethodPaginator[{m.return_symbol or 'None'}]"
    if m.binary:
        return "bytes"
    return m.generic_arg if m.generic_arg != "None" else "None"


def _facade_fields(m: MethodSpec, models: dict[str, ModelSpec]) -> tuple[list[FieldSpec], list[str]]:
    """Flatten body-model params into their fields; return (facade params, method-class call args).

    A param whose type is a generated object model (e.g. ``message: PostSendMessageMessage``)
    is replaced by that model's own fields as top-level params, and the call reconstructs the
    model inside (``message=PostSendMessageMessage(text=text)``). The method class is unchanged —
    this is a facade-only ergonomic unwrap. Sub-field names that clash with a sibling are
    prefixed with the parent name (``message_text``).
    """

    accounts = set(m.account_params)

    def _is_model(f: FieldSpec) -> bool:
        return f.name not in accounts and bool(
            models.get(_base_type(f.annotation)) and models[_base_type(f.annotation)].fields
        )

    # Plain (non-flattened) params own their names — pre-register so a flattened
    # sub-field that clashes yields (gets a parent prefix / numeric suffix), never the reverse.
    seen: set[str] = {f.name for f in m.fields if not _is_model(f)}

    def _uniq(preferred: str, *alts: str) -> str:
        for cand in (preferred, *alts):
            if cand not in seen:
                seen.add(cand)
                return cand
        i = 2
        while f"{preferred}_{i}" in seen:
            i += 1
        seen.add(f"{preferred}_{i}")
        return f"{preferred}_{i}"

    facade_fields: list[FieldSpec] = []
    call_args: list[str] = []
    for f in m.fields:
        if _is_model(f):
            sub_exprs: list[str] = []
            for sub in models[_base_type(f.annotation)].fields:
                pname = _uniq(sub.name, f"{f.name}_{sub.name}")
                facade_fields.append(sub if pname == sub.name else replace(sub, name=pname))
                sub_exprs.append(f"{sub.name}={pname}")
            call_args.append(f"{f.name}={_base_type(f.annotation)}({', '.join(sub_exprs)})")
        else:
            facade_fields.append(f)
            call_args.append(
                f"{f.name}=_resolve_customer_code(self) if {f.name} is None else {f.name}"
                if f.name in accounts
                else f"{f.name}={f.name}",
            )
    return facade_fields, call_args


def _render_call(m: MethodSpec, models: dict[str, ModelSpec]) -> str:
    accounts = set(m.account_params)
    facade_fields, call_args = _facade_fields(m, models)
    required = [f for f in facade_fields if f.required and f.name not in accounts]
    optional = [f for f in facade_fields if not f.required or f.name in accounts]

    params = [f"{f.name}: {f.annotation}" for f in required]
    for f in optional:
        annot = f.annotation if f.name not in accounts else f"{f.annotation} | None"
        params.append(f"{f.name}: {annot} = {'None' if f.name in accounts else (f.default_expr or 'None')}")
    signature = ", ".join(["self", *params])

    call = f"{m.class_name}({', '.join(call_args)})"

    method_name = m.method_name
    doc = render.class_docstring(
        m.doc, "Args", [(f.name, f.description) for f in facade_fields], indent="        "
    )
    kw, invoke = (
        ("def", f"self.paginate({call})") if m.paginated else ("async def", f"await self.execute({call})")
    )
    return "\n".join(
        [
            f"    {kw} {method_name}({signature}) -> {_return_annotation(m)}:",
            doc.rstrip("\n"),
            f"        return {invoke}",
        ],
    )
