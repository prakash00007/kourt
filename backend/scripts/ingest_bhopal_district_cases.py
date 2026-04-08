from __future__ import annotations

import argparse
import csv
from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

import pyarrow.parquet as pq

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStore


DEFAULT_INPUT_DIR = BACKEND_DIR / "district_sources" / "bhopal"
DEFAULT_EXPORT_DIR = BACKEND_DIR / "data" / "district_case_exports" / "bhopal"
BATCH_SIZE = 200

FIELD_ALIASES = {
    "state": [
        "state",
        "state_name",
        "statecode",
        "state_code_name",
        "st_name",
    ],
    "district": [
        "district",
        "district_name",
        "districtname",
        "dist_name",
        "dist_name_clean",
        "district_code_name",
    ],
    "court_name": [
        "court",
        "court_name",
        "courtname",
        "establishment_name",
        "bench",
        "bench_name",
    ],
    "case_reference": [
        "cnr",
        "cnr_number",
        "case_no",
        "case_number",
        "caseno",
        "case_id",
        "ddl_case_id",
        "id",
    ],
    "case_type": [
        "case_type",
        "casetype",
        "type_name",
        "case_category",
        "nature_of_case",
    ],
    "status": [
        "status",
        "case_status",
        "disposal_nature",
        "decision",
        "decision_type",
        "stage",
    ],
    "filing_date": [
        "filing_date",
        "registration_date",
        "reg_date",
        "filed_on",
        "date_of_filing",
    ],
    "decision_date": [
        "decision_date",
        "disposal_date",
        "disposed_on",
        "judgment_date",
        "order_date",
    ],
    "year": [
        "year",
        "case_year",
        "filing_year",
    ],
    "act": [
        "act",
        "act_name",
        "act_type",
        "act_section",
        "act_sections",
        "acts",
        "acts_sections",
    ],
    "sections": [
        "section",
        "sections",
        "section_name",
        "section_names",
        "section_numbers",
        "section_text",
    ],
    "petitioner": [
        "petitioner",
        "petitioner_name",
        "pet_name",
        "applicant",
        "plaintiff",
    ],
    "respondent": [
        "respondent",
        "respondent_name",
        "resp_name",
        "accused",
        "defendant",
    ],
    "judge": [
        "judge",
        "judge_name",
        "presiding_judge",
        "judge_designation",
    ],
    "police_station": [
        "police_station",
        "ps_name",
        "fir_police_station",
    ],
    "source_url": [
        "source_url",
        "url",
        "record_url",
        "case_url",
    ],
}

FOCUS_KEYWORDS = {
    "criminal": [
        "bail",
        "fir",
        "police",
        "criminal",
        "sessions",
        "ipc",
        "crpc",
        "bns",
        "custody",
        "remand",
        "charge sheet",
        "chargesheet",
    ],
    "ndps": [
        "ndps",
        "narcotic",
        "narcotics",
        "psychotropic",
        "commercial quantity",
        "section 37",
    ],
}


def canonicalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, list):
        return ", ".join(normalize_text(item) for item in value if normalize_text(item))
    return str(value).strip()


def normalize_row(row: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        normalized[canonicalize_key(str(key))] = normalize_text(value)
    return normalized


def pick_first(row: dict[str, str], aliases: list[str]) -> str:
    for alias in aliases:
        value = row.get(canonicalize_key(alias), "")
        if value:
            return value
    return ""


def normalize_location(value: str) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def row_matches_location(row: dict[str, str], *, state: str, district: str) -> bool:
    state_query = normalize_location(state)
    district_query = normalize_location(district)

    state_values = [
        pick_first(row, FIELD_ALIASES["state"]),
        pick_first(row, FIELD_ALIASES["court_name"]),
    ]
    district_values = [
        pick_first(row, FIELD_ALIASES["district"]),
        pick_first(row, FIELD_ALIASES["court_name"]),
    ]

    state_hit = any(state_query in normalize_location(value) for value in state_values if value)
    district_hit = any(district_query in normalize_location(value) for value in district_values if value)
    return state_hit and district_hit


def row_matches_focus(row: dict[str, str], focus: str) -> bool:
    if focus == "all":
        return True

    haystack = " ".join(row.values()).lower()
    keywords = FOCUS_KEYWORDS[focus]
    return any(keyword in haystack for keyword in keywords)


def infer_year(row: dict[str, str]) -> str:
    direct = pick_first(row, FIELD_ALIASES["year"])
    if direct:
        return direct

    for alias_group in ("filing_date", "decision_date"):
        value = pick_first(row, FIELD_ALIASES[alias_group])
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            return match.group(0)
    return ""


def build_record_title(case_reference: str, court_name: str, district: str) -> str:
    if case_reference:
        return f"{district} district case {case_reference}"
    if court_name:
        return f"{court_name} district case"
    return f"{district} district court record"


def build_case_text(record: dict[str, str]) -> str:
    lines = [
        "District Court Case Metadata",
        f"State: {record['state'] or 'Madhya Pradesh'}",
        f"District: {record['district'] or 'Bhopal'}",
        f"Court: {record['court_name'] or 'Not available'}",
        f"Case reference: {record['case_reference'] or 'Not available'}",
        f"Case type: {record['case_type'] or 'Not available'}",
        f"Status: {record['status'] or 'Not available'}",
        f"Filing date: {record['filing_date'] or 'Not available'}",
        f"Decision date: {record['decision_date'] or 'Not available'}",
        f"Year: {record['year'] or 'Not available'}",
        f"Act: {record['act'] or 'Not available'}",
        f"Sections: {record['sections'] or 'Not available'}",
        f"Petitioner or applicant: {record['petitioner'] or 'Not available'}",
        f"Respondent or accused: {record['respondent'] or 'Not available'}",
        f"Judge: {record['judge'] or 'Not available'}",
        f"Police station: {record['police_station'] or 'Not available'}",
        "",
        "This is a structured district-court metadata record for retrieval and filtering.",
        "It may not include the full order or judgment text.",
    ]
    return "\n".join(lines)


def build_metadata(
    *,
    record: dict[str, str],
    title: str,
    source_file: Path,
    source_name: str,
    focus: str,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "title": title,
        "citation": record["case_reference"] or None,
        "court": record["court_name"] or "Bhopal District Court",
        "source_url": record["source_url"] or None,
        "document_type": "district_case_metadata",
        "source": source_name,
        "state": record["state"] or "Madhya Pradesh",
        "district": record["district"] or "Bhopal",
        "case_reference": record["case_reference"] or None,
        "case_type": record["case_type"] or None,
        "status": record["status"] or None,
        "filing_date": record["filing_date"] or None,
        "decision_date": record["decision_date"] or None,
        "year": record["year"] or None,
        "act": record["act"] or None,
        "sections": record["sections"] or None,
        "petitioner": record["petitioner"] or None,
        "respondent": record["respondent"] or None,
        "judge": record["judge"] or None,
        "police_station": record["police_station"] or None,
        "source_file": source_file.name,
        "text_coverage": "metadata_only",
        "jurisdiction_scope": "district",
        "focus": focus,
    }
    return {key: value for key, value in metadata.items() if value not in (None, "")}


def build_document_id(source_file: Path, record: dict[str, str]) -> str:
    raw = json.dumps({"source_file": source_file.name, "record": record}, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"district::{source_file.stem}::{digest}"


def iter_csv_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def iter_json_rows(path: Path) -> Iterable[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    yield payload
        return

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
    elif isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            for item in records:
                if isinstance(item, dict):
                    yield item
        else:
            yield payload


def iter_parquet_rows(path: Path) -> Iterable[dict[str, Any]]:
    parquet_file = pq.ParquetFile(path)
    for batch in parquet_file.iter_batches(batch_size=1000):
        table = batch.to_pydict()
        keys = list(table.keys())
        row_count = len(next(iter(table.values()), []))
        for index in range(row_count):
            yield {key: table[key][index] for key in keys}


def iter_rows(path: Path) -> Iterable[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        yield from iter_csv_rows(path)
    elif suffix in {".json", ".jsonl"}:
        yield from iter_json_rows(path)
    elif suffix == ".parquet":
        yield from iter_parquet_rows(path)
    else:
        raise ValueError(f"Unsupported file type: {path.name}")


def discover_input_files(input_paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for input_path in input_paths:
        if input_path.is_file():
            files.append(input_path)
            continue
        if input_path.is_dir():
            for pattern in ("*.parquet", "*.csv", "*.jsonl", "*.json"):
                files.extend(sorted(input_path.rglob(pattern)))
    deduped = sorted(set(files))
    return [path for path in deduped if path.is_file()]


def flush_batch(
    *,
    vector_store: VectorStore,
    ids: list[str],
    texts: list[str],
    metadatas: list[dict[str, Any]],
) -> int:
    if not ids:
        return 0
    vector_store.add_documents(ids=ids, texts=texts, metadatas=metadatas)
    count = len(ids)
    ids.clear()
    texts.clear()
    metadatas.clear()
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize and ingest Bhopal district-court metadata into the local RAG corpus."
    )
    parser.add_argument(
        "--input",
        action="append",
        type=Path,
        help="File or folder with district-court exports. Repeatable. Defaults to backend/district_sources/bhopal.",
    )
    parser.add_argument("--state", default="Madhya Pradesh")
    parser.add_argument("--district", default="Bhopal")
    parser.add_argument("--focus", choices=["all", "criminal", "ndps"], default="criminal")
    parser.add_argument("--source-name", default="ddl_judicial_data")
    parser.add_argument("--limit", type=int, help="Stop after this many matching records.")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_paths = args.input or [DEFAULT_INPUT_DIR]
    files = discover_input_files(input_paths)
    if not files:
        raise SystemExit(
            f"No input files found. Place CSV/Parquet/JSONL exports under {DEFAULT_INPUT_DIR} or pass --input."
        )

    settings = get_settings()
    embeddings = EmbeddingService(settings)
    vector_store = VectorStore(settings, embeddings)

    args.export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    export_path = args.export_dir / f"{canonicalize_key(args.district)}-{args.focus}-{timestamp}.jsonl"
    summary_path = args.export_dir / f"{canonicalize_key(args.district)}-{args.focus}-{timestamp}-summary.json"

    scanned_rows = 0
    location_matches = 0
    focus_matches = 0
    ingested_rows = 0

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    with export_path.open("w", encoding="utf-8") as export_file:
        for source_file in files:
            for raw_row in iter_rows(source_file):
                scanned_rows += 1
                normalized_row = normalize_row(raw_row)
                if not row_matches_location(normalized_row, state=args.state, district=args.district):
                    continue
                location_matches += 1
                if not row_matches_focus(normalized_row, args.focus):
                    continue
                focus_matches += 1

                record = {
                    "state": pick_first(normalized_row, FIELD_ALIASES["state"]) or args.state,
                    "district": pick_first(normalized_row, FIELD_ALIASES["district"]) or args.district,
                    "court_name": pick_first(normalized_row, FIELD_ALIASES["court_name"]),
                    "case_reference": pick_first(normalized_row, FIELD_ALIASES["case_reference"]),
                    "case_type": pick_first(normalized_row, FIELD_ALIASES["case_type"]),
                    "status": pick_first(normalized_row, FIELD_ALIASES["status"]),
                    "filing_date": pick_first(normalized_row, FIELD_ALIASES["filing_date"]),
                    "decision_date": pick_first(normalized_row, FIELD_ALIASES["decision_date"]),
                    "year": infer_year(normalized_row),
                    "act": pick_first(normalized_row, FIELD_ALIASES["act"]),
                    "sections": pick_first(normalized_row, FIELD_ALIASES["sections"]),
                    "petitioner": pick_first(normalized_row, FIELD_ALIASES["petitioner"]),
                    "respondent": pick_first(normalized_row, FIELD_ALIASES["respondent"]),
                    "judge": pick_first(normalized_row, FIELD_ALIASES["judge"]),
                    "police_station": pick_first(normalized_row, FIELD_ALIASES["police_station"]),
                    "source_url": pick_first(normalized_row, FIELD_ALIASES["source_url"]),
                }
                title = build_record_title(record["case_reference"], record["court_name"], args.district)
                document_text = build_case_text(record)
                metadata = build_metadata(
                    record=record,
                    title=title,
                    source_file=source_file,
                    source_name=args.source_name,
                    focus=args.focus,
                )
                normalized_payload = {
                    "title": title,
                    "text": document_text,
                    "metadata": metadata,
                    "raw_record": raw_row,
                }
                export_file.write(json.dumps(normalized_payload, ensure_ascii=False) + "\n")

                if not args.dry_run:
                    ids.append(build_document_id(source_file, record))
                    texts.append(document_text)
                    metadatas.append(metadata)
                    if len(ids) >= BATCH_SIZE:
                        ingested_rows += flush_batch(
                            vector_store=vector_store,
                            ids=ids,
                            texts=texts,
                            metadatas=metadatas,
                        )

                if args.limit and focus_matches >= args.limit:
                    break
            if args.limit and focus_matches >= args.limit:
                break

        if not args.dry_run:
            ingested_rows += flush_batch(vector_store=vector_store, ids=ids, texts=texts, metadatas=metadatas)

    summary = {
        "state": args.state,
        "district": args.district,
        "focus": args.focus,
        "source_name": args.source_name,
        "input_files": [str(path) for path in files],
        "scanned_rows": scanned_rows,
        "location_matches": location_matches,
        "focus_matches": focus_matches,
        "ingested_rows": ingested_rows,
        "export_path": str(export_path),
        "dry_run": args.dry_run,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
