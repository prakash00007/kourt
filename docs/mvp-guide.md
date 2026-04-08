# Kourt MVP Build Guide

## 1. Product scope

Build only these three workflows:

- Legal research chat
- Judgment summarization from PDF
- Legal draft generation

This keeps the MVP focused on daily time-saving tasks for solo and small-firm Indian lawyers.

## 2. File structure

```text
kourt/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── scripts/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── .env.local.example
│   └── package.json
└── docs/
```

## 3. Backend flow

### Legal research

1. `POST /api/chat` receives the user query.
2. `EmbeddingService` turns the query into a vector.
3. `VectorStore` searches Chroma for the top legal chunks.
4. `ResearchService` builds a prompt with the query and retrieved context.
5. `LLMService` sends the prompt to Claude or OpenAI.
6. API returns answer, citations, source excerpts, and disclaimer.

### Judgment summarization

1. `POST /api/upload` receives a PDF.
2. `PDFParser` extracts text using PyMuPDF, then falls back to pdfplumber if needed.
3. Text is cleaned and trimmed.
4. `SummarizationService` prompts the LLM for facts, issues, judgment, and key takeaways.
5. API returns structured sections and disclaimer.

### Draft generation

1. `POST /api/draft` receives document type and case details.
2. `DraftingService` formats a legal drafting prompt.
3. LLM returns a structured first draft with placeholders instead of invented facts.

## 4. RAG ingestion pipeline

Use real Indian legal data:

- Supreme Court judgments
- High Court judgments
- India Code Bare Acts
- eCourts or NJDG metadata where lawful and available

### Ingestion steps

1. Download PDFs into a folder like `backend/sample_data/`.
2. Add sidecar JSON metadata where possible.
3. Run the ingestion script:

```bash
cd /Users/prakash/Documents/kourt/backend
PYTHONPATH=. python scripts/ingest_legal_corpus.py ./sample_data
```

### Suggested sidecar metadata

```json
{
  "title": "Arnesh Kumar v. State of Bihar",
  "citation": "(2014) 8 SCC 273",
  "court": "Supreme Court of India",
  "source_url": "https://indiankanoon.org/doc/..."
}
```

### What the script does

1. Extracts text from each PDF
2. Cleans headers, footers, and noisy lines
3. Splits text into 400-word chunks with overlap
4. Creates embeddings
5. Stores chunks plus metadata in Chroma

## 5. Environment setup

### Backend `.env`

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `LLM_PROVIDER=anthropic`
- `EMBEDDING_PROVIDER=sentence-transformers` for cheap local embeddings

### Frontend `.env.local`

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api`

## 6. Deploy to production

### Backend

Use Render, Railway, or AWS App Runner.

Basic Render setup:

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add environment variables from `.env.example`
- Mount persistent disk if using Chroma on the same service

### Frontend

Use Vercel.

- Root directory: `frontend`
- Framework preset: Next.js
- Set `NEXT_PUBLIC_API_BASE_URL` to your backend URL

### Storage

- Move uploaded PDFs to S3
- Keep only metadata or signed URLs in PostgreSQL
- Enable server-side encryption in S3

## 7. MVP hardening checklist

- Add request logging and analytics events
- Add API rate limiting
- Add Redis caching for repeated research queries
- Add signed upload URLs for production PDFs
- Add auth and subscription later, not in the first release

## 8. Testing checklist

Test these before onboarding lawyers:

- Queries return case references for known topics like bail, anticipatory bail, and NDPS
- Responses do not invent citations when retrieval has weak matches
- Uploaded PDFs with scanned or poor text are handled gracefully
- Drafts preserve Indian legal formatting and leave placeholders for missing facts
- Every screen shows the legal disclaimer

## 9. First-user rollout

Start with 10 to 50 lawyers:

- Seed 200 to 500 strong judgments in 3 to 5 common practice areas
- Focus on criminal law first, especially bail and NDPS
- Measure time saved per workflow
- Collect examples where answers miss the right precedent

## 10. Key assumption

This MVP is optimized for speed to launch, not perfect legal coverage. Better retrieval quality from curated Indian legal data will matter more than adding more product features.
