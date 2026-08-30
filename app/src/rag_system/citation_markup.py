"""Render answer markdown as HTML with clickable citation chips.

The LLM cites offers as ``[AG####]`` (or plain ``AG####`` in a trailing
source list) inside its answer. This module converts the answer markdown
to HTML and wraps every offer id in an ``<a class="cite-chip">`` element
so the frontend can make it clickable.
"""

from __future__ import annotations

import re

import markdown as _markdown

# Bracketed ids first (``[AG0091]``), then plain ids (``AG0091``) that are
# not part of a longer word/number. Single pass, so replacements are not
# re-scanned. ``AG12345`` and ``XAG0085Y`` do not match.
_OFFER_ID_RE = re.compile(r"\[(AG\d{4})\]|(?<![A-Za-z0-9])(AG\d{4})(?!\d)")

# The model sometimes emits a "source list" with literal asterisks instead
# of a proper markdown list — either one-line (``* AG0091 … * AG0078 …``)
# or line-start markers (``*   AG0091``) glued to the preceding paragraph
# (no blank line, so markdown keeps them as literal text). After markdown
# rendering those are plain ``*`` characters — swap them for middle dots.
# Applied to HTML so ``**bold**`` markers are already consumed and never
# touched. Matches a ``*`` at a line/word start followed by whitespace.
_ASTERISK_SEPARATOR_RE = re.compile(r"(?<!\S)\*(?=\s)")


def render_answer_html(content: str) -> str:
    """Convert answer markdown to HTML with clickable offer-id chips.

    - Markdown is rendered with the ``markdown`` package (bold, lists, …).
    - Every ``[AG####]`` and every plain ``AG####`` becomes
      ``<a class="cite-chip" data-offer="AG####" href="#">AG####</a>``.
    - ``AG12345``, ``XAG0085Y`` and other non-offer tokens are left as-is.
    - One-line source lists (``* AG0091 … * AG0078 …``) get their asterisk
      separators rendered as middle dots.
    """
    html = _markdown.markdown(content, extensions=["sane_lists"])
    html = _ASTERISK_SEPARATOR_RE.sub(" · ", html)
    return _OFFER_ID_RE.sub(_chip_replacement, html)


def _chip_replacement(match: re.Match) -> str:
    """Build the chip anchor from whichever alternative matched."""
    offer_id = match.group(1) or match.group(2)
    return f'<a class="cite-chip" data-offer="{offer_id}" href="#">{offer_id}</a>'


# --- Page-level citations: AG#### → AG####, Seite X --------------------------
# The model quotes the decisive passage verbatim (in „…"); the page is then
# resolved DETERMINISTICALLY from the "[Seite X von Y]" markers inside the
# chunk text. A quote that cannot be located verbatim never gets a page
# (ported from notebooks/05).
#
# Only citations that DIRECTLY follow a verbatim quote (short gap) are
# upgraded — the trailing source list ("Quellen: AG0085, AG0086") stays a
# plain, comma-separated overview.

PAGE_RE = re.compile(r"\[Seite (\d+) von \d+\]")
# German quotes („…") — the model occasionally closes with a straight
# double quote instead of ", so accept both closing variants.
QUOTE_RE = re.compile(r"[\u201e\"](.+?)[\u201c\"]", flags=re.DOTALL)
# Bracketed ids (legacy model output) or plain ids; never one that already
# carries a page ("AG0085, Seite 4").
CITE_RE = re.compile(
    r"(\[(AG\d{4})(?:\s*\|[^\]]*)?\]|(?<![A-Za-z0-9\[])(AG\d{4})(?!\d))"
    r"(?!\s*,\s*(?:S\.|Seite)\s*\d)"
)
# The gap between the closing quote and the citation must contain no letters
# for the page upgrade to apply — "„…" AG0001" qualifies, but a source list
# ("„…“ AG0001 … Quellen: AG0001") does not.
_CITE_GAP_RE = re.compile(r"[A-Za-z]")


def _norm(s: str) -> str:
    """Normalize whitespace + quote variants for robust quote matching."""
    s = re.sub(r"\s+", " ", s)
    for a, b in [
        ("\u201e", '"'), ("\u201c", '"'), ("\u201d", '"'),
        ("\u201a", "'"), ("\u2018", "'"), ("\u2019", "'"),
        ("\u2026", "..."),
    ]:
        s = s.replace(a, b)
    return s.strip()


def page_of_quote(chunk_text: str, quote: str) -> int | None:
    """Find the verbatim quote in the chunk text and return the number of the
    LAST ``[Seite X von Y]`` marker before it.

    Returns ``None`` when the quote cannot be located — a page is never
    guessed.
    """
    nq, nt = _norm(quote), _norm(chunk_text)
    pos = nt.find(nq)
    if pos < 0:
        return None
    pages = [int(m.group(1)) for m in PAGE_RE.finditer(nt) if m.start() < pos]
    return pages[-1] if pages else 1


def _format_date(value) -> str | None:
    """ISO date (``2026-05-01``) → German format (``01.05.2026``)."""
    if not value:
        return None
    parts = str(value).split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        y, m, d = parts
        return f"{d}.{m}.{y}"
    return str(value)


# Sentence end: period/exclamation/question mark, optionally followed by a
# closing quote, then whitespace.
_SENTENCE_END_RE = re.compile(r"[.!?][\u201c\"]?\s+")


def _dedupe_sentence_start_citations(content: str) -> str:
    """Drop a citation that starts a sentence when the same offer was
    already cited in the previous sentence.

    The model sometimes emits the id both at the end of one sentence and
    again at the start of the next ("…möglich sind. AG0085 Wörtlich heißt
    es: „…" AG0085") — the sentence-start one is redundant. Only citations
    DIRECTLY after a sentence end (no letters in between) are removed, so
    "Quellen: AG0085, AG0086" and in-sentence citations are untouched.
    A citation that directly follows a verbatim quote is the real one and
    is never removed.
    """
    matches = list(CITE_RE.finditer(content))
    if len(matches) < 2:
        return content
    quote_ends = [m.end() for m in QUOTE_RE.finditer(content)]
    seen: set[str] = set()
    removals: list[tuple[int, int]] = []
    for m in matches:
        offer_id = m.group(2) or m.group(3)
        # Never remove the citation that directly follows a quote.
        if any(not _CITE_GAP_RE.search(content[p : m.start()])
               for p in quote_ends if p < m.start()):
            seen.add(offer_id)
            continue
        gap = content[: m.start()]
        ends_sentence = False
        for sm in _SENTENCE_END_RE.finditer(gap):
            if not _CITE_GAP_RE.search(gap[sm.end():]):
                ends_sentence = True
        if ends_sentence and offer_id in seen:
            # Also swallow the trailing space so no double space remains.
            end = m.end()
            while end < len(content) and content[end] == " ":
                end += 1
            removals.append((m.start(), end))
        seen.add(offer_id)
    for start, end in reversed(removals):
        content = content[:start] + content[end:]
    return content


def upgrade_citations(content: str, chunks: list) -> str:
    """Append page and date to citations that directly follow a verbatim
    quote: ``AG0085`` → ``AG0085, Seite 4 vom 01.05.2026`` (and
    ``[AG0085]`` → same).

    For each citation the nearest preceding verbatim quote (``„…"``) is
    located in that offer's chunk texts; the page comes from the page
    markers inside the chunk, the date from the chunk metadata
    (``datum``). Deterministic — no LLM. Citations that cannot be
    resolved, or that are not directly after a quote (e.g. the trailing
    source list), are left as plain ``AG####``. A redundant
    sentence-start citation of an already-cited offer is dropped.

    ``chunks`` is the list of ``RetrievedChunk`` objects the answer was
    grounded on (``.source`` = offer id, ``.text`` = chunk text,
    ``.metadata`` = offer metadata incl. ``datum``).
    """
    content = _dedupe_sentence_start_citations(content)
    quotes = [(m.end(), m.group(1).strip()) for m in QUOTE_RE.finditer(content)]
    if not quotes:
        return content
    texts: dict[str, list[str]] = {}
    dates: dict[str, str | None] = {}
    for chunk in chunks:
        texts.setdefault(chunk.source, []).append(chunk.text)
        dates.setdefault(chunk.source, _format_date(chunk.metadata.get("datum")))
    pairs: list[tuple[re.Match, str]] = []
    for m in CITE_RE.finditer(content):
        offer_id = m.group(2) or m.group(3)
        # Only upgrade when a verbatim quote ENDS directly before the
        # citation (gap without letters) — that is the
        # "Wörtlich heißt es in AG0085: „…“ AG0085" pattern.
        preceding = [
            q for p, q in quotes
            if p < m.start() and not _CITE_GAP_RE.search(content[p : m.start()])
        ]
        if not preceding:
            continue
        quote = preceding[-1]
        page = None
        for text in texts.get(offer_id, []):
            page = page_of_quote(text, quote)
            if page:
                break
        if page:
            repl = f"{offer_id}, Seite {page}"
            date = dates.get(offer_id)
            if date:
                repl += f" vom {date}"
            pairs.append((m, repl))
    # Replace from the end so earlier positions stay valid.
    for m, repl in reversed(pairs):
        content = content[: m.start()] + repl + content[m.end():]
    return content
