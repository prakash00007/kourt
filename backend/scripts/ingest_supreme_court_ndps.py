from __future__ import annotations

import argparse
import io
import json
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import boto3
import pyarrow.parquet as pq
from botocore import UNSIGNED
from botocore.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.services.embeddings import EmbeddingService
from app.services.pdf_parser import PDFParser
from app.services.vector_store import VectorStore
from app.utils.text import chunk_text


BUCKET_NAME = "indian-supreme-court-judgments"
DEFAULT_YEAR_FROM = 2019
DEFAULT_YEAR_TO = 2024
DEFAULT_KEYWORDS = [
    "ndps",
    "narcotic",
    "psychotropic",
    "commercial quantity",
    "section 37",
    "narcotics control bureau",
]
DEFAULT_EXPORT_DIR = BACKEND_DIR / "data" / "aws_scj_exports"


@dataclass
class SupremeCourtRecord:
    year: int
    title: str
    citation: str | None
    path: str
    petitioner: str | None
    respondent: str | None
    description: str | None
    raw_html: str | None
    decision_date: str | None
    disposal_nature: str | None
    court: str | None
    case_id: str | None
    cnr: str | None
    available_languages: str | None
    nc_display: str | None
    scraped_at: str | None


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "query"


def export_json(export_dir: Path, filename: str, payload: dict[str, Any]) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_haystack(record: SupremeCourtRecord) -> str:
    return " ".join(
        part for part in [
            record.title,
            record.petitioner or "",
            record.respondent or "",
            record.description or "",
            record.raw_html or "",
            record.citation or "",
            record.nc_display or "",
            record.disposal_nature or "",
        ]
        if part
    ).lower()


def load_year_metadata(client, year: int) -> list[SupremeCourtRecord]:
    key = f"metadata/parquet/year={year}/metadata.parquet"
    obj = client.get_object(Bucket=BUCKET_NAME, Key=key)
    table = pq.read_table(io.BytesIO(obj["Body"].read()))
    records: list[SupremeCourtRecord] = []
    for row in table.to_pylist():
        records.append(
            SupremeCourtRecord(
                year=year,
                title=row.get("title") or "",
                citation=row.get("citation"),
                path=row.get("path") or "",
                petitioner=row.get("petitioner"),
                respondent=row.get("respondent"),
                description=row.get("description"),
                raw_html=row.get("raw_html"),
                decision_date=row.get("decision_date"),
                disposal_nature=row.get("disposal_nature"),
                court=row.get("court"),
                case_id=row.get("case_id"),
                cnr=row.get("cnr"),
                available_languages=row.get("available_languages"),
                nc_display=row.get("nc_display"),
                scraped_at=row.get("scraped_at"),
            )
        )
    return records


def record_matches(record: SupremeCourtRecord, keywords: list[str]) -> bool:
    haystack = build_haystack(record)
    return any(keyword.lower() in haystack for keyword in keywords)


def pdf_member_name(record: SupremeCourtRecord) -> str:
    return f"{record.path}_EN.pdf"


def extract_pdf_text_from_member(tar: tarfile.TarFile, member_name: str, parser: PDFParser) -> str | None:
    try:
        member = tar.getmember(member_name)
    except KeyError:
        return None

    file_obj = tar.extractfile(member)
    if file_obj is None:
        return None

    content = file_obj.read()
    try:
        text = parser.extract_text_from_bytes(content)
    except Exception:
        return None
    return text


def process_year(
    s3,
    year: int,
    keywords: list[str],
    limit_per_year: int | None,
    export_dir: Path,
    parser: PDFParser,
) -> list[dict[str, Any]]:
    records = load_year_metadata(s3, year)
    matches = [record for record in records if record_matches(record, keywords)]
    if limit_per_year is not None:
        matches = matches[:limit_per_year]

    export_json(
        export_dir,
        f"year-{year}-{slugify('-'.join(keywords))}.json",
        {
            "year": year,
            "keywords": keywords,
            "match_count": len(matches),
            "matches": [
                {
                    "title": record.title,
                    "citation": record.citation,
                    "path": record.path,
                    "decision_date": record.decision_date,
                    "disposal_nature": record.disposal_nature,
                }
                for record in matches
            ],
        },
    )

    ingested: list[dict[str, Any]] = []
    wanted = {pdf_member_name(record): record for record in matches}
    tar_key = f"data/tar/year={year}/english/english.tar"
    tar_obj = s3.get_object(Bucket=BUCKET_NAME, Key=tar_key)
    with tarfile.open(fileobj=tar_obj["Body"], mode="r|") as tar:
        for member in tar:
            record = wanted.pop(member.name, None)
            if record is None:
                if not wanted:
                    break
                continue
            file_obj = tar.extractfile(member)
            if file_obj is None:
                continue
            try:
                text = parser.extract_text_from_bytes(file_obj.read())
            except Exception:
                continue
            if text:
                ingested.append({"record": record, "text": text})
            if not wanted:
                break
    return ingested


def ingest_records(items: list[dict[str, Any]]) -> int:
    if not items:
        print("No matching judgments found.")
        return 0

    settings = get_settings()
    embeddings = EmbeddingService(settings)
    vector_store = VectorStore(settings, embeddings)
    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for item in items:
        record: SupremeCourtRecord = item["record"]
        text: str = item["text"]
        card_text = "\n".join(
            [
                f"Case title: {record.title}",
                f"Citation: {record.citation or 'Not available'}",
                f"Decision date: {record.decision_date or 'Not available'}",
                f"Disposal nature: {record.disposal_nature or 'Not available'}",
                "Topics: NDPS, bail, section 37, commercial quantity, narcotics, psychotropic substances",
                "This is an official Supreme Court of India judgment from the AWS open-data archive.",
            ]
        )
        ids.append(f"aws-scj::{record.year}::{record.path}::card")
        texts.append(card_text)
        metadatas.append(
            {
                "title": record.title,
                "citation": record.citation,
                "court": record.court or "Supreme Court of India",
                "source_url": "https://registry.opendata.aws/indian-supreme-court-judgments/",
                "document_type": "case_card",
                "source": "aws_indian_supreme_court_judgments",
                "year": record.year,
                "path": record.path,
                "decision_date": record.decision_date,
                "disposal_nature": record.disposal_nature,
                "case_id": record.case_id,
                "cnr": record.cnr,
                "nc_display": record.nc_display,
                "chunk_index": -1,
            }
        )
        chunks = chunk_text(text, chunk_size_words=450, overlap_words=60)
        if not chunks:
            continue
        for index, chunk in enumerate(chunks):
            ids.append(f"aws-scj::{record.year}::{record.path}::{index}")
            texts.append(chunk)
            metadatas.append(
                {
                    "title": record.title,
                    "citation": record.citation,
                    "court": record.court or "Supreme Court of India",
                    "source_url": "https://registry.opendata.aws/indian-supreme-court-judgments/",
                    "document_type": "judgment",
                    "source": "aws_indian_supreme_court_judgments",
                    "year": record.year,
                    "path": record.path,
                    "decision_date": record.decision_date,
                    "disposal_nature": record.disposal_nature,
                    "case_id": record.case_id,
                    "cnr": record.cnr,
                    "nc_display": record.nc_display,
                    "chunk_index": index,
                }
            )

    if ids:
        vector_store.add_documents(ids=ids, texts=texts, metadatas=metadatas)
    return len(items)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest NDPS-relevant Supreme Court judgments from the AWS open dataset.")
    parser.add_argument("--year-from", type=int, default=DEFAULT_YEAR_FROM)
    parser.add_argument("--year-to", type=int, default=DEFAULT_YEAR_TO)
    parser.add_argument(
        "--keywords",
        default=",".join(DEFAULT_KEYWORDS),
        help="Comma-separated search keywords used against metadata and raw HTML.",
    )
    parser.add_argument("--limit-per-year", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    keywords = [keyword.strip() for keyword in args.keywords.split(",") if keyword.strip()]
    s3 = boto3.client(
        "s3",
        region_name="ap-south-1",
        config=Config(signature_version=UNSIGNED, connect_timeout=30, read_timeout=300, retries={"max_attempts": 3}),
    )
    parser = PDFParser()

    all_items: list[dict[str, Any]] = []
    for year in range(args.year_from, args.year_to + 1):
        try:
            year_items = process_year(
                s3=s3,
                year=year,
                keywords=keywords,
                limit_per_year=args.limit_per_year,
                export_dir=args.export_dir,
                parser=parser,
            )
        except Exception as exc:
            print(f"Skipped year {year}: {exc}")
            continue
        print(f"{year}: {len(year_items)} matched judgments")
        all_items.extend(year_items)

    print(f"Total matched judgments: {len(all_items)}")
    if args.dry_run:
        return

    ingested = ingest_records(all_items)
    print(f"Ingested {ingested} judgments into Chroma")


if __name__ == "__main__":
    main()
