"""Streamlit frontend for the quote-history RAG system.

Run with:  streamlit run streamlit_app.py   (or: make run)

The app is a thin UI layer — all RAG logic lives in src/rag_system/.
"""

from __future__ import annotations

import streamlit as st

from rag_system.config import settings
from rag_system.llm import generate_answer
from rag_system.retriever import Retriever

st.set_page_config(page_title="Quote History RAG", page_icon="📄", layout="wide")

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
    """Run the RAG pipeline for one question and append the answer."""
    chunks = retriever.query(question, top_k=settings.top_k)
    answer = generate_answer(question, chunks)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.last_chunks = chunks


# --- UI -----------------------------------------------------------------------

st.title("📄 Quote History RAG")
st.caption("Self-hosted answers over your project quotes — no cloud, no per-token costs.")

with st.sidebar:
    st.header("Status")
    if retriever.is_available:
        st.success(f"Index loaded: `{settings.index_dir}`")
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

# Show citations of the last answer
if "last_chunks" in st.session_state and st.session_state.last_chunks:
    with st.expander(f"Sources ({len(st.session_state.last_chunks)})"):
        for i, chunk in enumerate(st.session_state.last_chunks, start=1):
            st.markdown(f"**{i}. {chunk.source}** (score {chunk.score:.3f})")
            st.caption(chunk.text[:300] + ("…" if len(chunk.text) > 300 else ""))

# Chat input
if prompt := st.chat_input("Ask about your project quotes…"):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Retrieving & generating…"):
            ask(prompt)
    st.rerun()
