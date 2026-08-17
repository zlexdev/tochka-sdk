"""Turn the portal's per-operation dumps into one OpenAPI document per product.

`scripts/download_tochka_specs.py` yields the portal's own shape — a flat registry of
operations, each carrying `method`, `path` and INLINE schemas (the portal resolves every
`$ref` before embedding). The generator expects a real OpenAPI document, so this module
reassembles one: `paths[path][method] = operation`, with `servers` hoisted to the root.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PORTAL_DIR = REPO_ROOT / "docs" / "tochka" / "api"
SPEC_DIR = REPO_ROOT / "dev" / "generated" / "openapi"

PRODUCT_TITLES = {
    "tochka-api": "Точка API",
    "cyclops": "Точка: номинальные счета (Cyclops)",
    "pay-gateway": "Точка: интернет-эквайринг",
    "medusa": "Точка: Medusa",
    "express-credit": "Точка: экспресс-кредит",
}

_OPERATION_ONLY_KEYS = ("method", "path", "postman", "jsonRequestBodyExample", "info")
_PATH_TO_ID = re.compile(r"[/{}.\-]")


def normalise_operation_id(operation_id: str, path: str, method: str) -> str:
    """Strip FastAPI's `<name>_<path>_<verb>` tail so the class name stays readable.

    Tochka runs FastAPI, whose default operationId appends the whole path and verb:
    `get_balance_info_open_banking_v1_0_accounts__accountId__balances_get`. Emitted
    verbatim it becomes `GetBalanceInfoOpenBankingV10AccountsAccountIdBalancesGet`.
    The tail is reconstructed by FastAPI's own rule and removed only on an exact match —
    an operationId shaped differently is left alone rather than guessed at.
    """

    suffix = f"{_PATH_TO_ID.sub('_', path)}_{method.lower()}"
    if operation_id.endswith(suffix) and len(operation_id) > len(suffix):
        return operation_id[: -len(suffix)]
    return operation_id


class ScrapeError(RuntimeError):
    """Raised when the portal dump does not carry what the generator needs."""


def _operation_body(api: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in api.items() if key not in _OPERATION_ONLY_KEYS}


def build_openapi(portal_payload: dict[str, Any]) -> dict[str, Any]:
    product = str(portal_payload.get("product", ""))
    operations = portal_payload.get("operations")
    if not isinstance(operations, dict) or not operations:
        raise ScrapeError(f"{product}: в дампе нет операций")

    paths: dict[str, dict[str, Any]] = {}
    servers: list[dict[str, Any]] = []
    for slug, entry in sorted(operations.items()):
        api = entry.get("api")
        if not isinstance(api, dict):
            raise ScrapeError(f"{product}/{slug}: нет объекта api")
        method, path = api.get("method"), api.get("path")
        if not isinstance(method, str) or not isinstance(path, str):
            raise ScrapeError(f"{product}/{slug}: операция без method/path")
        if not servers and isinstance(api.get("servers"), list):
            servers = api["servers"]
        operation = _operation_body(api)
        operation["x-portal-url"] = f"https://developers.tochka.com/docs/{product}/api/{slug}"
        raw_id = operation.get("operationId")
        operation["operationId"] = (
            normalise_operation_id(raw_id, path, method) if isinstance(raw_id, str) else slug
        )
        paths.setdefault(path, {})[method.lower()] = operation

    return {
        "openapi": "3.0.3",
        "info": {"title": PRODUCT_TITLES.get(product, product), "version": "portal"},
        "servers": servers,
        "paths": paths,
        "components": {"schemas": {}},
    }


def scrape(products: list[str] | None = None, *, portal_dir: Path = PORTAL_DIR) -> dict[str, Path]:
    """Rebuild `dev/generated/openapi/tochka_<product>.json` from the portal dumps."""
    dumps = sorted(portal_dir.glob("*.json"))
    if not dumps:
        raise ScrapeError(
            f"{portal_dir} пуст — сначала `python scripts/download_tochka_specs.py`",
        )

    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for dump in dumps:
        payload = json.loads(dump.read_text(encoding="utf-8"))
        product = str(payload.get("product", dump.stem))
        if products and product not in products:
            continue
        spec = build_openapi(payload)
        target = SPEC_DIR / f"tochka_{product.replace('-', '_')}.json"
        target.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written[product] = target
    return written


def main() -> int:
    for product, target in scrape().items():
        spec = json.loads(target.read_text(encoding="utf-8"))
        operations = sum(len(methods) for methods in spec["paths"].values())
        print(f"{target}: {len(spec['paths'])} путей, {operations} операций ({product})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
