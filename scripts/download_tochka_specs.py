"""Download Tochka Bank OpenAPI operation specs from the public developer portal.

The portal (developers.tochka.com) serves no OpenAPI document: it is a Docusaurus
site whose openapi-docs plugin embeds each operation into its own webpack chunk.
The chunk filename is assembled from TWO maps in `runtime~main.*.js` keyed by the
same chunk id — `id -> name` and `id -> hash` — so neither map alone yields a URL.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import sys
import urllib.error
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

BASE_URL = "https://developers.tochka.com"
USER_AGENT = "Mozilla/5.0 (compatible; tochka-sdk-spec-downloader)"
DEFAULT_OUTPUT_DIR = Path("docs/tochka/api")
REQUEST_TIMEOUT_SECONDS = 60
DEFAULT_WORKERS = 16

_CHUNK_MAP_RE = re.compile(r"\{(?:\"?[\w.~-]+\"?:\"[\w-]{6,12}\",){20,}[^}]*\}")
_CHUNK_PAIR_RE = re.compile(r"\"?([\w.~-]+)\"?:\"([\w-]{6,12})\"")
_RUNTIME_SCRIPT_RE = re.compile(r"/assets/js/runtime~main\.[0-9a-f]+\.js")
_METADATA_START_RE = re.compile(r"JSON\.parse\('")
_API_BLOB_RE = re.compile(r'"api":"([A-Za-z0-9+/=]{40,})"')
_ENDPOINT_RE = re.compile(r'method:"([a-z]+)",path:"([^"]+)"')


class SpecDownloadError(RuntimeError):
    """Raised when the portal no longer matches the shape this downloader expects."""


@dataclass(frozen=True, slots=True)
class Operation:
    product: str
    slug: str
    title: str
    description: str
    api: dict[str, object]


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8", "ignore")
    except urllib.error.URLError as exc:
        raise SpecDownloadError(f"Не удалось скачать {url}: {exc}") from exc


def discover_runtime_url(base_url: str) -> str:
    index = fetch(f"{base_url}/")
    match = _RUNTIME_SCRIPT_RE.search(index)
    if match is None:
        raise SpecDownloadError(f"{base_url} не содержит ссылки на runtime~main.js")
    return f"{base_url}{match.group(0)}"


def parse_chunk_maps(runtime_source: str) -> dict[str, str]:
    """Join the `id -> name` and `id -> hash` maps into `id -> "<name>.<hash>"`."""
    maps: list[dict[str, str]] = [
        dict(_CHUNK_PAIR_RE.findall(blob)) for blob in _CHUNK_MAP_RE.findall(runtime_source)
    ]
    if len(maps) < 2:
        raise SpecDownloadError("runtime~main.js не содержит двух карт чанков")

    names, hashes = maps[0], maps[1]
    shared = names.keys() & hashes.keys()
    if not shared:
        raise SpecDownloadError("карты чанков не пересекаются по chunk id")
    return {chunk_id: f"{names[chunk_id]}.{hashes[chunk_id]}" for chunk_id in shared}


def decode_api_blob(encoded: str) -> dict[str, object]:
    """`frontMatter.api` is the operation object, zlib-compressed and base64-encoded."""
    try:
        payload = zlib.decompress(base64.b64decode(encoded))
    except (binascii.Error, zlib.error) as exc:
        raise SpecDownloadError(f"Не удалось распаковать frontMatter.api: {exc}") from exc
    decoded = json.loads(payload.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise SpecDownloadError("frontMatter.api распакован не в объект")
    return decoded


def _iter_json_parse_literals(source: str) -> list[str]:
    """Yield the raw bodies of `JSON.parse('…')` calls, honouring escaped quotes."""
    literals: list[str] = []
    for match in _METADATA_START_RE.finditer(source):
        start = cursor = match.end()
        while True:
            end = source.find("')", cursor)
            if end < 0:
                break
            if source[end - 1] != "\\":
                literals.append(source[start:end])
                break
            cursor = end + 1
    return literals


def _unescape_js_string(raw: str) -> str:
    return raw.replace("\\'", "'")


def extract_operation(chunk_source: str) -> Operation | None:
    blob_match = _API_BLOB_RE.search(chunk_source)
    if blob_match is None:
        return None

    metadata: dict[str, object] | None = None
    for candidate in _iter_json_parse_literals(chunk_source):
        try:
            parsed = json.loads(_unescape_js_string(candidate))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "id" in parsed and "permalink" in parsed:
            metadata = parsed
            break
    if metadata is None:
        return None

    identifier = metadata.get("id")
    if not isinstance(identifier, str):
        return None
    product, _, slug = identifier.partition("/api/")
    if not slug:
        return None

    api = decode_api_blob(blob_match.group(1))
    endpoint_match = _ENDPOINT_RE.search(chunk_source)
    if endpoint_match is not None:
        api.setdefault("method", endpoint_match.group(1))
        api.setdefault("path", endpoint_match.group(2))

    return Operation(
        product=product,
        slug=slug,
        title=str(metadata.get("title", "")),
        description=str(metadata.get("description", "")),
        api=api,
    )


def download_operations(base_url: str, workers: int) -> list[Operation]:
    chunks = parse_chunk_maps(fetch(discover_runtime_url(base_url)))

    def load(name: str) -> Operation | None:
        try:
            return extract_operation(fetch(f"{base_url}/assets/js/{name}.js"))
        except SpecDownloadError:
            return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(load, sorted(set(chunks.values())))
    return sorted(
        (operation for operation in results if operation is not None),
        key=lambda operation: (operation.product, operation.slug),
    )


def group_by_product(operations: list[Operation]) -> dict[str, dict[str, object]]:
    products: dict[str, dict[str, object]] = {}
    for operation in operations:
        product = products.setdefault(operation.product, {"product": operation.product, "operations": {}})
        registry = product["operations"]
        if not isinstance(registry, dict):
            raise TypeError("operations registry must be a JSON object")
        registry[operation.slug] = {
            "slug": operation.slug,
            "title": operation.title,
            "description": operation.description,
            "api": operation.api,
        }
    return products


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Скачать спеки методов Точка API с портала разработчика.")
    parser.add_argument("--base-url", default=BASE_URL, help="Базовый URL портала.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Каталог для JSON-спек.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Число параллельных загрузок.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        operations = download_operations(args.base_url, args.workers)
    except SpecDownloadError as exc:
        print(exc, file=sys.stderr)
        return 2

    if not operations:
        print("Портал не отдал ни одной операции — формат чанков изменился.", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for product, payload in group_by_product(operations).items():
        target = args.output_dir / f"{product}.json"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        registry = payload["operations"]
        count = len(registry) if isinstance(registry, dict) else 0
        print(f"{target}: {count} операций")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
