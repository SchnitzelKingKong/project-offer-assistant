"""Build the persistent vector index from the documents in data/.

Usage:  python scripts/build_index.py   (or: make index)

Pipeline: load PDFs → chunk (SentenceSplitter) → embed (nomic-embed-text)
→ persist to ChromaDB in index_storage/.

The index is built ONCE; the app only reloads it.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make src/ importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag_system.config import settings  # noqa: E402


def main() -> None:
    data_dir = Path(settings.data_dir)
    if not data_dir.is_dir() or not any(data_dir.iterdir()):
        print(f"No documents found in `{data_dir}/` — nothing to index.")
        print("Add PDFs there first, then re-run.")
        return

    # TODO:
    # 1. Load documents (SimpleDirectoryReader / PyMuPDF)
    # 2. Chunk (SentenceSplitter, chunk_size=2000, chunk_overlap=400)
    # 3. Embed (nomic-embed-text via Ollama)
    # 4. Persist to ChromaDB (settings.index_dir, settings.chroma_collection)
    raise NotImplementedError("Index building not implemented yet")


if __name__ == "__main__":
    main()
