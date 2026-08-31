# 0005 - SQLite facts DB as a prepared building block for the SQL path

- Status: Accepted (deferred activation)
- Date: 2026-08-18

## Context

Aggregation questions ("what is the average day rate across all offers?")
are a poor fit for RAG: the LLM would have to read many chunks and do
arithmetic over them. A relational query over structured facts is the
correct tool. The pipeline already extracts structured facts
(angebot_id, datum, preis) during extraction.

## Decision

Notebook 03 writes the extracted facts to a **SQLite database**
(`data/db/sql/offers.db`, table `offers`) in parallel with the Chroma
index. The app does **not** query it yet: aggregation questions are routed
through normal RAG with an explicit limitation note
("a full evaluation across all offers will follow with the SQL path").

## Consequences

- The data model and the write path exist and are tested by the pipeline;
  activating the SQL path is an app-side change, not a rework.
- The limitation is declared in the answer instead of silently
  approximating — the app never presents a RAG-based estimate as a
  complete statistic.
- Two artifacts (Chroma index + SQLite DB) are built from the same
  extraction step, so they cannot disagree about the facts.

## Revisit

Activate the SQL path when aggregation quality becomes a requirement:
route `is_aggregation()` questions to a read-only query over `offers` and
compose the answer from query results instead of retrieved chunks.
