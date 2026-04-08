# Kourt Collaborator Guide

## Purpose of this document

This file is a practical handoff for anyone joining the Kourt repository and trying to understand what already exists, what was changed to make the MVP usable locally, how the codebase is organized, and where the next contributor should spend attention first. It is intentionally more operational than the main README. The README explains what the product is and how to run it. This guide explains how the project behaves in practice, how the folders connect to each other, what local fixes were applied, where the main risks are, and how a teammate should reason about the repository before making changes.

Kourt is an AI copilot for Indian legal work. It is not a general chatbot. The current MVP focuses on three narrow workflows that save time for a practicing lawyer:

1. RAG-backed legal research chat
2. judgment PDF summarization
3. first-draft legal document generation

Those three workflows are the center of the codebase. Almost every folder, component, service, and script exists to support one of them.

## High-level product summary

The best way to understand Kourt is to think of it as a legal-work assistant rather than a legal-answer engine.

The research chat is the retrieval product. It takes a user query, embeds it, searches the legal corpus in Chroma, and then asks the LLM to answer using retrieved legal text. If the vector store is empty, the chat is honest and says it could not find relevant materials. That is why corpus quality matters more than UI polish at this stage.

The upload flow is not corpus training. It is a one-document utility flow. A lawyer uploads a judgment PDF and receives a structured summary with facts, issues, judgment, and key takeaways. This helps with case review and note preparation. Today this flow does not automatically add uploaded documents into the vector store.

The draft generator is a practical productivity feature. A lawyer describes a matter in plain English, selects a document type, and receives a structured draft that feels like a junior lawyer assembled the first version. The system is designed to produce a useful starting point, not a final filing-ready document.

The local demo mode that is currently enabled is important for collaborators to know. The app was adjusted so that contributors can run and test the core workflows without getting blocked by auth or missing infrastructure. In local development, the app behaves like a product demo environment rather than a locked multi-user production app.

## Current repository state

The repo is in a much more usable state than the original scaffold. Several local-environment problems had to be solved to make it workable on a lightweight machine and publishable as an MVP.

The major improvements already in place are:

- the frontend and backend both run locally without Docker being strictly required
- the frontend can be started in a lightweight production mode with `npm start`
- the standalone Next.js server now serves static CSS and JS correctly
- local demo mode bypasses auth requirements for the core workflows
- `/login` redirects to `/draft` so users do not get trapped in auth
- the backend supports a local SQLite database instead of requiring Postgres
- local file storage fallback exists when S3 or MinIO is unavailable
- Redis-dependent features now degrade more gracefully when Redis is unavailable
- draft and summary features return local fallback output when external AI providers fail
- RAG ingestion has a dedicated folder and a simpler default command
- the repo has a real top-level README and safer git ignore rules for GitHub publishing

These changes are important because future collaborators may otherwise assume the app requires a more complete production stack than it currently does. The present branch is optimized to help a team move fast on product validation.

## How the codebase is organized

The repository has three meaningful top-level working areas:

- `frontend/`
- `backend/`
- `docs/`

The frontend contains the Next.js application. The backend contains the FastAPI API, ingestion logic, services, schemas, and persistence. The docs folder contains planning and handoff documents that explain the intended MVP direction.

### Frontend structure

The frontend is small and intentionally direct.

- `frontend/app/` contains the route pages
- `frontend/components/` contains the page-level UI panels and shared UI pieces
- `frontend/context/` contains the auth context
- `frontend/lib/` contains the API client and basic helpers
- `frontend/scripts/` contains the standalone runtime helper that prepares static assets before server start

The key routes are:

- `frontend/app/page.tsx` for the landing page
- `frontend/app/chat/page.tsx` for legal research
- `frontend/app/upload/page.tsx` for summarization
- `frontend/app/draft/page.tsx` for draft generation
- `frontend/app/login/page.tsx` which now redirects to `/draft`

The most important frontend components are:

- `chat-panel.tsx`
- `upload-panel.tsx`
- `draft-panel.tsx`
- `top-nav.tsx`
- `page-shell.tsx`

The API client in `frontend/lib/api.ts` is central to understanding the frontend. It defines how the browser talks to the backend and now supports optional auth headers so the app can function in demo mode. A contributor touching network behavior should usually start there.

### Backend structure

The backend follows a fairly standard FastAPI service layout.

- `backend/app/api/` contains routing and dependency wiring
- `backend/app/core/` contains config, middleware, error handling, security, logging, cache, and request-level concerns
- `backend/app/db/` contains DB setup
- `backend/app/models/` contains SQLAlchemy models
- `backend/app/schemas/` contains request and response models
- `backend/app/services/` contains business logic
- `backend/app/utils/` contains prompt helpers and text processing
- `backend/scripts/` contains corpus ingestion utilities

The backend is service-oriented. The routes are intentionally thin and most real work happens in service classes. That means collaborators should avoid adding logic directly into route files unless it is route-specific validation.

### Docs structure

The docs folder currently contains:

- `mvp-guide.md`
- this collaborator guide

The existing MVP guide is useful as a conceptual document. This collaborator guide is meant to be more practical and current.

## Main runtime flows

### 1. Research chat flow

The request comes into `POST /api/chat`. The route hands the request to `ResearchService`. That service uses `VectorStore` to search Chroma for relevant chunks. The retrieved chunks are converted into prompt context. Then the LLM service synthesizes an answer. The response includes answer text, citations, sources, and the standard disclaimer.

If retrieval returns nothing, the service returns a safe fallback response rather than pretending to know the law. That behavior is intentional and good.

This means research quality depends on three things:

- the legal corpus actually existing
- chunk quality and metadata quality
- the LLM being able to synthesize grounded context

If contributors want better research output, the highest-leverage work is usually corpus quality, ingestion quality, and metadata quality, not just changing prompts.

### 2. Upload and summary flow

The request comes into `POST /api/upload`. The uploaded file is validated as a PDF. The summarization service reads it, extracts text, anonymizes it for LLM calls, and produces a structured response. If the external LLM service fails, the service generates a local fallback summary from the extracted text.

This fallback is valuable because it keeps the feature usable during outages or bad API credentials. It is not as strong as a real model summary, but it is much better than a hard failure.

The upload feature also stores metadata about the uploaded document, but the current design should not be misunderstood: this is storage for document tracking and summarization, not RAG corpus ingestion.

### 3. Draft generation flow

The request comes into `POST /api/draft`. The backend formats a drafting prompt using the user-provided draft type and details. If the LLM provider is available, the app asks for a structured draft. If not, a local fallback draft is returned so the workflow is still demonstrable.

This fallback behavior is one of the reasons the app feels stable locally even when provider credentials are imperfect.

## What was fixed locally

This section matters because a new collaborator may otherwise undo useful stabilizing work.

### Frontend fixes

The frontend originally had a few issues that blocked normal use:

- typed routes caused strict href issues in some links
- the login route could get stuck on a loading fallback
- the standalone production server did not serve static CSS and JS correctly
- auth gating prevented users from reaching core workflows during local testing

The important fixes were:

- route casts were added where needed for typed route strictness
- the login page was simplified so it no longer depends on an awkward Suspense loading path
- `/login` now redirects to `/draft`
- the nav was changed to emphasize opening the workspace rather than auth actions
- `frontend/scripts/start-standalone.mjs` copies `.next/static` and `public` into the standalone bundle before startup
- feature pages no longer block on missing auth in local demo mode

Future contributors should be careful not to reintroduce the old standalone asset problem. If the start script is removed without another fix, the site may render as unstyled HTML again.

### Backend fixes

The backend originally assumed a more complete environment. Local running was hardened significantly:

- SQLite support was added for local work
- startup now creates tables automatically
- object storage falls back to local disk when MinIO or S3 is unavailable
- Redis-dependent logic degrades gracefully instead of causing hard breaks
- route aliases were added for compatibility with `/api/v1/...`
- password hashing behavior was improved to avoid fragile bcrypt-only assumptions
- draft, summary, and research flows now fail softer when AI services are unavailable
- local demo auth fallback was added so missing bearer tokens do not block feature testing

The anonymous demo user mechanism is implemented in API dependencies. If a valid token is present, the backend uses the real user. If not, and if demo mode is enabled in non-production environments, a demo user is returned.

This is practical for development, but it is not production behavior. Contributors should treat it as a local convenience feature, not the final auth model.

## Data, storage, and local persistence

There are three local persistence concepts to keep straight:

1. the relational database
2. the vector database
3. uploaded file storage

The local relational database is in `backend/data/kourt.db`. It stores user and document metadata.

The vector store lives in `backend/data/chroma`. This is where RAG chunks and embeddings are stored. When contributors ask whether the product has been "trained," this is the real answer: the app is not being fine-tuned. Instead, legal documents are being indexed into a retrieval store that is consulted at runtime.

Uploaded PDFs and derived local storage fallbacks live under `backend/data/uploads`, with extracted text handling under `backend/data/extracted`.

These folders are intentionally gitignored. They should not be committed.

## RAG corpus workflow

The collaborator must understand the difference between the product-facing upload feature and the corpus ingestion workflow.

The correct folder for RAG source files is:

- `backend/corpus_uploads/`

A contributor should place text-extractable legal PDFs there, ideally with optional metadata JSON files using the same base filename. Then they should run:

```bash
cd /Users/prakash/Documents/kourt/backend
./venv/bin/python scripts/ingest_legal_corpus.py
```

The ingestion script now defaults to `backend/corpus_uploads`, so there is no need to pass `PYTHONPATH=.` or a manual path for the common case.

At ingestion time the script:

- reads each PDF
- extracts text
- chunks the text into overlapping segments
- embeds those segments
- stores the chunk text and metadata in Chroma

## Important files and why they matter

This section is for contributors who want a fast map of the files that matter most. The repo contains a lot of standard framework glue, but only a smaller set of files define the actual product behavior.

### Frontend files worth reading early

- `frontend/lib/api.ts`
  This is the browser-to-backend contract. If an endpoint changes, headers change, or auth behavior changes, this file is usually involved.

- `frontend/components/chat-panel.tsx`
  This is the user-facing research workflow. It is a good place to understand what the research feature asks the backend to do and what shape the response takes.

- `frontend/components/upload-panel.tsx`
  This is the judgment summary workflow. A collaborator touching file upload, validation messaging, or summary rendering should begin here.

- `frontend/components/draft-panel.tsx`
  This is the drafting workflow. It shows how the frontend frames the drafting feature and what assumptions are currently built into the default UX.

- `frontend/components/top-nav.tsx`
  This file reflects an important product decision: the current local build emphasizes getting into the workspace fast rather than funneling users through auth.

- `frontend/app/login/page.tsx`
  This page is intentionally simple right now. Anyone trying to restore stricter auth later should review it carefully, because it currently redirects to the draft workspace.

- `frontend/scripts/start-standalone.mjs`
  This file is operationally important. It fixes the common standalone Next.js issue where static assets do not get served correctly from the standalone directory. If this file is changed carelessly, the site can appear broken even though the server is technically running.

### Backend files worth reading early

- `backend/app/api/deps.py`
  This file is critical because it controls auth behavior, the demo-user fallback, and draft quota enforcement. Anyone working on auth, access control, or local mode behavior should start here.

- `backend/app/core/config.py`
  This file defines the runtime assumptions of the application. It includes paths for Chroma, uploads, extracted text, database setup, provider selection, and local demo behavior.

- `backend/app/services/container.py`
  This is the wiring layer that assembles services together. It helps contributors see how the app composes embeddings, vector search, storage, caching, summarization, drafting, and research.

- `backend/app/services/research.py`
  This is one of the most important files in the repo. It shows how retrieval results become a grounded answer, how sources and citations are created, and what happens when retrieval finds nothing.

- `backend/app/services/vector_store.py`
  This file is the practical center of the RAG system. It creates the Chroma collection, stores chunk embeddings, and executes search queries.

- `backend/app/services/summarization.py`
  This file explains the summary workflow end to end, including validation, extraction, anonymization, LLM prompting, caching, and fallback behavior.

- `backend/app/services/drafting.py`
  This file explains how the draft-generation feature is actually shaped. Collaborators who want stronger outputs should inspect prompt framing and fallback behavior here.

- `backend/app/services/storage.py`
  This file matters operationally because it decides whether uploads go to object storage or local fallback storage. It is one of the key reasons the app works on a laptop without a full infrastructure stack.

- `backend/app/main.py`
  This is the backend entry point. It sets up startup behavior and is useful when debugging why the app boots, fails, or initializes services differently across environments.

- `backend/scripts/ingest_legal_corpus.py`
  This is the entry point for populating the legal corpus. It is the first place to improve if the team wants browser-triggered ingestion, richer metadata, deduplication, or better observability.

## Production mode versus local demo mode

Contributors should keep a strong distinction in mind between what is currently optimized for local use and what would be expected in a real production deployment.

In local demo mode:

- auth is softened through a demo-user fallback
- SQLite is acceptable
- local file storage fallback is acceptable
- external AI provider failures are tolerated through local fallback outputs
- a contributor can validate the three core product flows even if the full infrastructure stack is incomplete

In production mode, the expectations are different:

- auth should be explicit and role-aware
- database setup should be durable and managed
- object storage should be first-class, not fallback
- provider credentials must be real and actively maintained
- monitoring and failure visibility matter much more
- collaborators should not assume that demo shortcuts are appropriate defaults

This matters because a new contributor could easily "clean up" the code and remove local-demo behavior without realizing that it was added deliberately to make the MVP usable and shippable. The right mindset is not to delete that behavior casually, but to separate local-demo behavior from production behavior more cleanly over time.

## Debugging playbook for collaborators

When something looks broken, the fastest way to debug is to identify which layer is failing before changing code.

### If the frontend loads without styles or interactivity

Check the standalone asset flow first.

- confirm the server was started with `npm start`
- confirm `frontend/scripts/start-standalone.mjs` still exists and is being used
- confirm a real `/_next/static/...` CSS file returns `200`

If the HTML renders but CSS and JS do not, it is usually an asset-bundling or standalone-copy problem rather than a React problem.

### If chat returns weak or empty answers

Check the vector store before touching prompts.

- hit `/api/health`
- inspect `vector_document_count`
- if it is `0`, the problem is corpus absence, not model behavior
- if it is nonzero, review the actual source documents being ingested and whether the metadata is usable

The most common mistake in RAG debugging is trying to improve prompt wording when the real issue is retrieval coverage.

### If upload fails

Check whether the PDF is actually text-extractable.

- some PDFs are scanned images with little or no extractable text
- the summarization service validates both PDF structure and extractable text
- a contributor should inspect the extracted text path before blaming the prompt

### If drafts work but look generic

That usually means one of two things:

- the LLM provider failed and the local fallback draft was returned
- the source matter description is too shallow

The fallback is meant to keep the workflow alive, not to produce perfect legal writing.

### If the backend runs but features return fallback outputs

Check provider configuration:

- confirm which provider is selected in config
- confirm the API key is valid
- confirm the target model still exists

A contributor should remember that the app is intentionally coded to degrade gracefully. A graceful response does not always mean the premium path is healthy.

Right now the corpus health can be checked using `/api/health`, especially `vector_document_count`.

If a contributor notices weak research output, the first debug question should be: "Does the vector store actually contain relevant documents?" The second should be: "Are the documents text-extractable and chunking cleanly?" The third should be: "Do the metadata fields make sense for citation rendering?"

## Recommended contribution map

If a new teammate wants to work effectively, here is a good order of study:

1. read the top-level README
2. read this collaborator guide
3. inspect `frontend/lib/api.ts`
4. inspect `backend/app/api/routes.py`
5. inspect `backend/app/services/container.py`
6. inspect `backend/app/services/research.py`
7. inspect `backend/app/services/summarization.py`
8. inspect `backend/app/services/drafting.py`
9. inspect `backend/scripts/ingest_legal_corpus.py`

That sequence gives a contributor a very fast mental model of the whole system.

## Current known gaps and caveats

The app is working, but it is still an MVP and collaborators should not assume everything is production-ready.

The main current caveats are:

- the legal corpus is empty until someone ingests real documents
- uploaded PDFs are summarized but not automatically fed into RAG
- local demo mode bypasses real auth for convenience
- external provider configuration may be incomplete or stale
- fallback outputs are useful, but they are not a substitute for strong provider-backed results
- there is no admin UI yet for managing corpus ingestion from the browser

This means the strongest next-product improvements are not random polish tasks. The best next work is:

- corpus ingestion UX
- better source coverage
- metadata quality
- admin visibility into indexed documents
- clearer production and local-mode separation

## Collaboration guidance

A good collaborator on this repo should follow a few principles.

First, preserve the MVP focus. It is easy to get distracted into adding generalized chatbot behavior, account systems, dashboards, or features unrelated to the three core legal workflows. That would dilute the project.

Second, prefer improvements that increase reliability of the existing flows. Better retrieval quality, clearer citations, stronger PDF handling, and more usable draft structures are high-value improvements.

Third, avoid coupling the frontend too tightly to the current demo mode. The optional auth behavior is useful right now, but the code should still be easy to switch back toward stricter auth later.

Fourth, be careful around environment assumptions. The project is deliberately patched to run on a modest machine and without every supporting service online. Contributors should avoid casually reintroducing heavy dependencies unless they clearly improve product value.

Fifth, keep legal trustworthiness in mind. Fake citations, invented facts, and overconfident legal wording are worse than a partial answer. The app should prefer grounded incompleteness over hallucinated completeness.

## Suggested immediate next tasks for a new contributor

If someone joins the project today, the best backlog is probably:

1. build an admin corpus upload page that stores PDFs into `corpus_uploads` and triggers ingestion
2. add a simple indexed-documents listing page showing titles, citations, and chunk counts
3. improve the research UI so source excerpts and citations are easier to inspect
4. add retry or status messaging around provider fallbacks
5. separate demo mode from production mode more explicitly in the README and env setup
6. add lightweight tests around the ingestion script and the fallback service behavior

## Final orientation

Kourt is already far enough along that a new collaborator should not think of it as a blank starter. It has real workflows, a real repo structure, a functioning local demo environment, a publishable GitHub repository, and a clean mental model. The best way to contribute is to respect the current shape of the product and make the existing legal workflows more dependable, more explainable, and more operationally simple.

If you remember only five things from this document, remember these:

1. Kourt is about research, summary, and drafting only.
2. RAG depends on `backend/corpus_uploads` plus the ingestion script, not the upload page.
3. The current local setup is intentionally demo-friendly and auth-light.
4. The codebase is organized around thin routes and service-layer logic.
5. Retrieval quality and corpus quality will decide whether the product feels genuinely useful to lawyers.
