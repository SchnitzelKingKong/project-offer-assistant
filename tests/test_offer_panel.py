"""Tests for the offer detail panel data access (get_offer, extract_offer_ids)."""

from __future__ import annotations

from dataclasses import replace

from rag_system import retriever as retriever_module
from rag_system.retriever import Retriever, extract_offer_ids


# --- extract_offer_ids --------------------------------------------------------


def test_extract_offer_ids_order_and_dedupe():
    text = "Wie in [AG0085] beschrieben, vgl. auch [AG0048] und erneut [AG0085]."
    assert extract_offer_ids(text) == ["AG0085", "AG0048"]


def test_extract_offer_ids_no_false_positives():
    # Five-digit runs and embedded ids must not match
    assert extract_offer_ids("AG12345 und XAG0085Y") == []
    assert extract_offer_ids("Keine Citations in diesem Text.") == []


def test_extract_offer_ids_bracketed_and_plain():
    assert extract_offer_ids("[AG0002] und AG0091") == ["AG0002", "AG0091"]


# --- get_offer ----------------------------------------------------------------


class _FakeCollection:
    """Minimal stand-in for a Chroma collection."""

    def __init__(self, rows: list[tuple[str, str, dict]]):
        self._rows = rows  # (id, document, metadata)

    def get(self, where=None, include=None):
        rows = [
            (node_id, doc, meta)
            for node_id, doc, meta in self._rows
            if where is None or meta.get("angebot_id") == where.get("angebot_id")
        ]
        return {
            "ids": [r[0] for r in rows],
            "documents": [r[1] for r in rows],
            "metadatas": [r[2] for r in rows],
        }


def _retriever(rows: list[tuple[str, str, dict]]) -> Retriever:
    r = Retriever.__new__(Retriever)
    r._collection = _FakeCollection(rows)
    return r


def test_get_offer_from_file(tmp_path, monkeypatch):
    (tmp_path / "AG0001.txt").write_text("Voller Text\n\nSeite 2", encoding="utf-8")
    monkeypatch.setattr(
        retriever_module,
        "settings",
        replace(retriever_module.settings, offer_text_dir=str(tmp_path)),
    )
    rows = [
        (
            "n1",
            "Chunk 1",
            {"angebot_id": "AG0001", "datum": "2023-01-01", "preis": 100.0},
        )
    ]
    offer = _retriever(rows).get_offer("AG0001")
    assert offer is not None
    assert offer["text"] == "Voller Text\n\nSeite 2"
    assert offer["text_source"] == "file"
    assert offer["datum"] == "2023-01-01"
    assert offer["preis"] == 100.0


def test_get_offer_falls_back_to_index_chunks(tmp_path, monkeypatch):
    # Directory exists but the file does not → index fallback
    monkeypatch.setattr(
        retriever_module,
        "settings",
        replace(retriever_module.settings, offer_text_dir=str(tmp_path)),
    )
    rows = [
        ("n1", "Chunk eins", {"angebot_id": "AG0002", "datum": "2022-05-05", "preis": None}),
        ("n2", "Chunk zwei", {"angebot_id": "AG0002", "datum": "2022-05-05", "preis": None}),
    ]
    offer = _retriever(rows).get_offer("AG0002")
    assert offer is not None
    assert offer["text"] == "Chunk eins\n\nChunk zwei"
    assert offer["text_source"] == "index"


def test_get_offer_unknown_offer_returns_none():
    assert _retriever([]).get_offer("AG9999") is None


def test_get_offer_no_index_returns_none():
    r = Retriever.__new__(Retriever)
    r._collection = None
    assert r.get_offer("AG0001") is None
