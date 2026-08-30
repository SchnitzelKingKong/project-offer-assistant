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
