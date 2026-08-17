"""Orchestrator — spec IR → models + method specs + bound methods for one domain.

Runs the pipeline in the order that lets nested types register before emission:
build component models → walk every operation's fields (registering inline models/enums
+ collecting method specs) → detect entities → bind methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import config
from ..parser import Domain
from . import entities, naming
from .entities import BoundMethod
from .types import EnumSpec, FieldSpec, ModelBuilder, ModelSpec


@dataclass(slots=True)
class MethodSpec:
    """A fully-resolved method-class ready to emit."""

    class_name: str
    operation_id: str
    base: str  # "BaseMethod" | "PageMethod"
    generic_arg: str  # e.g. "Item", "bytes", "None"
    http_method: str
    endpoint: str
    fields: list[FieldSpec]
    account_params: tuple[str, ...]  # path params filled from the client (user_id)
    doc: str
    idempotent: bool
    multipart: bool
    binary: bool
    return_symbol: str | None  # model name to import from the models module
    paginated: bool
    product: str  # decides the base URL — each Tochka product has its own host
    method_name: str  # snake(class_name); globally de-duplicated for the facade (see collisions.py)


@dataclass(slots=True)
class GeneratedDomain:
    """Everything needed to render ``methods/<module>.py`` + ``models/<module>.py``."""

    slug: str
    module: str
    title: str
    docs_url: str
    product: str
    models: dict[str, ModelSpec]
    enums: dict[str, EnumSpec]
    root_models: dict[str, str] = field(default_factory=dict)
    methods: list[MethodSpec] = field(default_factory=list)
    bound: dict[str, list[BoundMethod]] = field(default_factory=dict)
    shared_imports: dict[str, str] = field(default_factory=dict)  # name -> "common" | "_shared" (dedup.py)


#: Pagination style → (base class, the query params that base supplies itself).
#: Tochka ships two styles: `page`/`perPage` on the Open Banking surface and
#: `limit`/`offset` on the acquiring one. A style not listed here stays a plain method.
PAGINATION_STYLES: dict[str, tuple[str, frozenset[str]]] = {
    "page": ("PageMethod", frozenset({"page", "per_page"})),
    "offset": ("OffsetMethod", frozenset({"limit", "offset"})),
}


#: The Open Banking envelope every Tochka response uses: `{Data: {...}, Links, Meta}`.
#: The entity — the thing carrying `paymentId`, `qrcId`, … — is inside `Data`, so binding
#: methods onto the response ROOT would find no id field and emit nothing.
_ENVELOPE_FIELD = "data"


def _entity_model(response_model: str, builder: ModelBuilder) -> str:
    """The model that actually holds the entity's fields — unwrapping `Data` when present."""

    model = builder.models.get(response_model)
    if model is None:
        return response_model
    for spec in model.fields:
        if spec.name != _ENVELOPE_FIELD:
            continue
        inner = spec.annotation.removeprefix("list[").removesuffix("]").split(" |")[0].strip()
        if inner in builder.models:
            return inner
    return response_model


def _pagination_style(op_query_names: set[str]) -> str | None:
    """Which pagination base fits this operation's query params, if any."""

    for style, (_, params) in PAGINATION_STYLES.items():
        if params <= op_query_names:
            return style
    return None


def build_domain(domain: Domain) -> GeneratedDomain:
    """Produce a :class:`GeneratedDomain` from a spec :class:`Domain` IR."""

    builder = ModelBuilder(domain)
    builder.build()

    gen = GeneratedDomain(
        slug=domain.slug,
        module=config.module_for_slug(domain.slug),
        title=domain.title,
        docs_url=config.DOCS_URL_TEMPLATE.format(slug=domain.slug),
        product=domain.product,
        models=builder.models,
        enums=builder.enums,
        root_models=builder.root_models,
    )
    field_specs: dict[str, FieldSpec] = {}
    #: operation class name -> the model its 200 parses into. Bound-method detection needs
    #: this because Tochka's schemas are inline: `op.response_ref` is None everywhere.
    response_models: dict[str, str] = {}

    for op in domain.operations:
        query_names = {p.name for p in op.query_params}
        # A modelled response is required: paging a body the SDK cannot inspect gives no
        # way to tell the last page from a full one. Tochka's schemas are inline, never
        # `$ref`, so testing only `response_ref` would disable paging everywhere.
        has_model = op.response_ref is not None or op.response_inline is not None
        style = _pagination_style(query_names) if has_model else None
        base = PAGINATION_STYLES[style][0] if style else "BaseMethod"
        supplied = PAGINATION_STYLES[style][1] if style else frozenset()

        # return type / generic argument
        if op.binary_response:
            generic, return_symbol = "bytes", None
        elif op.response_ref:
            generic = return_symbol = naming.pascal(op.response_ref)
        elif op.response_inline is not None:
            generic = return_symbol = builder.model_from_inline(
                f"{op.class_name}Response", op.response_inline
            )
        else:
            generic, return_symbol = "None", None

        fields: list[FieldSpec] = []
        for p in op.path_params:
            fs = builder.field_spec(
                p.name, p.wire_name, p.schema, p.required, op.class_name, description=p.description
            )
            fields.append(fs)
            field_specs[f"{op.class_name}.{p.name}"] = fs
        for p in op.query_params:
            if p.name in supplied:
                continue  # the pagination base declares these fields itself
            fs = builder.field_spec(
                p.name, p.wire_name, p.schema, p.required, op.class_name, description=p.description
            )
            fields.append(fs)
            field_specs[f"{op.class_name}.{p.name}"] = fs
        for prop in op.body_props:
            fs = builder.field_spec(
                prop.name,
                prop.wire_name,
                prop.schema,
                prop.required,
                op.class_name,
                description=prop.description,
            )
            fields.append(fs)
            field_specs[f"{op.class_name}.{prop.name}"] = fs

        if return_symbol:
            response_models[op.class_name] = _entity_model(return_symbol, builder)
        account_params = tuple(p.name for p in op.path_params if p.name in config.ACCOUNT_CONTEXT_PARAMS)
        gen.methods.append(
            MethodSpec(
                class_name=op.class_name,
                method_name=naming.facade_method_name(op.class_name),
                operation_id=op.operation_id,
                base=base,
                generic_arg=generic,
                http_method=op.http_method,
                endpoint=op.endpoint,
                fields=fields,
                account_params=account_params,
                doc=_method_doc(op.summary, op.description, op.http_method, op.endpoint),
                idempotent=op.idempotent,
                multipart=op.multipart,
                binary=op.binary_response,
                return_symbol=return_symbol,
                paginated=style is not None,
                product=domain.product,
            ),
        )

    model_fields = {name: frozenset(f.name for f in m.fields) for name, m in builder.models.items()}
    ents = entities.detect_entities(domain, model_fields, response_models=response_models)
    gen.bound = entities.bound_methods(domain, ents, field_specs)
    return gen


def _method_doc(summary: str | None, description: str | None, verb: str, endpoint: str) -> str:
    head = (summary or description or f"{verb} {endpoint}").replace("\n", " ").strip()
    return f"{head} via ``{verb} {endpoint}``."
