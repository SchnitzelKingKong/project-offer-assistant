"""Tests for src/rag_system/breadth.py (statistics + comparison routes)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from rag_system.breadth import (
    _FACTS_CACHE,
    comparison_route,
    draft_route,
    full_scan_facts,
    is_comparison,
    is_draft,
    is_statistics,
    is_year_question,
    reduce_statistics,
    statistics_route,
    year_route,
)
from rag_system.retriever import RetrievedChunk


# --- Detection ---------------------------------------------------------------


def test_is_statistics_matches_count_and_mean_words():
    assert is_statistics("Wie viele Angebote habe ich geschrieben?")
    assert is_statistics("Wieviel kostet das im Durchschnitt?")
    assert is_statistics("Gibt es Ausreißer bei den Preisen?")
    assert is_statistics("Wie hoch ist der Anteil mit Skonto?")
    assert not is_statistics("Wie hoch war der Preis von AG0085?")


def test_is_comparison_matches_comparison_words():
    assert is_comparison("Vergleiche die Zahlungsbedingungen der Angebote.")
    assert is_comparison("Was sind die Unterschiede bei der Lieferzeit?")
    assert is_comparison("Stellen Sie die Angebote nebeneinander.")
    assert not is_comparison("Wie hoch war der Preis von AG0085?")


def test_is_year_question_matches_year_plus_offer_word():
    assert is_year_question("Welche Angebote sind im Jahr 2024?")
    assert is_year_question("Gibt es Angebote aus 2023?")
    # A single aspect of a year is NOT a year-list question.
    assert not is_year_question("Wie hoch war der Preis im Jahr 2024?")
    assert not is_year_question("Wie sind die Zahlungsbedingungen?")


# --- Statistics reduce (pure code, no LLM) -----------------------------------


def _facts() -> dict[str, dict]:
    return {
        "AG0001": {"zahlungsziel_tage": 14, "skonto_prozent": None,
                   "lieferzeit": None, "garantie": None, "leistungen": [],
                   "preis": 1000.0, "datum": "2026-01-01"},
        "AG0002": {"zahlungsziel_tage": 30, "skonto_prozent": 5.0,
                   "lieferzeit": "10 Werktage", "garantie": None, "leistungen": [],
                   "preis": 1200.0, "datum": "2026-02-01"},
        "AG0003": {"zahlungsziel_tage": None, "skonto_prozent": None,
                   "lieferzeit": None, "garantie": None, "leistungen": [],
                   "preis": 1100.0, "datum": "2026-03-01"},
        "AG0004": {"zahlungsziel_tage": 0, "skonto_prozent": None,
                   "lieferzeit": None, "garantie": None, "leistungen": [],
                   "preis": 1050.0, "datum": "2026-04-01"},
        "AG0005": {"zahlungsziel_tage": None, "skonto_prozent": None,
                   "lieferzeit": None, "garantie": None, "leistungen": [],
                   "preis": 1150.0, "datum": "2026-05-01"},
        "AG0006": {"zahlungsziel_tage": None, "skonto_prozent": None,
                   "lieferzeit": None, "garantie": None, "leistungen": [],
                   "preis": 50000.0, "datum": "2026-06-01"},
    }


def test_reduce_statistics_counts_and_means():
    text = reduce_statistics(_facts())
    assert "6 Angebote" in text
    assert "2 von 6" in text  # only AG0001/AG0002 have a real Zahlungsziel
    assert "22 Tage" in text  # mean of 14 and 30
    assert "Spanne 14–30 Tage" in text
    assert "vollständiger Scan" in text


def test_reduce_statistics_detects_outliers():
    text = reduce_statistics(_facts())
    # 50.000 € is above mean + 2σ of [1000, 1200, 1100, 1050, 1150, 50000]
    assert "Ausreißer" in text
    assert "AG0006" in text


def test_reduce_statistics_without_payment_terms():
    facts = {"AG0001": {"zahlungsziel_tage": None, "preis": 100.0}}
    text = reduce_statistics(facts)
    assert "kein Angebot legt ein Zahlungsziel fest" in text


# --- Statistics route (map mocked, reduce real) ------------------------------


class _FakeRetriever:
    def all_offer_chunks(self):
        return {
            "AG0001": [RetrievedChunk(
                text="Zahlung 14 Tage netto.", source="AG0001", score=0.9,
                metadata={"preis": 1000.0, "datum": "2026-01-01"})],
            "AG0002": [RetrievedChunk(
                text="Zahlung 30 Tage netto.", source="AG0002", score=0.8,
                metadata={"preis": 1200.0, "datum": "2026-02-01"})],
        }


def test_statistics_route_uses_full_scan_and_code_reduce():
    _FACTS_CACHE.clear()
    fake_facts = {
        "AG0001": {"zahlungsziel_tage": 14, "skonto_prozent": None,
                   "lieferzeit": None, "garantie": None, "leistungen": [],
                   "preis": 1000.0, "datum": "2026-01-01"},
        "AG0002": {"zahlungsziel_tage": 30, "skonto_prozent": None,
                   "lieferzeit": None, "garantie": None, "leistungen": [],
                   "preis": 1200.0, "datum": "2026-02-01"},
    }
    with patch("rag_system.breadth.extract_offer_facts",
               side_effect=lambda text: {
                   "zahlungsziel_tage": 14 if "14" in text else 30,
                   "skonto_prozent": None, "lieferzeit": None,
                   "garantie": None, "leistungen": [],
               }) as mock_extract:
        route, content, chunks = statistics_route(_FakeRetriever(),
                                                  "Wie viele Angebote?")
    assert route == "Statistics"
    assert mock_extract.call_count == 2  # one LLM call per offer
    assert "2 Angebote" in content
    assert "22 Tage" in content
    assert chunks == []  # no retrieval involved
    _FACTS_CACHE.clear()


def test_full_scan_facts_is_cached_per_index():
    _FACTS_CACHE.clear()

    def _fresh_facts(text: str) -> dict:
        # A fresh dict per call — full_scan_facts mutates the result.
        return {"zahlungsziel_tage": 14 if "14" in text else 30,
                "skonto_prozent": None, "lieferzeit": None,
                "garantie": None, "leistungen": []}

    with patch("rag_system.breadth.extract_offer_facts",
               side_effect=_fresh_facts) as mock_extract:
        first = full_scan_facts(_FakeRetriever())
        second = full_scan_facts(_FakeRetriever())
    assert first is second
    assert mock_extract.call_count == 2  # only the first call scans
    assert first["AG0001"]["preis"] == 1000.0  # metadata merged in
    assert first["AG0002"]["preis"] == 1200.0
    _FACTS_CACHE.clear()


def test_full_scan_facts_skips_unextractable_offers():
    _FACTS_CACHE.clear()
    with patch("rag_system.breadth.extract_offer_facts", return_value=None):
        facts = full_scan_facts(_FakeRetriever())
    assert facts == {}
    _FACTS_CACHE.clear()


# --- Year route (deterministic metadata scan) ---------------------------------


class _YearFakeRetriever:
    def all_offer_chunks(self):
        return {
            "AG0070": [RetrievedChunk(
                text="...", source="AG0070", score=0.0,
                metadata={"datum": "2024-06-14"})],
            "AG0071": [RetrievedChunk(
                text="...", source="AG0071", score=0.0,
                metadata={"datum": "2024-07-01"})],
            "AG0073": [RetrievedChunk(
                text="...", source="AG0073", score=0.0,
                metadata={"datum": "2024-08-19"})],
            "AG0085": [RetrievedChunk(
                text="...", source="AG0085", score=0.0,
                metadata={"datum": "2026-05-01"})],
        }


def test_year_route_lists_all_offers_of_the_year_sorted():
    route, content, chunks = year_route(
        _YearFakeRetriever(), "Welche Angebote sind im Jahr 2024?")
    assert route == "Breadth"
    assert chunks == []  # no retrieval involved
    assert "3 Angebote" in content
    assert "AG0073 (19.08.2024)" in content
    assert "AG0071 (01.07.2024)" in content
    assert "AG0070 (14.06.2024)" in content
    assert "AG0085" not in content
    # Newest first.
    assert content.index("AG0073") < content.index("AG0071") < content.index("AG0070")


def test_year_route_without_matches_reports_empty():
    route, content, chunks = year_route(
        _YearFakeRetriever(), "Welche Angebote sind im Jahr 1999?")
    assert route == "Breadth"
    assert "Kein Angebot aus dem Jahr 1999" in content
    assert "4 Angebote" in content  # full scan over the whole index


# --- Comparison route (map/reduce mocked) ------------------------------------


class _FakeHybridRetriever:
    def hybrid_search(self, question, top_n=10, angebot_id=None,
                      hyde_passage=None):
        return [
            RetrievedChunk(text="AG0001: 14 Tage", source="AG0001", score=0.9,
                           metadata={}),
            RetrievedChunk(text="AG0001: Skonto 5%", source="AG0001", score=0.8,
                           metadata={}),
            RetrievedChunk(text="AG0002: 30 Tage", source="AG0002", score=0.7,
                           metadata={}),
        ]


def test_comparison_route_maps_per_offer_and_reduces():
    with patch("rag_system.breadth.comparison_line",
               side_effect=lambda q, oid, text: f"{oid}: 14 Tage") as mock_line, \
         patch("rag_system.breadth.comparison_reduce",
               return_value="AG0001 ist schneller [AG0001]."):
        route, content, chunks = comparison_route(
            _FakeHybridRetriever(), "Vergleiche die Zahlungsziele.")
    assert route == "Comparison"
    # Global citation behavior: grounded answers end with a source line.
    assert content == "AG0001 ist schneller [AG0001].\n\nQuellen: AG0001, AG0002"
    # One map call per OFFER (AG0001's two chunks merged), not per chunk.
    assert mock_line.call_count == 2
    assert [c.source for c in chunks] == ["AG0001", "AG0002"]


def test_comparison_route_empty_retrieval():
    class _Empty:
        def hybrid_search(self, *a, **k):
            return []

    route, content, chunks = comparison_route(_Empty(), "Vergleiche.")
    assert route == "Comparison"
    assert "Keine passenden Angebote" in content
    assert chunks == []


class _ScopedRetriever:
    """Returns chunks only for the offer id it is filtered to."""

    def hybrid_search(self, question, top_n=10, angebot_id=None,
                      hyde_passage=None):
        if angebot_id == "AG0002":
            return [RetrievedChunk(text="AG0002: 14 Tage", source="AG0002",
                                   score=0.9, metadata={})]
        if angebot_id == "AG0085":
            return [RetrievedChunk(text="AG0085: 30 Tage", source="AG0085",
                                   score=0.8, metadata={})]
        # Unfiltered topic retrieval would pull in unrelated offers.
        return [RetrievedChunk(text="AG0090: 30 Tage", source="AG0090",
                               score=0.7, metadata={})]


def test_comparison_route_scopes_to_named_offers():
    with patch("rag_system.breadth.comparison_line",
               side_effect=lambda q, oid, text: f"{oid}: 14 Tage"), \
         patch("rag_system.breadth.comparison_reduce",
               return_value="AG0002 vs AG0085."):
        route, content, chunks = comparison_route(
            _ScopedRetriever(), "Vergleiche AG0002 und AG0085.",
            offer_ids=["AG0002", "AG0085"],
        )
    assert route == "Comparison"
    # Only the two named offers are compared — the unrelated AG0090
    # that free topic retrieval would return is excluded.
    assert [c.source for c in chunks] == ["AG0002", "AG0085"]


# --- Draft route (map/reduce mocked) -----------------------------------------


def test_is_draft_matches_draft_words():
    assert is_draft("Stelle mir daraus einen Angebotsentwurf zusammen.")
    assert is_draft("Kannst du ein Angebot erstellen?")
    assert is_draft("Was würde ich verlangen?")
    assert is_draft("Bitte das Angebot aufsetzen.")
    # The verb must directly follow "Angebot" — otherwise normal questions
    # about offers ("ein Angebot für den Kunden anpassen") would misroute.
    assert not is_draft("Kannst du das Angebot für den Kunden anpassen?")
    # A normal question about an existing offer is NOT a draft request.
    assert not is_draft("Wie hoch war der Preis von AG0085?")
    assert not is_draft("Vergleiche die Zahlungsbedingungen.")


def test_draft_route_maps_per_offer_and_reduces():
    blocks = [
        {"positions": [{"position": "Color Grading", "menge": "2 Tag",
                        "satz_eur": 950.0, "betrag_eur": 1900.0}],
         "zahlungsbedingungen": "50 % Anzahlung", "abnahme": None,
         "lieferformate": ["ProRes"], "revisionen": None},
        {"positions": [{"position": "Mastering", "menge": "1 Festpreis",
                        "satz_eur": 600.0, "betrag_eur": 600.0}],
         "zahlungsbedingungen": None, "abnahme": None,
         "lieferformate": ["H.264"], "revisionen": None},
    ]
    with patch("rag_system.breadth.extract_draft_blocks",
               side_effect=lambda text: blocks[0] if "AG0001" in text
               else blocks[1]) as mock_map, \
         patch("rag_system.breadth.draft_reduce",
               return_value="Entwurf: 1.900,00 € + 600,00 € = 2.500,00 € "
                            "Quellen: AG0001, AG0002") as mock_reduce:
        route, content, chunks = draft_route(
            _FakeHybridRetriever(),
            "Neue Anfrage: Color Grading. Stelle mir einen Angebotsentwurf "
            "zusammen.")
    assert route == "Draft"
    assert "2.500,00 €" in content
    # One map call per OFFER (AG0001's two chunks merged), not per chunk.
    assert mock_map.call_count == 2
    # The reduce gets the scenario plus the blocks (with offer ids merged in).
    scenario, reduce_blocks = mock_reduce.call_args.args
    assert "Angebotsentwurf" in scenario
    assert [b["angebot_id"] for b in reduce_blocks] == ["AG0001", "AG0002"]
    assert reduce_blocks[0]["datum"] is None  # no datum in fake metadata
    assert [c.source for c in chunks] == ["AG0001", "AG0002"]


def test_draft_route_skips_unextractable_offers():
    with patch("rag_system.breadth.extract_draft_blocks",
               side_effect=lambda text: {"positions": []} if "AG0001" in text
               else None), \
         patch("rag_system.breadth.draft_reduce",
               return_value="Entwurf aus AG0001.") as mock_reduce:
        route, content, chunks = draft_route(
            _FakeHybridRetriever(), "Stelle mir einen Angebotsentwurf zusammen.")
    assert route == "Draft"
    # Only AG0001's block survived the map step.
    assert [b["angebot_id"] for b in mock_reduce.call_args.args[1]] == ["AG0001"]


def test_draft_route_empty_retrieval():
    class _Empty:
        def hybrid_search(self, *a, **k):
            return []

    route, content, chunks = draft_route(_Empty(), "Angebotsentwurf bitte.")
    assert route == "Draft"
    assert "Keine passenden Angebote" in content
    assert chunks == []


def test_draft_route_no_blocks_extracted():
    with patch("rag_system.breadth.extract_draft_blocks", return_value=None):
        route, content, chunks = draft_route(
            _FakeHybridRetriever(), "Stelle mir einen Angebotsentwurf zusammen.")
    assert route == "Draft"
    assert "Keine Bausteine" in content
    assert chunks == []
