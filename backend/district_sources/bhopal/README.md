# Bhopal District Source Folder

Put public district-court dataset files for Bhopal here.

Recommended sources for this folder:

- Development Data Lab district-court exports
- Any CSV, Parquet, JSON, or JSONL export that contains district-court case metadata
- Later, scraped e-Courts district exports if you generate them yourself

Supported file types:

- `.parquet`
- `.csv`
- `.jsonl`
- `.json`

The importer currently normalizes metadata into case cards for RAG. That means it is useful for:

- district-level procedural search
- filtering by act, section, case type, status, year, police station, or judge
- identifying candidate matters to fetch full orders/judgments for later

It does **not** magically create full judgment text if your source file only contains metadata.

Run the Bhopal importer:

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

Exports are written to:

- `backend/data/district_case_exports/bhopal/`

That export folder is the easiest handoff point if you later want to push normalized district data into remote object storage for a hosted RAG stack.
