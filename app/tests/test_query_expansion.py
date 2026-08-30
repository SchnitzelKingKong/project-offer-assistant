"""Tests for static acronym query expansion (retrieval failure mode #3b)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_system.query_expansion import expand_query  # noqa: E402


def test_acronym_gets_full_term_appended():
    expanded = expand_query("Was ist mit DNxHR geregelt?")
    assert "Dolby Vision" in expanded
    # original question preserved
    assert expanded.startswith("Was ist mit DNxHR geregelt?")


def test_full_term_gets_acronym_appended():
    expanded = expand_query("Welche Codec-Anforderungen für Dolby Vision?")
    assert "DNxHR" in expanded


def test_plain_question_unchanged():
    question = "Welche Zahlungsbedingungen gelten?"
    assert expand_query(question) == question


def test_word_boundary_no_false_positive():
    # "hd" must not match inside other words
    question = "Hat das Angebot eine Headline?"
    assert expand_query(question) == question


def test_case_insensitive_match():
    expanded = expand_query("agb bitte zusammenfassen")
    assert "Allgemeine Geschäftsbedingungen" in expanded


def test_multiple_acronyms_expanded_once():
    expanded = expand_query("DNxHR und DCP im Vergleich")
    assert "Dolby Vision" in expanded
    assert "Digital Cinema Package" in expanded
    # each expansion appears exactly once
    assert expanded.count("Dolby Vision") == 1


def test_hyphenated_ustid():
    expanded = expand_query("Welche USt-IdNr ist angegeben?")
    assert "Umsatzsteuer" in expanded
