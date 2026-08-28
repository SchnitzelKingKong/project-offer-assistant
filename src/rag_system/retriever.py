"""Vector retrieval over the persistent ChromaDB index.

The index is built once (see scripts/build_index.py) and reloaded here —
never re-embedded at query time.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
import ollama

from .config import settings


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the vector index, with provenance metadata."""

    text: str
    source: str  # document name / offer id
    score: float


class Retriever:
    """Loads the persistent ChromaDB collection and answers similarity queries."""

    def __init__(self) -> None:
        self._collection = None
        if self.is_available:
            client = chromadb.PersistentClient(path=settings.index_dir)
            self._collection = client.get_collection(settings.chroma_collection)

    @property
    def is_available(self) -> bool:
        """True if the index exists on disk and can be loaded."""
        return (Path(settings.index_dir) / "chroma.sqlite3").exists()

    def query(self, question: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return the top-k most similar chunks for the question."""
        if self._collection is None:
            raise RuntimeError("Index not available — run `make index` first")
        top_k = top_k or settings.top_k

        # Embed the question with the same model the index was built with
        embedding = ollama.Client(host=settings.embed_base_url).embed(
            model=settings.embed_model, input=question
        )
        result = self._collection.query(
            query_embeddings=[embedding.embeddings[0]],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[RetrievedChunk] = []
        for doc, meta, dist in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            meta = meta or {}
            source = meta.get("angebot_id") or meta.get("source") or "unknown"
            # Chroma L2 distance → similarity in [0, 1] for display
            score = max(0.0, 1.0 - dist / 2.0)
            chunks.append(RetrievedChunk(text=doc, source=str(source), score=score))
        return chunks
