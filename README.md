# Kourt

AI copilot for Indian legal work with three core workflows:

- RAG-based legal research chat
- judgment PDF summarization
- first-draft legal document generation

This repository contains a FastAPI backend and a Next.js frontend for a lawyer-focused MVP. The product is designed to help a lawyer search a legal corpus, summarize uploaded judgments, and create structured first drafts faster.

## What the product does

### 1. Research Chat

The chat feature is the RAG part of the product.

- A user asks a legal question in plain English
- the backend embeds that query
- it searches a Chroma vector store containing ingested legal documents
- the top relevant chunks are passed into the LLM
- the app returns a grounded answer with citations and source excerpts

If the legal corpus is empty, the app will tell you it could not find relevant legal materials.

### 2. Judgment Summary

The upload feature is for one-off summarization.

- A user uploads a judgment PDF
- the backend extracts text from the PDF
- the app returns a structured summary with:
  - facts
  - issues
  - judgment
  - key takeaways

Important: this upload flow does not add the uploaded PDF to the RAG corpus. It summarizes the file only.

### 3. Draft Generator

The drafting feature helps generate a first legal draft from matter details.

- A user selects the draft type
- enters the matter facts in plain language
- the app returns a structured draft that can be reviewed and refined by a lawyer

## Current local behavior

This repo is currently configured for a frictionless local demo.

- local demo mode is enabled, so you can use `chat`, `draft`, and `upload` without logging in
- `/login` redirects to `/draft`
- the backend still supports auth endpoints, but local demo mode injects a demo user when no token is provided

That makes it easier to test the product locally and publish the MVP without auth blocking the workflow.

## Repo structure

```text
kourt/
├── backend/
│   ├── app/                      # FastAPI application
│   ├── corpus_uploads/           # Drop PDFs here for RAG ingestion
│   ├── data/                     # Local DB, Chroma store, uploads
│   ├── scripts/                  # Ingestion and utility scripts
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                      # Next.js app router pages
│   ├── components/               # UI components
│   ├── lib/                      # API client and helpers
│   ├── scripts/                  # Runtime helpers for standalone start
│   ├── package.json
│   └── .env.local.example
├── docs/
│   └── mvp-guide.md
└── README.md
```

## Tech stack

### Frontend

- Next.js 16
- React 19
- Tailwind CSS

### Backend

- FastAPI
- SQLAlchemy
- SQLite for the local demo
- ChromaDB for the vector store
- sentence-transformers for embeddings
- Anthropic/OpenAI-compatible LLM integration with graceful fallback behavior

## Local setup

## Backend

```bash
cd /Users/prakash/Documents/kourt/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend health:

- [http://localhost:8000/api/health](http://localhost:8000/api/health)

## Frontend

```bash
cd /Users/prakash/Documents/kourt/frontend
npm install
cp .env.local.example .env.local
npm run build
npm start
```

Frontend app:

- [http://localhost:3000](http://localhost:3000)

## Notes for local demo mode

- `npm start` runs the standalone production server, which is lighter than `npm run dev`
- the repo includes a helper script that copies Next.js static assets into the standalone bundle before launch
- local auth is bypassed for core workflows via demo mode so the app is easier to test

## Main pages

- `/chat` - RAG legal research
- `/upload` - judgment summarization
- `/draft` - legal draft generation

## API endpoints

### Public and demo-friendly

- `GET /api/health`
- `POST /api/chat`
- `POST /api/upload`
- `POST /api/draft`

### Auth endpoints

- `POST /api/auth/signup`
- `POST /api/auth/login`

Compatibility aliases also exist under `/api/v1/...` for some routes.

## RAG corpus: where to upload legal documents

The dedicated folder for RAG source files is:

- [backend/corpus_uploads](/Users/prakash/Documents/kourt/backend/corpus_uploads)

Put your legal source material there:

- Supreme Court judgments
- High Court judgments
- bare acts
- rules
- notifications
- legal commentaries or law-book exports

Supported now:

- text-extractable `*.pdf`
- optional same-name `*.json` metadata sidecar

Example:

- `tofan-singh.pdf`
- `tofan-singh.json`

Example metadata:

```json
{
  "title": "Tofan Singh v. State of Tamil Nadu",
  "citation": "(2021) 4 SCC 1",
  "court": "Supreme Court of India",
  "source_url": "https://indiankanoon.org/doc/...",
  "document_type": "judgment"
}
```

## Ingest documents into the vector store

Run this from the backend folder:

```bash
cd /Users/prakash/Documents/kourt/backend
./venv/bin/python scripts/ingest_legal_corpus.py
```

What happens during ingestion:

- each PDF is parsed
- the extracted text is split into overlapping chunks
- embeddings are generated for each chunk
- the chunks and metadata are stored in Chroma

The local vector store lives at:

- [backend/data/chroma](/Users/prakash/Documents/kourt/backend/data/chroma)

To confirm the corpus has data, open:

- [http://localhost:8000/api/health](http://localhost:8000/api/health)

Check `vector_document_count`.

If it is `0`, your RAG chat has no legal corpus yet.

## Difference between upload and ingestion

This distinction matters:

- `/upload` summarizes one PDF for the user
- `backend/corpus_uploads/` + `scripts/ingest_legal_corpus.py` adds documents to the RAG knowledge base

So this project is not "training the model" in the fine-tuning sense. It is building a searchable legal corpus that the app retrieves from at runtime.

## Free or low-cost legal data sources

These are the most practical sources for this product:

### 1. Indian Kanoon API

Best fit for Indian case-law enrichment.

- useful for judgments, citations, search, and legal references
- good option when you want fresher or broader Indian case-law coverage
- official pricing and terms mention development credit and non-commercial credit options

Links:

- [Indian Kanoon API](https://api.indiankanoon.org/)
- [Indian Kanoon API Pricing](https://api.indiankanoon.org/pricing/)
- [Indian Kanoon API Terms](https://api.indiankanoon.org/terms/)

### 2. Indian Supreme Court Judgments on AWS Open Data

Best free dataset to seed the corpus quickly.

- bulk legal dataset
- not really an API, but very useful for initial RAG ingestion

Link:

- [AWS Open Data: Indian Supreme Court Judgments](https://registry.opendata.aws/indian-supreme-court-judgments/)

### 3. India Code

Best official source for statutes, acts, rules, and notifications.

- useful for bare acts and statutory material
- works better as a source website than as a ready-made public API

Link:

- [India Code](https://www.indiacode.nic.in/)

## Recommended data strategy

If you want the fastest path to a useful MVP:

1. seed the corpus with Indian Supreme Court judgments
2. add the bare acts and rules most relevant to your target practice areas
3. later connect Indian Kanoon API for fresher search coverage and metadata enrichment

## Example workflows

### Research workflow

1. Ingest legal PDFs into `backend/corpus_uploads`
2. Run the ingestion script
3. Open `/chat`
4. Ask a legal question
5. Review citations and excerpts

### Summary workflow

1. Open `/upload`
2. Upload a PDF judgment
3. Review facts, issues, judgment, and key takeaways

### Draft workflow

1. Open `/draft`
2. Select the draft type
3. Enter the case details
4. Generate the draft
5. Edit and verify before external use

## Known limitations

- if `vector_document_count` is `0`, RAG chat cannot return meaningful legal retrieval
- if the external LLM provider is unavailable, the app falls back to local draft and summary behavior where possible
- uploaded PDFs are summarized, not automatically ingested into the RAG corpus
- the corpus ingestion flow currently expects text-extractable PDFs
- there is no admin UI yet for corpus ingestion from the browser

## Suggested next features

- admin corpus upload page that ingests PDFs directly into RAG
- source management dashboard for uploaded corpus files
- practice-area tagging and filters
- better citation rendering and linked authorities
- corpus deduplication and re-index workflows
- production auth and multi-user organization support

## GitHub publishing checklist

Before pushing this repo to GitHub:

- do not commit `.env` files
- do not commit local databases or vector stores
- do not commit `node_modules`, `.next`, or local virtual environments
- do not commit copyrighted legal PDFs unless you are sure you have the right to publish them

This repo already ignores the main local-only files and folders in `.gitignore`.

## Publish to GitHub

If you want to create the repo manually:

```bash
cd /Users/prakash/Documents/kourt
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

If you prefer GitHub CLI:

```bash
cd /Users/prakash/Documents/kourt
gh auth login
git init
git add .
git commit -m "Initial commit"
gh repo create <repo-name> --source=. --remote=origin --private --push
```

Use `--public` instead of `--private` only if you intentionally want this code visible to everyone.

## Product summary in one line

Kourt is an AI legal-work assistant for Indian lawyers that combines corpus-backed legal research, judgment summarization, and first-draft generation in one local MVP.
