"""Vector retrieval over the persistent ChromaDB index.

The index is built once (see scripts/build_index.py) and reloaded here —
never re-embedded at query time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import chromadb
import ollama

from .config import settings


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the vector index, with provenance metadata."""

    text: str
    source: str  # offer id (AG####) or document name
    score: float
    metadata: dict = field(default_factory=dict)


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

    @property
    def offer_count(self) -> int:
        """Number of distinct offers (angebot_id) in the index."""
        if self._collection is None:
            return 0
        result = self._collection.get(include=["metadatas"])
        return len(
            {
                m.get("angebot_id")
                for m in result["metadatas"]
                if m and m.get("angebot_id")
            }
        )

    def query(
        self,
        question: str,
        top_k: int | None = None,
        angebot_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Return the top-k most similar chunks for the question.

        If ``angebot_id`` is given, retrieval is metadata-filtered to that
        offer only (ID-aware retrieval — fixes recall for explicit
        "AG####" references). An empty result means the offer is not in
        the index; callers must not fall back to unfiltered retrieval.
        """
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
            where={"angebot_id": angebot_id} if angebot_id else None,
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
            chunks.append(
                RetrievedChunk(text=doc, source=str(source), score=score, metadata=meta)
            )
        return chunks

    def candidates_for(self, question: str, top_k: int | None = None) -> list[dict]:
        """Deduplicated offer candidates for clarification.

        Returns one entry per distinct offer in the top-k results:
        ``{"angebot_id", "datum", "preis"}`` — the facts the UI needs to
        render tappable clarification chips.
        """
        chunks = self.query(question, top_k=top_k)
        seen: set[str] = set()
        candidates: list[dict] = []
        for chunk in chunks:
            if chunk.source in seen:
                continue
            seen.add(chunk.source)
            candidates.append(
                {
                    "angebot_id": chunk.source,
                    "datum": chunk.metadata.get("datum") or "—",
                    "preis": chunk.metadata.get("preis"),
                }
            )
        return candidates
