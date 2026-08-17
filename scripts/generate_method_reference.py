"""Render `docs/sdk/methods.md` — the full method reference, straight from the code.

Hand-writing 167 rows guarantees they rot: the reference is built from the generated
facades and method classes, so it cannot claim a method the SDK does not have.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "docs" / "sdk" / "methods.md"

sys.path.insert(0, str(REPO_ROOT))

from tochka.facade._base import FacadeBase  # noqa: E402
from tochka.methods._base import BaseMethod  # noqa: E402

#: Module prefix → the Tochka product it belongs to, for grouping the reference.
PRODUCTS: dict[str, str] = {
    "acquiring_": "Интернет-эквайринг (pay-gateway)",
    "nominal_": "Номинальные счета (cyclops)",
    "beneficiaries": "Номинальные счета (cyclops)",
    "deals": "Номинальные счета (cyclops)",
    "virtual_accounts": "Номинальные счета (cyclops)",
    "marketplace_": "Маркетплейс-выплаты (medusa)",
    "express_credits": "Экспресс-кредиты",
    "customer_info": "Справка о клиенте",
}
DEFAULT_PRODUCT = "Точка API (счета, платежи, СБП)"

_CALL_RE = re.compile(r"self\.(?:execute|paginate)\(\s*(\w+)\(")


@dataclass(frozen=True, slots=True)
class Entry:
    module: str
    facade_method: str
    signature: str
    method_class: str
    verb: str
    endpoint: str
    summary: str


def _product_of(module: str) -> str:
    for prefix, product in PRODUCTS.items():
        if module.startswith(prefix):
            return product
    return DEFAULT_PRODUCT


def _endpoints() -> dict[str, tuple[str, str, str]]:
    """Method class name → (verb, endpoint, first docstring line)."""

    import tochka.methods as methods_package

    found: dict[str, tuple[str, str, str]] = {}
    for module_info in pkgutil.iter_modules(methods_package.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"tochka.methods.{module_info.name}")
        for name, member in inspect.getmembers(module, inspect.isclass):
            if issubclass(member, BaseMethod) and member.__module__ == module.__name__:
                doc = (member.__doc__ or "").strip().split(" via ")[0].replace("\n", " ")
                found[name] = (member.__http_method__, member.__endpoint__, doc)
    return found


def collect() -> dict[str, list[Entry]]:
    import tochka.facade as facade_package

    endpoints = _endpoints()
    by_product: dict[str, list[Entry]] = defaultdict(list)

    for module_info in pkgutil.iter_modules(facade_package.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"tochka.facade.{module_info.name}")
        for _, facade in inspect.getmembers(module, inspect.isclass):
            if not issubclass(facade, FacadeBase) or facade.__module__ != module.__name__:
                continue
            for name, function in inspect.getmembers(facade, inspect.isfunction):
                if name.startswith("_") or function.__qualname__.split(".")[0] != facade.__name__:
                    continue
                # Take the class from the `execute(X(...))` / `paginate(X(...))` call itself.
                # Substring matching picks the wrong one whenever a name is a prefix of
                # another (`CreateInvoice` inside `CreateInvoiceInvoices`).
                source = inspect.getsource(function)
                call = _CALL_RE.search(source)
                method_class = call.group(1) if call and call.group(1) in endpoints else ""
                verb, endpoint, summary = endpoints.get(method_class, ("", "", ""))
                signature = str(inspect.signature(function)).replace("self, ", "").replace("'", "")
                by_product[_product_of(module_info.name)].append(
                    Entry(module_info.name, name, signature, method_class, verb, endpoint, summary),
                )
    return by_product


def render(by_product: dict[str, list[Entry]]) -> str:
    total = sum(len(entries) for entries in by_product.values())
    out = [
        "# Справочник методов",
        "",
        "Сгенерировано из кода: `python scripts/generate_method_reference.py`. "
        f"Всего **{total}** методов.",
        "",
        "Каждый метод вызывается на клиенте: `await client.<метод>(...)`.",
        "",
    ]
    for product in sorted(by_product):
        out += [f"## {product}", ""]
        by_module: dict[str, list[Entry]] = defaultdict(list)
        for entry in by_product[product]:
            by_module[entry.module].append(entry)
        for module in sorted(by_module):
            out += [f"### `{module}`", "", "| Метод | HTTP | Эндпоинт | Что делает |", "|---|---|---|---|"]
            for entry in sorted(by_module[module], key=lambda item: item.facade_method):
                summary = entry.summary.replace("|", "\\|")[:90] or "—"
                verb = entry.verb or "—"
                endpoint = entry.endpoint or "—"
                out.append(f"| `{entry.facade_method}` | {verb} | `{endpoint}` | {summary} |")
            out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    by_product = collect()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(render(by_product), encoding="utf-8")
    total = sum(len(entries) for entries in by_product.values())
    print(f"{TARGET}: {total} методов, {len(by_product)} продуктов")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
