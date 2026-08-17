"""Bound-method inference — link entity models to the operations that act on them.

The entity model for a path token ``{X_id}`` is auto-detected as the ``response_ref`` of
the *get-one* operation whose endpoint ends in ``{X_id}`` (``GET /items/{item_id}/`` →
its 200 model *is* the Item entity). No name guessing. :data:`config.ENTITY_BINDINGS`
only supplements cases where no get-one endpoint exists.

An operation becomes a bound method on entity ``E`` iff every path param is either ``E``'s
id token or account-context (``user_id``); the remaining (query + body) fields become the
bound method's arguments.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import ACCOUNT_CONTEXT_PARAMS, ENTITY_BINDINGS
from ..parser import Domain, Operation
from . import naming
from .types import FieldSpec


@dataclass(frozen=True, slots=True)
class Entity:
    """A model that owns bound methods."""

    token: str  # path token, e.g. "item_id"
    model: str  # entity model class name
    self_attr: str  # field on the model holding the id (e.g. "id")


@dataclass(frozen=True, slots=True)
class BoundArg:
    """One argument of a generated bound method."""

    name: str
    annotation: str
    required: bool
    default_expr: str | None


@dataclass(frozen=True, slots=True)
class BoundMethod:
    """A bound method to emit onto an entity model."""

    owner_model: str
    method_name: str
    method_class: str
    args: tuple[BoundArg, ...]
    fills: tuple[tuple[str, str], ...]  # (field_name, python_expr)


def _self_attr_for(token: str, model_fields: frozenset[str]) -> str | None:
    """Pick the field on the entity model that holds its id, or ``None`` if it has none.

    Returning ``None`` means the model is a wrapper (e.g. ``{account: Account}``) with no
    own id — binding an operation to it would emit ``self.id`` against a model without an
    ``id`` field. Such operations stay top-level methods only.
    """

    if "id" in model_fields:
        return "id"
    if token in model_fields:
        return token
    for f in sorted(model_fields):
        if f.endswith("_id"):
            return f
    return None


def detect_entities(
    domain: Domain,
    model_fields: dict[str, frozenset[str]],
    *,
    response_models: dict[str, str] | None = None,
) -> dict[str, Entity]:
    """Map each entity path token in ``domain`` to its :class:`Entity`.

    ``response_models`` maps an operation class name to the model its 200 parses into.
    It is required whenever the spec inlines its schemas (Tochka always does), because
    ``op.response_ref`` is then None and no entity would ever be detected.
    """

    by_operation = response_models or {}
    entities: dict[str, Entity] = {}
    for op in domain.operations:
        model = op.response_ref or by_operation.get(op.class_name)
        if op.http_method != "GET" or not op.path_params or not model:
            continue
        last = op.path_params[-1].name
        if last in ACCOUNT_CONTEXT_PARAMS or not last.endswith("_id"):
            continue
        if model in model_fields and last not in entities:
            attr = _self_attr_for(last, model_fields[model])
            if attr is not None:
                entities[last] = Entity(token=last, model=model, self_attr=attr)

    for token, (model, attr) in ENTITY_BINDINGS.items():
        if token not in entities and model in model_fields:
            entities[token] = Entity(token=token, model=model, self_attr=attr)
    return entities


def _bind(
    op: Operation, entities: dict[str, Entity], field_specs: dict[str, FieldSpec]
) -> BoundMethod | None:
    path_tokens = [p.name for p in op.path_params]
    entity_tokens = [t for t in path_tokens if t in entities]
    if len(entity_tokens) != 1:
        return None
    non_entity = [t for t in path_tokens if t not in entities]
    if any(t not in ACCOUNT_CONTEXT_PARAMS for t in non_entity):
        return None

    entity = entities[entity_tokens[0]]
    fills: list[tuple[str, str]] = []
    for p in op.path_params:
        if p.name == entity.token:
            fills.append((p.name, f"self.{entity.self_attr}"))
        else:  # account context — resolved from the bound client
            fills.append((p.name, "_resolve_customer_code(self._client)"))

    args: list[BoundArg] = []
    for name in [p.name for p in op.query_params] + [prop.name for prop in op.body_props]:
        fs = field_specs.get(f"{op.class_name}.{name}")
        if fs is None:
            continue
        args.append(
            BoundArg(
                name=fs.name, annotation=fs.annotation, required=fs.required, default_expr=fs.default_expr
            )
        )

    method_name = naming.facade_method_name(op.class_name)
    return BoundMethod(
        owner_model=entity.model,
        method_name=method_name,
        method_class=op.class_name,
        args=tuple(args),
        fills=tuple(fills),
    )


def bound_methods(
    domain: Domain,
    entities: dict[str, Entity],
    field_specs: dict[str, FieldSpec],
) -> dict[str, list[BoundMethod]]:
    """Group bound methods by owner model class name."""

    grouped: dict[str, list[BoundMethod]] = {}
    for op in domain.operations:
        bm = _bind(op, entities, field_specs)
        if bm is not None:
            grouped.setdefault(bm.owner_model, []).append(bm)
    return grouped
