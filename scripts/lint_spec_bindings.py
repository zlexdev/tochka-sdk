"""Coverage gate: every operation in the spec must be bound to exactly one SDK method.

The point is not tidiness — it is that
a silently unbound operation looks exactly like an operation the bank never had. It reports
four states:

  bound      — one method class owns the (method, path)
  unbound    — the spec has it, the SDK does not
  duplicate  — two method classes claim the same endpoint
  orphan     — an SDK method whose endpoint is not in the spec (a removed or renamed one)
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import pkgutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = REPO_ROOT / "dev" / "generated" / "openapi"

sys.path.insert(0, str(REPO_ROOT))

from tochka.methods._base import BaseMethod  # noqa: E402 — needs the path above

Endpoint = tuple[str, str]


@dataclass
class Report:
    bound: dict[Endpoint, list[str]] = field(default_factory=dict)
    unbound: list[Endpoint] = field(default_factory=list)
    duplicate: dict[Endpoint, list[str]] = field(default_factory=dict)
    orphan: dict[Endpoint, str] = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return bool(self.unbound or self.duplicate or self.orphan)

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": {
                "bound": len(self.bound),
                "unbound": len(self.unbound),
                "duplicate": len(self.duplicate),
                "orphan": len(self.orphan),
            },
            "unbound": [f"{verb} {path}" for verb, path in sorted(self.unbound)],
            "duplicate": {f"{verb} {path}": names for (verb, path), names in sorted(self.duplicate.items())},
            "orphan": {f"{verb} {path}": name for (verb, path), name in sorted(self.orphan.items())},
        }


def spec_endpoints() -> dict[Endpoint, str]:
    """Every `(VERB, path)` in the committed corpus → its operationId."""

    found: dict[Endpoint, str] = {}
    for spec_file in sorted(SPEC_DIR.glob("tochka_*.json")):
        spec = json.loads(spec_file.read_text(encoding="utf-8"))
        for path, methods in spec.get("paths", {}).items():
            for verb, operation in methods.items():
                found[(verb.upper(), path)] = str(operation.get("operationId", ""))
    return found


def sdk_endpoints() -> dict[Endpoint, list[str]]:
    """Every `(VERB, path)` a generated method class declares → the class names."""

    import tochka.methods as methods_package

    bound: dict[Endpoint, list[str]] = defaultdict(list)
    for module_info in pkgutil.iter_modules(methods_package.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"tochka.methods.{module_info.name}")
        for name, member in inspect.getmembers(module, inspect.isclass):
            if not issubclass(member, BaseMethod) or member.__module__ != module.__name__:
                continue
            bound[(member.__http_method__.upper(), member.__endpoint__)].append(name)
    return dict(bound)


def _normalise(path: str) -> str:
    """Spec paths use `{accountId}`, generated ones `{account_id}` — compare shape only."""

    out, depth = [], 0
    for char in path:
        if char == "{":
            depth += 1
            out.append("{")
        elif char == "}":
            depth -= 1
            out.append("}")
        elif depth == 0:
            out.append(char)
    return "".join(out)


def build_report() -> Report:
    spec = {(verb, _normalise(path)): op for (verb, path), op in spec_endpoints().items()}
    sdk = {(verb, _normalise(path)): names for (verb, path), names in sdk_endpoints().items()}

    report = Report()
    for endpoint in spec:
        names = sdk.get(endpoint)
        if not names:
            report.unbound.append(endpoint)
        elif len(names) > 1:
            report.duplicate[endpoint] = names
        else:
            report.bound[endpoint] = names
    for endpoint, names in sdk.items():
        if endpoint not in spec:
            report.orphan[endpoint] = names[0]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверить покрытие спеки методами SDK.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Вывести отчёт в JSON.")
    parser.add_argument("--strict", action="store_true", help="Ненулевой код возврата при любом расхождении.")
    args = parser.parse_args()

    report = build_report()
    if args.as_json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        summary = report.to_dict()["summary"]
        print(
            f"Операций в спеке: {len(report.bound) + len(report.unbound) + len(report.duplicate)}, {summary}"
        )
        for verb, path in sorted(report.unbound):
            print(f"[unbound]   {verb} {path}", file=sys.stderr)
        for (verb, path), names in sorted(report.duplicate.items()):
            print(f"[duplicate] {verb} {path} -> {', '.join(names)}", file=sys.stderr)
        for (verb, path), name in sorted(report.orphan.items()):
            print(f"[orphan]    {verb} {path} -> {name}", file=sys.stderr)

    return 1 if args.strict and report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
