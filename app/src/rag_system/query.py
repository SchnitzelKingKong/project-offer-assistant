"""Query orchestration: deterministic pre-checks, then retrieval + LLM.

Implements the response contract from the handoff (§3.3):

- ``AG####`` reference in the question  → metadata-filtered retrieval.
  If the filter returns nothing → "not found", no unfiltered fallback.
- Statistics words ("wie viele", "durchschnitt", "ausreißer", …)
  → full scan: LLM reads every offer (map → JSON facts), deterministic
  code reduces (count / mean / range / outliers). No retrieval, no top-k cap.
- Comparison words ("vergleiche", "unterschiede", …)
  → map-reduce over topic retrieval (one fact line per offer → comparison).
- Price/date/term question without any offer reference or year
  → clarification with candidate chips (no LLM call).
- Aggregation words ("welche", "alle", "mehr als X €", "im Jahr Y")
  → explicit limitation until the SQL path exists.
- Everything else → grounded RAG answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .breadth import (
    comparison_route,
    is_comparison,
    is_statistics,
    is_year_question,
    statistics_route,
    year_route,
)
from .config import settings
from .llm import generate_answer, hyde_passage, rerank
from .retriever import Retriever, RetrievedChunk

AG_RE = re.compile(r"\bAG\d{4}\b")

# Price/date/term questions that carry no offer reference and no year
# are ambiguous — they must be clarified, not answered.
AMBIGUOUS_TOPIC_RE = re.compile(
    r"\b(preis|netto|brutto|nettobetrag|gesamtpreis|summe|zahlung|"
    r"zahlungsbedingung|skonto|f&auml;llig|faellig|datum|termin|"
    r"honorar|kosten|preisbasis)\b",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

# Price questions that can be answered deterministically from metadata
# once the offer is known — no LLM needed.
PRICE_TOPIC_RE = re.compile(
    r"\b(preis|netto|brutto|nettobetrag|bruttopreis|gesamtpreis|summe|"
    r"honorar|kosten)\b",
    re.IGNORECASE,
)

# Aggregation signals — structurally impossible with top-k vector search.
AGGREGATION_RE = re.compile(
    r"\b(welche|alle|wie viele|mehr als|mindestens|&gt;|gr[oö]ßer als|"
    r"groesser als|teurer als|g[uü]nstiger als|im jahr|in dem jahr)\b",
    re.IGNORECASE,
)


@dataclass
class QueryResult:
    """The response contract the frontend renders against.

    ``route`` is the badge shown per answer: RAG / Clarify / Refusal.
    """

    type: str  # "answer" | "clarify" | "refusal"
    route: str  # "RAG" | "Clarify" | "Refusal"
    content: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)


def extract_offer_id(question: str) -> str | None:
    """First AG#### reference in the question, if any."""
    match = AG_RE.search(question)
    return match.group(0) if match else None


def is_ambiguous(question: str) -> bool:
    """Price/date/term question without offer reference or year."""
    return bool(AMBIGUOUS_TOPIC_RE.search(question)) and not YEAR_RE.search(question)


def is_aggregation(question: str) -> bool:
    """Aggregation question — needs the SQL path (not available yet)."""
    return bool(AGGREGATION_RE.search(question))


def is_compound(question: str) -> bool:
    """Question with several parts ("… und …", two question marks).

    No single chunk fully answers a compound question, so the rerank cut
    and the refusal gate need to be more lenient (see _rerank_and_gate).
    """
    if question.count("?") >= 2:
        return True
    return bool(re.search(r"\bund\b", question, flags=re.IGNORECASE))


def format_price(value) -> str:
    """Format a net price in German number format (1.251,03 €)."""
    if value is None:
        return ""
    return f"{value:,.2f} €".replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")


def is_price_question(question: str) -> bool:
    """Question asking about the price of an offer."""
    return bool(PRICE_TOPIC_RE.search(question))


def price_answer(offer_id: str, chunks: list[RetrievedChunk]) -> str | None:
    """Deterministic price answer from chunk metadata, if the price is known.

    Returns None when no retrieved chunk carries a price, so the caller
    can fall back to the LLM.
    """
    for chunk in chunks:
        price = chunk.metadata.get("preis")
        if price is not None:
            datum = chunk.metadata.get("datum") or ""
            date_part = f" (Datum: {datum})" if datum else ""
            return (
                f"Der Nettobetrag von Angebot **{offer_id}** beträgt "
                f"**{format_price(price)}**{date_part}."
            )
    return None


def _rerank_and_gate(
    question: str,
    chunks: list[RetrievedChunk],
    compound: bool = False,
) -> tuple[list[RetrievedChunk], str | None]:
    """Rerank candidates and apply the refusal gate.

    Returns (top_chunks, refusal_message). ``refusal_message`` is set when
    the best rerank score is below the threshold — the model is then not
    allowed to answer (handoff §4.1).

    For compound questions the cut keeps ``compound_keep`` candidates and
    the gate uses the lower ``compound_refusal_threshold``: no single chunk
    fully answers a two-part question, so the top score is structurally
    lower and a strict gate would refuse valid answers.
    """
    if not settings.rerank_enabled:
        keep = settings.compound_keep if compound else settings.top_k
        return chunks[:keep], None
    keep = settings.compound_keep if compound else settings.top_k
    threshold = (
        settings.compound_refusal_threshold if compound else settings.refusal_threshold
    )
    ranked = rerank(question, chunks, keep=keep)
    if ranked and (ranked[0].rerank_score or 0.0) < threshold:
        return ranked, (
            "Ich konnte keine zuverlässige Antwort in den vorliegenden "
            f"Angeboten finden (beste Übereinstimmung: "
            f"{ranked[0].rerank_score:.0f}/10)."
        )
    return ranked, None


def _hyde_for(question: str) -> str | None:
    """HyDE passage for retrieval, or None when disabled/failed."""
    if not settings.hyde_enabled:
        return None
    passage = hyde_passage(question)
    return passage or None


def run_query(retriever: Retriever, question: str) -> QueryResult:
    """Run the full query pipeline for one question."""
    offer_id = extract_offer_id(question)

    # 1) ID-aware retrieval: filter to the referenced offer, no fallback.
    if offer_id:
        chunks = retriever.hybrid_search(
            question, angebot_id=offer_id, hyde_passage=_hyde_for(question)
        )
        if not chunks:
            return QueryResult(
                type="refusal",
                route="Refusal",
                content=(
                    f"Angebot **{offer_id}** wurde nicht in den vorliegenden "
                    "Angeboten gefunden."
                ),
            )
        # Price questions with a known offer are answered deterministically
        # from metadata — no LLM, no confabulated numbers.
        if is_price_question(question):
            answer = price_answer(offer_id, chunks)
            if answer:
                return QueryResult(
                    type="answer", route="RAG", content=answer, chunks=chunks
                )
        chunks, refusal = _rerank_and_gate(question, chunks, is_compound(question))
        if refusal:
            return QueryResult(
                type="refusal", route="Refusal", content=refusal, chunks=chunks
            )
        return QueryResult(
            type="answer",
            route="RAG",
            content=generate_answer(question, chunks, retriever.offer_count),
            chunks=chunks,
        )

    # 2) Statistics (count/mean/outliers) → FULL SCAN + code reduce.
    #    Checked BEFORE ambiguous/aggregation: "wie viele … Zahlungsziel"
    #    would otherwise hit the clarification or RAG path.
    if is_statistics(question):
        route, content, chunks = statistics_route(retriever, question)
        return QueryResult(type="answer", route=route, content=content, chunks=chunks)

    # 3) Comparison (vergleiche/unterschiede) → map-reduce over topic retrieval.
    if is_comparison(question):
        route, content, chunks = comparison_route(
            retriever, question, hyde_passage=_hyde_for(question)
        )
        return QueryResult(type="answer", route=route, content=content, chunks=chunks)

    # 4) Year-list question ("Welche Angebote sind im Jahr 2024?") →
    #    deterministic metadata scan — complete list, no LLM, no retrieval.
    if is_year_question(question):
        route, content, chunks = year_route(retriever, question)
        return QueryResult(type="answer", route=route, content=content, chunks=chunks)

    # 5) Ambiguous price/date/term question → clarification (no LLM call).
    if is_ambiguous(question):
        candidates = retriever.candidates_for(question, top_k=settings.top_k)
        if candidates:
            lines = " · ".join(
                f"{c['angebot_id']} ({c['datum']}"
                + (f", {format_price(c['preis'])}" if c["preis"] else "")
                + ")"
                for c in candidates
            )
            return QueryResult(
                type="clarify",
                route="Clarify",
                content=(
                    f"Insgesamt liegen {retriever.offer_count} Angebote vor — "
                    f"meinst du eines dieser? {lines}"
                ),
                candidates=candidates,
            )

    # 6) Aggregation question → explicit limitation until the SQL path exists.
    if is_aggregation(question):
        chunks = retriever.hybrid_search(question, hyde_passage=_hyde_for(question))
        chunks, refusal = _rerank_and_gate(question, chunks, is_compound(question))
        if refusal:
            return QueryResult(
                type="refusal", route="Refusal", content=refusal, chunks=chunks
            )
        answer = generate_answer(question, chunks, retriever.offer_count)
        answer += (
            "\n\n*Hinweis: Ich kann nur die hier geladenen Angebote vergleichen — "
            "eine vollständige Auswertung über alle Angebote folgt mit dem "
            "SQL-Pfad.*"
        )
        return QueryResult(
            type="answer", route="RAG", content=answer, chunks=chunks
        )

    # 7) Default: grounded RAG answer.
    chunks = retriever.hybrid_search(question, hyde_passage=_hyde_for(question))
    chunks, refusal = _rerank_and_gate(question, chunks, is_compound(question))
    if refusal:
        return QueryResult(
            type="refusal", route="Refusal", content=refusal, chunks=chunks
        )
    return QueryResult(
        type="answer",
        route="RAG",
        content=generate_answer(question, chunks, retriever.offer_count),
        chunks=chunks,
    )
