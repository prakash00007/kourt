# Kourt Backend

FastAPI backend for the Indian lawyer AI copilot MVP.

## Features

- `POST /api/chat`: RAG-based legal research over Indian legal documents
- `POST /api/upload`: judgment PDF upload and structured summary generation
- `POST /api/draft`: Indian legal draft generation
- `GET /api/health`: operational health plus vector-store status

## Production hardening included

- Structured JSON logging
- Request IDs on every response
- Redis-backed distributed rate limiting
- Centralized error handling
- LLM fallback from primary provider to fallback model/provider
- Upload validation for type, size, extractable text, and page count
- Redis-backed TTL caching for repeated chat, draft, and summary requests
- Retrieval filtering and de-duplication
- Async PostgreSQL with SQLAlchemy models for users and document metadata
- JWT authentication with protected research, upload, and draft endpoints
- Alembic migration setup for schema changes
- S3/MinIO-backed PDF storage with no local disk persistence for uploads
- PII redaction before LLM calls and deanonymization for final drafts
- Redis-backed per-user daily draft usage limit

## Local setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d postgres redis minio
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Authentication

- `POST /api/auth/signup`
- `POST /api/auth/login`

Use the returned bearer token in the `Authorization: Bearer <token>` header for:

- `POST /api/chat`
- `POST /api/upload`
- `POST /api/draft`

## Ingest legal documents

Place PDFs in a folder and add optional sidecar metadata JSON with the same file name.

Example metadata:

```json
{
  "title": "Tofan Singh v. State of Tamil Nadu",
  "citation": "(2021) 4 SCC 1",
  "court": "Supreme Court of India",
  "source_url": "https://indiankanoon.org/doc/..."
}
```

Run ingestion:

```bash
PYTHONPATH=. python scripts/ingest_legal_corpus.py ./sample_data
```
