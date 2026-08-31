#!/usr/bin/env python3
"""Scrub local-environment details from notebook outputs before committing.

Notebook outputs are committed (they are part of the demo), but they are
generated on a local machine and can leak environment details:

- absolute local paths (``/Users/.../rag-system-for-quote-history/...``)
- the internal LLM/embedding endpoint host (``*.thdi.cc``)
- any other ``/Users/<name>/...`` path that is not inside this repo

This script rewrites the OUTPUTS of all ``notebooks/*.ipynb`` in place:

- ``<repo-root>/<subpath>``  ->  ``<repo-name>/<subpath>`` (repo-relative)
- ``/Users/<name>/...``      ->  ``<HOME>/...`` (outside the repo)
- ``https://<host>.thdi.cc`` ->  ``https://<INTERNAL-HOST>``

Cell *sources* are never touched — only ``outputs`` (stream text,
``text/plain`` data, error tracebacks).

Usage (from the repo root):

    python scripts/scrub_notebook_outputs.py            # scrub in place
    python scripts/scrub_notebook_outputs.py --check     # report only,
                                                         # exit 1 if found

Run this before every commit that includes notebook changes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_NAME = REPO_ROOT.name
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"

# Order matters: repo paths first, then generic /Users/, then hosts, then URLs.
REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    # Absolute repo path -> repo-relative ("rag-system-for-quote-history/.env")
    (re.compile(re.escape(str(REPO_ROOT)) + r"(?=/|$)"), REPO_NAME),
    # Any other local home path -> <HOME>
    (re.compile(r"/Users/[A-Za-z0-9._-]+(?=/|$)"), "<HOME>"),
    # Internal host (vLLM / embedding endpoints)
    (re.compile(r"[a-z0-9-]+\.thdi\.cc"), "<INTERNAL-HOST>"),
    # Any remaining URL (defensive; the host rule above already covers ours)
    (re.compile(r"https?://[^\s\"'\\)]+"), "<URL>"),
]

# Patterns used by --check to decide whether a line is sensitive.
CHECK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"/Users/"),
    re.compile(r"thdi\.cc"),
]


def scrub_text(text: str) -> str:
    for pattern, replacement in REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


def _scrub_value(value):
    """Scrub a text field (str or list of str). Returns (new_value, changed)."""
    if isinstance(value, str):
        new = scrub_text(value)
        return new, new != value
    if isinstance(value, list):
        new_list, changed = [], False
        for item in value:
            if isinstance(item, str):
                new_item = scrub_text(item)
                changed = changed or (new_item != item)
                new_list.append(new_item)
            else:
                new_list.append(item)
        return new_list, changed
    return value, False


def scrub_cell(cell: dict) -> int:
    """Scrub one cell's outputs. Returns the number of changed fields."""
    changed = 0
    for out in cell.get("outputs", []):
        # stream / execute_result text
        if "text" in out:
            out["text"], did_change = _scrub_value(out["text"])
            changed += did_change
        # text/plain data (execute_result / display_data)
        data = out.get("data")
        if isinstance(data, dict) and "text/plain" in data:
            data["text/plain"], did_change = _scrub_value(data["text/plain"])
            changed += did_change
        # error tracebacks (evalue + traceback lines)
        if out.get("ename"):
            out["evalue"], did_change = _scrub_value(str(out.get("evalue", "")))
            changed += did_change
            tb = out.get("traceback")
            if isinstance(tb, list):
                new_tb, tb_changed = _scrub_value(tb)
                if tb_changed:
                    out["traceback"] = new_tb
                    changed += 1
    return changed


def iter_sensitive_lines(nb_path: Path):
    """Yield (cell_index, line) for output lines that look sensitive."""
    data = json.loads(nb_path.read_text())
    for i, cell in enumerate(data.get("cells", [])):
        for out in cell.get("outputs", []):
            texts = []
            if "text" in out:
                t = out["text"]
                texts.extend(t if isinstance(t, list) else [t])
            tp = out.get("data", {}).get("text/plain")
            if tp:
                texts.extend(tp if isinstance(tp, list) else [tp])
            if out.get("ename"):
                texts.append(str(out.get("evalue", "")))
                texts.extend(out.get("traceback", []))
            for t in texts:
                for line in t.splitlines():
                    if any(p.search(line) for p in CHECK_PATTERNS):
                        yield i, line.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="only report sensitive output lines; exit 1 if any are found",
    )
    args = parser.parse_args()

    notebooks = sorted(NOTEBOOKS_DIR.glob("*.ipynb"))
    if not notebooks:
        print(f"No notebooks found in {NOTEBOOKS_DIR}")
        return 1

    total_found = 0
    for nb in notebooks:
        if args.check:
            hits = list(iter_sensitive_lines(nb))
            total_found += len(hits)
            if hits:
                print(f"⚠️  {nb.name}: {len(hits)} sensitive output line(s)")
                for i, line in hits[:10]:
                    print(f"   cell {i}: {line[:110]}")
            else:
                print(f"✅ {nb.name}: clean")
            continue

        raw = nb.read_text()
        data = json.loads(raw)
        changed_cells = sum(scrub_cell(c) for c in data.get("cells", []))
        if changed_cells:
            nb.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            print(f"🧽 {nb.name}: scrubbed {changed_cells} output field(s)")
        else:
            print(f"✅ {nb.name}: clean")

    if args.check:
        if total_found:
            print(f"\n❌ {total_found} sensitive line(s) found — run without --check to scrub.")
            return 1
        print("\n✅ All notebook outputs are clean.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
