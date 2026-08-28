# Project Offer Assistant™

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
streamlit_app.py          thin UI layer (chat, citations, status)
src/rag_system/           RAG logic (testable without the UI)
├── config.py             settings from .env
├── retriever.py          ChromaDB vector retrieval
└── llm.py                answer generation (OpenAI-compatible endpoint)
scripts/build_index.py    one-shot index build (PDF → chunk → embed → Chroma)
tests/                    pytest suite
```

**Build-once, reload-later:** the vector index is built once by
`scripts/build_index.py` and persisted to `index_storage/`. The app only
reloads it — never re-embeds at query time.

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

# 4. Add source documents to data/ (PDFs)
```

## Usage

```bash
make index              # build the vector index from data/ (one-shot)
make run                # start the app → http://localhost:8501
make test               # run the test suite
```

## Privacy

- Source documents (`data/`), the index (`index_storage/`) and `.env` are
  git-ignored — real customer data never enters version control.
- All inference runs locally / on your own LAN.
