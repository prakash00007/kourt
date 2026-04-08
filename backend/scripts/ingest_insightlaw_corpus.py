from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.services.embeddings import EmbeddingService
from app.services.insightlaw import InsightLawClient
from app.services.vector_store import VectorStore


DEFAULT_EXPORT_DIR = BACKEND_DIR / "data" / "insightlaw_exports"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "query"


def flatten_json(value: Any, prefix: str = "") -> list[str]:
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            next_prefix = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
            lines.extend(flatten_json(item, next_prefix))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            lines.extend(flatten_json(item, next_prefix))
    elif value is not None:
        rendered = str(value).strip()
        if rendered:
            lines.append(f"{prefix}: {rendered}" if prefix else rendered)
    return lines


def coerce_metadata_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def export_raw_payload(export_dir: Path, filename: str, payload: dict[str, Any]) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def record_to_text(record: dict[str, Any]) -> str:
    lines = flatten_json(record)
    return "\n".join(lines) if lines else json.dumps(record, ensure_ascii=False)


def normalize_search_results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("results", "items", "data", "hits"):
        value = payload.get(key)
        if isinstance(value, list):
            records = [item for item in value if isinstance(item, dict)]
            if records:
                return records

    return [payload]


def build_metadata(*, corpus: str, identifier: str, response: dict[str, Any], query: str | None = None) -> dict[str, Any]:
    title = response.get("title_en") or response.get("title") or response.get("name") or identifier
    metadata = {
        "title": coerce_metadata_value(title),
        "citation": coerce_metadata_value(response.get("citation") or response.get("section") or response.get("article")),
        "court": coerce_metadata_value("InsightLaw"),
        "source_url": "https://insightlaw.in/api",
        "document_type": "statute_section",
        "source": "insightlaw_api",
        "corpus": corpus,
        "record_id": identifier,
    }
    if query:
        metadata["query"] = query
    for key in ("section", "article", "chapter", "chapter_title", "languages"):
        if response.get(key) is not None:
            metadata[key] = coerce_metadata_value(response.get(key))
    return {key: value for key, value in metadata.items() if value not in (None, "")}


def ingest_records(
    *,
    corpus: str,
    items: list[tuple[str, dict[str, Any]]],
    export_dir: Path,
    query: str | None = None,
) -> None:
    settings = get_settings()
    embeddings = EmbeddingService(settings)
    vector_store = VectorStore(settings, embeddings)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    export_name = f"{corpus}-{slugify(query or 'ingest')}-{timestamp}.json"
    export_raw_payload(export_dir, export_name, {"corpus": corpus, "query": query, "items": items})

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for identifier, response in items:
        ids.append(f"insightlaw::{corpus}::{identifier}")
        texts.append(record_to_text(response))
        metadatas.append(build_metadata(corpus=corpus, identifier=identifier, response=response, query=query))

    vector_store.add_documents(ids=ids, texts=texts, metadatas=metadatas)
    print(f"Ingested {len(items)} InsightLaw records into Chroma")
    print(f"Raw export saved to {export_dir / export_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch free legal text from InsightLaw and ingest it into the local RAG corpus."
    )
    parser.add_argument("--corpus", choices=["constitution", "ipc", "bns", "search"], required=True)
    parser.add_argument("--article", action="append", help="Constitution article number. Repeatable.")
    parser.add_argument("--section", action="append", help="IPC/BNS section number. Repeatable.")
    parser.add_argument("--query", help="Search query for cross-corpus or corpus-specific search.")
    parser.add_argument("--start", type=int, help="Range start for section/article ingestion.")
    parser.add_argument("--end", type=int, help="Range end for section/article ingestion.")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print counts without writing to Chroma.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = InsightLawClient()
    try:
        items: list[tuple[str, dict[str, Any]]] = []

        if args.corpus == "constitution":
            identifiers = args.article or []
            if args.start is not None and args.end is not None:
                identifiers.extend(str(n) for n in range(args.start, args.end + 1))
            if not identifiers:
                raise SystemExit("Provide --article or --start/--end for constitution ingestion.")
            for identifier in identifiers:
                items.append((f"article-{identifier}", client.constitution_article(identifier)))
        elif args.corpus == "ipc":
            identifiers = args.section or []
            if args.start is not None and args.end is not None:
                identifiers.extend(str(n) for n in range(args.start, args.end + 1))
            if not identifiers:
                raise SystemExit("Provide --section or --start/--end for IPC ingestion.")
            for identifier in identifiers:
                items.append((f"ipc-{identifier}", client.ipc_section(identifier)))
        elif args.corpus == "bns":
            identifiers = args.section or []
            if args.start is not None and args.end is not None:
                identifiers.extend(str(n) for n in range(args.start, args.end + 1))
            if not identifiers:
                raise SystemExit("Provide --section or --start/--end for BNS ingestion.")
            for identifier in identifiers:
                items.append((f"bns-{identifier}", client.bns_section(identifier)))
        else:
            if not args.query:
                raise SystemExit("Provide --query for search ingestion.")
            results = normalize_search_results(client.search(args.query))
            items.extend((f"search-{index}", result) for index, result in enumerate(results, start=1))

        if args.dry_run:
            print(f"Fetched {len(items)} records")
            return

        ingest_records(corpus=args.corpus, items=items, export_dir=args.export_dir, query=args.query)
    finally:
        client.close()


if __name__ == "__main__":
    main()
