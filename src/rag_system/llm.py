"""LLM client for answer generation (OpenAI-compatible endpoint).

Works with both vLLM (GPU machine) and Ollama (local) since both expose
an OpenAI-compatible API.
"""

from __future__ import annotations

from .config import settings
from .retriever import RetrievedChunk

SYSTEM_PROMPT = """You are an assistant for project quote history.
Answer questions strictly based on the provided context chunks.
If the context does not contain a definite answer, say so.
Cite the source of each fact using the chunk's source label.
Answer in the language of the user's question."""


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    """Generate a grounded answer for the question from retrieved chunks.

    TODO: build the prompt (system + context + question) and call the
    LLM endpoint from settings.
    """
    raise NotImplementedError("Answer generation not implemented yet")
