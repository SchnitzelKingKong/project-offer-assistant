"""LLM client for chat and answer generation.

Supports two kinds of endpoints (both configured via ``LLM_BASE_URL``):

- **Local Ollama** — uses the native Ollama API so that thinking can be
  disabled (``think=False``); the OpenAI-compatible endpoint ignores the
  ``enable_thinking`` flag for Qwen3 models, which makes them think for
  minutes before answering.
- **Remote OpenAI-compatible server (vLLM)** — vLLM does not speak the
  native Ollama API, so an adapter (``_OpenAICompatClient``) exposes the
  same ``chat()`` interface on top of the OpenAI API. Qwen3 thinking is
  disabled there via ``chat_template_kwargs`` (vLLM-specific, passed
  through ``extra_body``).
"""

from __future__ import annotations

import json
import re
import time

import ollama

from .config import settings
from .retriever import RetrievedChunk

SYSTEM_PROMPT = """Du bist der Angebot-Assistent eines Post-Production-Studios. Du beantwortest
Fragen zu früheren Angeboten des Studios.

REGELN:
1. Antworte NUR auf Basis des bereitgestellten Kontexts. Erfinde keine Zahlen,
   Konditionen oder Formulierungen.
2. Jede konkrete Aussage (Preis, Datum, Zahlungsbedingung, Formulierung) muss
   einem konkreten Angebot zugeordnet sein. Zitiere inline als [AG####].
3. Vermische KEINE Daten aus verschiedenen Angeboten zu einer Antwort. Wenn du
   über mehrere Angebote vergleichst, nenne für jeden Wert das Angebot, aus dem
   er stammt.
4. Wenn die Frage ein konkretes Angebot nennt (z.B. "AG0085") und dieses NICHT
   im Kontext ist: sage das klar ("AG0085 wurde nicht gefunden") und antworte
   nicht spekulativ.
5. Wenn der Kontext die Frage nicht beantwortet: lehne ab in einem Satz
   ("Das steht in den vorliegenden Angeboten nicht.") — keine Schätzung.
6. Wenn die Frage mehrdeutig ist (z.B. "Wie hoch war der Preis?" ohne
   Angebotsbezug): antworte NICHT. Stelle stattdessen eine kurze Rückfrage und
   liste die Kandidaten aus dem Kontext auf, z.B.:
   "Meinst du eines dieser Angebote? AG0085 (01.05.2026, 5.844,52 €) ·
   AG0086 (…, 8.160,80 €) · AG0090 (…, 1.251,03 €)"
7. Antworte auf Deutsch. Struktur: zuerst die direkte Antwort (1–2 Sätze),
   dann Details mit Zitaten, am Ende die Quellenliste.
8. Der Index enthält insgesamt {offer_count} Angebote. Dein Kontext zeigt nur
   die ähnlichsten Treffer — behaupte niemals, der Index enthalte nur die im
   Kontext sichtbaren Angebote.
9. Nenne Preise, Beträge oder Kosten NUR, wenn die Frage danach fragt.
   Der Gesamtbetrag eines Angebots ist kein Beleg für den Preis eines
   einzelnen Leistungspunkts — verwechsle beides nicht."""

CHAT_SYSTEM_PROMPT = """You are the Project Offer Assistant, an in-house
assistant for project-based service providers. Be friendly and concise.
Answer in the language of the user's question."""

# HyDE (Hypothetical Document Embeddings): the model writes a short passage
# in the STYLE of an offer document that could answer the question. That
# passage is embedded and used as a third RRF list — it bridges the
# user↔document vocabulary gap (retrieval failure mode #2).
HYDE_PROMPT = (
    "Schreibe einen kurzen Absatz (max. 80 Wörter), wie er in einem "
    "Post-Production-Angebot stehen könnte, um die folgende Frage zu "
    "beantworten. Nutze typische Fachbegriffe aus solchen Angeboten "
    "(z.B. Planungsrahmen, Zahlungsziel, Skonto, Lieferdateien, Codec, "
    "Farbraum, Abnahme). Erfinde keine konkreten Zahlen, Preise, Namen "
    " oder Daten. Gib nur den Absatz aus, ohne Einleitung.\n\n"
    "Frage: {question}"
)


class _OpenAICompatClient:
    """Ollama-style ``chat()`` interface on top of an OpenAI-compatible API.

    Lets the rest of the module (and the tests, which patch ``_client``)
    stay unchanged while talking to vLLM instead of Ollama.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(self, model: str, messages: list[dict], think: bool = False) -> dict:
        kwargs: dict = {}
        if not think:
            # vLLM-specific: disable Qwen3 thinking via the chat template.
            kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
        response = self._client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )
        return {"message": {"content": response.choices[0].message.content}}


def _client() -> ollama.Client | _OpenAICompatClient:
    """LLM client pointed at the configured endpoint.

    Local Ollama (``localhost`` / ``127.0.0.1``) uses the native API;
    anything else is treated as an OpenAI-compatible server (vLLM).
    ``llm_base_url`` may be an OpenAI-compatible URL (``…/v1``) — for
    Ollama the native API lives at the host root.
    """
    base_url = settings.llm_base_url.removesuffix("/v1")
    host = base_url.split("//")[-1].split("/")[0].split(":")[0]
    if host in ("localhost", "127.0.0.1", "::1"):
        return ollama.Client(host=base_url)
    return _OpenAICompatClient(settings.llm_base_url, settings.llm_api_key)


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


def hyde_passage(question: str) -> str:
    """Write a hypothetical offer-style passage for the question (HyDE).

    Returns an empty string on any failure — the caller then simply skips
    the HyDE RRF list, so a slow or broken LLM never breaks retrieval.
    """
    try:
        response = _client().chat(
            model=settings.llm_model,
            messages=[{"role": "user", "content": HYDE_PROMPT.format(question=question)}],
            think=False,
        )
        return _strip_think(response["message"]["content"] or "").strip()
    except Exception:
        return ""


def _strip_think(text: str) -> str:
    """Remove a </think> block if the model thought despite think=False."""
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()
    if "<think>" in text:
        text = text.split("<think>", 1)[0].strip()
    return text


def rerank(
    question: str,
    candidates: list[RetrievedChunk],
    keep: int | None = None,
) -> list[RetrievedChunk]:
    """LLM rerank: score each candidate 0–10 for how well it ANSWERS the query.

    Ported from rag-pipeline.ipynb (DaVinci variant, with retry loop).
    Returns the top-``keep`` candidates sorted by rerank score (desc);
    each chunk gets ``rerank_score`` set and its ``score`` updated.
    """
    keep = keep or settings.top_k
    if not candidates:
        return []

    # Chunks can be ~4k chars; key facts (e.g. payment terms) often sit far
    # into the text, so keep a generous window for the rerank model.
    numbered = "\n\n".join(
        f"[{i}] {c.text[:2000]}" for i, c in enumerate(candidates, start=1)
    )
    prompt = (
        "Given the query, score each passage 0-10 for how well it ANSWERS the "
        "query. If the query has several parts, a passage that fully answers "
        "ANY one part deserves a high score. "
        "Return ONLY a JSON object mapping passage number to score.\n\n"
        f"Query: {question}\n\nPassages:\n{numbered}"
    )
    messages = [
        {"role": "system", "content": "You are a precise ranking engine. Output JSON only."},
        {"role": "user", "content": prompt},
    ]

    scores: dict[int, float] = {}
    for attempt in range(3):
        try:
            response = _client().chat(
                model=settings.llm_model, messages=messages, think=False
            )
            text = _strip_think(response["message"]["content"] or "")
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match:
                raw = json.loads(match.group(0))
                scores = {int(k): float(v) for k, v in raw.items()}
                break
        except Exception:
            pass
        time.sleep(0.5 * (attempt + 1))

    if not scores:
        # Rerank failed — fall back to retrieval order
        return candidates[:keep]

    for i, chunk in enumerate(candidates, start=1):
        chunk.rerank_score = scores.get(i, 0.0)
        chunk.score = chunk.rerank_score
    ranked = sorted(candidates, key=lambda c: c.rerank_score or 0.0, reverse=True)
    return ranked[:keep]


def _format_price(value) -> str:
    """Format a net price for the facts block (German number format)."""
    if value is None:
        return "—"
    return f"{value:,.2f} €".replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")


_PRICE_WORDS = (
    "preis", "preise", "kosten", "kostet", "betrag", "beträgt", "betrage",
    "euro", "€", "summe", "honorar", "satz", "tatsachen", "rechnungsbetrag",
)


def question_asks_about_price(question: str) -> bool:
    """True if the question is about prices, costs or amounts.

    The facts block only includes the total offer price in that case —
    otherwise the model is tempted to quote totals the user never asked
    for (and to confuse the offer total with a line-item price).
    """
    q = question.lower()
    return any(word in q for word in _PRICE_WORDS)


def _facts_block(chunks: list[RetrievedChunk], question: str) -> str:
    """Structured per-offer facts for the answer prompt.

    The total offer price is only included when the question is about
    prices — otherwise it is noise that the model may quote or confuse
    with line-item prices.
    """
    facts: list[str] = []
    seen: set[str] = set()
    include_price = question_asks_about_price(question)
    for chunk in chunks:
        if chunk.source in seen:
            continue
        seen.add(chunk.source)
        meta = chunk.metadata
        line = f"- {chunk.source}: datum={meta.get('datum') or '—'}"
        if include_price:
            line += f", preis={_format_price(meta.get('preis'))}"
        facts.append(line)
    return "\n".join(facts) if facts else "(keine strukturierten Daten)"


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    offer_count: int | None = None,
) -> str:
    """Generate a grounded answer for the question from retrieved chunks.

    The model receives, in order: structured facts for the retrieved offers
    (from metadata, not from the model's reading of the text), then the
    numbered chunks, then the question (handoff §3.1).

    ``offer_count`` is the total number of offers in the index — injected
    into the system prompt so the model does not claim the index only
    contains the chunks visible in its context.
    """
    facts_block = _facts_block(chunks, question)

    context = "\n\n".join(
        f"[{i}] ({chunk.source}, score {chunk.score:.2f})\n{chunk.text}"
        for i, chunk in enumerate(chunks, start=1)
    )
    system_prompt = SYSTEM_PROMPT.format(
        offer_count=offer_count if offer_count else "eine große Zahl"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Strukturierte Daten der Treffer:\n{facts_block}\n\n"
                f"Kontext:\n{context}\n\n"
                f"Frage: {question}"
            ),
        },
    ]
    return chat(messages)
