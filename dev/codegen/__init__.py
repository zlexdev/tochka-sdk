"""Tochka codegen — the auto-builder.

Reads the committed OpenAPI corpus (`dev/generated/openapi/`, produced by
`scripts/download_tochka_specs.py` + `scraper.py`) and regenerates the SDK surface —
`tochka/{enums,models,methods,facade}/` — in the project house style: method-as-class,
`TochkaObject` DTOs, `StrEnum`s and bound methods on entity models. The hand-written
machinery (client, transport, auth, pagination, webhooks) is never touched.

Usage::

    python -m dev.codegen scrape
    python -m dev.codegen generate
    python -m dev.codegen check
"""

from __future__ import annotations

from .engine.generate import all_slugs, generate, generate_all, render_domain

__all__ = ["all_slugs", "generate", "generate_all", "render_domain"]
