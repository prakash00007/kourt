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
from app.services.kleopatra import KleopatraClient
from app.services.vector_store import VectorStore


DEFAULT_EXPORT_DIR = BACKEND_DIR / "data" / "kleopatra_exports"


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


def normalize_response_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in (
        "cases",
        "caseDetails",
        "caseDetailsList",
        "results",
        "result",
        "records",
        "rows",
        "items",
        "data",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            records = [item for item in value if isinstance(item, dict)]
            if records:
                return records

    candidate_records: list[dict[str, Any]] = []
    for value in payload.values():
        if isinstance(value, list):
            candidate_records.extend(item for item in value if isinstance(item, dict))

    if candidate_records:
        return candidate_records

    return [payload]


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


def infer_title(record: dict[str, Any], fallback: str) -> str:
    for key in (
        "title",
        "caseTitle",
        "case_name",
        "caseName",
        "causeTitle",
        "petitioner",
        "respondent",
    ):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    petitioner = record.get("petitioner")
    respondent = record.get("respondent")
    if isinstance(petitioner, str) and isinstance(respondent, str):
        return f"{petitioner} v. {respondent}"

    return fallback


def build_metadata(
    *,
    court: str,
    query_name: str,
    year: str,
    stage: str,
    record: dict[str, Any],
    api_endpoint: str,
    bench_id: str | None = None,
    district_id: str | None = None,
    complex_id: str | None = None,
    party_type: str | None = None,
) -> dict[str, Any]:
    metadata = {
        "title": coerce_metadata_value(infer_title(record, f"{query_name} ({court.title()} {year})")),
        "citation": coerce_metadata_value(record.get("citation") or record.get("neutralCitation") or record.get("caseNumber")),
        "court": coerce_metadata_value(record.get("court") or f"{court.title()} Court"),
        "source_url": coerce_metadata_value(record.get("sourceUrl") or record.get("url") or api_endpoint),
        "document_type": "court_case",
        "source": "kleopatra_api",
        "court_scope": court,
        "query_name": coerce_metadata_value(query_name),
        "year": year,
        "stage": stage,
        "api_endpoint": api_endpoint,
        "record_id": coerce_metadata_value(record.get("id") or record.get("caseId") or record.get("case_id")),
    }
    if bench_id:
        metadata["bench_id"] = bench_id
    if district_id:
        metadata["district_id"] = district_id
    if complex_id:
        metadata["complex_id"] = complex_id
    if party_type:
        metadata["party_type"] = party_type

    for key in ("benchName", "districtName", "complexName", "courtName"):
        if record.get(key) and key not in metadata:
            metadata[key] = coerce_metadata_value(record.get(key))
    return {key: value for key, value in metadata.items() if value not in (None, "")}


def record_to_text(record: dict[str, Any]) -> str:
    lines = flatten_json(record)
    return "\n".join(lines) if lines else json.dumps(record, ensure_ascii=False)


def export_raw_payload(export_dir: Path, filename: str, payload: dict[str, Any]) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ingest_search_results(
    *,
    court: str,
    name: str,
    year: str,
    stage: str,
    party_type: str | None,
    bench_id: str | None,
    district_id: str | None,
    complex_id: str | None,
    export_dir: Path,
) -> None:
    settings = get_settings()
    client = KleopatraClient(settings)
    try:
        response = client.search_party(
            court,
            name=name,
            stage=stage,
            year=year,
            bench_id=bench_id,
            district_id=district_id,
            complex_id=complex_id,
            party_type=party_type,
        )
    finally:
        client.close()

    records = normalize_response_records(response)
    if not records:
        print(f"No records returned for {court} / {name} / {year}")
        return

    embeddings = EmbeddingService(settings)
    vector_store = VectorStore(settings, embeddings)

    api_endpoint = f"{settings.kleopatra_base_url.rstrip('/')}{'/core/live/supreme-court/search/party' if court == 'supreme' else '/core/live/high-court/search/party' if court == 'high' else '/core/live/district-court/search/party'}"
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_name = slugify(name)
    export_name = f"{court}-{safe_name}-{year}-{timestamp}.json"
    export_raw_payload(export_dir, export_name, response)

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for index, record in enumerate(records):
        text = record_to_text(record)
        record_id = str(record.get("id") or record.get("caseId") or record.get("case_id") or f"{safe_name}-{year}-{index}")
        doc_id = f"kleopatra::{court}::{year}::{slugify(name)}::{record_id}"
        ids.append(doc_id)
        texts.append(text)
        metadatas.append(
            build_metadata(
                court=court,
                query_name=name,
                year=year,
                stage=stage,
                record=record,
                api_endpoint=api_endpoint,
                bench_id=bench_id,
                district_id=district_id,
                complex_id=complex_id,
                party_type=party_type,
            )
        )

    vector_store.add_documents(ids=ids, texts=texts, metadatas=metadatas)
    print(f"Ingested {len(records)} Kleopatra records for {court}: {name} ({year}, stage={stage})")
    print(f"Raw API response saved to {export_dir / export_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch free legal case data from the Kleopatra API and ingest it into the local RAG corpus."
    )
    parser.add_argument("--court", choices=["supreme", "high", "district"], required=True)
    parser.add_argument("--name", action="append", help="Party name to search. You can pass this multiple times.")
    parser.add_argument("--name-file", type=Path, help="Optional text file with one party name per line.")
    parser.add_argument("--year", required=True, help="Case year to search.")
    parser.add_argument("--stage", default="BOTH", help="Search stage: BOTH, PENDING, or DISPOSED.")
    parser.add_argument("--type", dest="party_type", default="ANY", help="Supreme Court party type: ANY, PETITIONER, RESPONDENT.")
    parser.add_argument("--bench-id", help="High Court bench ID.")
    parser.add_argument("--district-id", help="District court district ID.")
    parser.add_argument("--complex-id", help="District court complex ID.")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR, help="Where to save raw API responses.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print counts without writing to Chroma.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    names: list[str] = []

    if args.name:
        names.extend(args.name)
    if args.name_file:
        names.extend(
            line.strip()
            for line in args.name_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    names = [name.strip() for name in names if name and name.strip()]
    if not names:
        raise SystemExit("Provide at least one --name or --name-file value.")

    settings = get_settings()
    if not settings.kleopatra_api_key:
        raise SystemExit("Set KLEOPATRA_API_KEY in backend/.env before running this importer.")

    if args.dry_run:
        client = KleopatraClient(settings)
        try:
            for name in names:
                response = client.search_party(
                    args.court,
                    name=name,
                    stage=args.stage,
                    year=args.year,
                    bench_id=args.bench_id,
                    district_id=args.district_id,
                    complex_id=args.complex_id,
                    party_type=args.party_type,
                )
                records = normalize_response_records(response)
                print(f"{name}: {len(records)} records")
        finally:
            client.close()
        return

    for name in names:
        ingest_search_results(
            court=args.court,
            name=name,
            year=args.year,
            stage=args.stage,
            party_type=args.party_type,
            bench_id=args.bench_id,
            district_id=args.district_id,
            complex_id=args.complex_id,
            export_dir=args.export_dir,
        )


if __name__ == "__main__":
    main()
