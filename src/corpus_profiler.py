"""
corpus_profiler.py
------------------
Profiles the raw RBI PDF corpus BEFORE any chunking/embedding is built.

Why this exists (the "data is sacred" rule):
A PDF's file size only proves the download finished. It does NOT prove the text
is extractable. A scanned/image-only PDF has ~0 selectable characters and would
silently poison a RAG system. This module inspects every page of every document
and reports, per file:
  - page count
  - total extracted characters (PyMuPDF)
  - average characters per page (text density)
  - number of "low-text" pages (< 100 chars -> possible scanned/image page)
  - embedded PDF metadata (title / author / creation date)
  - a multi-column heuristic (via pdfplumber word x-positions)

It returns a pandas DataFrame so the notebook can display + visualize it.
"""

from __future__ import annotations

import os
from pathlib import Path

import fitz  # PyMuPDF: fast, page-level text extraction (great for page citations)
import pdfplumber  # good at word-level x/y positions -> column-layout detection
import pandas as pd

# A page with fewer than this many extracted characters is flagged as "low-text"
# (a strong hint it may be a scanned image rather than real, selectable text).
LOW_TEXT_PAGE_THRESHOLD = 100


def _detect_multicolumn(pdf_path: str, sample_pages: int = 5) -> bool:
    """
    Heuristic: on a few sample pages, look at the horizontal (x) center of each word.
    If words cluster into two clearly separated bands across the page width, the
    page is likely two-column. Regulatory PDFs are usually single-column, but we
    check because multi-column text extraction can scramble reading order.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = pdf.pages[:sample_pages]
            two_col_votes = 0
            for page in pages_to_check:
                width = page.width or 1
                words = page.extract_words() or []
                if len(words) < 20:
                    continue
                # x-center of each word as a fraction of page width (0..1)
                centers = [((w["x0"] + w["x1"]) / 2.0) / width for w in words]
                left = sum(1 for c in centers if c < 0.45)
                right = sum(1 for c in centers if c > 0.55)
                middle = sum(1 for c in centers if 0.45 <= c <= 0.55)
                # Two dense side-bands + a sparse middle gutter => likely two columns
                if left > 0 and right > 0 and middle < 0.15 * len(centers) \
                        and min(left, right) > 0.25 * len(centers):
                    two_col_votes += 1
            return two_col_votes >= max(1, len(pages_to_check) // 2)
    except Exception:
        # If pdfplumber struggles on a file, don't crash the whole profile.
        return False


def profile_pdf(pdf_path: str) -> dict:
    """Profile a single PDF and return a dict of quality metrics."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata or {}

    total_chars = 0
    low_text_pages = 0
    page_count = doc.page_count

    for page in doc:
        text = page.get_text("text") or ""
        n = len(text.strip())
        total_chars += n
        if n < LOW_TEXT_PAGE_THRESHOLD:
            low_text_pages += 1

    doc.close()

    avg_chars = round(total_chars / page_count, 1) if page_count else 0.0

    return {
        "file": os.path.basename(pdf_path),
        "pages": page_count,
        "total_chars": total_chars,
        "avg_chars_per_page": avg_chars,
        "low_text_pages": low_text_pages,
        "multicolumn": _detect_multicolumn(pdf_path),
        "pdf_title": (meta.get("title") or "").strip()[:60],
        "created": (meta.get("creationDate") or "").strip()[:16],
    }


def profile_corpus(corpus_dir: str) -> pd.DataFrame:
    """Profile every *.pdf in a directory and return a sorted DataFrame."""
    pdf_paths = sorted(Path(corpus_dir).glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in: {corpus_dir}")
    rows = [profile_pdf(str(p)) for p in pdf_paths]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    # Quick manual run: python src/corpus_profiler.py <corpus_dir>
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "regulatory_corpus"
    df = profile_corpus(target)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 160)
    print(df.to_string(index=False))
    print("\n--- Corpus totals ---")
    print(f"Documents        : {len(df)}")
    print(f"Total pages      : {int(df['pages'].sum())}")
    print(f"Total characters : {int(df['total_chars'].sum()):,}")
    print(f"Docs with low-text pages : {int((df['low_text_pages'] > 0).sum())}")
    print(f"Multi-column docs        : {int(df['multicolumn'].sum())}")
