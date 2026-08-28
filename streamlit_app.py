"""Streamlit frontend for the Project Offer Assistant.

Run with:  streamlit run streamlit_app.py   (or: make run)

The app is a thin UI layer — all RAG logic lives in src/rag_system/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rag_system.config import settings
from rag_system.llm import chat
from rag_system.query import QueryResult, format_price, run_query
from rag_system.retriever import Retriever

st.set_page_config(page_title="Project Offer Assistant™", page_icon="📄", layout="wide")

# --- Cached resources (survive Streamlit re-execution) -----------------------


@st.cache_resource
def get_retriever() -> Retriever:
    """Load the persistent index once per app session."""
    return Retriever()


retriever = get_retriever()

# --- Chat state ---------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": ..., "content": ...}


def ask(question: str) -> None:
    """Answer one question — via RAG if an index exists, else plain chat."""
    if retriever.is_available:
        result: QueryResult = run_query(retriever, question)
        st.session_state.last_result = result
        st.session_state.clarify_question = (
            question if result.type == "clarify" else None
        )
    else:
        # Fallback: plain chat while no index has been built yet
        result = QueryResult(
            type="answer", route="Chat", content=chat(st.session_state.messages)
        )
        st.session_state.last_result = result
        st.session_state.clarify_question = None
    st.session_state.messages.append(
        {"role": "assistant", "content": result.content, "route": result.route}
    )


def _format_candidate(c: dict) -> str:
    """Chip label: AG#### · datum · preis."""
    preis = f" · {format_price(c['preis'])}" if c.get("preis") else ""
    return f"{c['angebot_id']} · {c['datum']}" + preis


# --- UI -----------------------------------------------------------------------

st.title("📄 Project Offer Assistant™")
st.caption("Your in-house offer history as a RAG database — no cloud, no per-token costs.")

with st.sidebar:
    st.header("Status")
    if retriever.is_available:
        st.success(
            f"Index loaded: `{settings.chroma_collection}` "
            f"({retriever.offer_count} offers)"
        )
    else:
        st.warning("No index found. Build it first: `make index`")
    st.divider()
    st.caption(
        f"LLM: `{settings.llm_model}` @ `{settings.llm_base_url}`  \n"
        f"Embeddings: `{settings.embed_model}`  \n"
        f"Top-k: {settings.top_k}"
    )

# Render conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("route"):
            st.caption(f"Route: **{message['route']}**")

# Show citations of the last answer
last_result = st.session_state.get("last_result")
if last_result and last_result.chunks:
    with st.expander(f"Sources ({len(last_result.chunks)})"):
        for i, chunk in enumerate(last_result.chunks, start=1):
            st.markdown(f"**{i}. {chunk.source}** (score {chunk.score:.3f})")
            st.caption(chunk.text[:300] + ("…" if len(chunk.text) > 300 else ""))

# Clarification chips — re-ask the question with the chosen offer id
if last_result and last_result.type == "clarify" and st.session_state.get("clarify_question"):
    st.markdown("**Meinst du eines dieser Angebote?**")
    cols = st.columns(min(len(last_result.candidates), 3))
    for col, candidate in zip(cols, last_result.candidates):
        with col:
            if st.button(
                _format_candidate(candidate),
                key=f"clarify_{candidate['angebot_id']}",
                width="stretch",
            ):
                follow_up = (
                    f"{st.session_state.clarify_question} "
                    f"(gemeint ist Angebot {candidate['angebot_id']})"
                )
                st.session_state.messages.append(
                    {"role": "user", "content": follow_up}
                )
                with st.chat_message("user"):
                    st.markdown(follow_up)
                with st.chat_message("assistant"):
                    with st.spinner("Retrieving & generating…"):
                        ask(follow_up)
                st.rerun()

# Chat input
if prompt := st.chat_input("Ask about your project quotes…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Retrieving & generating…"):
            ask(prompt)
    st.rerun()
