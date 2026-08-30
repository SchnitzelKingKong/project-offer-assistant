"""Tests for src/rag_system/citation_markup.py."""

from __future__ import annotations

from rag_system.citation_markup import (
    page_of_quote,
    render_answer_html,
    upgrade_citations,
)
from rag_system.retriever import RetrievedChunk


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


# --- Page-level citations: [AG####] → [AG#### | S. X] ------------------------


def _chunk(text: str, source: str = "AG0001") -> RetrievedChunk:
    return RetrievedChunk(
        text=text, source=source, score=0.5,
        metadata={"datum": "2026-05-01"},
    )


def test_page_of_quote_finds_last_marker_before_quote():
    text = (
        "[Seite 1 von 4] Einleitung\n"
        "[Seite 2 von 4] Zahlung innerhalb von 14 Tagen netto.\n"
        "[Seite 3 von 4] Sonstiges"
    )
    assert page_of_quote(text, "Zahlung innerhalb von 14 Tagen netto.") == 2


def test_page_of_quote_before_any_marker_is_page_1():
    assert page_of_quote("[Seite 2 von 4] Text", "Text") == 2
    assert page_of_quote("Kein Marker, nur Text", "Text") == 1


def test_page_of_quote_not_found_returns_none():
    assert page_of_quote("[Seite 1 von 2] Anderer Text", "nicht da") is None


def test_page_of_quote_normalizes_whitespace_and_quotes():
    text = "[Seite 2 von 3]   Lieferung   in   10   Werktagen."
    assert page_of_quote(text, "Lieferung in 10 Werktagen.") == 2


def test_upgrade_citations_appends_page_and_date():
    chunk = _chunk("[Seite 1 von 4] Kopf\n[Seite 2 von 4] Zahlung 14 Tage netto.")
    content = "Wörtlich heißt es in AG0001: \u201eZahlung 14 Tage netto.\u201c AG0001"
    upgraded = upgrade_citations(content, [chunk])
    assert "AG0001, Seite 2 vom 01.05.2026" in upgraded


def test_upgrade_citations_drops_redundant_sentence_start_citation():
    # "…möglich sind. AG0085 Wörtlich heißt es: „…" AG0085" — the
    # sentence-start AG0085 is redundant (already cited in sentence 1).
    chunk = _chunk("[Seite 2 von 4] Zahlung 14 Tage netto.")
    content = (
        "In AG0001 gilt Zahlung 14 Tage. AG0001 Wörtlich heißt es: "
        "\u201eZahlung 14 Tage netto.\u201c AG0001"
    )
    upgraded = upgrade_citations(content, [chunk])
    assert upgraded.count("AG0001") == 2  # in-sentence + after quote
    assert "In AG0001 gilt Zahlung 14 Tage. Wörtlich heißt es:" in upgraded
    assert "AG0001, Seite 2 vom 01.05.2026" in upgraded


def test_upgrade_citations_keeps_sentence_start_citation_when_new_offer():
    # Different offer at the sentence start must NOT be removed.
    chunk1 = _chunk("[Seite 2 von 4] Zahlung 14 Tage netto.")
    chunk2 = _chunk("[Seite 1 von 2] Lieferung in 10 Werktagen.", source="AG0002")
    content = (
        "In AG0001 gilt Zahlung 14 Tage. AG0002 Wörtlich heißt es: "
        "\u201eLieferung in 10 Werktagen.\u201c AG0002"
    )
    upgraded = upgrade_citations(content, [chunk1, chunk2])
    assert "AG0002 Wörtlich heißt es:" in upgraded
    assert "AG0002, Seite 1 vom 01.05.2026" in upgraded


def test_upgrade_citations_keeps_source_list_after_sentence():
    # "Quellen: AG0001" is not directly after a sentence end.
    chunk = _chunk("[Seite 2 von 4] Zahlung 14 Tage netto.")
    content = "In AG0001 gilt Zahlung 14 Tage.\n\nQuellen: AG0001"
    upgraded = upgrade_citations(content, [chunk])
    assert "Quellen: AG0001" in upgraded


def test_upgrade_citations_citation_after_quote_not_in_sentence():
    # New style: "Wörtlich heißt es: „…" AG0001" (id after the quote).
    chunk = _chunk("[Seite 2 von 4] Zahlung 14 Tage netto.")
    content = "Wörtlich heißt es: \u201eZahlung 14 Tage netto.\u201c AG0001"
    upgraded = upgrade_citations(content, [chunk])
    assert "AG0001, Seite 2 vom 01.05.2026" in upgraded


def test_upgrade_citations_accepts_straight_closing_quote():
    # The model sometimes closes with a straight " instead of ".
    chunk = _chunk("[Seite 2 von 4] Zahlung 14 Tage netto.")
    content = 'Wörtlich heißt es in AG0001: \u201eZahlung 14 Tage netto." AG0001'
    upgraded = upgrade_citations(content, [chunk])
    assert "AG0001, Seite 2 vom 01.05.2026" in upgraded


def test_upgrade_citations_without_date_metadata():
    chunk = RetrievedChunk(
        text="[Seite 2 von 4] Zahlung 14 Tage netto.",
        source="AG0001", score=0.5, metadata={},
    )
    content = "Wörtlich: \u201eZahlung 14 Tage netto.\u201c AG0001"
    upgraded = upgrade_citations(content, [chunk])
    assert "AG0001, Seite 2" in upgraded
    assert "vom" not in upgraded


def test_upgrade_citations_bracketed_id_becomes_plain_with_page():
    chunk = _chunk("[Seite 2 von 4] Zahlung 14 Tage netto.")
    content = "Wörtlich: \u201eZahlung 14 Tage netto.\u201c [AG0001]"
    upgraded = upgrade_citations(content, [chunk])
    assert "AG0001, Seite 2 vom 01.05.2026" in upgraded
    assert "[AG0001]" not in upgraded


def test_upgrade_citations_without_quotes_unchanged():
    chunk = _chunk("[Seite 1 von 4] Zahlung 14 Tage netto.")
    content = "Kurzantwort ohne Zitat AG0001."
    assert upgrade_citations(content, [chunk]) == content


def test_upgrade_citations_unresolvable_quote_keeps_plain_citation():
    chunk = _chunk("[Seite 1 von 4] Kompletlich anderer Text.")
    content = "Behauptung: \u201eetwas anderes\u201c AG0001."
    assert upgrade_citations(content, [chunk]) == content


def test_upgrade_citations_ignores_other_offers_chunks():
    other = _chunk("[Seite 5 von 9] Zahlung 14 Tage netto.", source="AG0002")
    content = "Zitat: \u201eZahlung 14 Tage netto.\u201c AG0001."
    # The quote only exists in AG0002's chunk → AG0001 citation stays plain.
    assert upgrade_citations(content, [other]) == content


def test_upgrade_citations_leaves_trailing_source_list_plain():
    """The source list is far from any quote → stays a plain overview."""
    chunk = _chunk("[Seite 2 von 4] Zahlung 14 Tage netto.")
    content = (
        "Wörtlich heißt es in AG0001: \u201eZahlung 14 Tage netto.\u201c AG0001\n\n"
        "Quellen: AG0001, AG0002"
    )
    upgraded = upgrade_citations(content, [chunk])
    assert "AG0001, Seite 2 vom 01.05.2026" in upgraded
    assert "Quellen: AG0001, AG0002" in upgraded  # untouched
