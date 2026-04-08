# Contributing to Kourt

Thanks for contributing to Kourt.

This repository is an MVP for an AI copilot focused on Indian legal work. The product currently centers on three workflows only:

- RAG-based legal research
- judgment PDF summarization
- first-draft legal document generation

If you are contributing here, the most helpful mindset is to make those three workflows more reliable, more grounded, and easier to operate. Avoid widening scope casually into unrelated product areas unless the change clearly supports the MVP.

## Before you start

Read these files first:

- [README.md](/Users/prakash/Documents/kourt/README.md)
- [docs/collaborator-guide.md](/Users/prakash/Documents/kourt/docs/collaborator-guide.md)
- [docs/mvp-guide.md](/Users/prakash/Documents/kourt/docs/mvp-guide.md)

Those documents explain what the product is, how it runs locally, what has already been fixed, and how the repository is structured.

## Core contribution principles

### 1. Preserve MVP focus

Kourt is not a general-purpose chatbot. Contributions should strengthen one or more of these:

- retrieval quality
- citation quality
- judgment summarization quality
- draft usefulness
- local reliability
- operational clarity

### 2. Prefer grounded behavior over flashy behavior

In a legal product, incomplete but honest is better than polished but invented.

Good changes:

- better source retrieval
- stronger metadata
- clearer fallback behavior
- more transparent disclaimers
- better handling of weak or missing source material

Risky changes:

- more confident legal wording without stronger retrieval
- hiding missing-corpus issues behind generic answers
- presenting synthetic outputs as authoritative

### 3. Respect local demo mode

This repo currently supports a frictionless local demo flow:

- `/login` redirects to `/draft`
- `chat`, `upload`, and `draft` work without requiring a token in local demo mode

Do not remove or break this casually. If you improve auth, keep local contribution and testing practical.

### 4. Do not commit local secrets or local data

Never commit:

- `.env`
- `.env.local`
- local DB files
- `backend/data/`
- `node_modules/`
- `.next/`
- local venv folders
- corpus PDFs or JSON files unless there is a deliberate reason and clear rights to share them

The repo already ignores the main unsafe files, but contributors should still check staged changes before committing.

## Repo map

### Frontend

- `frontend/app/` route pages
- `frontend/components/` UI panels
- `frontend/context/` auth context
- `frontend/lib/` API client and browser helpers
- `frontend/scripts/` standalone runtime helpers

### Backend

- `backend/app/api/` routes and dependencies
- `backend/app/core/` config, middleware, security, cache, logging
- `backend/app/db/` database setup
- `backend/app/models/` SQLAlchemy models
- `backend/app/schemas/` request and response models
- `backend/app/services/` business logic
- `backend/scripts/` corpus ingestion scripts
- `backend/corpus_uploads/` folder for RAG source documents

### Docs

- `docs/mvp-guide.md`
- `docs/collaborator-guide.md`

## Recommended reading order for contributors

If you are new to the codebase, start in this order:

1. `frontend/lib/api.ts`
2. `frontend/components/chat-panel.tsx`
3. `frontend/components/upload-panel.tsx`
4. `frontend/components/draft-panel.tsx`
5. `backend/app/api/deps.py`
6. `backend/app/services/research.py`
7. `backend/app/services/summarization.py`
8. `backend/app/services/drafting.py`
9. `backend/app/services/vector_store.py`
10. `backend/scripts/ingest_legal_corpus.py`

That sequence gives a fast mental model of how the product actually works.

## Local setup

### Backend

```bash
cd /Users/prakash/Documents/kourt/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd /Users/prakash/Documents/kourt/frontend
npm install
cp .env.local.example .env.local
npm run build
npm start
```

### App URLs

- frontend: [http://localhost:3000](http://localhost:3000)
- backend health: [http://localhost:8000/api/health](http://localhost:8000/api/health)

## Working with the RAG corpus

The RAG corpus is not populated through the user-facing upload page.

To add legal source material:

1. put text-extractable PDFs in [backend/corpus_uploads](/Users/prakash/Documents/kourt/backend/corpus_uploads)
2. optionally add same-name metadata JSON files
3. run:

```bash
cd /Users/prakash/Documents/kourt/backend
./venv/bin/python scripts/ingest_legal_corpus.py
```

Use `/api/health` to check `vector_document_count` afterward.

If `vector_document_count` is `0`, research quality will be weak no matter how good the UI looks.

## Branching and commits

Keep changes focused and reviewable.

Recommended branch naming:

- `feature/<short-name>`
- `fix/<short-name>`
- `docs/<short-name>`

Examples:

- `feature/admin-ingest-page`
- `fix/standalone-assets`
- `docs/setup-cleanup`

Commit messages should be short and concrete:

- `Add collaborator guide`
- `Fix standalone asset serving`
- `Improve upload fallback summary`

Avoid giant mixed-purpose commits if possible.

## Pull request expectations

A strong PR for this repo should answer:

- what user or developer problem does this solve
- which workflow does it affect: research, upload, draft, or infrastructure
- how was it tested locally
- are there any fallbacks, caveats, or behavior changes

When opening a PR, include:

- a short summary
- screenshots for frontend changes when useful
- exact test steps
- any env or migration notes

## Testing guidance

There is not yet a large automated test suite, so manual testing discipline matters.

At minimum, test the flow you changed.

### If you changed research

Check:

- `/chat` renders correctly
- request reaches backend
- retrieval works when the corpus contains data
- fallback response is still safe when the corpus is empty

### If you changed upload

Check:

- file selection works
- PDF validation still works
- extractable PDFs return a structured summary
- failures are surfaced clearly

### If you changed drafting

Check:

- `/draft` renders correctly
- result format still looks usable
- fallback draft behavior still works if provider calls fail

### If you changed infra or startup behavior

Check:

- backend boots locally
- frontend boots with `npm start`
- the standalone server serves CSS and JS correctly
- `/api/health` still returns expected service status

## Common pitfalls

### 1. Mistaking upload for corpus ingestion

The upload page summarizes a single PDF. It does not currently train or ingest the RAG corpus.

### 2. Debugging prompts before debugging retrieval

If research output is weak, check corpus coverage and `vector_document_count` first.

### 3. Breaking standalone frontend startup

The standalone start path includes a helper script that copies static assets into the standalone bundle. If this is removed or bypassed, the app may render without CSS or JS.

### 4. Treating demo mode as production mode

Local demo behavior is helpful for contributors, but it should not be mistaken for the final production access model.

## Good first contributions

If you are looking for a useful first task, these are good options:

- improve README clarity
- improve error messages
- build an admin corpus upload and ingestion page
- add indexed-document visibility
- improve citation rendering in chat
- improve local setup instructions
- add lightweight automated tests around ingestion or fallback behaviors

## Code style and collaboration norms

- keep files readable and avoid unnecessary abstraction
- prefer changing the smallest layer that solves the problem
- keep routes thin and business logic in services
- document behavior changes when they are non-obvious
- do not revert someone else’s unrelated work without discussion
- if a change has product consequences, explain them in plain language

## Final note

The best contributions to Kourt are the ones that make a lawyer trust the product more:

- better retrieval
- better source clarity
- better summaries
- better drafts
- better operational reliability

If you are unsure what to work on, choose the change that reduces hallucination, reduces friction, or improves the quality of grounded legal output.
