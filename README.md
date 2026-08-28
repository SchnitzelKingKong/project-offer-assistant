# Quote History RAG

A self-hosted RAG application that answers questions over your project quote
history — no cloud APIs, no per-token costs, full data privacy.

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
