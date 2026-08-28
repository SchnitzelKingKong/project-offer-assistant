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
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "quote_history")

    # Source documents
    data_dir: str = os.getenv("DATA_DIR", "data")

    # Retrieval
    top_k: int = 3


settings = Settings()
