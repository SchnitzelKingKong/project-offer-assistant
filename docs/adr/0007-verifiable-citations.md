# 0007 - Every claim is verifiable: citations resolved deterministically, source always available

- Status: Accepted
- Date: 2026-08-31

## Context

A RAG answer is only as trustworthy as its grounding. Two failure modes
matter:

1. **The model invents references** — a page number or offer id that does
   not exist in the retrieved chunks (confabulated citations).
2. **The user cannot check** — the answer states something, but the source
   is not surfaced, so the claim cannot be verified.

Both must be ruled out by construction, not by prompting.

## Decision

**Citations are a contract, not a model output.** Every answer ships with
its retrieved chunks, and the UI makes the source available at two levels:

- **Inline:** every `[AG####]` reference in the answer text is rendered as
  a clickable link (custom Streamlit component). Clicking it opens the
  **offer panel** — the full redacted text of that offer (or its indexed
  chunks) with id, date, and price — so any claim can be checked against
  the source document.
- **Source line:** each answer ends with a deterministic source line
  (`„…" — 01.05.2026 · AG0085 (S. 4)`) appended by the app, not generated
  by the model. The chat additionally shows a "Sources" expander listing
  every chunk behind the last answer with its score and text excerpt.

**Page numbers are resolved deterministically, never by the LLM.** The
pipeline embeds `[Seite X von Y]` markers into every chunk at ingest time.
At query time the app locates the verbatim quote inside the chunk text and
takes the last page marker before it. If the quote cannot be located
verbatim, no page is shown (`[AG1001]` instead of `[AG1001 | S. 3]`) —
the app never guesses a page.

**No answer without grounding.** The refusal gate refuses when the best
rerank score is below threshold, so a low-confidence answer (and its
citations) is not shown at all.

## Consequences

- A user can verify every claim in three clicks: read the claim → click
  the offer id → read the source text. Trust is checkable, not assumed.
- Citation markup is plain, inspectable Python (`citation_markup.py`) —
  unit-tested without the UI, no framework involved (see ADR 0001).
- The page markers make chunking slightly less "clean" (marker text inside
  chunks); this is an accepted cost for deterministic page resolution.
- The offer panel reads redacted full texts only when `OFFER_TEXT_DIR` is
  configured (opt-in); otherwise it falls back to the indexed chunks, so
  the guarantee holds in both modes.

## Revisit

If offers grow multi-page PDFs with non-linear structure (appendices,
repeated headers), the "last marker before the quote" rule may need a
page-map per offer instead of inline markers.
