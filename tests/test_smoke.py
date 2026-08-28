"""Smoke tests — importability and configuration."""

from rag_system.config import settings
from rag_system.retriever import Retriever


def test_settings_load():
    assert settings.llm_model
    assert settings.embed_model
    assert settings.index_dir


def test_retriever_instantiates():
    retriever = Retriever()
    # No index on disk in a fresh checkout → not available, but no crash
    assert isinstance(retriever.is_available, bool)
