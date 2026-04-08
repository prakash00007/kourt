import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

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
        text = parser.extract_text(pdf_path)
        chunks = chunk_text(text, chunk_size_words=400, overlap_words=60)

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for index, chunk in enumerate(chunks):
            ids.append(str(uuid4()))
            documents.append(chunk)
            metadatas.append(
                {
                    "title": metadata.get("title", pdf_path.stem),
                    "citation": metadata.get("citation"),
                    "court": metadata.get("court"),
                    "source_url": metadata.get("source_url"),
                    "document_type": metadata.get("document_type", "judgment"),
                    "chunk_index": index,
                    "file_name": pdf_path.name,
                }
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
