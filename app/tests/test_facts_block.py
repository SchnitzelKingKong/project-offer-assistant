"""Tests for the price-aware facts block in the answer prompt."""

from __future__ import annotations

from rag_system.llm import _facts_block, question_asks_about_price
from rag_system.retriever import RetrievedChunk


def _chunk(source: str, preis: float | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        text=f"Text von {source}",
        source=source,
        score=0.9,
        metadata={"angebot_id": source, "datum": "2023-01-01", "preis": preis},
    )


def test_price_question_detected():
    assert question_asks_about_price("Wie hoch war der Preis für AG0085?")
    assert question_asks_about_price("Was kostet ein Tag Color Grading?")
    assert question_asks_about_price("Welcher Betrag wurde berechnet?")
    assert question_asks_about_price("Wie viel Euro war das Angebot?")


def test_non_price_question_not_detected():
    assert not question_asks_about_price(
        "Was sind übliche Zeitrahmen und Geschäftsbedingungen?"
    )
    assert not question_asks_about_price("Welches Codec-Format wurde geliefert?")


def test_facts_block_omits_price_for_non_price_question():
    chunks = [_chunk("AG0001", 6600.0), _chunk("AG0002", 1200.0)]
    block = _facts_block(chunks, "Welche Zahlungsbedingungen gelten?")
    assert "preis=" not in block
    assert "AG0001: datum=2023-01-01" in block
    assert "AG0002: datum=2023-01-01" in block


def test_facts_block_includes_price_for_price_question():
    chunks = [_chunk("AG0001", 6600.0)]
    block = _facts_block(chunks, "Wie hoch war der Preis?")
    assert "preis=6.600,00 €" in block


def test_facts_block_deduplicates_offers():
    chunks = [_chunk("AG0001", 6600.0), _chunk("AG0001", 6600.0)]
    block = _facts_block(chunks, "Wie hoch war der Preis?")
    assert block.count("AG0001") == 1


def test_facts_block_empty():
    assert _facts_block([], "Wie hoch war der Preis?") == "(keine strukturierten Daten)"
