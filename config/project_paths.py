"""
project_paths.py
================
Single source of truth for where "Grounded" keeps its heavy artifacts.

WHY THIS FILE EXISTS
--------------------
The C: drive on this machine is nearly full, while D: has plenty of room.
To avoid ever filling C: again, ALL large, regenerable artifacts live on D::
  * downloaded AI models (HuggingFace cache: embeddings, re-ranker, NLI)
  * the local LLM models (Ollama)
  * the ChromaDB vector store

Importing this module (and calling apply_env()) points the relevant libraries
at D: BEFORE they are first used. The notebook calls this in its setup cell,
so the redirect is reproducible and self-documenting — not hidden machine state.

None of these paths hold anything irreplaceable: models re-download, the vector
store rebuilds from the PDFs. The real source data (PDFs) stays in the repo.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---- The roomy drive where heavy, regenerable data lives -------------------
# Portable: defaults to D: on this machine, but any environment (e.g. a Linux CI
# runner where D:\ does not exist) can override via GROUNDED_CACHE_ROOT.
CACHE_ROOT = Path(os.environ.get("GROUNDED_CACHE_ROOT", r"D:\grounded_rag_cache"))

# HuggingFace model cache (sentence-transformers embeddings, cross-encoder, NLI)
HF_HOME = CACHE_ROOT / "huggingface"

# Local LLM (Ollama) model store — used in Phase 3 for offline generation
OLLAMA_MODELS = CACHE_ROOT / "ollama"

# ChromaDB persistent vector store (rebuildable from the corpus)
CHROMA_DIR = CACHE_ROOT / "chroma_store"

# ---- Repository-relative paths (these DO live with the code) ---------------
REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = REPO_ROOT / "regulatory_corpus"
EVALUATION_DIR = REPO_ROOT / "evaluation"
PROMPTS_DIR = REPO_ROOT / "prompts"

# Precomputed corpus embeddings committed WITH the repo (small, ~1.9 MB) so the
# cloud demo can build the retriever instantly without recomputing on cold start.
REPO_EMBEDDINGS = REPO_ROOT / "corpus_embeddings.npy"


def apply_env() -> dict:
    """
    Ensure the cache folders exist and point the ML libraries at D: by setting
    the environment variables they read on import. Returns a small summary dict
    so the notebook can print exactly where things will be stored.

    IMPORTANT: call this BEFORE importing sentence_transformers / transformers,
    because those libraries read these variables at import time.
    """
    for p in (HF_HOME, OLLAMA_MODELS, CHROMA_DIR):
        p.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(HF_HOME)
    os.environ["HF_HUB_CACHE"] = str(HF_HOME / "hub")
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(HF_HOME)
    os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS)

    return {
        "HF_HOME": os.environ["HF_HOME"],
        "OLLAMA_MODELS": os.environ["OLLAMA_MODELS"],
        "CHROMA_DIR": str(CHROMA_DIR),
        "CORPUS_DIR": str(CORPUS_DIR),
    }


if __name__ == "__main__":
    from pprint import pprint
    pprint(apply_env())
