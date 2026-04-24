# Kourt Backend

FastAPI backend for the Indian lawyer AI copilot MVP.

## Features

- `POST /api/chat`: RAG-based legal research over Indian legal documents
- `POST /api/agents/research`: LangGraph-orchestrated supervisor + subagent workflow with trace output
- `POST /api/upload`: judgment PDF upload and structured summary generation
- `POST /api/draft`: Indian legal draft generation
- `GET /api/health`: operational health plus vector-store status
- `GET /api/health/live`: liveness probe endpoint
- `GET /api/health/ready`: readiness probe endpoint
- `GET /api/metrics`: Prometheus metrics endpoint

## Agent folder architecture

The backend now uses a hierarchical folder layout for agent workflows:

```text
backend/app/agents/
├── main/
│   └── supervisor.py                            # top supervisor ("main subagent")
├── shared/
│   └── trace.py                                 # trace/report contracts
└── tasks/
    ├── research/
    │   ├── supervisor.py                        # LangGraph-compiled research supervisor
    │   ├── state.py                             # typed graph state contract
    │   └── subagents/
    │       ├── planner.py
    │       ├── retriever.py
    │       ├── synthesizer.py
    │       └── verifier.py
    ├── drafting/
    │   ├── supervisor.py
    │   └── subagents/
    │       └── drafting_worker.py
    └── summarization/
        ├── supervisor.py
        └── subagents/
            └── summarization_worker.py
```

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

## Free API source for legal data

For API-based corpus seeding, the best fully free source I found is the Kleopatra E-Courts India API:

- [Kleopatra API docs](https://e-courts-india-api.readme.io/)

It uses a bearer API key and exposes party-name search endpoints for:

- Supreme Court
- High Courts
- District Courts

Example usage from the backend folder:

```bash
./venv/bin/python scripts/ingest_kleopatra_cases.py \
  --court supreme \
  --name "State of Tamil Nadu" \
  --year 2021 \
  --stage BOTH
```

Notes:

- This API is free in the sense that the docs present it as a free developer API, but you still need a valid API key from Kleopatra.
- It is best for seeding the corpus from known party names and court scopes, not for topic search like "NDPS bail" by itself.
- The script writes raw API responses to `backend/data/kleopatra_exports`, which is already ignored by git.

## Other free API option

If you want a free API with no key at all, use InsightLaw:

- [InsightLaw API](https://insightlaw.in/)

It currently exposes Constitution, IPC, and BNS text plus search endpoints.

Example:

```bash
cd /Users/prakash/Documents/kourt/backend
./venv/bin/python scripts/ingest_insightlaw_corpus.py \
  --corpus ipc \
  --start 1 \
  --end 50
```

Notes:

- This is useful for building a statutory backbone and general criminal-law context.
- It does not appear to provide NDPS judgments.
- The API is free and keyless, with a free tier limit documented on the site.

## Supreme Court open data source

For actual judgment ingestion, the most useful free source is the official AWS open data bucket for Indian Supreme Court judgments:

- [AWS Open Data registry entry](https://registry.opendata.aws/indian-supreme-court-judgments/)

The backend includes a selective importer that looks for NDPS-related judgments and pulls the matching PDFs from the public bucket:

```bash
cd /Users/prakash/Documents/kourt/backend
./venv/bin/python scripts/ingest_supreme_court_ndps.py \
  --year-from 2019 \
  --year-to 2024 \
  --limit-per-year 12
```

If you want more or fewer hits, tweak `--keywords` or the year range. The importer stores raw year-level match reports in `backend/data/aws_scj_exports`.

## District court starter path

District-court data is much harder to obtain as a clean public API, so the backend now includes a Bhopal-first metadata importer.

Put district exports under:

- `backend/district_sources/bhopal/`

Supported inputs:

- CSV
- Parquet
- JSON
- JSONL

Run the importer:

```bash
cd /Users/prakash/Documents/kourt/backend
./venv/bin/python scripts/ingest_bhopal_district_cases.py
```

Useful variants:

```bash
./venv/bin/python scripts/ingest_bhopal_district_cases.py --focus all
./venv/bin/python scripts/ingest_bhopal_district_cases.py --focus ndps
./venv/bin/python scripts/ingest_bhopal_district_cases.py --dry-run
```

What it does:

- filters records to `Madhya Pradesh` + `Bhopal`
- narrows the corpus to `criminal` records by default
- normalizes messy district metadata into consistent case cards
- writes a JSONL export to `backend/data/district_case_exports/bhopal/`
- ingests those case cards into Chroma for retrieval

Important limitation:

- this importer is `metadata-first`, not full-text judgments
- it helps you build district coverage and candidate retrieval, but for real district case-law answers you will still want order/judgment text from e-Courts or another source

The export folder is also a good remote-storage handoff point if you later move district RAG data into S3, R2, or another object store.
