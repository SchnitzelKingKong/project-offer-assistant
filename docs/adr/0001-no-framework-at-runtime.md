# 0001 - No framework at runtime — hand-rolled RAG

- Status: Accepted
- Date: 2026-08-18

## Context

The index pipeline (notebooks 01–03) uses LlamaIndex for chunking, the
document model, and the Chroma adapter. The question was whether the app
should also be built on a RAG framework (LlamaIndex, LangChain, …) instead
of plain Python.

## Decision

The app is a small, **stateless RAG system written from scratch** —
retrieval (ChromaDB + BM25 with RRF fusion), question routing, and answer
generation are plain Python with direct `chromadb` / `ollama` /
OpenAI-compatible API calls. LlamaIndex is used only to *build* the index,
never at query time. There are zero framework imports in
`app/src/rag_system/`.

## Consequences

- Small runtime dependency footprint, no framework lock-in.
- Every stage (router, fusion, refusal gate, citation markup) is directly
  inspectable and unit-testable — the 92-test suite covers the RAG logic
  without the UI, all LLM calls mocked.
- We maintain retrieval logic ourselves instead of relying on framework
  updates; the codebase stays small enough to read end to end.

## Revisit

A deliberate choice that can be revisited later — see the outlook in
[`../OVERVIEW.md`](../OVERVIEW.md).
