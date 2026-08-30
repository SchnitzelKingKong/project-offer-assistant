# Project Offer Assistant

*Your in-house offer history as a RAG database — for project-based service providers.*

## Mission

The Project Offer Assistant turns a growing pile of past project offers into a
searchable, self-hosted knowledge base.

It ingests multiple offer documents — heterogeneous PDFs of 1–5 pages each,
with no uniform structure — and turns them into a structured RAG database that
you can query in natural language.

The focus is on the context around the numbers: **framework conditions,
timelines, and line items** — how similar projects were scoped, what was
included, under which terms.

It is **not a price calculator**. For vague inquiries it answers the question
that actually matters in the first call: *"where do we end up?"* — an
orientation based on what similar projects looked like before.

Everything runs in-house: no cloud APIs, no per-token costs, full data privacy.

## Architecture

```
app/streamlit_app.py      thin UI layer (chat, citations, status)
app/src/rag_system/       RAG logic (testable without the UI)
├── config.py             settings from .env
├── retriever.py          ChromaDB vector retrieval
└── llm.py                answer generation (OpenAI-compatible endpoint)
app/tests/                pytest suite
notebooks/                offer pipeline (PDF → sanitize → extract → index)
source/offers/            fictitious sample offers + generator
sanitizer.py              PII sanitizer (used by the pipeline)
```

**Build-once, reload-later:** the vector index is built once by the pipeline
notebooks (persisted to `data/db/chroma/`) and the app only reloads it via
`INDEX_DIR` in `.env` — never re-embeds at query time.

## Pipeline

The offer pipeline (PDF → sanitize → extract → index → retrieval demo) lives at
the repository root: `notebooks/`, `source/offers/`, `sanitizer.py`, `data/`.
See [`notebooks/PIPELINE.md`](notebooks/PIPELINE.md) for the layout, setup,
and how to run the notebooks (01 → 05).

| Component | Choice |
|---|---|
| LLM | Qwen 27B via vLLM (GPU) or Ollama (local) — OpenAI-compatible API |
| Embeddings | `nomic-embed-text` via Ollama (local, CPU) |
| Vector DB | ChromaDB, persistent on disk |
| Framework | LlamaIndex |
| Frontend | Streamlit |

## Setup

```bash
# 1. Create the environment (or use your existing one)
conda create -n quote-rag python=3.11 -y
conda activate quote-rag

# 2. Install dependencies
make install            # = pip install -r requirements.txt

# 3. Configure
cp .env.example .env    # then edit endpoints / model names

# 4. Add source documents to source/offers/ (PDFs)
#    (10 fictitious sample offers are included)
```

## Usage

```bash
# build the vector index: run notebooks/ 01 → 03 (see notebooks/PIPELINE.md)
make -C app run         # start the app → http://localhost:8501
make -C app test        # run the test suite
```

## Privacy

- Unredacted texts (`data/raw/`), the index (`data/db/`) and `.env` are
  git-ignored — real customer data never enters version control.
- `data/redacted/` and `data/extracted/` contain only fictitious sample data.
- All inference runs locally / on your own LAN.
