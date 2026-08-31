# 0002 - BM25 keyword index built at runtime from the vector DB

- Status: Accepted
- Date: 2026-08-18

## Context

Hybrid retrieval combines semantic (vector) search with keyword (BM25)
search. A keyword index could be persisted to disk as a second artifact of
the pipeline — or derived from the vector DB at query time.

## Decision

**No keyword index on disk.** At query time the retrieval layer
(`retriever.py`) loads the chunk corpus from the Chroma collection
(`collection.get(include=["documents", "metadatas"])`), tokenizes it, and
builds a fresh `BM25Okapi` index per query. The vector DB is the single
source of truth for the corpus.

## Consequences

- The keyword path can never drift out of sync with the vector path —
  there is exactly one artifact to build, ship, and reload (`INDEX_DIR`).
- Index switching (demo index vs. full index) stays a one-variable change.
- Building the BM25 index per query costs a corpus load + tokenization;
  for the corpus sizes of this project (hundreds to low thousands of
  chunks) this is negligible compared to the LLM call.

## Revisit

If the corpus grows to a size where per-query BM25 construction becomes
measurably slow, persist the keyword index as a second pipeline artifact —
and accept the sync risk, or add a checksum to detect drift.
