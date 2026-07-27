"""
append_new_sections.py
======================
Adds newly-built notebook sections to the EXISTING executed notebook WITHOUT
re-running the whole thing — so already-baked outputs (and their charts) are
preserved, and any new compute-heavy cells are left for the user to run live.

How it works:
  * The builder's build_cells() is the full, ordered source of truth (no outputs).
  * The executed notebook on disk already contains the first N cells WITH outputs.
  * Since we only ever ADD cells at the end, the new cells are exactly
    build_cells()[N:]. We append those to the executed notebook and save.
"""

from __future__ import annotations

import os
import nbformat as nbf

from notebook_builder import build_cells

NB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "notebooks",
                 "Grounded_RAG_Compliance_Assistant.ipynb")
)


def _strip_trailing_empty(cells: list) -> int:
    """Remove trailing empty code cells (Jupyter auto-adds these on 'Run All')."""
    removed = 0
    while cells and cells[-1].cell_type == "code" \
            and not (("".join(cells[-1].source)
                      if isinstance(cells[-1].source, list) else cells[-1].source).strip()) \
            and not cells[-1].get("outputs"):
        cells.pop()
        removed += 1
    return removed


def main() -> None:
    existing = nbf.read(NB_PATH, as_version=4)
    stripped = _strip_trailing_empty(existing.cells)
    if stripped:
        print(f"Stripped {stripped} trailing empty code cell(s).")
    n_existing = len(existing.cells)

    full = build_cells()
    n_full = len(full)

    if n_full <= n_existing:
        print(f"No new cells to append (existing={n_existing}, builder={n_full}).")
        return

    new_cells = full[n_existing:]
    existing.cells.extend(new_cells)
    nbf.write(existing, NB_PATH)
    print(f"Appended {len(new_cells)} new cell(s): {n_existing} -> {len(existing.cells)} total.")
    print("Earlier executed outputs preserved; new cells are unexecuted (for you to run).")


if __name__ == "__main__":
    main()
