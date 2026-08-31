# Offer Pipeline (notebooks)

The pipeline ingests offer PDFs, sanitizes PII, extracts structured facts,
builds the Chroma index, and demonstrates the full retrieval stack
(hybrid BM25+vector+RRF → LLM rerank → refusal gate → cited answers, plus
router, HyDE, statistics and comparison routes).

## Layout

| Path | Purpose | Committed? |
|------|---------|------------|
| `notebooks/` | 5 demo notebooks (run in order 01 → 05) | yes |
| `source/offers/` | 10 fictitious sample offer PDFs + `generate_sample_pdfs.py` | yes |
| `scripts/sanitizer.py` | `PIISanitizer` (regex PII layer) — imported by notebook 02 from `scripts/` | yes |
| `scripts/scrub_notebook_outputs.py` | Scrubs local paths/hosts from notebook **outputs** before committing | yes |
| `data/redacted/` | Sanitized full texts + PII block reports (fictitious PII) | yes |
| `data/extracted/` | Structured facts per offer (JSON) | yes |
| `data/raw/` | Unredacted intermediate texts | **no** |
| `data/db/chroma/` | Chroma index (collection `offers`) — the interface to the app | **no** |

## Setup

```bash
pip install -r scripts/requirements.txt
cp .env.example .env   # adjust LLM/EMBED endpoints
```

Notebooks load `.env` from the repo root (they resolve paths relative to
`Path.cwd().parent`, so run them from inside `notebooks/`).

## Run

Execute the notebooks in order (01 → 05). Each is self-contained and
idempotent — re-running 03 rebuilds the index from scratch.

1. `01-ingest-normalize` — PDF → text (PyMuPDF, per-page markers)
2. `02-sanitize-extract` — PII sanitization + structured fact extraction
3. `03-build-index` — chunk (1500/300) + embed (nomic-embed-text) → Chroma
4. `04-retrieval-demo-rag` — hybrid retrieval, rerank, refusal gate, citations
5. `05-retrieval-demo-full` — router, HyDE, statistics + comparison routes

### Resume mode vs. clean slate

The three data stages (01–03) start with a `CLEAN_SLATE` flag, **default
`False` (resume mode)**:

- **`False` (default):** finished offers are skipped via the per-offer
  caches, so re-running is safe and cheap — existing data is never
  overwritten. If no data exists yet, the run simply processes everything.
- **`True`:** the stage's own output directory is wiped first and every
  offer is reprocessed from scratch (fresh LLM calls). Use this when you
  want to regenerate the committed outputs or after changing the
  extraction prompts/logic.

Each flag only affects its own stage (01 → `data/raw/`, 02 →
`data/redacted/` + `data/extracted/`, 03 → `data/db/`); later stages are
untouched. Note 03 rebuilds the Chroma collection either way, so its flag
only controls whether the artifact directories are removed first.

## Before committing notebook changes

Notebook outputs are committed, but they are generated on a local machine and
can leak environment details (absolute paths, the internal LLM endpoint).
Run the scrubber before every commit that includes notebook changes:

```bash
python scripts/scrub_notebook_outputs.py --check   # report only (exit 1 if found)
python scripts/scrub_notebook_outputs.py           # scrub in place
```

It rewrites **outputs only** (cell sources stay untouched):
repo-absolute paths become repo-relative, other `/Users/<name>/...` paths
become `<HOME>/...`, and internal hosts/URLs become `<INTERNAL-HOST>`/`<URL>`.

## Using the index in the app

The app (`app/`) reads the same collection `offers` via
`INDEX_DIR` in `.env`. Point it at the pipeline output:

```
INDEX_DIR=data/db/chroma
```

The only interface between pipeline and app is the index on disk —
metadata fields `angebot_id`, `datum`, `preis` are the contract.
