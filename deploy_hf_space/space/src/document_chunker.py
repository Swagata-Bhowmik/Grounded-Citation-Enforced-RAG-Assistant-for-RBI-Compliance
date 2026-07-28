"""
document_chunker.py
===================
Turns the raw RBI PDFs into small, page-tagged text chunks ready for embedding.

DESIGN CHOICES (defensible line-by-line)
----------------------------------------
1. PAGE-LEVEL PROVENANCE. We extract text page by page with PyMuPDF and tag every
   chunk with its exact 1-indexed page number. This is what makes "page-level
   citation enforcement" real: a retrieved chunk always knows which page it came
   from, in which document.

2. TOKEN-BASED SIZING IN THE EMBEDDER'S OWN TOKENS. Chunk size is measured with
   the tokenizer of the embedding model we will actually use
   (BAAI/bge-small-en-v1.5, hard limit 512 tokens). Measuring in *its* tokens
   guarantees no chunk is silently truncated at embedding time.

3. STRUCTURE-AWARE SPLITTING. RecursiveCharacterTextSplitter tries to break on
   natural boundaries first (paragraph -> line -> sentence -> word), so chunks
   stay coherent instead of being cut mid-word.

4. OVERLAP. Consecutive chunks share some tokens so an idea sitting on a chunk
   boundary is not lost to retrieval.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_MODEL_TOKEN_LIMIT = 512  # bge-small hard cap; chunks must stay under this

# Minimum characters for a page's text to be worth chunking (skips blank/divider
# pages such as the "Withdrawn"/"Deleted" pages found during profiling).
MIN_PAGE_CHARS = 40


def get_tokenizer(model_name: str = EMBED_MODEL_NAME):
    """Load the embedding model's tokenizer (downloads once to the D: HF cache)."""
    return AutoTokenizer.from_pretrained(model_name)


def _make_splitter(tokenizer, chunk_tokens: int, overlap_tokens: int):
    """Build a splitter whose length is counted in the embedder's tokens."""
    return RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=chunk_tokens,
        chunk_overlap=overlap_tokens,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_corpus(
    corpus_dir: str,
    chunk_tokens: int = 384,
    overlap_tokens: int = 64,
    tokenizer=None,
) -> list[dict]:
    """
    Chunk every PDF in `corpus_dir`, page by page.

    Returns a list of chunk dicts, each with:
      chunk_id, source_file, page (1-indexed), text, token_count
    """
    if tokenizer is None:
        tokenizer = get_tokenizer()
    splitter = _make_splitter(tokenizer, chunk_tokens, overlap_tokens)

    chunks: list[dict] = []
    for pdf_path in sorted(Path(corpus_dir).glob("*.pdf")):
        doc = fitz.open(str(pdf_path))
        for page_index in range(doc.page_count):
            page_text = (doc[page_index].get_text("text") or "").strip()
            if len(page_text) < MIN_PAGE_CHARS:
                continue  # skip blank / divider pages
            for piece in splitter.split_text(page_text):
                piece = piece.strip()
                if not piece:
                    continue
                n_tokens = len(tokenizer.encode(piece, add_special_tokens=False))
                chunks.append(
                    {
                        "chunk_id": f"{pdf_path.stem}__p{page_index + 1}__c{len(chunks)}",
                        "source_file": pdf_path.name,
                        "page": page_index + 1,
                        "text": piece,
                        "token_count": n_tokens,
                    }
                )
        doc.close()
    return chunks


def experiment_chunk_sizes(
    corpus_dir: str,
    configs: list[tuple[int, int]],
    tokenizer=None,
) -> pd.DataFrame:
    """
    Try several (chunk_tokens, overlap_tokens) settings and summarize each:
    number of chunks, average/median/max tokens per chunk, and how many chunks
    would exceed the embedder's 512-token limit (should be zero).
    """
    if tokenizer is None:
        tokenizer = get_tokenizer()

    rows = []
    for chunk_tokens, overlap_tokens in configs:
        chunks = chunk_corpus(
            corpus_dir, chunk_tokens, overlap_tokens, tokenizer=tokenizer
        )
        tok = pd.Series([c["token_count"] for c in chunks])
        rows.append(
            {
                "chunk_tokens": chunk_tokens,
                "overlap_tokens": overlap_tokens,
                "n_chunks": len(chunks),
                "avg_tokens": round(tok.mean(), 1),
                "median_tokens": int(tok.median()),
                "max_tokens": int(tok.max()),
                "over_512": int((tok > EMBED_MODEL_TOKEN_LIMIT).sum()),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "regulatory_corpus"
    tk = get_tokenizer()
    print("Tokenizer loaded:", EMBED_MODEL_NAME)

    exp = experiment_chunk_sizes(
        target, configs=[(256, 40), (384, 64), (480, 80)], tokenizer=tk
    )
    print("\n--- Chunk-size experiment ---")
    print(exp.to_string(index=False))

    chosen = chunk_corpus(target, 384, 64, tokenizer=tk)
    print(f"\nChosen config (384/64): {len(chosen)} chunks")
    print("\nExample chunk:")
    ex = chosen[50]
    print(f"  id   : {ex['chunk_id']}")
    print(f"  file : {ex['source_file']}  (page {ex['page']})")
    print(f"  toks : {ex['token_count']}")
    print(f"  text : {ex['text'][:300]}...")
