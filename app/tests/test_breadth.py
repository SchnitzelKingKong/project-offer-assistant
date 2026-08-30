"""Tests for src/rag_system/breadth.py (statistics + comparison routes)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from rag_system.breadth import (
    _FACTS_CACHE,
    comparison_route,
    full_scan_facts,
    is_comparison,
    is_statistics,
    reduce_statistics,
    statistics_route,
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
    assert content == "AG0001 ist schneller [AG0001]."
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
