"""OpenAPI 3.0 → intermediate representation.

Resolves ``$ref`` pointers, normalises parameters (drops transport-owned headers,
snake-cases names), and extracts one :class:`Operation` per ``(path, verb)``. Property
``$ref``s are deliberately *kept* so the type mapper can link them to model class names;
only parameter / requestBody / response envelope refs are resolved here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import IDEMPOTENT_VERBS, SKIP_HEADER_PARAMS
from .engine import naming

_HTTP_VERBS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})


class SpecError(RuntimeError):
    """Raised on a malformed or unresolvable spec."""


@dataclass(frozen=True, slots=True)
class Param:
    """A path or query parameter of an operation."""

    name: str
    wire_name: str
    location: str  # "path" | "query"
    schema: dict[str, Any]
    required: bool
    description: str | None


@dataclass(frozen=True, slots=True)
class Prop:
    """A property of a schema / flattened request-body field."""

    name: str
    wire_name: str
    schema: dict[str, Any]
    required: bool
    description: str | None


@dataclass(frozen=True, slots=True)
class Operation:
    """One endpoint call — becomes a ``BaseMethod`` subclass."""

    class_name: str
    operation_id: str
    http_method: str
    endpoint: str
    path_params: tuple[Param, ...]
    query_params: tuple[Param, ...]
    body_props: tuple[Prop, ...]
    body_ref: str | None  # component schema name of the requestBody, if any
    body_required: bool
    multipart: bool
    binary_response: bool
    response_ref: str | None  # component schema name of the 200 body, if any
    response_inline: dict[str, Any] | None  # inline 200 object schema, if any
    idempotent: bool
    summary: str | None
    description: str | None


@dataclass(slots=True)
class Domain:
    """A whole API domain: its operations plus the raw component schemas they reference."""

    slug: str
    title: str
    #: Tochka product this domain belongs to. Load-bearing: each product has its OWN host
    #: (cyclops is on api.tochka.com, pay-gateway adds a `pay/` prefix), so a method that
    #: does not know its product gets sent to the wrong server.
    product: str = "tochka-api"
    operations: list[Operation] = field(default_factory=list)
    schemas: dict[str, dict[str, Any]] = field(default_factory=dict)


class Resolver:
    """Resolves ``$ref`` pointers within a single spec document."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self._spec = spec

    @staticmethod
    def ref_name(ref: str) -> str:
        """``#/components/schemas/Item`` → ``Item``."""

        return ref.rsplit("/", 1)[-1]

    def resolve(self, node: dict[str, Any]) -> dict[str, Any]:
        """Follow a single ``$ref`` (if present); otherwise return ``node`` unchanged."""

        seen: set[str] = set()
        while "$ref" in node:
            ref = node["$ref"]
            if ref in seen:
                raise SpecError(f"circular $ref: {ref}")
            seen.add(ref)
            parts = ref.lstrip("#/").split("/")
            cur: Any = self._spec
            for p in parts:
                cur = cur[p]
            node = cur
        return node


def _norm_param(raw: dict[str, Any], resolver: Resolver) -> Param | None:
    p = resolver.resolve(raw)
    location = p.get("in")
    wire = p.get("name", "")
    if location == "header" or wire.lower() in SKIP_HEADER_PARAMS:
        return None
    if location not in ("path", "query"):
        return None
    return Param(
        name=naming.snake(wire),
        wire_name=wire,
        location=location,
        schema=p.get("schema", {}),
        required=bool(p.get("required", location == "path")),
        description=p.get("description"),
    )


def _flatten_body(op: dict[str, Any], resolver: Resolver) -> tuple[tuple[Prop, ...], str | None, bool, bool]:
    """Return (body_props, body_ref, required, multipart) from an operation's requestBody."""

    rb = op.get("requestBody")
    if not rb:
        return (), None, False, False
    rb = resolver.resolve(rb)
    content = rb.get("content", {})
    multipart = "multipart/form-data" in content
    media: dict[str, Any] = (
        content.get("application/json")
        or content.get("multipart/form-data")
        or next(iter(content.values()), {})
    )
    schema_node = media.get("schema", {})
    body_ref = Resolver.ref_name(schema_node["$ref"]) if "$ref" in schema_node else None
    resolved = resolver.resolve(schema_node)
    props = _props_of(resolved)
    return props, body_ref, bool(rb.get("required", False)), multipart


def _props_of(schema: dict[str, Any]) -> tuple[Prop, ...]:
    required = set(schema.get("required", []))
    out: list[Prop] = []
    for wire, node in schema.get("properties", {}).items():
        out.append(
            Prop(
                name=naming.snake(wire),
                wire_name=wire,
                schema=node,
                required=wire in required,
                description=node.get("description") or node.get("title"),
            ),
        )
    return tuple(out)


def _response(op: dict[str, Any], resolver: Resolver) -> tuple[str | None, dict[str, Any] | None, bool]:
    """Return (response_ref, inline_object_schema, is_binary) for the success response."""

    responses = op.get("responses", {})
    ok = responses.get("200") or responses.get("201") or responses.get("default")
    if not ok:
        return None, None, False
    ok = resolver.resolve(ok)
    content = ok.get("content", {})
    if not content:
        return None, None, False
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
        if "$ref" in schema:
            return Resolver.ref_name(schema["$ref"]), None, False
        if schema.get("type") == "object":
            return None, schema, False
        return None, None, False
    # non-JSON success (pdf, octet-stream, plain text) → binary/passthrough
    return None, None, True


def build_domain(slug: str, title: str, spec: dict[str, Any], product: str = "tochka-api") -> Domain:
    """Parse a full spec document into a :class:`Domain` IR."""

    resolver = Resolver(spec)
    domain = Domain(slug=slug, title=title, product=product)
    domain.schemas = dict(spec.get("components", {}).get("schemas", {}))
    # reserve every model/enum class name (= pascal of a schema) so a method-class never
    # collides with a model it imports (both live in the methods file's namespace)
    seen_classes: dict[str, int] = {naming.pascal(s): 1 for s in domain.schemas}

    def _unique(name: str) -> str:
        if name not in seen_classes:
            seen_classes[name] = 1
            return name
        seen_classes[name] += 1
        return f"{name}{seen_classes[name]}"

    for path, item in spec.get("paths", {}).items():
        endpoint = naming.normalise_endpoint(path)
        shared = [rp for rp in (item.get("parameters", []) or [])]
        for verb, op in item.items():
            if verb not in _HTTP_VERBS or not isinstance(op, dict):
                continue
            op_id = op.get("operationId")
            if not op_id:
                continue
            raw_params = shared + (op.get("parameters", []) or [])
            params = [p for p in (_norm_param(rp, resolver) for rp in raw_params) if p is not None]
            path_params = tuple(p for p in params if p.location == "path")
            query_params = tuple(p for p in params if p.location == "query")
            body_props, body_ref, body_required, multipart = _flatten_body(op, resolver)
            response_ref, response_inline, is_binary = _response(op, resolver)
            domain.operations.append(
                Operation(
                    class_name=_unique(naming.class_name_for_operation(op_id)),
                    operation_id=op_id,
                    http_method=verb.upper(),
                    endpoint=endpoint,
                    path_params=path_params,
                    query_params=query_params,
                    body_props=body_props,
                    body_ref=body_ref,
                    body_required=body_required,
                    multipart=multipart,
                    binary_response=is_binary,
                    response_ref=response_ref,
                    response_inline=response_inline,
                    idempotent=verb.upper() in IDEMPOTENT_VERBS,
                    summary=op.get("summary"),
                    description=op.get("description"),
                ),
            )
    return domain
