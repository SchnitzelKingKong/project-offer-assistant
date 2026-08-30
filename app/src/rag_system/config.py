"""Central configuration, loaded from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo root (this file lives in app/src/rag_system/).
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Load .env from the repo root regardless of the current working directory.
# .env.example acts as the default layer: it is loaded first, then .env
# overrides it (override=True so .env wins over .env.example). Without a
# .env, the .env.example values apply as-is.
load_dotenv(_REPO_ROOT / ".env.example")
load_dotenv(_REPO_ROOT / ".env", override=True)

# Local-development index override (user-approved 2026-08-30): while the
# submission pipeline still ships the fictitious demo index, the app can be
# pointed at the real lecture-project index via INDEX_SOURCE=real in .env.
# Remove this switch (and the constant) before submission.
_REAL_INDEX_DIR = ".references/final-project/02-demonstration/data/db/chroma"


def _resolve(path: str) -> str:
    """Resolve a (possibly relative) path against the repo root.

    This keeps the app working whether it is started from the repo root
    (``streamlit run app/streamlit_app.py``) or from ``app/`` (``make run``).
    """
    if not path:
        return ""
    p = Path(path)
    return str(p if p.is_absolute() else _REPO_ROOT / p)


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the RAG system.

    All values come from environment variables (see .env.example).
    """

    # LLM (OpenAI-compatible endpoint: vLLM or Ollama)
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "ollama")
    llm_model: str = os.getenv("LLM_MODEL", "qwen3.5:0.8b")

    # Embeddings (Ollama, local)
    embed_base_url: str = os.getenv("EMBED_BASE_URL", "http://localhost:11434")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")

    # Vector store. INDEX_SOURCE selects the index: "env" (default) uses
    # INDEX_DIR from the environment files; "real" (local development only)
    # overrides it with the real lecture-project index.
    index_source: str = os.getenv("INDEX_SOURCE", "env").strip().lower()
    index_dir: str = _resolve(
        _REAL_INDEX_DIR if index_source == "real" else os.getenv("INDEX_DIR", "data/db/chroma")
    )
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "offers")

    # Source documents
    data_dir: str = _resolve(os.getenv("DATA_DIR", "data"))

    # Optional directory of redacted full-text offer documents
    # (``<angebot_id>.txt``) for the offer detail panel. Empty → the panel
    # falls back to the indexed chunks.
    offer_text_dir: str = _resolve(os.getenv("OFFER_TEXT_DIR", ""))

    # Retrieval
    top_k: int = int(os.getenv("TOP_K", "3"))

    # Hybrid retrieval (BM25 + vector, fused via RRF) — ported from
    # rag-pipeline.ipynb / transcript-rag.ipynb (see HANDOFF §4.1).
    hybrid_top_n: int = int(os.getenv("HYBRID_TOP_N", "10"))
    rrf_w_vec: float = float(os.getenv("RRF_W_VEC", "0.5"))
    rrf_w_bm25: float = float(os.getenv("RRF_W_BM25", "0.5"))
    rrf_k: int = int(os.getenv("RRF_K", "60"))

    # HyDE (Hypothetical Document Embeddings) — a third RRF list built from an
    # LLM-written hypothetical answer. Bridges the user↔document vocabulary gap
    # (retrieval failure mode #2). Off by default; costs one extra LLM call.
    hyde_enabled: bool = os.getenv("HYDE_ENABLED", "0") == "1"
    rrf_w_hyde: float = float(os.getenv("RRF_W_HYDE", "0.3"))
    # When the HyDE arm is active the two base arms are re-weighted so all
    # three arms sum to 1.0 (0.4/0.3/0.3, see notebooks/05).
    rrf_w_vec_hyde: float = float(os.getenv("RRF_W_VEC_HYDE", "0.4"))
    rrf_w_bm25_hyde: float = float(os.getenv("RRF_W_BM25_HYDE", "0.3"))

    # Breadth routes (notebooks/05): the comparison map-reduce caps the
    # number of offers mapped per question.
    comparison_top_offers: int = int(os.getenv("COMPARISON_TOP_OFFERS", "15"))

    # LLM rerank (top_n → top_k, 0–10 scores) + refusal gate
    rerank_enabled: bool = os.getenv("RERANK_ENABLED", "1") == "1"
    refusal_threshold: float = float(os.getenv("REFUSAL_THRESHOLD", "5.0"))
    # Compound questions ("… und …", two question marks): no single chunk
    # fully answers both parts, so the rerank cut keeps more candidates and
    # the gate uses a lower bar to avoid false refusals.
    compound_keep: int = int(os.getenv("COMPOUND_KEEP", "5"))
    compound_refusal_threshold: float = float(
        os.getenv("COMPOUND_REFUSAL_THRESHOLD", "4.0")
    )

settings = Settings()
