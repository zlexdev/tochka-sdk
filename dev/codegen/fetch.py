"""Spec source — read the local OpenAPI documents and slice them into tag domains.

Tochka publishes no spec of its own (see `scripts/download_tochka_specs.py`), so the
source of truth is the committed `dev/generated/openapi/tochka_<product>.json` corpus.
One product carries up to 71 operations, which would emit a single unreadable module —
so a *domain* here is a `(product, tag)` pair, mapped to a module name by
`config.TAG_TO_DOMAIN`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import TAG_TO_DOMAIN

SPEC_DIR = Path(__file__).resolve().parents[2] / "dev" / "generated" / "openapi"

_UNTAGGED = "<без тега>"


class SpecFetchError(RuntimeError):
    """Raised when the local spec corpus is missing or a tag has no module mapping."""


@dataclass(frozen=True, slots=True)
class DomainInfo:
    """One generated module: every operation of `product` carrying `tag`."""

    slug: str
    title: str
    product: str
    tag: str


def _spec_path(product: str) -> Path:
    return SPEC_DIR / f"tochka_{product.replace('-', '_')}.json"


def load_spec(product: str) -> dict[str, Any]:
    path = _spec_path(product)
    if not path.exists():
        raise SpecFetchError(f"{path} нет — сначала `python -m dev.codegen scrape`")
    document: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise SpecFetchError(f"{path}: корень спеки не объект")
    return document


def _tags_of(operation: dict[str, Any]) -> list[str]:
    tags = operation.get("tags") or []
    names = [tag if isinstance(tag, str) else str(tag.get("name", "")) for tag in tags]
    return [name for name in names if name] or [_UNTAGGED]


def domain_for_tag(product: str, tag: str) -> str:
    """Module basename for `(product, tag)`.

    An unmapped tag raises: a new Tochka section must be named deliberately in
    `config.TAG_TO_DOMAIN`, never swept into a `misc.py` nobody reads.
    """

    slug = TAG_TO_DOMAIN.get((product, tag))
    if slug is None:
        raise SpecFetchError(
            f"тег {tag!r} продукта {product!r} не назван в config.TAG_TO_DOMAIN — добавьте модуль",
        )
    return slug


def list_domains(products: list[str] | None = None) -> list[DomainInfo]:
    """Every `(product, tag)` domain present in the local corpus."""

    from .config import PRODUCTS

    domains: list[DomainInfo] = []
    for product in products or PRODUCTS:
        if not _spec_path(product).exists():
            continue
        spec = load_spec(product)
        seen: set[str] = set()
        for methods in spec.get("paths", {}).values():
            for operation in methods.values():
                if not isinstance(operation, dict):
                    continue
                for tag in _tags_of(operation):
                    if tag in seen:
                        continue
                    seen.add(tag)
                    domains.append(
                        DomainInfo(
                            slug=domain_for_tag(product, tag),
                            title=tag,
                            product=product,
                            tag=tag,
                        ),
                    )
    return sorted(domains, key=lambda domain: domain.slug)


def fetch_spec(slug: str, *, use_cache: bool = True) -> dict[str, Any]:
    """Return an OpenAPI document holding only the operations of domain `slug`.

    `use_cache` exists for engine-call compatibility; the corpus is already on disk.
    """

    del use_cache
    domain = next((info for info in list_domains() if info.slug == slug), None)
    if domain is None:
        raise SpecFetchError(f"домен {slug!r} не найден в локальном корпусе спек")

    spec = load_spec(domain.product)
    paths: dict[str, dict[str, Any]] = {}
    for path, methods in spec.get("paths", {}).items():
        kept = {
            verb: operation
            for verb, operation in methods.items()
            if isinstance(operation, dict) and domain.tag in _tags_of(operation)
        }
        if kept:
            paths[path] = kept

    return {**spec, "paths": paths}
