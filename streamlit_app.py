"""Streamlit frontend for the Project Offer Assistant.

Run with:  streamlit run streamlit_app.py   (or: make run)

The app is a thin UI layer — all RAG logic lives in src/rag_system/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rag_system.citation_markup import render_answer_html
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
    # Defensive: a stale browser tab can hit a fresh server session where
    # the top-level initialization did not run for this execution.
    st.session_state.setdefault("messages", [])
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


# --- Offer detail panel -------------------------------------------------------


@st.cache_data
def _offer(angebot_id: str) -> dict | None:
    """Cached offer details (header data + full text) for the panel."""
    return retriever.get_offer(angebot_id)


def _text_to_markdown(text: str) -> str:
    """Convert plain offer text to markdown, preserving line breaks.

    Markdown collapses single newlines, so each line gets two trailing
    spaces (hard break); blank lines stay paragraph separators.
    """
    paragraphs = []
    for block in text.split("\n\n"):
        lines = [line.rstrip() for line in block.split("\n")]
        paragraphs.append("  \n".join(lines))
    return "\n\n".join(paragraphs)


# --- Inline citation component (CCv2) ----------------------------------------
# Renders the answer markdown as HTML where every [AG####] is a clickable,
# highlighted chip. Clicks are reported back via a trigger and open the
# offer panel.

_ANSWER_HTML = """<div id="root"></div>"""

_ANSWER_CSS = """
#root {
  font-size: inherit;
  line-height: 1.6;
  color: var(--st-text-color, inherit);
}
#root p { margin: 0 0 0.6em 0; }
#root ul, #root ol { margin: 0 0 0.6em 0; padding-left: 1.4em; }
#root li { margin: 0.15em 0; }
.cite-chip {
  display: inline-block;
  padding: 0 6px;
  margin: 0 1px;
  border-radius: 6px;
  background: var(--st-secondary-background-color, #e8f0fe);
  color: var(--st-primary-color, #1a73e8);
  font-weight: 600;
  font-size: 0.85em;
  text-decoration: none;
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
}
.cite-chip:hover {
  border-color: var(--st-primary-color, #1a73e8);
  text-decoration: underline;
}
"""

_ANSWER_JS = """
export default function (component) {
  const { data, parentElement, setTriggerValue } = component
  const root = parentElement.querySelector("#root")
  if (!root) return
  root.innerHTML = (data && data.html) || ""
  root.querySelectorAll("a.cite-chip").forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault()
      setTriggerValue("clicked", a.getAttribute("data-offer"))
    })
  })
}
"""

_answer_view = st.components.v2.component(
    "answer_with_citations",
    html=_ANSWER_HTML,
    css=_ANSWER_CSS,
    js=_ANSWER_JS,
)


def _render_answer(message_index: int, content: str) -> None:
    """Render one assistant answer with clickable inline citations."""
    result = _answer_view(
        key=f"answer_{message_index}",
        data={"html": render_answer_html(content)},
        on_clicked_change=lambda: None,
    )
    if result.clicked:
        st.session_state.selected_offer = result.clicked
        st.rerun()


def _render_offer_panel() -> None:
    """Right-hand panel showing the full text of the selected offer."""
    st.subheader("Angebot")
    selected = st.session_state.get("selected_offer")
    if not selected:
        st.caption(
            "Klicke auf eine zitierte Citation im Antworttext, um das "
            "vollständige Angebot zu sehen."
        )
        return
    offer = _offer(selected)
    if offer is None:
        st.warning(f"Angebot {selected} wurde im Index nicht gefunden.")
        return
    preis = f" · {format_price(offer['preis'])}" if offer.get("preis") else ""
    st.markdown(f"### 📄 {offer['angebot_id']}")
    st.caption(f"{offer['datum']}{preis}")
    with st.container(height=620):
        st.markdown(_text_to_markdown(offer["text"]))
    st.caption(
        "Quelle: "
        + (
            "redigierter Volltext"
            if offer["text_source"] == "file"
            else "Index-Chunks"
        )
    )
    if st.button("Schließen", key="close_offer_panel"):
        st.session_state.selected_offer = None
        st.rerun()


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

chat_col, panel_col = st.columns([3, 2], gap="large")

with chat_col:
    # Render conversation history
    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                _render_answer(message_index, message["content"])
            else:
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
    if (
        last_result
        and last_result.type == "clarify"
        and st.session_state.get("clarify_question")
    ):
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
        st.session_state.setdefault("messages", [])
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving & generating…"):
                ask(prompt)
        st.rerun()

with panel_col:
    _render_offer_panel()
