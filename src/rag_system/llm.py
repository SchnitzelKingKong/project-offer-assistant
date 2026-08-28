"""LLM client for chat and answer generation.

Uses the native Ollama API so that thinking/reasoning can be disabled
(``think=False``) — the OpenAI-compatible endpoint ignores the
``enable_thinking`` flag for Qwen3 models, which makes them think for
minutes before answering.
"""

from __future__ import annotations

import ollama

from .config import settings
from .retriever import RetrievedChunk

SYSTEM_PROMPT = """You are the Project Offer Assistant, an in-house assistant
for project-based service providers. You answer questions about past project
offers: framework conditions, timelines, and line items.

Rules:
- When context chunks are provided, answer strictly based on them.
- If the context does not contain a definite answer, say so.
- Cite the source of each fact using the chunk's source label.
- Answer in the language of the user's question."""

CHAT_SYSTEM_PROMPT = """You are the Project Offer Assistant, an in-house
assistant for project-based service providers. Be friendly and concise.
Answer in the language of the user's question."""


def _client() -> ollama.Client:
    """Ollama client pointed at the configured endpoint.

    ``llm_base_url`` may be an OpenAI-compatible URL (``…/v1``) — the
    native API lives at the host root.
    """
    base_url = settings.llm_base_url.removesuffix("/v1")
    return ollama.Client(host=base_url)


def chat(messages: list[dict]) -> str:
    """Plain chat (no RAG) — used as fallback while no index exists.

    ``messages`` is a list of {"role": ..., "content": ...} dicts.
    """
    response = _client().chat(
        model=settings.llm_model,
        messages=[{"role": "system", "content": CHAT_SYSTEM_PROMPT}, *messages],
        # Qwen3 models think by default — disable it for fast, direct answers
        think=False,
    )
    return response["message"]["content"] or ""


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    """Generate a grounded answer for the question from retrieved chunks."""
    context = "\n\n".join(
        f"[Source: {chunk.source}]\n{chunk.text}" for chunk in chunks
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        },
    ]
    return chat(messages)
