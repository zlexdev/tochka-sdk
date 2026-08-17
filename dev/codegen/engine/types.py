"""Schema → Python type + ``Field(...)`` mapping, with enum / nested-model collection.

:class:`ModelBuilder` walks a domain's component schemas once, producing:

* ``models`` — one :class:`ModelSpec` per object schema (extends ``TochkaObject``),
* ``enums`` — one :class:`EnumSpec` per string-enum (top-level or inline),
* a reusable :meth:`resolve` used by both model and method emission.

Constraint map: ``minLength→min_length``, ``maxLength→max_length``, ``minimum→ge``,
``maximum→le``, ``exclusiveMinimum→gt``, ``exclusiveMaximum→lt``, ``pattern``, ``default``,
``description``/``title``→``description``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..parser import Domain, Resolver
from . import naming

_ENUM_INVALID = re.compile(r"\W+")

_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _translit(text: str) -> str:
    return "".join(_TRANSLIT.get(ch, _TRANSLIT.get(ch.lower(), ch)) for ch in text)


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """A rendered model/method field.

    ``assignment`` is the RHS of the field line, or ``None`` for a bare required field
    with no constraints/alias (``name: int``). ``Field(...)`` is only used when the field
    carries a constraint (ge/le/min_length/…) or a wire ``alias``.
    """

    name: str
    annotation: str
    assignment: str | None
    wire_name: str
    description: str | None  # rendered in the class docstring, not in ``Field(...)``
    required: bool
    default_expr: str | None  # plain default for a call signature (None ⇒ required, no default)


@dataclass(slots=True)
class ModelSpec:
    """A generated Pydantic model."""

    name: str
    fields: list[FieldSpec] = field(default_factory=list)
    doc: str | None = None


@dataclass(slots=True)
class EnumSpec:
    """A generated ``StrEnum``."""

    name: str
    members: list[tuple[str, str]] = field(default_factory=list)  # (MEMBER, "value")


@dataclass(frozen=True, slots=True)
class Resolved:
    """Result of mapping one schema node."""

    annotation: str
    needs: frozenset[str]  # type symbols requiring an import (datetime, date, Any, …)


def _enum_member(value: str) -> str:
    token = _ENUM_INVALID.sub("_", _translit(value)).strip("_").upper() or "EMPTY"
    if token[0].isdigit():
        token = f"V_{token}"
    if token in {"I", "O", "L"}:  # E741 ambiguous single-letter names
        token = f"{token}_"
    return token


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _clean_desc(text: str) -> str:
    """Strip HTML tags (``<br/>`` …) and collapse whitespace in a description; keep markdown."""

    return _escape(_WS.sub(" ", _HTML_TAG.sub(" ", text)))


_BACKTICK = re.compile(r"`([^`]+)`")
_ENUM_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _desc_enum_values(description: str) -> list[str] | None:
    """Extract an enum value set from backtick-listed tokens in a prose description.

    Tochka often documents allowed string values only in the description (``\\`Credit\\`,
    \\`Debit\\`, …``) instead of a formal ``enum:``. Returns the distinct tokens
    when there are ≥2 identifier-like ones, else ``None`` (avoids false positives on paths,
    formats, single code refs).
    """

    tokens = [t for t in _BACKTICK.findall(description) if _ENUM_TOKEN.match(t)]
    unique = list(dict.fromkeys(tokens))
    return unique if len(unique) >= 2 else None


class ModelBuilder:
    """Builds model/enum specs and maps schema nodes to Python types for one domain."""

    def __init__(self, domain: Domain) -> None:
        self._schemas = domain.schemas
        self._resolver = Resolver({"components": {"schemas": domain.schemas}})
        self.models: dict[str, ModelSpec] = {}
        self.enums: dict[str, EnumSpec] = {}
        self.root_models: dict[str, str] = {}  # name -> inner annotation (RootModel wrappers)

    def build(self) -> None:
        """Emit a model / enum / root-model for every top-level component schema."""

        for name, schema in self._schemas.items():
            cls = naming.pascal(name)
            if _is_object(schema):
                self._model_for(cls, schema)
            elif "enum" in schema and schema.get("type") == "string":
                self._enum_for(cls, schema)
            else:  # array / primitive top-level schema → RootModel (a valid BaseMethod return)
                self.root_models[cls] = self.resolve(schema, cls, "root").annotation

    def model_from_inline(self, name: str, schema: dict[str, Any]) -> str:
        """Register a model from an inline (non-component) object schema; return its name."""

        self._model_for(name, schema)
        return name

    def resolve(self, schema: dict[str, Any], owner: str, field_name: str) -> Resolved:
        """Map a schema node to a Python annotation, registering nested types."""

        if "$ref" in schema:
            return self._resolve_ref(schema["$ref"])

        stype = schema.get("type")
        if "enum" in schema and stype == "string":
            enum_cls = naming.enum_class_name(owner, field_name)
            self._enum_for(enum_cls, schema)
            return Resolved(enum_cls, frozenset())
        if stype == "string":
            fmt = schema.get("format")
            if fmt == "date-time":
                return Resolved("TZDatetime", frozenset({"TZDatetime"}))
            if fmt == "date":
                return Resolved("date", frozenset({"date"}))
            desc_values = _desc_enum_values(schema.get("description") or schema.get("title") or "")
            if desc_values:
                enum_cls = naming.enum_class_name(owner, field_name)
                self._enum_from_values(enum_cls, desc_values)
                return Resolved(enum_cls, frozenset())
            return Resolved("str", frozenset())
        if stype == "integer":
            return Resolved("int", frozenset())
        if stype == "number":
            return Resolved("float", frozenset())
        if stype == "boolean":
            return Resolved("bool", frozenset())
        if stype == "array":
            inner = self.resolve(schema.get("items", {}), owner, field_name)
            return Resolved(f"list[{inner.annotation}]", inner.needs)
        if stype == "object" or "properties" in schema:
            if schema.get("properties"):
                nested = naming.pascal(f"{owner}_{field_name}")
                self._model_for(nested, schema)
                return Resolved(nested, frozenset())
            return Resolved("dict[str, Any]", frozenset({"Any"}))
        return Resolved("Any", frozenset({"Any"}))

    def _enum_default(self, annotation: str, value: object) -> str | None:
        """`("Kind", "standard")` → `"Kind.STANDARD"`, or None when the field is not an enum."""

        enum_name = annotation.split(" |")[0].strip()
        spec = self.enums.get(enum_name)
        if spec is None or not isinstance(value, str):
            return None
        for member, member_value in spec.members:
            if member_value == value:
                return f"{enum_name}.{member}"
        return None

    def field_spec(
        self,
        name: str,
        wire: str,
        schema: dict[str, Any],
        required: bool,
        owner: str,
        description: str | None = None,
    ) -> FieldSpec:
        """Build a fully-rendered :class:`FieldSpec` for a property/param/body field.

        A default on an enum-typed field is emitted as the enum MEMBER, not the raw string:
        `x: Kind = "standard"` is a type error, and mypy reports it on generated code the
        author cannot edit.

        ``description`` overrides the schema's own description — used for path/query params
        whose description lives on the parameter object, not its ``schema`` sub-node.
        """

        resolved = self.resolve(schema, owner, name)
        annotation = resolved.annotation
        constraints = _constraint_kwargs(schema)
        # Array defaults are unreliable: Tochka specs put a *scalar* default on an array param
        # (``chat_types: {type: array, default: "u2i"}``) — emitting it verbatim yields
        # ``list[T] = "u2i"`` (wrong type), and a real list default is a mutable default in a
        # call signature anyway. Treat every optional array as ``list[T] | None = None``; the
        # server applies its own default when the field is omitted.
        is_array = schema.get("type") == "array"
        has_default = "default" in schema and not is_array

        if required:
            head = "..."
            default_expr: str | None = None
        elif has_default:
            head = default_expr = self._enum_default(annotation, schema["default"]) or _literal(
                schema["default"],
            )
            if head == "None":  # a null default is still optional — keep the annotation nullable
                annotation = f"{annotation} | None"
        else:
            annotation = f"{annotation} | None"
            head = default_expr = "None"

        alias = [f'alias="{wire}"'] if wire != name else []
        if constraints or alias:
            assignment: str | None = f"Field({', '.join([head, *constraints, *alias])})"
        elif required:
            assignment = None  # bare required field: ``name: T``
        else:
            assignment = head  # ``= None`` or ``= <default>``

        desc = description or schema.get("description") or schema.get("title")
        return FieldSpec(
            name=name,
            annotation=annotation,
            assignment=assignment,
            wire_name=wire,
            description=_clean_desc(desc) if desc else None,
            required=required,
            default_expr=default_expr,
        )

    def _resolve_ref(self, ref: str) -> Resolved:
        name = Resolver.ref_name(ref)
        target = self._schemas.get(name, {})
        cls = naming.pascal(name)
        if _is_object(target):
            return Resolved(cls, frozenset())
        if "enum" in target and target.get("type") == "string":
            return Resolved(cls, frozenset())
        # ref to a primitive/array alias — map its underlying type inline
        return self.resolve(
            {k: v for k, v in target.items() if k != "$ref"} or {"type": "string"}, name, "value"
        )

    def _model_for(self, cls: str, schema: dict[str, Any]) -> None:
        if cls in self.models:
            return
        model = ModelSpec(
            name=cls, doc=_clean_desc(schema["description"]) if schema.get("description") else None
        )
        self.models[cls] = model  # register early so nested self-refs resolve
        required = set(schema.get("required", []))
        for wire, node in schema.get("properties", {}).items():
            fname = naming.snake(wire)
            model.fields.append(self.field_spec(fname, wire, node, wire in required, cls))

    def _enum_from_values(self, cls: str, values: list[str]) -> None:
        if cls not in self.enums:
            self.enums[cls] = EnumSpec(
                name=cls, members=_dedup_members([(_enum_member(v), v) for v in values])
            )

    def _enum_for(self, cls: str, schema: dict[str, Any]) -> None:
        if cls not in self.enums:
            raw = [(_enum_member(str(v)), str(v)) for v in schema.get("enum", [])]
            self.enums[cls] = EnumSpec(name=cls, members=_dedup_members(raw))


def _dedup_members(members: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """De-dup enum member names (distinct values can sanitise to the same identifier)."""

    seen: dict[str, int] = {}
    unique: list[tuple[str, str]] = []
    for member, value in members:
        name = member
        if member in seen:
            seen[member] += 1
            name = f"{member}_{seen[member]}"
        else:
            seen[member] = 0
        unique.append((name, value))
    return unique


def _is_object(schema: dict[str, Any]) -> bool:
    return schema.get("type") == "object" or ("properties" in schema and "enum" not in schema)


def _constraint_kwargs(schema: dict[str, Any]) -> list[str]:
    out: list[str] = []
    mapping = (
        ("minimum", "ge"),
        ("maximum", "le"),
        ("exclusiveMinimum", "gt"),
        ("exclusiveMaximum", "lt"),
        ("minLength", "min_length"),
        ("maxLength", "max_length"),
        ("minItems", "min_length"),
        ("maxItems", "max_length"),
    )
    for spec_key, field_key in mapping:
        if spec_key in schema:
            out.append(f"{field_key}={_literal(schema[spec_key])}")
    if "pattern" in schema:
        out.append(f"pattern={_literal(schema['pattern'])}")
    return out


def _literal(value: Any) -> str:
    if isinstance(value, str):
        return f'"{_escape(value)}"'
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "None"
    if isinstance(value, list):
        return "[]" if not value else repr(value)
    return repr(value)


def build_models(domain: Domain) -> ModelBuilder:
    """Convenience: construct a :class:`ModelBuilder` and run :meth:`ModelBuilder.build`."""

    builder = ModelBuilder(domain)
    builder.build()
    return builder
