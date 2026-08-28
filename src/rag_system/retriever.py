"""Vector retrieval over the persistent ChromaDB index.

The index is built once (see scripts/build_index.py) and reloaded here —
never re-embedded at query time.
"""

from __future__ import annotations

from dataclasses import dataclass

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
        self._collection = None  # TODO: lazy-load ChromaDB collection

    @property
    def is_available(self) -> bool:
        """True if the index exists on disk and can be loaded."""
        # TODO: check settings.index_dir for a persisted collection
        return False

    def query(self, question: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return the top-k most similar chunks for the question.

        TODO: embed the question (nomic-embed-text via Ollama) and run a
        similarity search over the collection.
        """
        raise NotImplementedError("Retrieval not implemented yet")
