"""Tests for src/rag_system/citation_markup.py."""

from __future__ import annotations

from rag_system.citation_markup import render_answer_html


def test_bracketed_offer_id_becomes_chip():
    html = render_answer_html("Siehe Angebot [AG0091] für Details.")
    assert '<a class="cite-chip" data-offer="AG0091" href="#">AG0091</a>' in html
    assert "[AG0091]" not in html


def test_multiple_citations_all_become_chips():
    html = render_answer_html("Erstens [AG0091], zweitens [AG0078].")
    assert html.count('class="cite-chip"') == 2
    assert 'data-offer="AG0091"' in html
    assert 'data-offer="AG0078"' in html


def test_plain_offer_id_is_left_untouched():
    html = render_answer_html("Das Angebot AG0091 ist teuer.")
    assert "cite-chip" not in html
    assert "AG0091" in html


def test_non_offer_brackets_are_left_untouched():
    html = render_answer_html("Siehe [AG12345] und [XAG0085Y].")
    assert "cite-chip" not in html


def test_markdown_is_rendered():
    html = render_answer_html("**Zahlungsziel:** 14 Tage [AG0072].")
    assert "<strong>Zahlungsziel:</strong>" in html
    assert 'data-offer="AG0072"' in html


def test_lists_are_rendered():
    html = render_answer_html("- Punkt eins [AG0078]\n- Punkt zwei")
    assert "<ul>" in html
    assert "<li>" in html
    assert 'data-offer="AG0078"' in html
