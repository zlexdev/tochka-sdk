"""Cross-domain facade collision resolution — make every ``Client`` method name unique.

``Client`` inherits one ``*Facade`` mixin per domain, so two domains that emit the same
method name collide in the MRO: the second is unreachable and ``mypy`` flags incompatible
overrides. :func:`resolve_facade_collisions` renames the later duplicates in place —
keeping the first (by slug order, deterministic across runs) bare and suffixing the rest
with their domain module (``get_access_token`` / ``get_access_token_autoteka``).
"""

from __future__ import annotations

import logging

from .build import GeneratedDomain

logger = logging.getLogger(__name__)


def resolve_facade_collisions(domains: list[GeneratedDomain]) -> dict[str, str]:
    """Mutate ``MethodSpec.method_name`` so every facade method name is globally unique.

    Domains are processed in the order given (slug order from the catalogue), so the
    winner of any clash is stable. Returns a ``{qualified_class: new_name}`` log of the
    renames applied (empty when there were no collisions).
    """

    seen: dict[str, str] = {}  # method_name -> module that first claimed it
    renames: dict[str, str] = {}
    for gen in domains:
        for method in gen.methods:
            owner = seen.get(method.method_name)
            if owner is None:
                seen[method.method_name] = gen.module
                continue
            new_name = f"{method.method_name}_{gen.module}"
            # A suffixed name can itself clash (rare) — walk until free.
            while new_name in seen:
                new_name = f"{new_name}_x"
            logger.info(
                "facade collision: %s.%s -> %s (first claimed by %s)",
                gen.module,
                method.method_name,
                new_name,
                owner,
            )
            renames[f"{gen.module}.{method.class_name}"] = new_name
            method.method_name = new_name
            seen[new_name] = gen.module
    return renames
