"""CLI for the Tochka codegen.

python -m dev.codegen scrape              # portal dumps -> dev/generated/openapi/
python -m dev.codegen generate            # every domain (dedup + collision passes)
python -m dev.codegen generate --slug payments
python -m dev.codegen generate --dry-run  # list target files, write nothing
python -m dev.codegen check               # ruff + mypy over the generated package
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .engine.generate import all_slugs, generate, generate_all

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "tochka"


def _gate() -> int:
    """Run the quality gate over the package; a red gate is the point of this command."""

    failed = 0
    for name, command in (
        ("ruff", ["ruff", "check", str(PACKAGE)]),
        ("ruff format", ["ruff", "format", "--check", str(PACKAGE)]),
        ("mypy", ["mypy", str(PACKAGE)]),
    ):
        result = subprocess.run(command, check=False, cwd=REPO_ROOT)
        status = "ok" if result.returncode == 0 else "FAILED"
        print(f"[{name}] {status}")
        failed += result.returncode != 0
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dev.codegen", description="Regenerate the Tochka SDK surface.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scrape", help="Rebuild the OpenAPI corpus from the portal dumps.")
    gen = sub.add_parser("generate", help="Render methods/models/enums/facades.")
    gen.add_argument("--slug", help="One domain only (no cross-domain dedup/collision passes).")
    gen.add_argument("--dry-run", action="store_true", help="Print target files without writing.")
    sub.add_parser("check", help="ruff + mypy over the generated package.")

    args = parser.parse_args(argv)

    if args.command == "scrape":
        from .scraper import main as scrape_main

        return scrape_main()

    if args.command == "check":
        return _gate()

    verb = "would write" if args.dry_run else "wrote"
    if args.slug:
        files = generate(args.slug, dry_run=args.dry_run)
        print(f"[{args.slug}] {verb}: {', '.join(sorted(files))}")
        return 0

    files = generate_all(dry_run=args.dry_run)
    print(f"[all] {verb} {len(files)} files across {len(all_slugs())} domains.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
