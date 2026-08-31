# 0006 - Vision-based PDF normalization after failed text-layer extraction

- Status: Accepted
- Date: 2026-08-18

## Context

The pipeline must turn heterogeneous offer PDFs (1–5 pages, no uniform
structure) into normalized, structured text. We evaluated the extraction
routes empirically, including a manual test with deliberately difficult
layouts to find out where a robust architecture has to start:

1. **PyMuPDF / pdfplumber, default settings** — chaotic text extraction:
   reading order broken, table cells interleaved, headers and footers
   mixed into body text.
2. **pdfplumber `layout=True`** — preserved the visual layout, but at the
   cost of large amounts of whitespace and still-unstructured output.
3. **LLM cleanup of the raw layout text** — fed the messy text-layer
   output to an LLM for restructuring; produced plausible-looking but
   factually wrong content (hallucinated or dropped values).

All three routes failed the fidelity requirement: the text that gets
indexed must be a faithful transcription of the document, because the
whole value proposition is *citing what the offer actually said*.

## Decision

**Extract via a vision model, verify deterministically.** Page images
(@150 DPI) go directly to the vision model (`qwen3.8:27b`, thinking OFF,
temperature 0), which transcribes the document and structures the layout
(label/value lines, table rows, address blocks, page markers) without
changing the content. The pdfplumber flat text (`layout=False`) is kept
only as a deterministic reference for a **fidelity check**: a word-multiset
diff plus page-marker completeness, with a bounded repair loop (max. 2
attempts, exact violation tokens fed back). Offers with remaining
violations abort the run (STRICT mode) — nothing unverified is indexed.

## Consequences

- Extraction quality no longer depends on the PDF text layer at all —
  scanned or image-heavy documents work the same way.
- The fidelity check makes the LLM step auditable: every indexed text is
  verified against a deterministic reference, and failures are loud, not
  silent.
- Cost: one vision call per page (plus repair attempts) at index time —
  acceptable because indexing is a one-time, offline pipeline step.
- The pdfplumber reference doubles as the source for deterministic facts
  (e.g. the offer date), which never pass through the model.

## Revisit

The model choice is a convenience decision, not an optimization:
`qwen3.8:27b` was the strong vision model available on our own
infrastructure at the time. Self-hosting was a hard requirement, not a
preference — the extraction tests ran on real customer offers, so page
images could not be sent to a third-party API. The pipeline is
model-agnostic (any OpenAI-compatible vision endpoint via
`LLM_BASE_URL`), so swapping in a dedicated document-OCR model or a
smaller/faster model is a configuration change, not a re-architecture —
worth revisiting if extraction cost or fidelity-repair rates become a
problem (while staying on self-hosted infrastructure).

The manual layout test that started this decision also defined the
acceptance bar for future document types. The next candidate is the
**pitch deck**: in agency work, offers are frequently accompanied by a
pitch deck that restates the idea — a document type that belongs in the
offer database and must be extractable with the same fidelity guarantees.
If pitch decks (or other visual-heavy formats) break the current
transcription prompt, the fix belongs in the normalization stage, not in
retrieval.
