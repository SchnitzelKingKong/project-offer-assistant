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


def test_plain_offer_id_becomes_chip():
    html = render_answer_html("Das Angebot AG0091 ist teuer.")
    assert '<a class="cite-chip" data-offer="AG0091" href="#">AG0091</a>' in html


def test_source_list_ids_become_chips():
    html = render_answer_html("Quellenliste: * AG0091 (2026-07-09) * AG0078")
    assert html.count('class="cite-chip"') == 2
    assert " · " in html  # asterisk separators rendered as middle dots
    assert " * " not in html


def test_bold_markdown_survives_asterisk_cleanup():
    html = render_answer_html("**Zahlungsziel:** 14 Tage [AG0072].")
    assert "<strong>Zahlungsziel:</strong>" in html
    assert "**" not in html


def test_line_start_asterisk_list_becomes_dots():
    # Model emits list markers glued to the preceding paragraph (no blank
    # line), so markdown keeps them as literal text.
    content = "**Quellenliste:**\n*   AG0078 (S.1)\n*   AG0072 (S.1)"
    html = render_answer_html(content)
    assert "*" not in html
    assert html.count('class="cite-chip"') == 2
    assert " · " in html


def test_non_offer_ids_are_left_untouched():
    html = render_answer_html("Siehe [AG12345] und XAG0085Y.")
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
