"""Tests for the deterministic query pre-checks (no LLM, no index needed)."""

from rag_system.query import (
    extract_offer_id,
    is_aggregation,
    is_ambiguous,
)


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
