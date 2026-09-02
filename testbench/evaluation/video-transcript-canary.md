# Video Transcript Canary — Retrieval Quality

**Corpus:** Course video transcript (7 h 38 min), chunked with video timestamps.
**Pipeline:** hybrid (vector + BM25 + RRF) → LLM rerank (top 10 → keep 3) → refusal gate (threshold 5.0).
**Models:** `qwen3.8:27b-fp8` (LLM / reranker), `nomic-embed-text` (embedder).
**Deck reference:** slide 11 — canary **3/10 → 8/10**.

## What the canary is

A single, deliberately hard retrieval query used as a canary: it is the kind of
question where plain vector search retrieves *plausible-looking but wrong*
chunks. If the pipeline can fix the canary, it has fixed the underlying recall
problem.

- **Canary query:** "What are the main RAG failure modes?"
- **Control query:** "How does hybrid search combine vector and keyword results?"
  (a query that vector search already handles well — it should stay strong.)

The reported number is the **best-candidate rerank score** (0–10) for the canary
query — i.e. how confident the LLM reranker is in the single best retrieved
chunk. It is *not* a "3 of 10 questions" score.

## Result

| Stage | Best-candidate rerank score (canary) |
|---|---|
| Vector only (before) | **3/10** |
| Hybrid + LLM rerank (after) | **8/10** |

### Before — vector only, top 3 (all irrelevant)

| # | Timestamp | Vector score | Why it's wrong |
|---|---|---|---|
| 1 | @02:23:22 | 0.353 | "bad answer … you don't know who created it" — off-topic |
| 2 | @04:37:24 | 0.343 | prompt-injection / delimiter cleaning — different topic |
| 3 | @04:33:41 | 0.338 | config file / API key loading — different topic |

The real failure-modes content lives around **@01:48 / @01:55 / @01:56:45**,
which vector search does not surface.

### After — hybrid (vector + BM25 + RRF) → LLM rerank

- **@01:56:45** (the actual failure-modes chunk) now ranks first and scores
  **8/10** (was 3/10 with vector-only candidates).
- **@00:59:21** (bad-embeddings failure mode) is also recovered.
- BM25 finds the exact-phrase chunks that vector search misses; RRF fuses the
  two lists; the reranker then promotes the correct chunk.

### Control query (stayed strong)

- "How does hybrid search combine vector and keyword results?" — RRF top chunk
  **9/10**, "best of both worlds" chunk **8/10**. No regression from adding
  hybrid + rerank.

## Why this matters

The canary isolates the **recall** failure mode: vector search alone retrieves
semantically-adjacent but wrong chunks for exact-phrase questions. Hybrid search
(BM25) restores recall; the LLM reranker restores precision. The 3/10 → 8/10
jump is the measurable evidence that the full pipeline — not just one component
— is what fixes retrieval on a foreign-domain corpus.

## Reproducibility

The before/after comparison is computed in `02-video-transcript-rag.ipynb`
(sections: retrieval test, LLM-as-reranker, before/after comparison, full
pipeline test). This file is a static summary of those outputs; the notebook is
the source of truth.
