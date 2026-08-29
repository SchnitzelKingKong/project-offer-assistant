"""Central configuration, loaded from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


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

    # Vector store
    index_dir: str = os.getenv("INDEX_DIR", "index_storage")
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "offers")

    # Source documents
    data_dir: str = os.getenv("DATA_DIR", "data")

    # Retrieval
    top_k: int = 3

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
