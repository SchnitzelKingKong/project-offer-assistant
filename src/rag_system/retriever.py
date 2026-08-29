"""Vector retrieval over the persistent ChromaDB index.

The index is built once (see scripts/build_index.py) and reloaded here —
never re-embedded at query time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import chromadb
import nltk
import ollama
from rank_bm25 import BM25Okapi

from .config import settings
from .query_expansion import expand_query

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:  # one-time download, needed for BM25 tokenization
    nltk.download("punkt", quiet=True)


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the vector index, with provenance metadata."""

    text: str
    source: str  # offer id (AG####) or document name
    score: float
    metadata: dict = field(default_factory=dict)
    rerank_score: float | None = None  # 0–10, set by llm.rerank


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

    # ------------------------------------------------------------------
    # Hybrid retrieval: BM25 (keyword) + vector (semantic), fused via
    # Reciprocal Rank Fusion — ported from rag-pipeline.ipynb /
    # transcript-rag.ipynb (see HANDOFF §4.1).
    # ------------------------------------------------------------------

    def _bm25_corpus(self, angebot_id: str | None = None) -> list[RetrievedChunk]:
        """All chunks (optionally filtered by offer id) as BM25 candidates.

        Loaded from Chroma so the corpus always matches the index on disk —
        no kernel state to drift out of sync.
        """
        if self._collection is None:
            return []
        result = self._collection.get(include=["documents", "metadatas"])
        chunks = []
        for node_id, text, metadata in zip(
            result["ids"], result["documents"], result["metadatas"]
        ):
            if angebot_id and (metadata or {}).get("angebot_id") != angebot_id:
                continue
            chunks.append(
                RetrievedChunk(
                    text=text or "",
                    source=(metadata or {}).get("angebot_id", node_id),
                    score=0.0,
                    metadata=metadata or {},
                )
            )
        return chunks

    def bm25_search(
        self, question: str, top_n: int | None = None, angebot_id: str | None = None
    ) -> list[RetrievedChunk]:
        """Keyword search over the (optionally filtered) chunk corpus."""
        top_n = top_n or settings.hybrid_top_n
        corpus = self._bm25_corpus(angebot_id)
        if not corpus:
            return []
        tokenized = [nltk.word_tokenize(c.text.lower()) for c in corpus]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(nltk.word_tokenize(question.lower()))
        top_indices = scores.argsort()[::-1][:top_n]
        return [corpus[i] for i in top_indices if scores[i] > 0]

    @staticmethod
    def rrf_fuse(
        vec_results: list[RetrievedChunk],
        bm25_results: list[RetrievedChunk],
        w_vec: float | None = None,
        w_bm25: float | None = None,
        k: int | None = None,
        top_n: int | None = None,
        hyde_results: list[RetrievedChunk] | None = None,
        w_hyde: float | None = None,
    ) -> list[RetrievedChunk]:
        """Reciprocal Rank Fusion of two (or three, with HyDE) ranked lists.

        Rank-based, not score-based: a chunk ranked high in several lists
        beats a chunk that tops only one.
        """
        w_vec = settings.rrf_w_vec if w_vec is None else w_vec
        w_bm25 = settings.rrf_w_bm25 if w_bm25 is None else w_bm25
        w_hyde = settings.rrf_w_hyde if w_hyde is None else w_hyde
        k = settings.rrf_k if k is None else k
        top_n = top_n or settings.hybrid_top_n

        fused: dict[str, RetrievedChunk] = {}

        def _add(results: list[RetrievedChunk], weight: float) -> None:
            for rank, chunk in enumerate(results):
                key = chunk.source + "\x00" + chunk.text
                entry = fused.setdefault(key, chunk)
                entry.metadata["rrf_score"] = entry.metadata.get("rrf_score", 0.0) + (
                    weight / (k + rank + 1)
                )

        _add(vec_results, w_vec)
        _add(bm25_results, w_bm25)
        if hyde_results:
            _add(hyde_results, w_hyde)
        ranked = sorted(fused.values(), key=lambda c: c.metadata["rrf_score"], reverse=True)
        for chunk in ranked:
            chunk.score = chunk.metadata["rrf_score"]
        return ranked[:top_n]

    def hybrid_search(
        self,
        question: str,
        top_n: int | None = None,
        angebot_id: str | None = None,
        hyde_passage: str | None = None,
    ) -> list[RetrievedChunk]:
        """Vector + BM25 (+ optional HyDE) retrieval fused via RRF.

        The offer-id filter applies to BOTH the vector query and the BM25
        corpus, so ID-scoped questions stay scoped.

        The question is acronym-expanded (query side only) before retrieval:
        both the vector and the BM25 path see the expanded form, while the
        original question stays untouched for rerank, gate, and generation.

        ``hyde_passage`` (HyDE) is embedded and vector-searched as a third
        RRF list — it bridges the user↔document vocabulary gap.
        """
        top_n = top_n or settings.hybrid_top_n
        expanded = expand_query(question)
        vec_results = self.query(expanded, top_k=top_n, angebot_id=angebot_id)
        bm25_results = self.bm25_search(expanded, top_n=top_n, angebot_id=angebot_id)
        hyde_results: list[RetrievedChunk] | None = None
        if hyde_passage:
            hyde_results = self.query(hyde_passage, top_k=top_n, angebot_id=angebot_id)
        return self.rrf_fuse(
            vec_results, bm25_results, top_n=top_n, hyde_results=hyde_results
        )

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
