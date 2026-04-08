import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.services.embeddings import EmbeddingService
from app.services.pdf_parser import PDFParser
from app.services.vector_store import VectorStore
from app.utils.text import chunk_text

DEFAULT_DATA_DIR = BACKEND_DIR / "corpus_uploads"


def load_metadata(metadata_path: Path) -> dict:
    if not metadata_path.exists():
        return {}
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def sanitize_metadata(metadata: dict) -> dict:
    sanitized: dict = {}
    for key, value in metadata.items():
        if value is None:
            continue
        sanitized[key] = value
    return sanitized


def build_chunk_id(pdf_path: Path, chunk_index: int) -> str:
    raw = f"{pdf_path.resolve()}::{chunk_index}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def ingest_directory(data_dir: Path) -> None:
    settings = get_settings()
    embeddings = EmbeddingService(settings)
    vector_store = VectorStore(settings, embeddings)
    parser = PDFParser()

    data_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {data_dir}")
        return

    for pdf_path in pdf_files:
        metadata_path = pdf_path.with_suffix(".json")
        metadata = load_metadata(metadata_path)
        try:
            text = parser.extract_text(pdf_path)
        except Exception as exc:
            print(f"Skipped {pdf_path.name}: {exc}")
            continue

        chunks = chunk_text(text, chunk_size_words=400, overlap_words=60)

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for index, chunk in enumerate(chunks):
            ids.append(build_chunk_id(pdf_path, index))
            documents.append(chunk)
            metadatas.append(
                sanitize_metadata(
                {
                    "title": metadata.get("title", pdf_path.stem),
                    "citation": metadata.get("citation"),
                    "court": metadata.get("court"),
                    "source_url": metadata.get("source_url"),
                    "document_type": metadata.get("document_type", "judgment"),
                    "chunk_index": index,
                    "file_name": pdf_path.name,
                    "source_folder": data_dir.name,
                }
                )
            )

        if documents:
            vector_store.add_documents(ids=ids, texts=documents, metadatas=metadatas)
            print(f"Ingested {pdf_path.name}: {len(documents)} chunks")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description="Ingest Indian legal PDFs into Chroma.")
    cli.add_argument(
        "data_dir",
        nargs="?",
        default=str(DEFAULT_DATA_DIR),
        help="Directory containing PDFs and optional sidecar metadata JSON files.",
    )
    args = cli.parse_args()
    ingest_directory(Path(args.data_dir))
