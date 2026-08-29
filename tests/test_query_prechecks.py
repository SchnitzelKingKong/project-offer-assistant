"""Tests for the deterministic query pre-checks (no LLM, no index needed)."""

from rag_system.query import (
    extract_offer_id,
    is_aggregation,
    is_ambiguous,
    is_price_question,
    price_answer,
)
from rag_system.retriever import RetrievedChunk


def test_extract_offer_id_found():
    assert extract_offer_id("Wie hoch war der Nettobetrag von AG0085?") == "AG0085"


def test_extract_offer_id_not_found():
    assert extract_offer_id("Wie sind die Zahlungsbedingungen?") is None


def test_ambiguous_price_question_without_reference():
    assert is_ambiguous("Wie hoch war der Preis?") is True


def test_not_ambiguous_with_year():
    assert is_ambiguous("Wie hoch war der Preis im Jahr 2024?") is False


def test_not_ambiguous_neutral_question():
    assert is_ambiguous("Welche Positionen hat ein Color Grading Angebot?") is False


def test_aggregation_detected():
    assert is_aggregation("Welche Angebote aus 2024 waren teurer als 5000 Euro?")
    assert is_aggregation("Wie viele Angebote gibt es?")


def test_no_aggregation_for_single_offer_question():
    assert not is_aggregation("Wie hoch war der Nettobetrag des Angebots AG0085?")


def test_price_question_detected():
    assert is_price_question("Wie hoch war der Preis? (gemeint ist Angebot AG0086)")
    assert is_price_question("Was war der Nettobetrag von AG0085?")
    assert not is_price_question("Welche Positionen hat das Angebot?")


def test_price_answer_from_metadata():
    chunks = [
        RetrievedChunk(
            text="...",
            source="AG0086",
            score=0.6,
            metadata={"angebot_id": "AG0086", "datum": "2026-05-12", "preis": 8160.80},
        )
    ]
    answer = price_answer("AG0086", chunks)
    assert answer is not None
    assert "8.160,80 €" in answer
    assert "AG0086" in answer


def test_price_answer_none_without_price():
    chunks = [
        RetrievedChunk(
            text="...",
            source="AG0086",
            score=0.6,
            metadata={"angebot_id": "AG0086", "datum": "2026-05-12", "preis": None},
        )
    ]
    assert price_answer("AG0086", chunks) is None
