"""Tests for hybrid retrieval (RRF fusion) and LLM rerank parsing (no index, no LLM)."""

from unittest.mock import patch

from rag_system.llm import rerank
from rag_system.retriever import Retriever, RetrievedChunk


def _chunk(text: str, source: str = "AG0001") -> RetrievedChunk:
    return RetrievedChunk(text=text, source=source, score=0.5, metadata={})


def test_rrf_fuse_prefers_chunks_ranked_high_in_both_lists():
    a, b, c = _chunk("alpha"), _chunk("beta"), _chunk("gamma")
    vec = [a, b, c]
    bm25 = [c, a, b]  # a ranked #1 in vec, #2 in bm25 → best overall
    fused = Retriever.rrf_fuse(vec, bm25, w_vec=0.5, w_bm25=0.5, k=60, top_n=10)
    assert [c.text for c in fused] == ["alpha", "gamma", "beta"]
    # RRF score of alpha = 0.5/61 (vec rank 0) + 0.5/62 (bm25 rank 1)
    assert abs(fused[0].metadata["rrf_score"] - (0.5 / 61 + 0.5 / 62)) < 1e-9


def test_rrf_fuse_deduplicates_identical_chunks():
    a = _chunk("same")
    b = _chunk("other")
    fused = Retriever.rrf_fuse([a, b], [a, b], k=60, top_n=10)
    assert len(fused) == 2
    assert fused[0].text == "same"


def test_rrf_fuse_respects_top_n():
    chunks = [_chunk(f"chunk {i}") for i in range(10)]
    fused = Retriever.rrf_fuse(chunks, list(reversed(chunks)), k=60, top_n=3)
    assert len(fused) == 3


def test_hybrid_search_uses_hyde_weights_when_hyde_active():
    """With a HyDE passage the base arms are re-weighted to 0.4/0.3 (vec/bm25)
    so all three arms sum to 1.0 (notebooks/05)."""
    r = Retriever.__new__(Retriever)  # skip __init__ (no index needed)
    a, b = _chunk("alpha"), _chunk("beta")
    with patch.object(r, "query", return_value=[a, b]), \
         patch.object(r, "bm25_search", return_value=[b, a]):
        fused = r.hybrid_search("q", top_n=10, hyde_passage="hypothetical")
    # alpha: vec rank 0 (0.4/61) + bm25 rank 1 (0.3/62) + hyde rank 0 (0.3/61)
    expected = 0.4 / 61 + 0.3 / 62 + 0.3 / 61
    assert abs(fused[0].metadata["rrf_score"] - expected) < 1e-9


def test_hybrid_search_uses_default_weights_without_hyde():
    r = Retriever.__new__(Retriever)
    a, b = _chunk("alpha"), _chunk("beta")
    with patch.object(r, "query", return_value=[a, b]), \
         patch.object(r, "bm25_search", return_value=[b, a]):
        fused = r.hybrid_search("q", top_n=10)
    # alpha: vec rank 0 (0.5/61) + bm25 rank 1 (0.5/62), no hyde arm
    expected = 0.5 / 61 + 0.5 / 62
    assert abs(fused[0].metadata["rrf_score"] - expected) < 1e-9


def test_rerank_orders_by_llm_scores():
    candidates = [_chunk(f"passage {i}") for i in range(1, 5)]
    fake_response = {
        "message": {"content": 'Here is the ranking: {"1": 2, "2": 9, "3": 4, "4": 7}'}
    }
    with patch("rag_system.llm._client") as mock_client:
        mock_client.return_value.chat.return_value = fake_response
        ranked = rerank("test query", candidates, keep=3)
    assert [c.text for c in ranked] == ["passage 2", "passage 4", "passage 3"]
    assert ranked[0].rerank_score == 9.0
    assert ranked[0].score == 9.0


def test_rerank_strips_think_block():
    candidates = [_chunk("only passage")]
    fake_response = {
        "message": {"content": "thinking...</think>\n{\"1\": 8}"}
    }
    with patch("rag_system.llm._client") as mock_client:
        mock_client.return_value.chat.return_value = fake_response
        ranked = rerank("q", candidates, keep=1)
    assert ranked[0].rerank_score == 8.0


def test_rerank_falls_back_to_retrieval_order_on_bad_json():
    candidates = [_chunk(f"passage {i}") for i in range(1, 4)]
    fake_response = {"message": {"content": "I cannot produce JSON."}}
    with patch("rag_system.llm._client") as mock_client:
        mock_client.return_value.chat.return_value = fake_response
        with patch("rag_system.llm.time.sleep"):  # skip backoff waits
            ranked = rerank("q", candidates, keep=2)
    assert [c.text for c in ranked] == ["passage 1", "passage 2"]
    assert all(c.rerank_score is None for c in ranked)
