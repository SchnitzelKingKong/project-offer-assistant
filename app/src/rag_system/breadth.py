"""Breadth routes for cross-offer questions (ported from notebooks/05).

Top-k retrieval is capped by construction, so breadth questions need
different strategies:

- **Statistics** (count / mean / outliers): full scan — the LLM reads every
  offer once (map → structured JSON facts), then deterministic code reduces
  (count, mean, range, outliers). No retrieval, no top-k cap, no LLM in the
  reduce → exact numbers, complete coverage.
- **Comparison** (vergleiche / unterschiede): map-reduce over topic
  retrieval (top-20, dedup by offer) → one fact line per offer → comparison
  (the ``tree_summarize`` principle, hand-rolled to keep the hybrid
  BM25+vector+RRF retrieval pipeline).
"""

from __future__ import annotations

import re

from .citation_markup import _format_date
from .config import settings
from .llm import (
    append_source_line,
    comparison_line,
    comparison_reduce,
    draft_reduce,
    extract_draft_blocks,
    extract_offer_facts,
)
from .retriever import Retriever, RetrievedChunk

STATISTICS_RE = re.compile(
    r"\b(wie viele|wieviel|durchschnitt|ausreißer|ausreisser|anteil|prozent|"
    r"median|häufig|hoeufig)\b",
    re.IGNORECASE,
)
COMPARISON_RE = re.compile(
    r"\b(vergleiche|vergleich|unterschiede|unterschied|unterscheiden|"
    r"unterschiedlich|nebeneinander)\b",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
OFFER_WORD_RE = re.compile(r"\b(angebot|angebote)\b", re.IGNORECASE)


def is_statistics(question: str) -> bool:
    """Count/mean/outlier question → needs full coverage, not top-k."""
    return bool(STATISTICS_RE.search(question))


def is_comparison(question: str) -> bool:
    """Cross-offer comparison → map-reduce over topic retrieval."""
    return bool(COMPARISON_RE.search(question))


def is_year_question(question: str) -> bool:
    """Year-list question ("Welche Angebote sind im Jahr 2024?").

    A year plus an offer word → the answer is a complete list from the
    index metadata, not a top-k retrieval. Questions about a single
    aspect of a year ("Wie hoch war der Preis im Jahr 2024?") do NOT
    match — they stay on the aggregation/statistics routes.
    """
    return bool(YEAR_RE.search(question) and OFFER_WORD_RE.search(question))


# New-request scenario + "assemble a draft" → draft route. Top-k RAG
# cannot do this: a draft needs building blocks (line items, rates,
# payment terms, acceptance clauses, delivery formats) from SEVERAL
# offers, so the route retrieves broadly and assembles via map-reduce.
DRAFT_RE = re.compile(
    r"\b(angebotsentwurf|angebotsmuster|angebot\s+(zusammenstellen|erstellen|"
    r"aufsetzen|ausarbeiten|kalkulieren|anfertigen)|"
    r"was\s+w[uü]rde\s+ich\s+(verlangen|berechnen|durchrechnen))\b",
    re.IGNORECASE,
)


def is_draft(question: str) -> bool:
    """New-request scenario + 'assemble a draft' → draft route."""
    return bool(DRAFT_RE.search(question))


# ----------------------------------------------------------------------
# Year list: deterministic metadata scan (no LLM, no retrieval)
# ----------------------------------------------------------------------


def year_route(retriever: Retriever, question: str) -> tuple[str, str, list]:
    """List every offer of a year from the index metadata.

    Deterministic breadth answer: the ``datum`` metadata of every offer
    in the index is scanned, so the list is complete by construction —
    no retrieval, no top-k cap, no LLM.
    """
    year = YEAR_RE.search(question).group(0)
    by_offer = retriever.all_offer_chunks()
    matches: list[tuple[str, str]] = []
    for offer_id, chunks in by_offer.items():
        datum = str((chunks[0].metadata or {}).get("datum") or "")
        if datum.startswith(year):
            matches.append((offer_id, datum))
    matches.sort(key=lambda t: t[1], reverse=True)
    if not matches:
        return (
            "Breadth",
            f"Kein Angebot aus dem Jahr {year} ist im Index vorhanden "
            f"(vollständiger Scan über {len(by_offer)} Angebote).",
            [],
        )
    lines = " · ".join(
        f"{offer_id} ({_format_date(datum) or datum})" for offer_id, datum in matches
    )
    content = (
        f"Im Index sind **{len(matches)} Angebote** aus dem Jahr {year} "
        f"(vollständiger Scan über alle {len(by_offer)} Angebote, kein "
        f"Retrieval): {lines}."
    )
    # No source line: every matching offer is already listed inline.
    return "Breadth", content, []


# ----------------------------------------------------------------------
# Statistics: full scan (map) + deterministic code (reduce)
# ----------------------------------------------------------------------

# In-memory cache for the full-scan facts: the corpus is static while the
# index is, so one scan per app session per index — otherwise every
# statistics question would cost one LLM call per offer again.
_FACTS_CACHE: dict[tuple[str, str], dict[str, dict]] = {}


def full_scan_facts(retriever: Retriever) -> dict[str, dict]:
    """MAP: the LLM reads EVERY offer once → structured facts.

    Complete coverage by construction (no retrieval, no top-k cap).
    Cached per index; offers whose facts could not be extracted are skipped.
    """
    key = (settings.index_dir, settings.chroma_collection)
    if key in _FACTS_CACHE:
        return _FACTS_CACHE[key]
    by_offer = retriever.all_offer_chunks()
    facts: dict[str, dict] = {}
    for offer_id, chunks in sorted(by_offer.items()):
        text = "\n\n".join(c.text for c in chunks)
        meta = chunks[0].metadata
        extracted = extract_offer_facts(text)
        if extracted is None:
            continue
        extracted["preis"] = meta.get("preis")
        extracted["datum"] = meta.get("datum")
        facts[offer_id] = extracted
    _FACTS_CACHE[key] = facts
    return facts


def _format_price(value) -> str:
    """Format a net price in German number format (1.251,03 €)."""
    if value is None:
        return "—"
    return f"{value:,.2f} €".replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")


def reduce_statistics(facts: dict[str, dict]) -> str:
    """REDUCE: deterministic CODE — count / mean / range / outliers.

    No LLM: statistics questions need exact numbers, and an LLM that
    'reads N partial answers' estimates instead of computing.
    """
    total = len(facts)
    lines = [
        f"Über alle **{total} Angebote** im Index gilt "
        "(vollständiger Scan, kein Retrieval):"
    ]

    zz = {
        o: f["zahlungsziel_tage"]
        for o, f in facts.items()
        if (f.get("zahlungsziel_tage") or 0) > 0
    }
    if zz:
        values = list(zz.values())
        mean = sum(values) / len(values)
        lines.append(
            f"- **Zahlungsziel:** {len(zz)} von {total} Angeboten legen ein "
            f"Zahlungsziel fest — durchschnittlich {mean:.0f} Tage "
            f"(Spanne {min(values)}–{max(values)} Tage)."
        )
    else:
        lines.append("- **Zahlungsziel:** kein Angebot legt ein Zahlungsziel fest.")

    prices = {o: f["preis"] for o, f in facts.items() if f.get("preis") is not None}
    if prices:
        values = list(prices.values())
        mean = sum(values) / len(values)
        line = (
            f"- **Nettobetrag:** Durchschnitt **{_format_price(mean)}** "
            f"(n={len(values)}), Spanne {_format_price(min(values))} – "
            f"{_format_price(max(values))}."
        )
        if len(values) >= 3:
            sd = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
            if sd > 0:
                outliers = {o: p for o, p in prices.items() if p > mean + 2 * sd}
                if outliers:
                    line += " Ausreißer (> Mittelwert + 2σ): " + ", ".join(
                        f"{o} ({_format_price(p)})"
                        for o, p in sorted(outliers.items())
                    )
        lines.append(line)

    lines.append(
        "\n*Basis: vollständiger Scan aller Angebote "
        "(kein Retrieval, keine Top-k-Grenze).*"
    )
    return "\n".join(lines)


def statistics_route(
    retriever: Retriever, question: str
) -> tuple[str, str, list[RetrievedChunk]]:
    """Statistics question → full scan (map) + code reduce. No retrieval."""
    facts = full_scan_facts(retriever)
    if not facts:
        return (
            "Statistics",
            "Keine Fakten konnten aus den Angeboten extrahiert werden.",
            [],
        )
    return ("Statistics", reduce_statistics(facts), [])


# ----------------------------------------------------------------------
# Comparison: map-reduce over topic retrieval
# ----------------------------------------------------------------------


def comparison_route(
    retriever: Retriever,
    question: str,
    hyde_passage: str | None = None,
) -> tuple[str, str, list[RetrievedChunk]]:
    """MAP-REDUCE (tree_summarize principle) over topic retrieval.

    Retrieve on the topic (top-20, dedup by offer) → MAP: one fact line per
    offer → REDUCE: the comparison. Hand-rolled instead of a framework
    summarizer so the hybrid BM25+vector+RRF retrieval pipeline is kept.
    """
    chunks = retriever.hybrid_search(
        question, top_n=20, hyde_passage=hyde_passage
    )
    by_offer: dict[str, list[RetrievedChunk]] = {}
    for chunk in chunks:
        by_offer.setdefault(chunk.source, []).append(chunk)
    offers = list(by_offer.items())[: settings.comparison_top_offers]
    if not offers:
        return ("Comparison", "Keine passenden Angebote gefunden.", [])

    lines: list[str] = []
    for offer_id, offer_chunks in offers:
        text = "\n\n".join(c.text for c in offer_chunks)[:2500]
        line = comparison_line(question, offer_id, text)
        if line:
            lines.append(line)
    if not lines:
        return ("Comparison", "Keine Vergleichsdaten extrahiert.", [])

    text = comparison_reduce(question, lines)
    ranked = [offer_chunks[0] for _, offer_chunks in offers]
    return ("Comparison", append_source_line(text, ranked), ranked)


# ----------------------------------------------------------------------
# Draft: map-reduce assembly of a NEW offer from historical offers
# ----------------------------------------------------------------------


def draft_route(
    retriever: Retriever,
    question: str,
    hyde_passage: str | None = None,
) -> tuple[str, str, list[RetrievedChunk]]:
    """MAP-REDUCE draft assembly over broad topic retrieval.

    The user describes a NEW incoming request (scenario) and asks for a
    draft offer. Top-k RAG cannot assemble a draft — it needs building
    blocks (line items, rates, payment terms, acceptance clauses,
    delivery formats) from SEVERAL offers. Strategy:

    1. Retrieve broadly (top-25, dedup by offer, capped by
       ``comparison_top_offers``).
    2. MAP: the LLM extracts structured building blocks per offer.
    3. REDUCE: the LLM assembles the draft — line items, payment terms,
       acceptance, formats, and a reference price derived transparently
       from the historical rates.
    """
    chunks = retriever.hybrid_search(
        question, top_n=25, hyde_passage=hyde_passage
    )
    by_offer: dict[str, list[RetrievedChunk]] = {}
    for chunk in chunks:
        by_offer.setdefault(chunk.source, []).append(chunk)
    offers = list(by_offer.items())[: settings.comparison_top_offers]
    if not offers:
        return ("Draft", "Keine passenden Angebote für den Entwurf gefunden.", [])

    blocks: list[dict] = []
    for offer_id, offer_chunks in offers:
        text = "\n\n".join(c.text for c in offer_chunks)[:12000]
        block = extract_draft_blocks(text)
        if block is None:
            continue
        block["angebot_id"] = offer_id
        block["datum"] = next(
            (c.metadata.get("datum") for c in offer_chunks
             if c.metadata.get("datum")),
            None,
        )
        blocks.append(block)
    if not blocks:
        return ("Draft", "Keine Bausteine konnten extrahiert werden.", [])

    text = draft_reduce(question, blocks)
    ranked = [offer_chunks[0] for _, offer_chunks in offers]
    return ("Draft", append_source_line(text, ranked), ranked)
