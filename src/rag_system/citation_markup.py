"""Render answer markdown as HTML with clickable citation chips.

The LLM cites offers as ``[AG####]`` inside its answer. This module converts
the answer markdown to HTML and wraps every bracketed offer id in an
``<a class="cite-chip">`` element so the frontend can make it clickable.
Plain (unbracketed) ids are left untouched.
"""

from __future__ import annotations

import re

import markdown as _markdown

_BRACKETED_OFFER_RE = re.compile(r"\[(AG\d{4})\]")


def render_answer_html(content: str) -> str:
    """Convert answer markdown to HTML with clickable ``[AG####]`` chips.

    - Markdown is rendered with the ``markdown`` package (bold, lists, …).
    - Every ``[AG####]`` becomes
      ``<a class="cite-chip" data-offer="AG####" href="#">AG####</a>``.
    - Anything else (plain ``AG####`` without brackets, ``AG12345``, …)
      is left as-is.
    """
    html = _markdown.markdown(content, extensions=["sane_lists"])
    return _BRACKETED_OFFER_RE.sub(
        r'<a class="cite-chip" data-offer="\1" href="#">\1</a>', html
    )
