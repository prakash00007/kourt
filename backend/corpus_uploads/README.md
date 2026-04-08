Drop your RAG source files here.

Supported now:
- `*.pdf` legal judgments, orders, acts, rules, bare acts, commentaries, or law-book exports that contain extractable text
- optional sidecar `*.json` metadata file with the same base name

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

To ingest everything in this folder into the RAG store:

```bash
cd /Users/prakash/Documents/kourt/backend
./venv/bin/python scripts/ingest_legal_corpus.py
```

The embeddings are stored locally in:
- `/Users/prakash/Documents/kourt/backend/data/chroma`
