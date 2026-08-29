"""Tests for HyDE (third RRF list) and the compound-question gate (no index, no LLM)."""

from unittest.mock import patch

from rag_system.llm import hyde_passage
from rag_system.query import is_compound
from rag_system.retriever import Retriever, RetrievedChunk


def _chunk(text: str, source: str = "AG0001") -> RetrievedChunk:
    return RetrievedChunk(text=text, source=source, score=0.5, metadata={})


def test_hyde_passage_returns_stripped_text():
    fake_response = {"message": {"content": "  Ein Planungsrahmen von zwei Wochen.  "}}
    with patch("rag_system.llm._client") as mock_client:
        mock_client.return_value.chat.return_value = fake_response
        assert hyde_passage("Wie lange dauert es?") == "Ein Planungsrahmen von zwei Wochen."


def test_hyde_passage_strips_think_block():
    fake_response = {"message": {"content": "thinking\n</think>\nEin Absatz."}}
    with patch("rag_system.llm._client") as mock_client:
        mock_client.return_value.chat.return_value = fake_response
        assert hyde_passage("q") == "Ein Absatz."


def test_hyde_passage_returns_empty_on_error():
    with patch("rag_system.llm._client") as mock_client:
        mock_client.return_value.chat.side_effect = RuntimeError("down")
        assert hyde_passage("q") == ""


def test_rrf_fuse_with_hyde_list_boosts_agreement():
    a, b, c = _chunk("alpha"), _chunk("beta"), _chunk("gamma")
    vec = [b, a, c]
    bm25 = [b, c, a]
    hyde = [a, b, c]
    fused = Retriever.rrf_fuse(
        vec, bm25, hyde_results=hyde, w_vec=0.4, w_bm25=0.3, w_hyde=0.3, k=60, top_n=10
    )
    # b is #1 in vec AND bm25 → wins overall
    assert fused[0].text == "beta"
    # a is #1 in hyde, #2 in vec, #3 in bm25 → second
    assert fused[1].text == "alpha"


def test_rrf_fuse_without_hyde_unchanged():
    a, b = _chunk("alpha"), _chunk("beta")
    fused = Retriever.rrf_fuse([a, b], [b, a], k=60, top_n=10)
    assert [c.text for c in fused] == ["alpha", "beta"]


def test_is_compound_two_question_marks():
    assert is_compound("Wie lange dauert es? Und welche Bedingungen gelten?")


def test_is_compound_und_connector():
    assert is_compound("Was sind die Zeitrahmen und welche Geschäftsbedingungen?")


def test_is_compound_plain_question():
    assert not is_compound("Wie hoch war der Preis von AG0085?")
